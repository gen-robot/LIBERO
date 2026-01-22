"""
LIBERO evaluation script for VLA models.

Based on openpi/examples/libero/main.py.
Self-contained version with local openpi_client.
"""

import collections
import dataclasses
import json
import logging
import math
import pathlib

import imageio
from libero.libero import benchmark
from libero.libero import get_libero_path
from libero.libero.envs import SegmentationRenderEnv
import numpy as np
import tqdm
import tyro

from openpi_client import image_tools
from openpi_client import websocket_client_policy as _websocket_client_policy

LIBERO_DUMMY_ACTION = [0.0] * 6 + [-1.0]
LIBERO_ENV_RESOLUTION = 256


def swap_left_right(instruction: str) -> str:
    """Swap 'left' and 'right' in instruction to match 180° image rotation.
    
    Since we apply [::-1, ::-1] to images (180° rotation), objects that appear
    on the left in the original image appear on the right after rotation.
    We must apply the same transformation to language instructions.
    """
    # Use placeholder to avoid double-swap
    instruction = instruction.replace(" left ", " __LEFT__ ")
    instruction = instruction.replace(" right ", " __RIGHT__ ")
    instruction = instruction.replace(" __LEFT__ ", " right ")
    instruction = instruction.replace(" __RIGHT__ ", " left ")
    return instruction


@dataclasses.dataclass
class Args:
    # Model server parameters
    host: str = "0.0.0.0"
    port: int = 8000
    resize_size: int = 224
    replan_steps: int = 5

    # LIBERO environment-specific parameters
    task_suite_name: str = "libero_10"
    num_steps_wait: int = 10
    num_trials_per_task: int = 50

    # Whether to send ground-truth segmentation to the policy server
    enable_gt_segmentation: bool = False

    # Utils
    video_out_path: str = "data/libero/videos"
    seed: int = 7


