# LIBERO Datasets

This directory contains LIBERO benchmark datasets in LeRobot format, along with visualization videos for verification.

## Dataset Summary

| Suite | Tasks | Episodes | Frames | Status |
|-------|-------|----------|--------|--------|
| LIBERO-10 | 10 | 381 | - | Consistent with official |
| LIBERO-OBJECT | 10 | 452 | - | Consistent with official |
| LIBERO-GOAL | 10 | 423 | - | Consistent with official |
| LIBERO-SPATIAL | 10 | 435 | - | Consistent with official |
| LIBERO-90 | 73 | 3923 | 569524 | **Issues detected** (see below) |

---

## LIBERO-10

**Location:** `libero_10_lerobot/libero_10_no_noops_lerobot/`

Long-horizon tasks requiring multiple skills.

| # | Task |
|---|------|
| 0 | turn on the stove and put the moka pot on it |
| 1 | put the black bowl in the bottom drawer of the cabinet and close it |
| 2 | put the yellow and white mug in the microwave and close it |
| 3 | put both moka pots on the stove |
| 4 | put both the alphabet soup and the cream cheese box in the basket |
| 5 | put both the alphabet soup and the tomato sauce in the basket |
| 6 | put both the cream cheese box and the butter in the basket |
| 7 | put the white mug on the left plate and put the yellow and white mug on the right plate |
| 8 | put the white mug on the plate and put the chocolate pudding to the right of the plate |
| 9 | pick up the book and place it in the back compartment of the caddy |

---

## LIBERO-OBJECT

**Location:** `libero_object_lerobot/libero_object_no_noops_lerobot/`

Object manipulation tasks - same action (pick and place), different objects.

| # | Task |
|---|------|
| 0 | pick up the alphabet soup and place it in the basket |
| 1 | pick up the bbq sauce and place it in the basket |
| 2 | pick up the butter and place it in the basket |
| 3 | pick up the chocolate pudding and place it in the basket |
| 4 | pick up the cream cheese and place it in the basket |
| 5 | pick up the ketchup and place it in the basket |
| 6 | pick up the milk and place it in the basket |
| 7 | pick up the orange juice and place it in the basket |
| 8 | pick up the salad dressing and place it in the basket |
| 9 | pick up the tomato sauce and place it in the basket |

---

## LIBERO-GOAL

**Location:** `libero_goal_lerobot/libero_goal_no_noops_lerobot/`

Goal-oriented tasks - different goals in the same environment.

| # | Task |
|---|------|
| 0 | open the middle drawer of the cabinet |
| 1 | open the top drawer and put the bowl inside |
| 2 | push the plate to the front of the stove |
| 3 | put the bowl on the plate |
| 4 | put the bowl on the stove |
| 5 | put the bowl on top of the cabinet |
| 6 | put the cream cheese in the bowl |
| 7 | put the wine bottle on the rack |
| 8 | put the wine bottle on top of the cabinet |
| 9 | turn on the stove |

---

## LIBERO-SPATIAL

**Location:** `libero_spatial_lerobot/libero_spatial_no_noops_lerobot/`

Spatial reasoning tasks - same object, different spatial locations.

| # | Task |
|---|------|
| 0 | pick up the black bowl between the plate and the ramekin and place it on the plate |
| 1 | pick up the black bowl from table center and place it on the plate |
| 2 | pick up the black bowl in the top drawer of the wooden cabinet and place it on the plate |
| 3 | pick up the black bowl next to the cookie box and place it on the plate |
| 4 | pick up the black bowl next to the plate and place it on the plate |
| 5 | pick up the black bowl next to the ramekin and place it on the plate |
| 6 | pick up the black bowl on the cookie box and place it on the plate |
| 7 | pick up the black bowl on the ramekin and place it on the plate |
| 8 | pick up the black bowl on the stove and place it on the plate |
| 9 | pick up the black bowl on the wooden cabinet and place it on the plate |

---

## LIBERO-90

