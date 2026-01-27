# ER-SPATIAL (20-task) Suite Summary

This document summarizes the **current 20-task** ER-SPATIAL task set defined in `er_spatial_tasks.yaml`.

## Design Constraints (for this 20-task subset)

1. **Principle**
   - Each task uses a spatial reference (e.g., next_to / on / between / left_of) with landmarks injected from other suites.
2. **Source provenance**
   - Tasks 1–10 primarily use (`source_a` + `source_b`); some tasks may additionally use `source_c` for landmark injection.
   - Tasks 11–20 use (`source_a` + `source_b` + `source_c`) to add extra clutter/landmark providers.

## Tasks 1–10

| ID | Task ID | Instruction | Source A | Source B (Landmark/Scene provider) | Source C (Optional) | Notes (from config) |
|---|---|---|---|---|---|---|
| 01 | `er_spatial_01` | pick up the black bowl next to the butter and place it on the plate | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` |  | From SUITE.md ER-SPATIAL #01 (butter as spatial landmark) |
| 02 | `er_spatial_02` | pick up the black bowl next to the milk and place it on the plate | `libero_spatial/pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` |  | From SUITE.md ER-SPATIAL #03 (milk as spatial landmark) |
| 03 | `er_spatial_03` | pick up the black bowl next to the cream cheese and place it on the plate | `libero_spatial/pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` |  | From SUITE.md ER-SPATIAL #04 (cream cheese as spatial landmark) |
| 04 | `er_spatial_04` | pick up the butter next to the black bowl and put it in the basket | `libero_90/LIVING_ROOM_SCENE2_pick_up_the_butter_and_put_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_plate.bddl` |  | From SUITE.md ER-SPATIAL #06 (bowl as landmark for butter) |
| 05 | `er_spatial_05` | pick up the ketchup next to the moka pot and put it in the basket | `libero_90/LIVING_ROOM_SCENE1_pick_up_the_ketchup_and_put_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` |  | From SUITE.md ER-SPATIAL #08 (moka pot as landmark) |
| 06 | `er_spatial_06` | pick up the milk next to the wine bottle and put it in the basket | `libero_90/LIVING_ROOM_SCENE2_pick_up_the_milk_and_put_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` |  | From SUITE.md ER-SPATIAL #09 (wine bottle as landmark) |
| 07 | `er_spatial_07` | pick up the tomato sauce next to the book and put it in the basket | `libero_90/LIVING_ROOM_SCENE1_pick_up_the_tomato_sauce_and_put_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` |  | From SUITE.md ER-SPATIAL #10 (book as landmark) |
| 08 | `er_spatial_08` | pick up the black bowl on the frying pan and place it on the plate | `libero_spatial/pick_up_the_black_bowl_on_the_ramekin_and_place_it_on_the_plate.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` |  | From SUITE.md ER-SPATIAL #11 (novel 'on frying pan' relation) |
| 09 | `er_spatial_09` | pick up the black bowl between the butter and the ketchup and place it on the plate | `libero_spatial/pick_up_the_black_bowl_between_the_plate_and_the_ramekin_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` |  | From SUITE.md ER-SPATIAL #13 (novel between two food items) |
| 10 | `er_spatial_10` | pick up the salad dressing next to the butter and put it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | From SUITE.md ER-SPATIAL #14 (butter as landmark) |

## Tasks 11–20

| ID | Task ID | Instruction | Source A | Source B (Landmark/Scene provider) | Source C (Distractor provider) | Notes (from config) |
|---|---|---|---|---|---|---|
| 11 | `er_spatial_11` | pick up the black bowl next to the orange juice and place it on the plate | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | From SUITE.md ER-SPATIAL #24 (OJ landmark + study distractors) |
| 12 | `er_spatial_12` | pick up the black bowl next to the tomato sauce and place it on the plate | `libero_spatial/pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | From SUITE.md ER-SPATIAL #25 (tomato landmark + goal distractor) |
| 13 | `er_spatial_13` | pick up the black bowl on the butter and place it on the plate | `libero_spatial/pick_up_the_black_bowl_on_the_ramekin_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | From SUITE.md ER-SPATIAL #31 (on butter + kitchen distractor) |
| 14 | `er_spatial_14` | pick up the black bowl on the cream cheese and place it on the plate | `libero_spatial/pick_up_the_black_bowl_on_the_cookie_box_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | From SUITE.md ER-SPATIAL #32 (on cream cheese + kitchen distractor) |
| 15 | `er_spatial_15` | pick up the salad dressing next to the frying pan and put it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | `libero_goal/push_the_plate_to_the_front_of_the_stove.bddl` | From SUITE.md ER-SPATIAL #34 (frypan landmark + plate distractor) |
| 16 | `er_spatial_16` | pick up the chocolate pudding next to the tray and put it in the basket | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE3_pick_up_the_butter_and_put_it_in_the_tray.bddl` | `libero_goal/put_the_wine_bottle_on_top_of_the_cabinet.bddl` | From SUITE.md ER-SPATIAL #35 (tray landmark + goal distractor) |
| 17 | `er_spatial_17` | pick up the bbq sauce next to the caddy and put it in the basket | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | `libero_spatial/pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_plate.bddl` | From SUITE.md ER-SPATIAL #36 (caddy landmark + spatial-scene distractors) |
| 18 | `er_spatial_18` | pick up the alphabet soup next to the wine rack and put it in the basket | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | From SUITE.md ER-SPATIAL #37 (wine rack landmark + study distractors) |
| 19 | `er_spatial_19` | pick up the orange juice next to the stove and put it in the basket | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | From SUITE.md ER-SPATIAL #38 (stove landmark + study distractors) |
| 20 | `er_spatial_20` | pick up the black bowl to the left of the butter and place it on the plate | `libero_spatial/pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_cream_cheese_in_the_bowl.bddl` | From SUITE.md ER-SPATIAL #39 (left_of butter + goal distractor) |
