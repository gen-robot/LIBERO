# ER (Environment Recombination) Suite Tasks

This document lists all tasks in the ER evaluation suites, showing task instructions and their construction from source BDDL files.

## Overview

| Suite | Tasks | Principle | Construction |
|-------|-------|-----------|--------------|
| ER-OBJECT | 20 | Same manipulation in different scene contexts | 2-3 source merge |
| ER-GOAL | 20 | Novel object-target combinations | 2-3 source merge |
| ER-SPATIAL | 20 | Novel spatial references for objects | 2-3 source merge |
| ER-SEQUENTIAL | 20 | Novel action sequences | Multi-step composition |

---

## ER-OBJECT Suite (20 tasks)

**Principle**: Same manipulation (action + target object + goal) transferred to DIFFERENT scene contexts.

### Two-Source Tasks (10)

| # | Task ID | Instruction | Manipulation Source | Scene Source |
|---|---------|-------------|---------------------|--------------|
| 1 | er_object_01 | pick up the alphabet soup and place it in the basket | libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl | libero_90/KITCHEN_SCENE1 |
| 2 | er_object_02 | pick up the butter and place it in the basket | libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl | libero_90/KITCHEN_SCENE4 |
| 3 | er_object_03 | pick up the cream cheese and place it in the basket | libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl | libero_90/STUDY_SCENE1 |
| 4 | er_object_04 | pick up the ketchup and place it in the basket | libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl | libero_90/LIVING_ROOM_SCENE3 |
| 5 | er_object_05 | pick up the milk and place it in the basket | libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl | libero_90/KITCHEN_SCENE1 |
| 6 | er_object_06 | pick up the orange juice and place it in the basket | libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl | libero_90/STUDY_SCENE1 |
| 7 | er_object_07 | pick up the tomato sauce and place it in the basket | libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl | libero_90/KITCHEN_SCENE4 |
| 8 | er_object_08 | pick up the salad dressing and place it in the basket | libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl | libero_90/LIVING_ROOM_SCENE1 |
| 9 | er_object_09 | pick up the chocolate pudding and place it in the basket | libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl | libero_90/KITCHEN_SCENE1 |
| 10 | er_object_10 | pick up the bbq sauce and place it in the basket | libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl | libero_90/LIVING_ROOM_SCENE3 |

### Three-Source Tasks (10)

| # | Task ID | Instruction | Manipulation Source | Scene Source | Background Objects |
|---|---------|-------------|---------------------|--------------|-------------------|
| 11 | er_object_11 | pick up the alphabet soup and place it in the basket | libero_object/alphabet_soup | KITCHEN_SCENE1 | black_book, white_yellow_mug |
| 12 | er_object_12 | pick up the butter and place it in the basket | libero_object/butter | STUDY_SCENE1 | plate, akita_black_bowl |
| 13 | er_object_13 | pick up the cream cheese and place it in the basket | libero_object/cream_cheese | KITCHEN_SCENE4 | wooden_tray |
| 14 | er_object_14 | pick up the ketchup and place it in the basket | libero_object/ketchup | KITCHEN_SCENE1 | moka_pot, wine_bottle |
| 15 | er_object_15 | pick up the milk and place it in the basket | libero_object/milk | LIVING_ROOM_SCENE1 | chefmate_8_frypan |
| 16 | er_object_16 | pick up the orange juice and place it in the basket | libero_object/orange_juice | KITCHEN_SCENE4 | black_book |
| 17 | er_object_17 | pick up the tomato sauce and place it in the basket | libero_object/tomato_sauce | STUDY_SCENE1 | wooden_tray, red_coffee_mug |
| 18 | er_object_18 | pick up the salad dressing and place it in the basket | libero_object/salad_dressing | KITCHEN_SCENE1 | yellow_book, porcelain_mug |
| 19 | er_object_19 | pick up the chocolate pudding and place it in the basket | libero_object/chocolate_pudding | LIVING_ROOM_SCENE3 | plate, glazed_rim_porcelain_ramekin |
| 20 | er_object_20 | pick up the bbq sauce and place it in the basket | libero_object/bbq_sauce | STUDY_SCENE1 | akita_black_bowl, wine_bottle, cookies |

---

## ER-GOAL Suite (20 tasks)

