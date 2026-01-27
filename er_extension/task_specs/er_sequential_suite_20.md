# ER-SEQUENTIAL (10-task) Suite Summary

This document summarizes the **current 10-task** ER-SEQUENTIAL task set defined in `er_extension/task_specs/er_sequential_tasks.yaml`.

## Design Constraints (for this 10-task subset)

1. **Source provenance**
   - Tasks 1–5 are two-step sequences (2 BDDL sources).
   - Tasks 6–10 are three-step sequences (3 BDDL sources).
2. **Novelty principle**
   - Each task composes a new multi-action sequence from individually trained behaviors.

## Tasks 1–5 (Two-Step Tasks; 2-source)

| ID | Task ID | Instruction | Source A | Source B | Notes (from config) |
|---|---|---|---|---|---|
| 01 | `er_seq_01` | put the bowl on the plate, then put the butter on the cabinet | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | Two-target sequence (bowl->plate; butter->cabinet) |
| 02 | `er_seq_02` | turn on the stove and put the butter on it | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | Turn-on then place (stove->on; butter->stove) |
| 03 | `er_seq_03` | put the cream cheese on the plate and close the drawer | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE5_close_the_top_drawer_of_the_cabinet.bddl` | Place then close (cheese->plate; drawer->closed) |
| 04 | `er_seq_04` | put the milk in the basket, then put the ketchup in the basket | `libero_90/LIVING_ROOM_SCENE2_pick_up_the_milk_and_put_it_in_the_basket.bddl` | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | Two different objects to basket (milk, then ketchup) |
| 05 | `er_seq_05` | put the frying pan on the stove and turn it on | `libero_90/KITCHEN_SCENE3_put_the_frying_pan_on_the_stove.bddl` | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | Place pan then turn stove on |

## Tasks 6–10 (Three-Step Tasks; 3-source)

| ID | Task ID | Instruction | Source A | Source B | Source C | Notes (from config) |
|---|---|---|---|---|---|---|
| 06 | `er_seq_06` | turn on the stove, put the moka pot on it, and put the butter on the plate | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | Stove on, moka pot on stove, butter on plate |
| 07 | `er_seq_07` | open the drawer, put the black bowl in it, and close the drawer | `libero_90/KITCHEN_SCENE1_open_the_top_drawer_of_the_cabinet.bddl` | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE5_close_the_top_drawer_of_the_cabinet.bddl` | Open-put-close drawer with black bowl |
| 08 | `er_seq_08` | put the bowl on the plate, put the butter on the plate, and put the ketchup on the cabinet | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | Two objects on plate plus ketchup on cabinet |
| 09 | `er_seq_09` | turn on the stove, put the moka pot on it, and put the cream cheese on the plate | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | Stove + moka pot + dairy on plate |
| 10 | `er_seq_10` | put the pudding in the basket, put the butter in the basket, and put the tomato sauce in the basket | `libero_90/LIVING_ROOM_SCENE2_pick_up_the_milk_and_put_it_in_the_basket.bddl` | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | Three objects to the same basket (pudding, butter, tomato_sauce) |