**Location:** `libero_90_lerobot/libero_90_no_noops_lerobot/`

Large-scale benchmark with 90 tasks across diverse scenes.

### Known Issues

The dataset has **73 tasks instead of 90** due to:

1. **Scene merging (16 tasks lost):** Tasks with identical instructions from different scenes were merged. Official LIBERO-90 has scene-specific variants (e.g., "open the top drawer" in KITCHEN_SCENE1 vs KITCHEN_SCENE2).

2. **Left/right swap errors (10 tasks):** Some task instructions have incorrect left/right references.

3. **Missing task (1 task):** "pick up the butter and put it in the basket" is completely missing.

### Left/Right Swap Errors

| Task # | Dataset Instruction | Official (Correct) Instruction |
|--------|---------------------|-------------------------------|
| 32 | put the **left** moka pot on the stove | put the **right** moka pot on the stove |
| 49 | pick up the black bowl on the **right** and put it in the tray | pick up the black bowl on the **left** and put it in the tray |
| 56 | put the white mug on the **right** plate | put the white mug on the **left** plate |
| 57 | put the yellow and white mug on the **left** plate | put the yellow and white mug on the **right** plate |
| 65 | place it to the **left** of the caddy | place it to the **right** of the caddy |
| 67 | pick up the red mug and place it to the **left** of the caddy | pick up the red mug and place it to the **right** of the caddy |
| 68 | pick up the white mug and place it to the **left** of the caddy | pick up the white mug and place it to the **right** of the caddy |
| 70 | pick up the book on the left and place it on the **cabinet shelf** | pick up the book on the left and place it **on top of** the shelf |
| 71 | pick up the book on the **left** and place it under the cabinet shelf | pick up the book on the **right** and place it under the cabinet shelf |
| 72 | pick up the book on the right and place it **on top of** the shelf | pick up the book on the right and place it on the **cabinet shelf** |

### Task List (73 tasks in dataset)