**Principle**: Same action pattern applied to NOVEL object-target combinations.

### Two-Source Tasks (10)

| # | Task ID | Instruction | Scene Source | Object | Target |
|---|---------|-------------|--------------|--------|--------|
| 1 | er_goal_01 | put the butter on the plate | KITCHEN_SCENE1 | butter | plate_1 |
| 2 | er_goal_02 | put the cream cheese on top of the cabinet | KITCHEN_SCENE1 | cream_cheese | wooden_cabinet_1_top_side |
| 3 | er_goal_03 | put the ketchup on the stove | KITCHEN_SCENE3 | ketchup | flat_stove_1_cook_region |
| 4 | er_goal_04 | put the milk on the wine rack | KITCHEN_SCENE4 | milk | wine_rack_1 |
| 5 | er_goal_05 | put the tomato sauce on the plate | KITCHEN_SCENE5 | tomato_sauce | plate_1 |
| 6 | er_goal_06 | put the butter in the basket | LIVING_ROOM_SCENE1 | butter | basket_1_contain_region |
| 7 | er_goal_07 | put the milk in the tray | LIVING_ROOM_SCENE3 | milk | wooden_tray_1_contain_region |
| 8 | er_goal_08 | put the cream cheese in the caddy | STUDY_SCENE1 | cream_cheese | desk_caddy_1_front_region |
| 9 | er_goal_09 | put the chocolate pudding on top of the cabinet | KITCHEN_SCENE9 | chocolate_pudding | wooden_cabinet_1_top_side |
| 10 | er_goal_10 | put the orange juice in the basket | LIVING_ROOM_SCENE1 | orange_juice | basket_1_contain_region |

### Three-Source Tasks (10)

| # | Task ID | Instruction | Scene Source | Object | Target | Distractors |
|---|---------|-------------|--------------|--------|--------|-------------|
| 11 | er_goal_11 | put the butter on the plate | KITCHEN_SCENE1 | butter | plate_1 | ketchup |
| 12 | er_goal_12 | put the milk on the stove | KITCHEN_SCENE3 | milk | flat_stove_1_cook_region | cream_cheese |
| 13 | er_goal_13 | put the tomato sauce on the wine rack | KITCHEN_SCENE4 | tomato_sauce | wine_rack_1 | butter |
| 14 | er_goal_14 | put the chocolate pudding in the basket | LIVING_ROOM_SCENE1 | chocolate_pudding | basket_1_contain_region | ketchup |
| 15 | er_goal_15 | put the orange juice in the tray | LIVING_ROOM_SCENE3 | orange_juice | wooden_tray_1_contain_region | milk |
| 16 | er_goal_16 | put the butter in the caddy | STUDY_SCENE1 | butter | desk_caddy_1_front_region | alphabet_soup |
| 17 | er_goal_17 | put the ketchup on top of the cabinet | KITCHEN_SCENE5 | ketchup | wooden_cabinet_1_top_side | milk |
| 18 | er_goal_18 | put the cream cheese on the stove | KITCHEN_SCENE9 | cream_cheese | flat_stove_1_cook_region | butter |
| 19 | er_goal_19 | put the alphabet soup in the basket | LIVING_ROOM_SCENE1 | alphabet_soup | basket_1_contain_region | tomato_sauce, butter |
| 20 | er_goal_20 | put the milk in the caddy | STUDY_SCENE1 | milk | desk_caddy_1_left_region | chocolate_pudding |

---

## ER-SPATIAL Suite (20 tasks)

**Principle**: Same goal with NOVEL spatial reference for locating the object.

### Two-Source Tasks (10)

