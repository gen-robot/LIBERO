# ER-GOAL (20-task) Suite Summary

This document summarizes the **current 20-task** ER-GOAL task set defined in `er_goal_tasks.yaml`.

## Design Constraints (for this 20-task subset)

1. **Source provenance**
   - Tasks 1–10 are two-source constructions (`source_a` + `source_b`).
   - Tasks 11–20 are three-source constructions (`source_a` + `source_b` + `source_c`).
2. **Core principle**
   - Novel object-target combinations (object X placed on target Y, where this pair was never seen together in training).

## Two-Source Tasks (1–10)

| ID | Task ID | Instruction | Source A | Source B (Target Scene) | Notes (from config) |
|---|---|---|---|---|---|
| 01 | `er_goal_01` | put the butter on the plate | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | Butter on plate (never trained) |
| 02 | `er_goal_02` | put the cream cheese on top of the cabinet | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_top_of_the_cabinet.bddl` | Cream cheese on cabinet |
| 03 | `er_goal_03` | put the ketchup on the stove | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | Ketchup on stove |
| 04 | `er_goal_04` | put the milk on the plate | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | Milk on LR plate (never trained) |
| 05 | `er_goal_05` | put the orange juice on top of the cabinet | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_top_of_the_cabinet.bddl` | Orange juice on cabinet top (never trained) |
| 06 | `er_goal_06` | put the orange juice on the stove | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | Orange juice on stove (never trained) |
| 07 | `er_goal_07` | put the tomato sauce in the caddy | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_right_compartment_of_the_caddy.bddl` | Tomato sauce in caddy (never trained) |
| 08 | `er_goal_08` | put the chocolate pudding on the plate | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | Pudding on LR plate |
| 09 | `er_goal_09` | put the bbq sauce in the caddy | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | BBQ sauce in caddy |
| 10 | `er_goal_10` | put the alphabet soup on the cabinet | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | Soup on study shelf |

## Three-Source Tasks (11–20)

| ID | Task ID | Instruction | Source A | Source B (Target Scene) | Source C (Distractor provider) | Notes (from config) |
|---|---|---|---|---|---|---|
| 11 | `er_goal_11` | put the butter on the plate | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | Butter+plate with ketchup |
| 12 | `er_goal_12` | put the cream cheese on the stove | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_90/KITCHEN_SCENE3_put_the_frying_pan_on_the_stove.bddl` | Cream cheese+stove with milk |
| 13 | `er_goal_13` | put the ketchup in the caddy | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_left_compartment_of_the_caddy.bddl` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | Ketchup+caddy with butter |
| 14 | `er_goal_14` | put the milk on top of the cabinet | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_top_of_the_cabinet.bddl` | `libero_90/LIVING_ROOM_SCENE6_put_the_red_mug_on_the_plate.bddl` | Milk on cabinet top (never trained) |
| 15 | `er_goal_15` | put the orange juice on the stove | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | Orange juice on stove with wine+cheese distractors |
| 16 | `er_goal_16` | put the tomato sauce on the stove | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_yellow_and_white_mug_and_place_it_to_the_right_of_the_caddy.bddl` | Tomato sauce on stove (never trained) |
| 17 | `er_goal_17` | put the cream cheese on the plate | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | `libero_90/STUDY_SCENE2_pick_up_the_book_and_place_it_in_the_back_compartment_of_the_caddy.bddl` | Cream cheese on LR plate with study clutter |
| 18 | `er_goal_18` | put the chocolate pudding in the caddy | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | `libero_goal/put_the_bowl_on_top_of_the_cabinet.bddl` | Pudding+caddy with bowl+cabinet distractor |
| 19 | `er_goal_19` | put the bbq sauce on the cabinet | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | `libero_90/KITCHEN_SCENE8_put_the_right_moka_pot_on_the_stove.bddl` | BBQ sauce on shelf with kitchen clutter |
| 20 | `er_goal_20` | put the alphabet soup on the stove | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_goal/push_the_plate_to_the_front_of_the_stove.bddl` | Soup on stove with extra stove objects |
