"""
Parallel LIBERO evaluation script for VLA models.

Spawns multiple worker processes to run episodes in parallel.
All workers connect to the same policy server.

Usage:
    python eval_parallel.py --args.task-suite-name libero_10 --args.num-workers 8
"""

import collections
import dataclasses
import json
import logging
import math
import multiprocessing as mp
import os
import pathlib
import queue
import time
from typing import Dict, List, Optional, Tuple

import imageio
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
    instruction = instruction.replace(" left ", " __LEFT__ ")
    instruction = instruction.replace(" right ", " __RIGHT__ ")
    instruction = instruction.replace(" __LEFT__ ", " right ")
    instruction = instruction.replace(" __RIGHT__ ", " left ")
    return instruction


# Max steps per task suite
MAX_STEPS = {
    "libero_spatial": 220,
    "libero_object": 280,
    "libero_goal": 300,
    "libero_10": 520,
    "libero_90": 400,
}


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

    # Parallel execution
    num_workers: int = 4

    # Utils
    video_out_path: str = "data/libero/videos"
    seed: int = 7
    save_video: bool = True


@dataclasses.dataclass
class EpisodeResult:
    """Result of a single episode evaluation."""
    task_id: int
    episode_idx: int
    task_description: str
    success: bool
    num_steps: int
    video_path: Optional[str] = None


def quat2axisangle(quat: np.ndarray) -> np.ndarray:
    """Convert quaternion to axis-angle representation."""
    if quat[3] > 1.0:
        quat[3] = 1.0
    elif quat[3] < -1.0:
        quat[3] = -1.0

    den = np.sqrt(1.0 - quat[3] * quat[3])
    if math.isclose(den, 0.0):
        return np.zeros(3)

    return (quat[:3] * 2.0 * math.acos(quat[3])) / den


