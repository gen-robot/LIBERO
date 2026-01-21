# LIBERO-ER Evaluation

Evaluation pipeline for VLA models on LIBERO benchmarks.

Self-contained version with local `openpi_client` module.

## Features

- Supports all LIBERO suites: `libero_10`, `libero_90`, `libero_spatial`, `libero_object`, `libero_goal`
- Connects to VLA model server via WebSocket
- Compatible with openpi policy server

## Installation

```bash
# From LIBERO-ER root directory
cd /path/to/LIBERO-ER

# Create virtual environment
uv venv --python 3.8 eval/.venv
source eval/.venv/bin/activate

# Install all dependencies (eval + libero)
uv pip sync eval/requirements.txt requirements.txt --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy=unsafe-best-match

# Install libero package
uv pip install -e .

# Set PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$PWD/eval
```

## Usage

### Quick Start (Parallel - Recommended)

```bash
# Start policy server (Terminal 1)
# From openpi or vla_lib directory
uv run scripts/serve_policy.py --env LIBERO

# Run parallel eval (Terminal 2)
cd /path/to/LIBERO-ER
source eval/.venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PWD/eval

# 8 workers for fast evaluation
python eval/eval_parallel.py --args.task-suite-name libero_10 --args.num-workers 8 --args.host localhost --args.port 8000
```

### 1. Start the model server

In a separate terminal, start your VLA model server (e.g., openpi policy server):

```bash
# From openpi directory
uv run scripts/serve_policy.py --env LIBERO
```

### 2. Run evaluation

```bash
cd /path/to/LIBERO-ER
source eval/.venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$PWD/eval

# Evaluate on libero_10 (default)
python eval/eval.py --args.host localhost --args.port 8000

# Evaluate on libero_90
python eval/eval.py --args.task-suite-name libero_90 --args.host localhost --args.port 8000

# Evaluate on libero_spatial
python eval/eval.py --args.task-suite-name libero_spatial --args.host localhost --args.port 8000

# Evaluate on libero_object
python eval/eval.py --args.task-suite-name libero_object --args.host localhost --args.port 8000

# Evaluate on libero_goal
python eval/eval.py --args.task-suite-name libero_goal --args.host localhost --args.port 8000

# Use glx for Mujoco (if you have egl errors)
MUJOCO_GL=glx python eval/eval.py --args.task-suite-name libero_90 --args.host localhost --args.port 8000
```

### Parallel Evaluation (Faster)

```bash
# Run with 8 parallel workers
python eval/eval_parallel.py --args.task-suite-name libero_10 --args.num-workers 8 --args.host localhost --args.port 8000

# Run libero_90 with 16 workers (for machines with many CPU cores)
python eval/eval_parallel.py --args.task-suite-name libero_90 --args.num-workers 16 --args.host localhost --args.port 8000

# Disable video saving for faster evaluation
python eval/eval_parallel.py --args.task-suite-name libero_10 --args.num-workers 8 --args.save-video false

# Use the Osmesa renderer to avoid OpenGL/EGL library dependency issues.

LD_LIBRARY_PATH=/usr/local/nvidia/lib64:/usr/local/nvidia/lib:/usr/lib/x86_64-linux-gnu MUJOCO_GL=osmesa python eval/eval_parallel.py --args.task-suite-name libero_90 --args.num-workers 16 --args.host localhost --args.port 8000
```

**Speedup estimate:**
- Sequential: 10 tasks × 50 episodes × ~30s = ~4 hours
- 8 workers: ~30 minutes (theoretical 8x speedup, actual ~4-6x)

### Full options

```bash
python eval/eval.py --help
```

| Argument | Description | Default |
|----------|-------------|---------|
| `--args.host` | Model server host | `0.0.0.0` |
| `--args.port` | Model server port | `8000` |
| `--args.resize-size` | Image resize size | `224` |
| `--args.replan-steps` | Replan every N steps | `5` |
| `--args.task-suite-name` | Task suite name | `libero_10` |
| `--args.num-steps-wait` | Steps to wait for objects to stabilize | `10` |
| `--args.num-trials-per-task` | Episodes per task | `50` |
| `--args.video-out-path` | Video output path | `data/libero/videos` |
| `--args.seed` | Random seed | `7` |
| `--args.num-workers` | Number of parallel workers (eval_parallel.py only) | `4` |
| `--args.save-video` | Save episode videos (eval_parallel.py only) | `true` |

## Task Suites

| Suite | Tasks | Description |
|-------|-------|-------------|
| `libero_spatial` | 10 | Spatial reasoning tasks |
| `libero_object` | 10 | Object manipulation tasks |
| `libero_goal` | 10 | Goal-oriented tasks |
| `libero_10` | 10 | Long-horizon tasks for downstream testing |
| `libero_90` | 90 | Large-scale pretraining benchmark |

## Output

- Videos saved to `--video-out-path` (default: `data/libero/videos/`)
- Naming format: `rollout_{task_description}_{success|failure}.mp4`
- Console logs with per-task and overall success rates

## Updating requirements.txt

To regenerate the compiled requirements.txt:

```bash
uv pip compile eval/requirements.in -o eval/requirements.txt --python-version 3.8 --extra-index-url https://download.pytorch.org/whl/cu113 --index-strategy=unsafe-best-match
```