| # | Task ID | Instruction | Scene | Object | Landmark | Relation | Target |
|---|---------|-------------|-------|--------|----------|----------|--------|
| 1 | er_spatial_01 | pick up the black bowl next to the butter and place it on the plate | libero_spatial | akita_black_bowl | butter | next_to | plate_1 |
| 2 | er_spatial_02 | pick up the black bowl to the left of the ketchup and place it on the plate | libero_spatial | akita_black_bowl | ketchup | left_of | plate_1 |
| 3 | er_spatial_03 | pick up the black bowl to the right of the milk and place it on the plate | libero_spatial | akita_black_bowl | milk | right_of | plate_1 |
| 4 | er_spatial_04 | pick up the butter next to the black bowl and put it on the plate | KITCHEN_SCENE1 | butter | akita_black_bowl | next_to | plate_1 |
| 5 | er_spatial_05 | pick up the cream cheese behind the plate and put it on the cabinet | KITCHEN_SCENE1 | cream_cheese | plate | behind | wooden_cabinet_1_top_side |
| 6 | er_spatial_06 | pick up the butter next to the soup and put it in the basket | LIVING_ROOM_SCENE2 | butter | alphabet_soup | next_to | basket_1_contain_region |
| 7 | er_spatial_07 | pick up the milk to the left of the tomato sauce and put it in the basket | LIVING_ROOM_SCENE2 | milk | tomato_sauce | left_of | basket_1_contain_region |
| 8 | er_spatial_08 | pick up the ketchup in front of the black bowl and put it on the plate | KITCHEN_SCENE5 | ketchup | akita_black_bowl | in_front_of | plate_1 |
| 9 | er_spatial_09 | pick up the tomato sauce to the right of the plate and put it on the cabinet | KITCHEN_SCENE5 | tomato_sauce | plate | right_of | wooden_cabinet_1_top_side |
| 10 | er_spatial_10 | pick up the pudding next to the butter and put it in the basket | LIVING_ROOM_SCENE2 | chocolate_pudding | butter | next_to | basket_1_contain_region |

### Three-Source Tasks (10)

| # | Task ID | Instruction | Scene | Object | Landmark | Distractors |
|---|---------|-------------|-------|--------|----------|-------------|
| 11 | er_spatial_11 | pick up the black bowl next to the cream cheese and place it on the plate | libero_spatial | akita_black_bowl | cream_cheese | ketchup |
| 12 | er_spatial_12 | pick up the black bowl to the left of the tomato sauce and place it on the plate | libero_spatial | akita_black_bowl | tomato_sauce | milk |
| 13 | er_spatial_13 | pick up the butter behind the black bowl and put it on the plate | KITCHEN_SCENE1 | butter | akita_black_bowl | ketchup |
| 14 | er_spatial_14 | pick up the milk to the right of the cream cheese and put it on the cabinet | KITCHEN_SCENE5 | milk | cream_cheese | butter |
| 15 | er_spatial_15 | pick up the soup next to the milk and put it in the basket | LIVING_ROOM_SCENE2 | alphabet_soup | milk | butter |
| 16 | er_spatial_16 | pick up the ketchup to the left of the pudding and put it in the basket | LIVING_ROOM_SCENE2 | ketchup | chocolate_pudding | cream_cheese |
| 17 | er_spatial_17 | pick up the black bowl in front of the butter and place it on the plate | libero_spatial | akita_black_bowl | butter | tomato_sauce |
| 18 | er_spatial_18 | pick up the tomato sauce next to the ketchup and put it in the basket | LIVING_ROOM_SCENE2 | tomato_sauce | ketchup | alphabet_soup |
| 19 | er_spatial_19 | pick up the cream cheese to the right of the bowl and put it on the cabinet | KITCHEN_SCENE1 | cream_cheese | akita_black_bowl | milk |
| 20 | er_spatial_20 | pick up the pudding behind the butter and put it in the basket | LIVING_ROOM_SCENE2 | chocolate_pudding | butter | ketchup, milk |

---

## ER-SEQUENTIAL Suite (20 tasks)

**Principle**: Compose NOVEL action sequences from individual trained actions.

### Two-Step Tasks (10)