def run_episode(
    task_id: int,
    episode_idx: int,
    task_suite_name: str,
    host: str,
    port: int,
    resize_size: int,
    replan_steps: int,
    num_steps_wait: int,
    seed: int,
    video_out_path: str,
    save_video: bool,
    worker_id: int,
) -> EpisodeResult:
    """Run a single episode and return the result.
    
    This function is called by worker processes.
    Each call creates its own env and policy client.
    """
    # Import here to avoid issues with multiprocessing
    from libero.libero import benchmark, get_libero_path
    from libero.libero.envs import SegmentationRenderEnv

    # Get task info
    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[task_suite_name]()
    task = task_suite.get_task(task_id)
    initial_states = task_suite.get_task_init_states(task_id)
    
    # Create environment
    task_description = task.language
    
    # Swap left/right in instruction to match 180° image rotation
    task_description = swap_left_right(task_description)
    
    task_bddl_file = pathlib.Path(get_libero_path("bddl_files")) / task.problem_folder / task.bddl_file
    env = SegmentationRenderEnv(
        bddl_file_name=str(task_bddl_file),
        camera_heights=LIBERO_ENV_RESOLUTION,
        camera_widths=LIBERO_ENV_RESOLUTION,
    )
    env.seed(seed + worker_id)  # Different seed per worker for variety
    
    # Connect to policy server
    client = _websocket_client_policy.WebsocketClientPolicy(host, port)
    
    max_steps = MAX_STEPS.get(task_suite_name, 400)
    
    # Run episode
    env.reset()
    action_plan = collections.deque()
    obs = env.set_init_state(initial_states[episode_idx])
    
    t = 0
    replay_images = []
    done = False
    current_raw_text = None
    episode_text_log: List[Dict] = []
    episode_seg_log: Dict[str, List[np.ndarray]] = {}
    
    while t < max_steps + num_steps_wait:
        # During dummy steps we do not record video / text / segmentation.
        if t < num_steps_wait:
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

        # Preprocess images
        img = np.ascontiguousarray(obs["agentview_image"][::-1, ::-1])
        wrist_img = np.ascontiguousarray(obs["robot0_eye_in_hand_image"][::-1, ::-1])
        img = image_tools.convert_to_uint8(
            image_tools.resize_with_pad(img, resize_size, resize_size)
        )
        wrist_img = image_tools.convert_to_uint8(
            image_tools.resize_with_pad(wrist_img, resize_size, resize_size)
        )

        if not action_plan:
            element = {
                "observation/image": img,
                "observation/wrist_image": wrist_img,
                "observation/state": np.concatenate((
                    obs["robot0_eef_pos"],
                    quat2axisangle(obs["robot0_eef_quat"]),
                    obs["robot0_gripper_qpos"],
                )),
                "prompt": str(task_description),
            }

            infer_result = client.infer(element)
            action_chunk = infer_result["actions"]
            raw_text = (
                infer_result.get("generated_text")
                or infer_result.get("text")
                or infer_result.get("caption")
            )
            if raw_text is not None:
                current_raw_text = str(raw_text)

            action_plan.extend(action_chunk[:replan_steps])

        # After we possibly updated current_raw_text, log generated text for this step.
        episode_text_log.append(
            {
                # Use evaluation-relative step index (0-based, excluding dummy steps).
                "t": int(t - num_steps_wait),
                "generated_text": current_raw_text,
            }
        )

        if save_video:
            # Store raw image frames only; text overlays are handled offline.
            replay_images.append(img)

        action = action_plan.popleft()
        obs, reward, done, info = env.step(action.tolist())
        
        if done:
            break
        t += 1
    
    # Save video and logs
    video_path = None
    if save_video and replay_images:
        suffix = "success" if done else "failure"
        # Do not truncate the task description in the filename.
        task_segment = task_description.replace(" ", "_")
        video_path = pathlib.Path(video_out_path) / f"task{task_id:02d}_ep{episode_idx:02d}_{task_segment}_{suffix}.mp4"
        imageio.mimwrite(str(video_path), [np.asarray(x) for x in replay_images], fps=60)

        # Save generated text log aligned with video filename.
        # Build segmentation id ↔ instance name mapping from the environment, if available.
        seg_name_to_id: Dict[str, int] = {}
        seg_id_to_name: Dict[int, str] = {}
        if hasattr(env, "instance_to_id"):
            for name, seg_id in env.instance_to_id.items():
                seg_name_to_id[name] = int(seg_id)
                seg_id_to_name[int(seg_id)] = name
        if hasattr(env, "segmentation_robot_id") and env.segmentation_robot_id is not None:
            robot_base_id = int(env.segmentation_robot_id)
            seg_id_to_name[robot_base_id + 1] = "robot"

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

        # Save segmentation ground-truth if available.
        if episode_seg_log:
            seg_arrays = {k: np.stack(v, axis=0) for k, v in episode_seg_log.items()}
            seg_path = video_path.with_suffix(".segmentation.npz")
            np.savez_compressed(seg_path, **seg_arrays)

    env.close()
    
    return EpisodeResult(
        task_id=task_id,
        episode_idx=episode_idx,
        task_description=task_description,
        success=done,
        num_steps=t,
        video_path=video_path,
    )


def worker_fn(
    worker_id: int,
    work_queue: mp.Queue,
    result_queue: mp.Queue,
    args: Args,
):
    """Worker process function.
    
    Pulls work items from queue, runs episodes, puts results in result queue.
    """
    # Set up logging for worker
    logging.basicConfig(
        level=logging.WARNING,  # Less verbose for workers
        format=f"[Worker {worker_id}] %(message)s",
    )
    
    while True:
        try:
            work_item = work_queue.get(timeout=1.0)
        except queue.Empty:
            continue
        
        if work_item is None:  # Poison pill
            break
        
        task_id, episode_idx = work_item
        
        result = run_episode(
            task_id=task_id,
            episode_idx=episode_idx,
            task_suite_name=args.task_suite_name,
            host=args.host,
            port=args.port,
            resize_size=args.resize_size,
            replan_steps=args.replan_steps,
            num_steps_wait=args.num_steps_wait,
            seed=args.seed,
            video_out_path=args.video_out_path,
            save_video=args.save_video,
            worker_id=worker_id,
        )
        
        result_queue.put(result)