| # | Task |
|---|------|
| 0 | close the top drawer of the cabinet and put the black bowl on top of it |
| 1 | close the top drawer of the cabinet |
| 2 | put the black bowl in the top drawer of the cabinet |
| 3 | put the butter at the back in the top drawer of the cabinet and close it |
| 4 | put the butter at the front in the top drawer of the cabinet and close it |
| 5 | put the chocolate pudding in the top drawer of the cabinet and close it |
| 6 | open the bottom drawer of the cabinet |
| 7 | open the top drawer of the cabinet and put the bowl in it |
| 8 | open the top drawer of the cabinet |
| 9 | put the black bowl on the plate |
| 10 | put the black bowl on top of the cabinet |
| 11 | put the black bowl at the back on the plate |
| 12 | put the black bowl at the front on the plate |
| 13 | put the middle black bowl on the plate |
| 14 | put the middle black bowl on top of the cabinet |
| 15 | stack the black bowl at the front on the black bowl in the middle |
| 16 | stack the middle black bowl on the back black bowl |
| 17 | put the frying pan on the stove |
| 18 | put the moka pot on the stove |
| 19 | turn on the stove and put the frying pan on it |
| 20 | turn on the stove |
| 21 | close the bottom drawer of the cabinet and open the top drawer |
| 22 | close the bottom drawer of the cabinet |
| 23 | put the black bowl in the bottom drawer of the cabinet |
| 24 | put the wine bottle in the bottom drawer of the cabinet |
| 25 | put the wine bottle on the wine rack |
| 26 | put the ketchup in the top drawer of the cabinet |
| 27 | close the microwave |
| 28 | put the yellow and white mug to the front of the white mug |
| 29 | open the microwave |
| 30 | put the white bowl on the plate |
| 31 | put the white bowl to the right of the plate |
| 32 | put the left moka pot on the stove |
| 33 | turn off the stove |
| 34 | put the frying pan on the cabinet shelf |
| 35 | put the frying pan on top of the cabinet |
| 36 | put the frying pan under the cabinet shelf |
| 37 | put the white bowl on top of the cabinet |
| 38 | pick up the alphabet soup and put it in the basket |
| 39 | pick up the cream cheese box and put it in the basket |
| 40 | pick up the ketchup and put it in the basket |
| 41 | pick up the tomato sauce and put it in the basket |
| 42 | pick up the milk and put it in the basket |
| 43 | pick up the orange juice and put it in the basket |
| 44 | pick up the alphabet soup and put it in the tray |
| 45 | pick up the butter and put it in the tray |
| 46 | pick up the cream cheese and put it in the tray |
| 47 | pick up the ketchup and put it in the tray |
| 48 | pick up the tomato sauce and put it in the tray |
| 49 | pick up the black bowl on the right and put it in the tray |
| 50 | pick up the chocolate pudding and put it in the tray |
| 51 | pick up the salad dressing and put it in the tray |
| 52 | stack the left bowl on the right bowl and place them in the tray |
| 53 | stack the right bowl on the left bowl and place them in the tray |
| 54 | put the red mug on the left plate |
| 55 | put the red mug on the right plate |
| 56 | put the white mug on the right plate |
| 57 | put the yellow and white mug on the left plate |
| 58 | put the chocolate pudding to the left of the plate |
| 59 | put the chocolate pudding to the right of the plate |
| 60 | put the red mug on the plate |
| 61 | put the white mug on the plate |
| 62 | pick up the book and place it in the front compartment of the caddy |
| 63 | pick up the book and place it in the left compartment of the caddy |
| 64 | pick up the book and place it in the right compartment of the caddy |
| 65 | pick up the yellow and white mug and place it to the left of the caddy |
| 66 | pick up the book and place it in the back compartment of the caddy |
| 67 | pick up the red mug and place it to the left of the caddy |
| 68 | pick up the white mug and place it to the left of the caddy |
| 69 | pick up the book in the middle and place it on the cabinet shelf |
| 70 | pick up the book on the left and place it on the cabinet shelf |
| 71 | pick up the book on the left and place it under the cabinet shelf |
| 72 | pick up the book on the right and place it on top of the shelf |

---

## Visualization Videos

Each suite has a corresponding visualization directory with one video per task:

| Suite | Visualization Directory | Videos |
|-------|------------------------|--------|
| LIBERO-10 | `libero_10_visualization/` | 10 |
| LIBERO-OBJECT | `libero_object_visualization/` | 10 |
| LIBERO-GOAL | `libero_goal_visualization/` | 10 |
| LIBERO-SPATIAL | `libero_spatial_visualization/` | 10 |
| LIBERO-90 | `libero_90_visualization/` | 73 |

Each video shows:
- **Left**: Main camera view
- **Right**: Wrist camera view
- **Top**: Camera labels
- **Overlay**: Task index and instruction

Videos are named as: `task_{XX}_{task_name}.mp4`

---

## Dataset Format (LeRobot v2.1)

Each dataset contains:
```
{suite}_no_noops_lerobot/
├── data/
│   └── chunk-{XXX}/
│       └── episode_{XXXXXX}.parquet
├── videos/
│   └── chunk-{XXX}/
│       ├── image/
│       │   └── episode_{XXXXXX}.mp4
│       └── wrist_image/
│           └── episode_{XXXXXX}.mp4
└── meta/
    ├── info.json
    ├── tasks.jsonl
    ├── episodes.jsonl
    └── episodes_stats.jsonl
```

### Features
- **image**: Main camera (256x256, RGB, AV1 codec)
- **wrist_image**: Wrist camera (256x256, RGB, AV1 codec)
- **state**: Robot state (8D: x, y, z, axis_angle1-3, gripper, gripper)
- **actions**: Robot actions (7D: x, y, z, axis_angle1-3, gripper)
- **FPS**: 20

---

## Reference

Official LIBERO repository: https://github.com/Lifelong-Robot-Learning/LIBERO