def eval_libero(args: Args) -> None:
    np.random.seed(args.seed)

    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[args.task_suite_name]()
    num_tasks_in_suite = task_suite.n_tasks
    logging.info(f"Task suite: {args.task_suite_name}")

    pathlib.Path(args.video_out_path).mkdir(parents=True, exist_ok=True)

    if args.task_suite_name == "libero_spatial":
        max_steps = 220
    elif args.task_suite_name == "libero_object":
        max_steps = 280
    elif args.task_suite_name == "libero_goal":
        max_steps = 300
    elif args.task_suite_name == "libero_10":
        max_steps = 520
    elif args.task_suite_name == "libero_90":
        max_steps = 400
    else:
        raise ValueError(f"Unknown task suite: {args.task_suite_name}")

    client = _websocket_client_policy.WebsocketClientPolicy(args.host, args.port)

    total_episodes, total_successes = 0, 0
    for task_id in tqdm.tqdm(range(num_tasks_in_suite)):
        task = task_suite.get_task(task_id)
        initial_states = task_suite.get_task_init_states(task_id)
        env, task_description = _get_libero_env(task, LIBERO_ENV_RESOLUTION, args.seed)
        
        # Swap left/right in instruction to match 180° image rotation
        task_description = swap_left_right(task_description)

        task_episodes, task_successes = 0, 0
        for episode_idx in tqdm.tqdm(range(args.num_trials_per_task)):
            logging.info(f"\nTask: {task_description}")

            env.reset()
            action_plan = collections.deque()
            obs = env.set_init_state(initial_states[episode_idx])

            t = 0
            replay_images = []
            current_raw_text = None
            episode_text_log = []
            episode_seg_log = {}
            # Per-episode cache of segmentation metadata and current resized mask
            seg_name_to_id = None
            seg_id_to_name = None
            current_segmentation_for_server = None

            logging.info(f"Starting episode {task_episodes+1}...")
            while t < max_steps + args.num_steps_wait:
                # During dummy steps we do not record video / text / segmentation.
                if t < args.num_steps_wait:
                    obs, reward, done, info = env.step(LIBERO_DUMMY_ACTION)
                    t += 1
                    continue

                # From this point on (after dummy steps), we record segmentation and text.
                seg_items = {k: v for k, v in obs.items() if "seg" in k.lower()}
                if seg_items:
                    if not episode_seg_log:
                        episode_seg_log = {k: [] for k in seg_items}
                    for k, v in seg_items.items():
                        seg = np.array(v)
                        # Rotate segmentation by 180° to match the image rotation.
                        seg = seg[::-1, ::-1]
                        episode_seg_log[k].append(seg)

                    # Prepare a resized segmentation mask for the policy server, if requested.
                    if args.enable_gt_segmentation:
                        # Prefer the main-agent-view segmentation if available.
                        agentview_keys = [
                            k for k in seg_items.keys() if "agentview" in k.lower()
                        ]
                        if agentview_keys:
                            seg_key = sorted(agentview_keys)[0]
                        else:
                            # Fallback: deterministic but generic choice.
                            seg_key = sorted(seg_items.keys())[0]

                        seg_for_server = np.array(seg_items[seg_key])
                        # Rotate segmentation by 180° to match the RGB image rotation.
                        seg_for_server = seg_for_server[::-1, ::-1]
                        current_segmentation_for_server = _resize_segmentation_mask(
                            seg_for_server,
                            args.resize_size,
                            args.resize_size,
                        )
                    else:
                        current_segmentation_for_server = None

                img = np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])
                wrist_img = np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1])
                img = image_tools.convert_to_uint8(
                    image_tools.resize_with_pad(img, args.resize_size, args.resize_size)
                )
                wrist_img = image_tools.convert_to_uint8(
                    image_tools.resize_with_pad(wrist_img, args.resize_size, args.resize_size)
                )

                if not action_plan:
                    element = {
                        "observation/image": img,
                        "observation/wrist_image": wrist_img,
                        "observation/state": np.concatenate(
                            (
                                obs["robot0_eef_pos"],
                                _quat2axisangle(obs["robot0_eef_quat"]),
                                obs["robot0_gripper_qpos"],
                            )
                        ),
                        "prompt": str(task_description),
                    }

                    if args.enable_gt_segmentation and current_segmentation_for_server is not None:
                        # Lazily build instance-name ↔ segmentation-id mapping once per episode.
                        if seg_name_to_id is None or seg_id_to_name is None:
                            seg_name_to_id = {}
                            seg_id_to_name = {}
                            if hasattr(env, "instance_to_id"):
                                for name, seg_id in env.instance_to_id.items():
                                    seg_id = int(seg_id)
                                    seg_name_to_id[name] = seg_id
                                    # Use string keys so msgpack strict_map_key=True accepts them.
                                    seg_id_to_name[str(seg_id)] = name
                            if hasattr(env, "segmentation_robot_id") and env.segmentation_robot_id is not None:
                                robot_base_id = int(env.segmentation_robot_id)
                                # In SegmentationRenderEnv, robot pixels are typically encoded as robot_id + 1.
                                seg_id_to_name[str(robot_base_id + 1)] = "robot"

                        # Attach segmentation mask and mapping to the observation payload.
                        element["observation/gt_segmentation"] = current_segmentation_for_server.astype(
                            np.int32
                        )
                        element["observation/segmentation_instance_to_id"] = seg_name_to_id
                        element["observation/segmentation_id_to_instance"] = seg_id_to_name

                    # Receive actions (and optionally generated text) from the policy server.
                    infer_result = client.infer(element)
                    action_chunk = infer_result["actions"]
                    # Try to retrieve generated text if the server provides it.
                    raw_text = (
                        infer_result.get("generated_text")
                        or infer_result.get("text")
                        or infer_result.get("caption")
                    )
                    if raw_text is not None:
                        current_raw_text = str(raw_text)

                    assert (
                        len(action_chunk) >= args.replan_steps
                    ), f"We want to replan every {args.replan_steps} steps, but policy only predicts {len(action_chunk)} steps."
                    action_plan.extend(action_chunk[: args.replan_steps])

                # After we possibly updated current_raw_text, log generated text for this step.
                episode_text_log.append(
                    {
                        # Use evaluation-relative step index (0-based, excluding dummy steps).
                        "t": int(t - args.num_steps_wait),
                        "generated_text": current_raw_text,
                    }
                )

                # Store raw visualization frame (image only). Text overlays are handled offline.
                replay_images.append(img)

                action = action_plan.popleft()

                obs, reward, done, info = env.step(action.tolist())
                if done:
                    task_successes += 1
                    total_successes += 1
                    break
                t += 1

            task_episodes += 1
            total_episodes += 1

            suffix = "success" if done else "failure"
            # Include task_id and episode_idx in filename so each episode gets its own video.
            # Do not truncate the task description in the filename.
            task_segment = task_description.replace(" ", "_")
            video_path = pathlib.Path(args.video_out_path) / (
                f"rollout_task{task_id:02d}_ep{episode_idx:02d}_{task_segment}_{suffix}.mp4"
            )
            imageio.mimwrite(
                video_path,
                [np.asarray(x) for x in replay_images],
                fps=60,
            )

            # Build segmentation id ↔ instance name mapping from the environment, if available.
            seg_name_to_id = {}
            seg_id_to_name = {}
            if hasattr(env, "instance_to_id"):
                for name, seg_id in env.instance_to_id.items():
                    seg_name_to_id[name] = int(seg_id)
                    seg_id_to_name[int(seg_id)] = name
            # Optionally include robot id mapping for completeness.
            if hasattr(env, "segmentation_robot_id") and env.segmentation_robot_id is not None:
                robot_base_id = int(env.segmentation_robot_id)
                # In SegmentationRenderEnv, robot pixels are typically encoded as robot_id + 1.
                seg_id_to_name[robot_base_id + 1] = "robot"

            # Save generated text log for this episode as JSON (aligned with video filename).
            text_log_path = video_path.with_suffix(".json")
            with text_log_path.open("w", encoding="utf-8") as f:
                json.dump(
                    {
                        "task_id": task_id,
                        "episode_idx": episode_idx,
                        "task_description": task_description,
                         "segmentation_instance_to_id": seg_name_to_id,
                         "segmentation_id_to_instance": seg_id_to_name,
                        "steps": episode_text_log,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            # Save segmentation ground-truth for this episode, if available.
            if episode_seg_log:
                seg_arrays = {k: np.stack(v, axis=0) for k, v in episode_seg_log.items()}
                seg_path = video_path.with_suffix(".segmentation.npz")
                np.savez_compressed(seg_path, **seg_arrays)

            logging.info(f"Success: {done}")
            logging.info(f"# episodes completed so far: {total_episodes}")
            logging.info(f"# successes: {total_successes} ({total_successes / total_episodes * 100:.1f}%)")

        logging.info(f"Current task success rate: {float(task_successes) / float(task_episodes)}")
        logging.info(f"Current total success rate: {float(total_successes) / float(total_episodes)}")

    logging.info(f"Total success rate: {float(total_successes) / float(total_episodes)}")
    logging.info(f"Total episodes: {total_episodes}")


def _get_libero_env(task, resolution, seed):
    """Initializes and returns the LIBERO environment, along with the task description."""
    task_description = task.language
    task_bddl_file = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    # Use SegmentationRenderEnv so we can access segmentation ground-truth if needed.
    env = SegmentationRenderEnv(
        bddl_file_name=task_bddl_file,
        camera_heights=resolution,
        camera_widths=resolution,
    )
    env.seed(seed)
    return env, task_description


def _resize_segmentation_mask(seg, target_h, target_w):
    """Resize a 2D segmentation mask to (target_h, target_w) using nearest-neighbor sampling.

    This keeps label ids intact while roughly matching the policy image resolution.
    """
    seg = np.asarray(seg)
    # Some envs return masks as (H, W, 1); squeeze the last dim in that case.
    if seg.ndim == 3 and seg.shape[-1] == 1:
        seg = seg[..., 0]
    if seg.ndim != 2:
        raise ValueError(f"Expected 2D segmentation mask, got shape {seg.shape}")

    h, w = seg.shape
    if h == target_h and w == target_w:
        return seg

    # Nearest-neighbor resize implemented via index sampling.
    y_idx = (np.linspace(0, h - 1, target_h)).astype(np.int64)
    x_idx = (np.linspace(0, w - 1, target_w)).astype(np.int64)
    return seg[y_idx][:, x_idx]


def _quat2axisangle(quat):
    """
    Copied from robosuite: https://github.com/ARISE-Initiative/robosuite/blob/eafb81f54ffc104f905ee48a16bb15f059176ad3/robosuite/utils/transform_utils.py#L490C1-L512C55
    """
    if quat[3] > 1.0:
        quat[3] = 1.0
    elif quat[3] < -1.0:
        quat[3] = -1.0

    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)

    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tyro.cli(eval_libero)