def eval_libero_parallel(args: Args) -> Dict:
    """Run parallel evaluation."""
    # Import here to get task count
    from libero.libero import benchmark
    
    benchmark_dict = benchmark.get_benchmark_dict()
    task_suite = benchmark_dict[args.task_suite_name]()
    num_tasks = task_suite.n_tasks
    
    logging.info(f"Task suite: {args.task_suite_name} ({num_tasks} tasks)")
    logging.info(f"Episodes per task: {args.num_trials_per_task}")
    logging.info(f"Total episodes: {num_tasks * args.num_trials_per_task}")
    logging.info(f"Workers: {args.num_workers}")
    
    # Create output directory
    pathlib.Path(args.video_out_path).mkdir(parents=True, exist_ok=True)
    
    # Create work queue with all (task_id, episode_idx) pairs
    work_queue = mp.Queue()
    result_queue = mp.Queue()
    
    total_work_items = 0
    for task_id in range(num_tasks):
        for episode_idx in range(args.num_trials_per_task):
            work_queue.put((task_id, episode_idx))
            total_work_items += 1
    
    # Add poison pills to stop workers
    for _ in range(args.num_workers):
        work_queue.put(None)
    
    # Start workers
    workers = []
    for worker_id in range(args.num_workers):
        p = mp.Process(
            target=worker_fn,
            args=(worker_id, work_queue, result_queue, args),
        )
        p.start()
        workers.append(p)
    
    logging.info(f"Started {args.num_workers} workers")
    
    # Collect results with progress bar
    results: List[EpisodeResult] = []
    pbar = tqdm.tqdm(total=total_work_items, desc="Episodes")
    
    completed = 0
    while completed < total_work_items:
        try:
            result = result_queue.get(timeout=60.0)
            results.append(result)
            completed += 1
            
            # Update progress bar with running stats
            successes = sum(1 for r in results if r.success)
            pbar.set_postfix({
                "success": f"{successes}/{len(results)}",
                "rate": f"{100*successes/len(results):.1f}%",
            })
            pbar.update(1)
        except queue.Empty:
            # Check if workers are still alive
            alive_workers = sum(1 for p in workers if p.is_alive())
            if alive_workers == 0:
                logging.warning("All workers died unexpectedly")
                break
    
    pbar.close()
    
    # Wait for workers to finish
    for p in workers:
        p.join(timeout=5.0)
        if p.is_alive():
            p.terminate()
    
    # Aggregate results
    task_results = {}
    for task_id in range(num_tasks):
        task_episodes = [r for r in results if r.task_id == task_id]
        if task_episodes:
            successes = sum(1 for r in task_episodes if r.success)
            task_results[task_id] = {
                "description": task_episodes[0].task_description,
                "episodes": len(task_episodes),
                "successes": successes,
                "success_rate": successes / len(task_episodes),
            }
            logging.info(
                f"Task {task_id}: {task_results[task_id]['description'][:50]} - "
                f"{successes}/{len(task_episodes)} ({100*successes/len(task_episodes):.1f}%)"
            )
    
    # Overall stats
    total_episodes = len(results)
    total_successes = sum(1 for r in results if r.success)
    overall_success_rate = total_successes / total_episodes if total_episodes > 0 else 0.0
    
    logging.info("=" * 60)
    logging.info(f"Overall: {total_successes}/{total_episodes} ({100*overall_success_rate:.1f}%)")
    logging.info("=" * 60)
    
    return {
        "task_results": task_results,
        "total_episodes": total_episodes,
        "total_successes": total_successes,
        "overall_success_rate": overall_success_rate,
    }


if __name__ == "__main__":
    # Use spawn method for multiprocessing (required for CUDA)
    mp.set_start_method("spawn", force=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    
    tyro.cli(eval_libero_parallel)