| # | Task ID | Instruction | Scene | Step 1 | Step 2 |
|---|---------|-------------|-------|--------|--------|
| 1 | er_seq_01 | put the black bowl on the plate and then put the butter on the cabinet | KITCHEN_SCENE1 | bowl -> plate | butter -> cabinet |
| 2 | er_seq_02 | turn on the stove and then put the moka pot on it | KITCHEN_SCENE3 | turn_on stove | moka_pot -> stove |
| 3 | er_seq_03 | put the wine bottle on the rack and then put the bowl on the cabinet | KITCHEN_SCENE4 | wine -> rack | bowl -> cabinet |
| 4 | er_seq_04 | open the top drawer and put the butter in it | KITCHEN_SCENE10 | open drawer | butter -> drawer |
| 5 | er_seq_05 | put the ketchup on the plate and close the top drawer | KITCHEN_SCENE5 | ketchup -> plate | close drawer |
| 6 | er_seq_06 | put the soup in the basket and then put the butter in the basket | LIVING_ROOM_SCENE1 | soup -> basket | butter -> basket |
| 7 | er_seq_07 | put the milk in the basket and then put the ketchup in the basket | LIVING_ROOM_SCENE2 | milk -> basket | ketchup -> basket |
| 8 | er_seq_08 | put the cream cheese on the plate and then put the milk on the cabinet | KITCHEN_SCENE1 | cream_cheese -> plate | milk -> cabinet |
| 9 | er_seq_09 | put the bowl on the stove and turn it on | KITCHEN_SCENE3 | bowl -> stove | turn_on stove |
| 10 | er_seq_10 | put the tomato sauce in the basket and then put the cream cheese in the basket | LIVING_ROOM_SCENE1 | tomato -> basket | cream_cheese -> basket |

### Three-Step Tasks (10)

| # | Task ID | Instruction | Scene | Step 1 | Step 2 | Step 3 |
|---|---------|-------------|-------|--------|--------|--------|
| 11 | er_seq_11 | open the drawer, put the bowl on the plate, and close the drawer | KITCHEN_SCENE10 | open drawer | bowl -> plate | close drawer |
| 12 | er_seq_12 | turn on the stove, put the moka pot on it, and put the bowl on the plate | KITCHEN_SCENE3 | turn_on stove | moka -> stove | bowl -> plate |
| 13 | er_seq_13 | put the wine on the rack, put the butter on the cabinet, and put the bowl on the plate | KITCHEN_SCENE4 | wine -> rack | butter -> cabinet | bowl -> plate |
| 14 | er_seq_14 | put the soup, butter, and ketchup in the basket | LIVING_ROOM_SCENE1 | soup -> basket | butter -> basket | ketchup -> basket |
| 15 | er_seq_15 | put the milk, tomato sauce, and cream cheese in the basket | LIVING_ROOM_SCENE2 | milk -> basket | tomato -> basket | cream_cheese -> basket |
| 16 | er_seq_16 | open the drawer, put the ketchup in it, and close the drawer | KITCHEN_SCENE5 | open drawer | ketchup -> drawer | close drawer |
| 17 | er_seq_17 | put the bowl on the plate, put the butter on the plate, and put the ketchup on the cabinet | KITCHEN_SCENE1 | bowl -> plate | butter -> plate | ketchup -> cabinet |
| 18 | er_seq_18 | turn on the stove, put the moka pot on it, and put the cream cheese on the plate | KITCHEN_SCENE3 | turn_on stove | moka -> stove | cream_cheese -> plate |
| 19 | er_seq_19 | put the wine on the rack, put the bowl on the cabinet, and close the bottom drawer | KITCHEN_SCENE4 | wine -> rack | bowl -> cabinet | close drawer |
| 20 | er_seq_20 | put the pudding, butter, and tomato sauce in the basket | LIVING_ROOM_SCENE1 | pudding -> basket | butter -> basket | tomato -> basket |

---

## Source BDDL Files Reference

### libero_object (Floor Scene)
Simple floor-based scenes used as manipulation sources:
- `pick_up_the_{object}_and_place_it_in_the_basket.bddl`

### libero_90 Scene Types
- **KITCHEN_SCENE1-10**: Kitchen table with cabinet, plate, bowl
- **LIVING_ROOM_SCENE1-5**: Living room table with basket, tray
- **STUDY_SCENE1-3**: Study table with desk caddy, books

### libero_spatial
Spatial reasoning tasks with landmark-based object identification.

---

## Task Construction Methods

### Two-Source Merge
1. **Manipulation Source (A)**: Provides action, manipulated object, and goal predicate
2. **Scene Source (B)**: Provides table type, fixtures, and background layout

### Three-Source Merge
1. **Manipulation Source (A)**: Action + manipulated object + goal
2. **Scene Source (B)**: Table + fixtures
3. **Distractor Source (C)**: Additional background objects from different scenes

### Multi-Step Composition (Sequential)
1. Individual actions from training tasks combined into novel sequences
2. Each step maintains physics consistency with previous steps

