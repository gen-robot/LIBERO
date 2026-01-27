# ER-OBJECT (20-task) Suite Summary

This document summarizes the **current 20-task** ER-OBJECT task set defined in `er_object_tasks.yaml`.

## Design Constraints (for this 20-task subset)

1. **Source provenance**
   - Tasks 1–10 are two-source constructions (`source_a` + `source_b`).
   - Tasks 11–20 are three-source constructions (`source_a` + `source_b` + `source_c`).
2. **Principle**
   - Same manipulation (pick X, place in basket) in different scene contexts; three-source tasks add extra clutter via `source_c`.

## Two-Source Tasks (1–10)

| ID | Task ID | Instruction | Source A | Source B (Scene) | Notes (from config) |
|---|---|---|---|---|---|
| 01 | `er_object_01` | pick up the alphabet soup and place it in the basket | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE3_pick_up_the_butter_and_put_it_in_the_tray.bddl` | From SUITE.md ER-OBJECT #11 (living-room tray scene) |
| 02 | `er_object_02` | pick up the butter and place it in the basket | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE4_pick_up_the_chocolate_pudding_and_put_it_in_the_tray.bddl` | From SUITE.md ER-OBJECT #12 (living-room tray scene) |
| 03 | `er_object_03` | pick up the cream cheese and place it in the basket | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | From SUITE.md ER-OBJECT #13 (living-room mug/plate scene) |
| 04 | `er_object_04` | pick up the ketchup and place it in the basket | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` | From SUITE.md ER-OBJECT #04 (kitchen wine-rack scene) |
| 05 | `er_object_05` | pick up the milk and place it in the basket | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_plate.bddl` | From SUITE.md ER-OBJECT #15 (libero_goal plate scene) |
| 06 | `er_object_06` | pick up the orange juice and place it in the basket | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | From SUITE.md ER-OBJECT #16 (libero_goal wine-rack scene) |
| 07 | `er_object_07` | pick up the tomato sauce and place it in the basket | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | From SUITE.md ER-OBJECT #17 (libero_spatial main-table scene) |
| 08 | `er_object_08` | pick up the salad dressing and place it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_plate.bddl` | From SUITE.md ER-OBJECT #18 (libero_spatial main-table scene) |
| 09 | `er_object_09` | pick up the chocolate pudding and place it in the basket | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE3_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | From SUITE.md ER-OBJECT #09 (study caddy scene) |
| 10 | `er_object_10` | pick up the bbq sauce and place it in the basket | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | From SUITE.md ER-OBJECT #10 (study shelf scene) |

## Three-Source Tasks (11–20)

| ID | Task ID | Instruction | Source A | Source B (Scene) | Source C (Distractor provider) | Distractors (from `source_c.take`) | Notes (from config) |
|---|---|---|---|---|---|---|---|
| 11 | `er_object_11` | pick up the alphabet soup and place it in the basket | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_yellow_and_white_mug_and_place_it_to_the_right_of_the_caddy.bddl` | black_book_1, white_yellow_mug_1 | From SUITE.md ER-OBJECT #21 (kitchen + study distractors) |
| 12 | `er_object_12` | pick up the butter and place it in the basket | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE2_put_the_black_bowl_at_the_front_on_the_plate.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | glazed_rim_porcelain_ramekin_1, cookies_1 | From SUITE.md ER-OBJECT #22 (kitchen + ramekin/cookies distractors) |
| 13 | `er_object_13` | pick up the cream cheese and place it in the basket | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | `libero_goal/put_the_wine_bottle_on_top_of_the_cabinet.bddl` | wine_bottle_1 | From SUITE.md ER-OBJECT #23 (stove scene + wine bottle distractor) |
| 14 | `er_object_14` | pick up the ketchup and place it in the basket | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE6_put_the_red_mug_on_the_plate.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | cookies_1, glazed_rim_porcelain_ramekin_1 | From SUITE.md ER-OBJECT #34 (living-room + cookies/ramekin distractors) |
| 15 | `er_object_15` | pick up the milk and place it in the basket | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE5_put_the_black_bowl_on_the_plate.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | moka_pot_1, chefmate_8_frypan_1 | From SUITE.md ER-OBJECT #25 (kitchen + cookware distractors) |
| 16 | `er_object_16` | pick up the orange juice and place it in the basket | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | black_book_1, yellow_book_1 | From SUITE.md ER-OBJECT #26 (kitchen shelf + books distractors) |
| 17 | `er_object_17` | pick up the tomato sauce and place it in the basket | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | akita_black_bowl_1, plate_1 | From SUITE.md ER-OBJECT #27 (study + dishware distractors) |
| 18 | `er_object_18` | pick up the salad dressing and place it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE2_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | `libero_90/LIVING_ROOM_SCENE3_pick_up_the_butter_and_put_it_in_the_tray.bddl` | wooden_tray_1 | From SUITE.md ER-OBJECT #28 (study + tray distractor) |
| 19 | `er_object_19` | pick up the chocolate pudding and place it in the basket | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | `libero_goal/put_the_cream_cheese_in_the_bowl.bddl` | cream_cheese_1 | From SUITE.md ER-OBJECT #39 (spatial main-table scene + food distractor) |
| 20 | `er_object_20` | pick up the bbq sauce and place it in the basket | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | glazed_rim_porcelain_ramekin_1, plate_1 | From SUITE.md ER-OBJECT #40 (goal scene + dishware distractors) |
