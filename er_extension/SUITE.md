# ER (Environment Recombination) Suite Construction Plan

This document details how each ER task is constructed by recombining elements from 2 or 3 existing BDDL files.

## Source BDDL Files Available

### libero_object (10 files) - Floor scene, basket manipulation
| File | Objects |
|------|---------|
| `pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | alphabet_soup, basket |
| `pick_up_the_butter_and_place_it_in_the_basket.bddl` | butter, basket |
| `pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | cream_cheese, basket |
| `pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | ketchup, basket |
| `pick_up_the_milk_and_place_it_in_the_basket.bddl` | milk, basket |
| `pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | orange_juice, basket |
| `pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | tomato_sauce, basket |
| `pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | salad_dressing, basket |
| `pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | chocolate_pudding, basket |
| `pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | bbq_sauce, basket |

### libero_goal (10 files) - Same scene, different goals
| File | Key Elements |
|------|--------------|
| `put_the_bowl_on_the_plate.bddl` | bowl, plate |
| `put_the_bowl_on_the_stove.bddl` | bowl, stove |
| `put_the_bowl_on_top_of_the_cabinet.bddl` | bowl, cabinet |
| `put_the_wine_bottle_on_the_rack.bddl` | wine_bottle, wine_rack |
| `put_the_wine_bottle_on_top_of_the_cabinet.bddl` | wine_bottle, cabinet |
| `put_the_cream_cheese_in_the_bowl.bddl` | cream_cheese, bowl |
| `turn_on_the_stove.bddl` | stove |
| `open_the_middle_drawer_of_the_cabinet.bddl` | cabinet drawer |
| `open_the_top_drawer_and_put_the_bowl_inside.bddl` | drawer, bowl |
| `push_the_plate_to_the_front_of_the_stove.bddl` | plate, stove |

### libero_spatial (10 files) - Spatial references
| File | Spatial Relation |
|------|------------------|
| `pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | next_to ramekin |
| `pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | next_to cookie_box |
| `pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate.bddl` | next_to plate |
| `pick_up_the_black_bowl_on_the_ramekin_and_place_it_on_the_plate.bddl` | on ramekin |
| `pick_up_the_black_bowl_on_the_cookie_box_and_place_it_on_the_plate.bddl` | on cookie_box |
| `pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_plate.bddl` | on stove |
| `pick_up_the_black_bowl_on_the_wooden_cabinet_and_place_it_on_the_plate.bddl` | on cabinet |
| `pick_up_the_black_bowl_from_table_center_and_place_it_on_the_plate.bddl` | table_center |
| `pick_up_the_black_bowl_in_the_top_drawer_of_the_wooden_cabinet_and_place_it_on_the_plate.bddl` | in drawer |
| `pick_up_the_black_bowl_between_the_plate_and_the_ramekin_and_place_it_on_the_plate.bddl` | between |

### libero_90 (90 files) - Diverse scenes
Key scenes used:
- KITCHEN_SCENE1-10: Various kitchen setups with cabinets, stoves, drawers
- LIVING_ROOM_SCENE1-6: Baskets, trays, mugs, plates
- STUDY_SCENE1-4: Desk caddies, books, shelves

---

## ER-OBJECT Suite (40 tasks)

**Principle**: Same manipulation (pick object, place in basket) in DIFFERENT scene contexts.

### Two-Source Tasks (1-20)

| ID | Instruction | Source A (Manipulation) | Source B (Scene) | Construction | Novelty |
|----|-------------|------------------------|------------------|--------------|---------|
| 01 | pick up the alphabet soup and place it in the basket | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | Take {alphabet_soup, basket, goal} from A; Take {kitchen_table, wooden_cabinet, plate} from B | Basket task in kitchen with cabinet |
| 02 | pick up the butter and place it in the basket | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE2_put_the_black_bowl_at_the_front_on_the_plate.bddl` | Take {butter, basket, goal} from A; Take {kitchen_table, cabinet, bowls} from B | Basket in multi-bowl scene |
| 03 | pick up the cream cheese and place it in the basket | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE3_turn_on_the_stove.bddl` | Take {cream_cheese, basket, goal} from A; Take {kitchen_table, stove, moka_pot} from B | Basket task with stove fixtures |
| 04 | pick up the ketchup and place it in the basket | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` | Take {ketchup, basket, goal} from A; Take {kitchen_table, wine_rack, cabinet} from B | Basket task with wine rack |
| 05 | pick up the milk and place it in the basket | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE5_put_the_black_bowl_on_the_plate.bddl` | Take {milk, basket, goal} from A; Take {kitchen_table, cabinet, drawer} from B | Milk-basket (not in L90) |
| 06 | pick up the orange juice and place it in the basket | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | Take {orange_juice, basket, goal} from A; Take {kitchen_table, cabinet_shelf, stove} from B | OJ-basket with shelf scene |
| 07 | pick up the tomato sauce and place it in the basket | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | Take {tomato_sauce, basket, goal} from A; Take {study_table, desk_caddy} from B | Basket in study with caddy |
| 08 | pick up the salad dressing and place it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE2_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | Take {salad_dressing, basket, goal} from A; Take {study_table, desk_caddy} from B | Salad dressing in study2 |
| 09 | pick up the chocolate pudding and place it in the basket | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE3_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | Take {chocolate_pudding, basket, goal} from A; Take {study_table, desk_caddy, mugs} from B | Pudding-basket in study3 |
| 10 | pick up the bbq sauce and place it in the basket | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | Take {bbq_sauce, basket, goal} from A; Take {study_table, cabinet_shelf, books} from B | BBQ sauce in study4 |
| 11 | pick up the alphabet soup and place it in the basket | `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE3_pick_up_the_butter_and_put_it_in_the_tray.bddl` | Take {alphabet_soup, basket, goal} from A; Take {living_room_table, tray} from B | Basket in tray scene |
| 12 | pick up the butter and place it in the basket | `libero_object/pick_up_the_butter_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE4_pick_up_the_chocolate_pudding_and_put_it_in_the_tray.bddl` | Take {butter, basket, goal} from A; Take {living_room_table, tray, bowls} from B | Butter-basket in LR4 |
| 13 | pick up the cream cheese and place it in the basket | `libero_object/pick_up_the_cream_cheese_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | Take {cream_cheese, basket, goal} from A; Take {living_room_table, plates, mugs} from B | Basket in mug/plate scene |
| 14 | pick up the ketchup and place it in the basket | `libero_object/pick_up_the_ketchup_and_place_it_in_the_basket.bddl` | `libero_90/LIVING_ROOM_SCENE6_put_the_red_mug_on_the_plate.bddl` | Take {ketchup, basket, goal} from A; Take {living_room_table, plate, mugs} from B | Ketchup-basket in LR6 |
| 15 | pick up the milk and place it in the basket | `libero_object/pick_up_the_milk_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_plate.bddl` | Take {milk, basket, goal} from A; Take {main_table, cabinet, plate, bowl} from B | Basket in libero_goal scene |
| 16 | pick up the orange juice and place it in the basket | `libero_object/pick_up_the_orange_juice_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | Take {orange_juice, basket, goal} from A; Take {main_table, wine_rack, cabinet} from B | OJ-basket in goal wine scene |
| 17 | pick up the tomato sauce and place it in the basket | `libero_object/pick_up_the_tomato_sauce_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl` | Take {tomato_sauce, basket, goal} from A; Take {main_table, stove, cabinet, ramekin, plate} from B | Basket in spatial scene |
| 18 | pick up the salad dressing and place it in the basket | `libero_object/pick_up_the_salad_dressing_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_plate.bddl` | Take {salad_dressing, basket, goal} from A; Take {main_table, stove, cabinet, plate} from B | Salad in spatial stove scene |
| 19 | pick up the chocolate pudding and place it in the basket | `libero_object/pick_up_the_chocolate_pudding_and_place_it_in_the_basket.bddl` | `libero_spatial/pick_up_the_black_bowl_next_to_the_cookie_box_and_place_it_on_the_plate.bddl` | Take {chocolate_pudding, basket, goal} from A; Take {main_table, cookie_box, plate} from B | Pudding in cookie scene |
| 20 | pick up the bbq sauce and place it in the basket | `libero_object/pick_up_the_bbq_sauce_and_place_it_in_the_basket.bddl` | `libero_goal/put_the_bowl_on_the_stove.bddl` | Take {bbq_sauce, basket, goal} from A; Take {main_table, stove, cabinet} from B | BBQ in goal stove scene |

### Three-Source Tasks (21-40)

| ID | Instruction | Source A (Manipulation) | Source B (Scene) | Source C (Distractors) | Construction | Novelty |
|----|-------------|------------------------|------------------|----------------------|--------------|---------|
| 21 | pick up the alphabet soup and place it in the basket | `libero_object/...alphabet_soup...` | `libero_90/KITCHEN_SCENE1_...` | `libero_90/STUDY_SCENE1_...` | A: manipulation; B: scene; C: {black_book, mug} | Kitchen + study objects |
| 22 | pick up the butter and place it in the basket | `libero_object/...butter...` | `libero_90/KITCHEN_SCENE2_...` | `libero_spatial/...ramekin...` | A: manipulation; B: scene; C: {ramekin, cookies} | Kitchen + spatial objects |
| 23 | pick up the cream cheese and place it in the basket | `libero_object/...cream_cheese...` | `libero_90/KITCHEN_SCENE3_...` | `libero_goal/...wine_bottle...` | A: manipulation; B: scene; C: {wine_bottle} | Stove scene + wine |
| 24 | pick up the ketchup and place it in the basket | `libero_object/...ketchup...` | `libero_90/KITCHEN_SCENE4_...` | `libero_90/LIVING_ROOM_SCENE3_...` | A: manipulation; B: scene; C: {wooden_tray} | Wine rack + tray |
| 25 | pick up the milk and place it in the basket | `libero_object/...milk...` | `libero_90/KITCHEN_SCENE5_...` | `libero_90/KITCHEN_SCENE3_...` | A: manipulation; B: scene; C: {moka_pot, frying_pan} | Cabinet + cookware |
| 26 | pick up the orange juice and place it in the basket | `libero_object/...orange_juice...` | `libero_90/KITCHEN_SCENE9_...` | `libero_90/STUDY_SCENE4_...` | A: manipulation; B: scene; C: {books} | Shelf + books |
| 27 | pick up the tomato sauce and place it in the basket | `libero_object/...tomato_sauce...` | `libero_90/STUDY_SCENE1_...` | `libero_90/KITCHEN_SCENE1_...` | A: manipulation; B: scene; C: {plate, bowl} | Study + kitchen dishware |
| 28 | pick up the salad dressing and place it in the basket | `libero_object/...salad_dressing...` | `libero_90/STUDY_SCENE2_...` | `libero_90/LIVING_ROOM_SCENE3_...` | A: manipulation; B: scene; C: {wooden_tray} | Study + tray |
| 29 | pick up the chocolate pudding and place it in the basket | `libero_object/...chocolate_pudding...` | `libero_90/STUDY_SCENE3_...` | `libero_90/KITCHEN_SCENE4_...` | A: manipulation; B: scene; C: {wine_bottle} | Study + wine |
| 30 | pick up the bbq sauce and place it in the basket | `libero_object/...bbq_sauce...` | `libero_90/STUDY_SCENE4_...` | `libero_spatial/...ramekin...` | A: manipulation; B: scene; C: {ramekin} | Study shelf + ramekin |
| 31 | pick up the alphabet soup and place it in the basket | `libero_object/...alphabet_soup...` | `libero_90/LIVING_ROOM_SCENE3_...` | `libero_90/KITCHEN_SCENE9_...` | A: manipulation; B: scene; C: {frying_pan} | Tray + frypan |
| 32 | pick up the butter and place it in the basket | `libero_object/...butter...` | `libero_90/LIVING_ROOM_SCENE4_...` | `libero_90/STUDY_SCENE1_...` | A: manipulation; B: scene; C: {book, mug} | LR + study |
| 33 | pick up the cream cheese and place it in the basket | `libero_object/...cream_cheese...` | `libero_90/LIVING_ROOM_SCENE5_...` | `libero_goal/...bowl...` | A: manipulation; B: scene; C: {bowl} | Mug scene + bowl |
| 34 | pick up the ketchup and place it in the basket | `libero_object/...ketchup...` | `libero_90/LIVING_ROOM_SCENE6_...` | `libero_spatial/...cookie_box...` | A: manipulation; B: scene; C: {cookie_box, cookies} | LR + cookies |
| 35 | pick up the milk and place it in the basket | `libero_object/...milk...` | `libero_goal/put_the_bowl_on_the_plate.bddl` | `libero_90/KITCHEN_SCENE3_...` | A: manipulation; B: scene; C: {moka_pot} | Goal scene + moka |
| 36 | pick up the orange juice and place it in the basket | `libero_object/...orange_juice...` | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | `libero_90/STUDY_SCENE1_...` | A: manipulation; B: scene; C: {book} | Goal wine + book |
| 37 | pick up the tomato sauce and place it in the basket | `libero_object/...tomato_sauce...` | `libero_spatial/...ramekin...` | `libero_90/LIVING_ROOM_SCENE3_...` | A: manipulation; B: scene; C: {wooden_tray} | Spatial + tray |
| 38 | pick up the salad dressing and place it in the basket | `libero_object/...salad_dressing...` | `libero_spatial/...stove...` | `libero_90/STUDY_SCENE4_...` | A: manipulation; B: scene; C: {books} | Spatial stove + books |
| 39 | pick up the chocolate pudding and place it in the basket | `libero_object/...chocolate_pudding...` | `libero_spatial/...cookie_box...` | `libero_goal/...cream_cheese...` | A: manipulation; B: scene; C: {cream_cheese} | Spatial + cream cheese |
| 40 | pick up the bbq sauce and place it in the basket | `libero_object/...bbq_sauce...` | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_spatial/...ramekin...` | A: manipulation; B: scene; C: {ramekin, plate} | Goal stove + spatial |

---

## ER-GOAL Suite (40 tasks)

**Principle**: Novel object-target combinations (object X placed on target Y, where this pair was never seen together in training).

### Two-Source Tasks (1-20)

| ID | Instruction | Source A (Object) | Source B (Target Scene) | Construction | Novelty |
|----|-------------|-------------------|------------------------|--------------|---------|
| 01 | put the butter on the plate | `libero_object/...butter...` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl` | Take {butter} from A; Take {plate, scene} from B; Goal: (On butter plate) | Butter on plate (never trained) |
| 02 | put the cream cheese on top of the cabinet | `libero_object/...cream_cheese...` | `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_top_of_the_cabinet.bddl` | Take {cream_cheese} from A; Take {cabinet, scene} from B | Cream cheese on cabinet |
| 03 | put the ketchup on the stove | `libero_object/...ketchup...` | `libero_90/KITCHEN_SCENE3_put_the_moka_pot_on_the_stove.bddl` | Take {ketchup} from A; Take {stove, scene} from B | Ketchup on stove |
| 04 | put the milk on the wine rack | `libero_object/...milk...` | `libero_90/KITCHEN_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` | Take {milk} from A; Take {wine_rack, scene} from B | Milk on wine rack |
| 05 | put the orange juice on the cabinet shelf | `libero_object/...orange_juice...` | `libero_90/KITCHEN_SCENE9_put_the_frying_pan_on_the_cabinet_shelf.bddl` | Take {orange_juice} from A; Take {cabinet_shelf, scene} from B | OJ on cabinet shelf |
| 06 | put the tomato sauce in the drawer | `libero_object/...tomato_sauce...` | `libero_90/KITCHEN_SCENE5_put_the_black_bowl_in_the_top_drawer_of_the_cabinet.bddl` | Take {tomato_sauce} from A; Take {drawer, scene} from B | Tomato sauce in drawer |
| 07 | put the salad dressing in the tray | `libero_object/...salad_dressing...` | `libero_90/LIVING_ROOM_SCENE3_pick_up_the_butter_and_put_it_in_the_tray.bddl` | Take {salad_dressing} from A; Take {tray, scene} from B | Salad dressing in tray |
| 08 | put the chocolate pudding on the plate | `libero_object/...chocolate_pudding...` | `libero_90/LIVING_ROOM_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | Take {chocolate_pudding} from A; Take {plate, scene} from B | Pudding on LR plate |
| 09 | put the bbq sauce in the caddy | `libero_object/...bbq_sauce...` | `libero_90/STUDY_SCENE1_pick_up_the_book_and_place_it_in_the_front_compartment_of_the_caddy.bddl` | Take {bbq_sauce} from A; Take {caddy, scene} from B | BBQ sauce in caddy |
| 10 | put the alphabet soup on the cabinet | `libero_object/...alphabet_soup...` | `libero_90/STUDY_SCENE4_pick_up_the_book_on_the_left_and_place_it_on_top_of_the_shelf.bddl` | Take {alphabet_soup} from A; Take {cabinet_shelf, scene} from B | Soup on study shelf |
| 11 | put the butter on the stove | `libero_object/...butter...` | `libero_goal/put_the_bowl_on_the_stove.bddl` | Take {butter} from A; Take {stove, scene} from B | Butter on stove |
| 12 | put the milk on the plate | `libero_object/...milk...` | `libero_goal/put_the_bowl_on_the_plate.bddl` | Take {milk} from A; Take {plate, scene} from B | Milk on goal plate |
| 13 | put the ketchup on top of the cabinet | `libero_object/...ketchup...` | `libero_goal/put_the_bowl_on_top_of_the_cabinet.bddl` | Take {ketchup} from A; Take {cabinet_top, scene} from B | Ketchup on goal cabinet |
| 14 | put the cream cheese in the bowl | `libero_object/...cream_cheese...` | `libero_goal/put_the_cream_cheese_in_the_bowl.bddl` | Different arrangement; Take {cream_cheese} from A; Take {bowl position, scene} from B | Cream cheese position novel |
| 15 | put the orange juice on the plate | `libero_object/...orange_juice...` | `libero_spatial/pick_up_the_black_bowl_next_to_the_plate_and_place_it_on_the_plate.bddl` | Take {orange_juice} from A; Take {plate, scene} from B | OJ on spatial plate |
| 16 | put the tomato sauce on top of the cabinet | `libero_object/...tomato_sauce...` | `libero_spatial/pick_up_the_black_bowl_on_the_wooden_cabinet_and_place_it_on_the_plate.bddl` | Take {tomato_sauce} from A; Take {cabinet, scene} from B | Tomato on spatial cabinet |
| 17 | put the salad dressing on the stove | `libero_object/...salad_dressing...` | `libero_spatial/pick_up_the_black_bowl_on_the_stove_and_place_it_on_the_plate.bddl` | Take {salad_dressing} from A; Take {stove, scene} from B | Salad on spatial stove |
| 18 | put the chocolate pudding in the drawer | `libero_object/...chocolate_pudding...` | `libero_spatial/pick_up_the_black_bowl_in_the_top_drawer_of_the_wooden_cabinet_and_place_it_on_the_plate.bddl` | Take {chocolate_pudding} from A; Take {drawer, scene} from B | Pudding in spatial drawer |
| 19 | put the bbq sauce on the plate | `libero_object/...bbq_sauce...` | `libero_90/LIVING_ROOM_SCENE6_put_the_red_mug_on_the_plate.bddl` | Take {bbq_sauce} from A; Take {plate, scene} from B | BBQ on LR6 plate |
| 20 | put the alphabet soup in the tray | `libero_object/...alphabet_soup...` | `libero_90/LIVING_ROOM_SCENE4_pick_up_the_chocolate_pudding_and_put_it_in_the_tray.bddl` | Take {alphabet_soup} from A; Take {tray, scene} from B | Soup in LR4 tray |

### Three-Source Tasks (21-40)

| ID | Instruction | Source A (Object) | Source B (Target Scene) | Source C (Distractor) | Construction | Novelty |
|----|-------------|-------------------|------------------------|----------------------|--------------|---------|
| 21 | put the butter on the plate | `libero_object/...butter...` | `libero_90/KITCHEN_SCENE1_...plate...` | `libero_object/...ketchup...` | A: object; B: scene+target; C: {ketchup} distractor | Butter+plate with ketchup |
| 22 | put the cream cheese on the stove | `libero_object/...cream_cheese...` | `libero_90/KITCHEN_SCENE3_...stove...` | `libero_object/...milk...` | A: object; B: scene; C: {milk} | Cream cheese+stove with milk |
| 23 | put the ketchup on the wine rack | `libero_object/...ketchup...` | `libero_90/KITCHEN_SCENE4_...wine_rack...` | `libero_object/...butter...` | A: object; B: scene; C: {butter} | Ketchup+rack with butter |
| 24 | put the milk on the cabinet shelf | `libero_object/...milk...` | `libero_90/KITCHEN_SCENE9_...cabinet_shelf...` | `libero_object/...tomato_sauce...` | A: object; B: scene; C: {tomato_sauce} | Milk+shelf with tomato |
| 25 | put the orange juice in the drawer | `libero_object/...orange_juice...` | `libero_90/KITCHEN_SCENE5_...drawer...` | `libero_object/...cream_cheese...` | A: object; B: scene; C: {cream_cheese} | OJ+drawer with cheese |
| 26 | put the tomato sauce in the tray | `libero_object/...tomato_sauce...` | `libero_90/LIVING_ROOM_SCENE3_...tray...` | `libero_object/...salad_dressing...` | A: object; B: scene; C: {salad_dressing} | Tomato+tray with salad |
| 27 | put the salad dressing on the plate | `libero_object/...salad_dressing...` | `libero_90/LIVING_ROOM_SCENE5_...plate...` | `libero_object/...chocolate_pudding...` | A: object; B: scene; C: {chocolate_pudding} | Salad+plate with pudding |
| 28 | put the chocolate pudding in the caddy | `libero_object/...chocolate_pudding...` | `libero_90/STUDY_SCENE1_...caddy...` | `libero_object/...bbq_sauce...` | A: object; B: scene; C: {bbq_sauce} | Pudding+caddy with bbq |
| 29 | put the bbq sauce on the cabinet | `libero_object/...bbq_sauce...` | `libero_90/STUDY_SCENE4_...cabinet...` | `libero_object/...alphabet_soup...` | A: object; B: scene; C: {alphabet_soup} | BBQ+cabinet with soup |
| 30 | put the alphabet soup on the stove | `libero_object/...alphabet_soup...` | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_object/...butter...` | A: object; B: scene; C: {butter} | Soup+goal_stove with butter |
| 31 | put the butter on top of the cabinet | `libero_object/...butter...` | `libero_goal/put_the_bowl_on_top_of_the_cabinet.bddl` | `libero_object/...milk...` | A: object; B: scene; C: {milk} | Butter+goal_cabinet with milk |
| 32 | put the cream cheese on the plate | `libero_object/...cream_cheese...` | `libero_goal/put_the_bowl_on_the_plate.bddl` | `libero_object/...orange_juice...` | A: object; B: scene; C: {orange_juice} | Cheese+goal_plate with OJ |
| 33 | put the ketchup on the plate | `libero_object/...ketchup...` | `libero_spatial/...plate...` | `libero_object/...tomato_sauce...` | A: object; B: scene; C: {tomato_sauce} | Ketchup+spatial with tomato |
| 34 | put the milk on the stove | `libero_object/...milk...` | `libero_spatial/...stove...` | `libero_object/...salad_dressing...` | A: object; B: scene; C: {salad_dressing} | Milk+spatial_stove with salad |
| 35 | put the orange juice on top of the cabinet | `libero_object/...orange_juice...` | `libero_spatial/...cabinet...` | `libero_object/...chocolate_pudding...` | A: object; B: scene; C: {chocolate_pudding} | OJ+spatial_cabinet with pudding |
| 36 | put the tomato sauce in the drawer | `libero_object/...tomato_sauce...` | `libero_spatial/...drawer...` | `libero_object/...bbq_sauce...` | A: object; B: scene; C: {bbq_sauce} | Tomato+spatial_drawer with bbq |
| 37 | put the salad dressing in the tray | `libero_object/...salad_dressing...` | `libero_90/LIVING_ROOM_SCENE4_...tray...` | `libero_object/...alphabet_soup...` | A: object; B: scene; C: {alphabet_soup} | Salad+LR4_tray with soup |
| 38 | put the chocolate pudding on the plate | `libero_object/...chocolate_pudding...` | `libero_90/LIVING_ROOM_SCENE6_...plate...` | `libero_object/...butter...` | A: object; B: scene; C: {butter} | Pudding+LR6 with butter |
| 39 | put the bbq sauce in the tray | `libero_object/...bbq_sauce...` | `libero_90/LIVING_ROOM_SCENE3_...tray...` | `libero_object/...cream_cheese...` | A: object; B: scene; C: {cream_cheese} | BBQ+tray with cheese |
| 40 | put the alphabet soup on the cabinet shelf | `libero_object/...alphabet_soup...` | `libero_90/KITCHEN_SCENE9_...cabinet_shelf...` | `libero_object/...ketchup...` | A: object; B: scene; C: {ketchup} | Soup+shelf with ketchup |

---

## ER-SPATIAL Suite (40 tasks)

**Principle**: Novel spatial references for locating objects (object X is described relative to landmark Y, where this spatial relationship is new).

### Two-Source Tasks (1-20)

| ID | Instruction | Source A (Spatial Template) | Source B (Novel Landmark) | Construction | Novelty |
|----|-------------|----------------------------|--------------------------|--------------|---------|
| 01 | pick up the black bowl next to the butter and place it on the plate | `libero_spatial/...next_to_the_ramekin...` | `libero_object/...butter...` | A: spatial structure, bowl; B: {butter} as landmark | Butter as spatial landmark |
| 02 | pick up the black bowl next to the ketchup and place it on the plate | `libero_spatial/...next_to_the_ramekin...` | `libero_object/...ketchup...` | A: spatial; B: {ketchup} | Ketchup as landmark |
| 03 | pick up the black bowl next to the milk and place it on the plate | `libero_spatial/...next_to_the_plate...` | `libero_object/...milk...` | A: spatial; B: {milk} | Milk as landmark |
| 04 | pick up the black bowl next to the cream cheese and place it on the plate | `libero_spatial/...next_to_the_cookie_box...` | `libero_object/...cream_cheese...` | A: spatial; B: {cream_cheese} | Cream cheese as landmark |
| 05 | pick up the black bowl next to the orange juice and place it on the plate | `libero_spatial/...next_to_the_ramekin...` | `libero_object/...orange_juice...` | A: spatial; B: {orange_juice} | OJ as landmark |
| 06 | pick up the butter next to the black bowl and put it in the basket | `libero_90/LIVING_ROOM_SCENE2_...butter...` | `libero_goal/put_the_bowl_on_the_plate.bddl` | A: butter+basket; B: {bowl} for spatial ref | Bowl as landmark for butter |
| 07 | pick up the cream cheese next to the plate and put it in the basket | `libero_90/LIVING_ROOM_SCENE1_...cream_cheese...` | `libero_spatial/...plate...` | A: cream_cheese+basket; B: plate landmark | Plate as landmark for cheese |
| 08 | pick up the ketchup next to the moka pot and put it in the basket | `libero_90/LIVING_ROOM_SCENE1_...ketchup...` | `libero_90/KITCHEN_SCENE3_...moka_pot...` | A: ketchup+basket; B: {moka_pot} | Moka pot as landmark |
| 09 | pick up the milk next to the wine bottle and put it in the basket | `libero_90/LIVING_ROOM_SCENE2_...milk...` | `libero_90/KITCHEN_SCENE4_...wine_bottle...` | A: milk+basket; B: {wine_bottle} | Wine bottle as landmark |
| 10 | pick up the tomato sauce next to the book and put it in the basket | `libero_90/LIVING_ROOM_SCENE1_...tomato_sauce...` | `libero_90/STUDY_SCENE1_...book...` | A: tomato+basket; B: {book} | Book as landmark |
| 11 | pick up the black bowl on the butter and place it on the plate | `libero_spatial/...on_the_ramekin...` | `libero_object/...butter...` | A: "on" relation; B: {butter} | "on butter" relation |
| 12 | pick up the black bowl on the cream cheese and place it on the plate | `libero_spatial/...on_the_cookie_box...` | `libero_object/...cream_cheese...` | A: "on" relation; B: {cream_cheese} | "on cream cheese" |
| 13 | pick up the black bowl between the butter and the ketchup and place it on the plate | `libero_spatial/...between_the_plate_and_the_ramekin...` | `libero_object/...butter...` + `libero_object/...ketchup...` | A: between template; B: {butter, ketchup} | Between food items |
| 14 | pick up the salad dressing next to the frying pan and put it in the basket | `libero_object/...salad_dressing...` | `libero_90/KITCHEN_SCENE9_...frying_pan...` | A: salad+basket; B: {frying_pan} | Frying pan as landmark |
| 15 | pick up the chocolate pudding next to the tray and put it in the basket | `libero_object/...chocolate_pudding...` | `libero_90/LIVING_ROOM_SCENE3_...tray...` | A: pudding+basket; B: {tray} | Tray as landmark |
| 16 | pick up the bbq sauce next to the caddy and put it in the basket | `libero_object/...bbq_sauce...` | `libero_90/STUDY_SCENE1_...caddy...` | A: bbq+basket; B: {caddy} | Caddy as landmark |
| 17 | pick up the alphabet soup next to the wine rack and put it in the basket | `libero_object/...alphabet_soup...` | `libero_90/KITCHEN_SCENE4_...wine_rack...` | A: soup+basket; B: {wine_rack} | Wine rack as landmark |
| 18 | pick up the orange juice next to the stove and put it in the basket | `libero_object/...orange_juice...` | `libero_90/KITCHEN_SCENE3_...stove...` | A: OJ+basket; B: {stove} | Stove as landmark |
| 19 | pick up the black bowl from the left of the butter and place it on the plate | `libero_spatial/...from_table_center...` | `libero_object/...butter...` | A: spatial; B: "left of butter" | Left-of butter |
| 20 | pick up the black bowl from the right of the ketchup and place it on the plate | `libero_spatial/...from_table_center...` | `libero_object/...ketchup...` | A: spatial; B: "right of ketchup" | Right-of ketchup |

### Three-Source Tasks (21-40)

| ID | Instruction | Source A | Source B | Source C | Construction | Novelty |
|----|-------------|----------|----------|----------|--------------|---------|
| 21 | pick up the black bowl next to the butter and place it on the plate | `libero_spatial/...ramekin...` | `libero_object/...butter...` | `libero_object/...ketchup...` | A: spatial; B: landmark; C: distractor | Butter landmark + ketchup |
| 22 | pick up the black bowl next to the milk and place it on the plate | `libero_spatial/...plate...` | `libero_object/...milk...` | `libero_object/...cream_cheese...` | A: spatial; B: landmark; C: distractor | Milk + cream cheese |
| 23 | pick up the black bowl next to the cream cheese and place it on the plate | `libero_spatial/...cookie_box...` | `libero_object/...cream_cheese...` | `libero_object/...tomato_sauce...` | A: spatial; B: landmark; C: distractor | Cheese + tomato |
| 24 | pick up the black bowl next to the orange juice and place it on the plate | `libero_spatial/...ramekin...` | `libero_object/...orange_juice...` | `libero_object/...salad_dressing...` | A: spatial; B: landmark; C: distractor | OJ + salad |
| 25 | pick up the black bowl next to the tomato sauce and place it on the plate | `libero_spatial/...plate...` | `libero_object/...tomato_sauce...` | `libero_object/...chocolate_pudding...` | A: spatial; B: landmark; C: distractor | Tomato + pudding |
| 26 | pick up the butter next to the bowl and put it in the basket | `libero_90/LR_SCENE2_...butter...` | `libero_goal/...bowl...` | `libero_object/...ketchup...` | A: butter; B: bowl; C: distractor | Butter near bowl + ketchup |
| 27 | pick up the cream cheese next to the plate and put it in the basket | `libero_90/LR_SCENE1_...cream_cheese...` | `libero_spatial/...plate...` | `libero_object/...milk...` | A: cheese; B: plate; C: distractor | Cheese near plate + milk |
| 28 | pick up the ketchup next to the moka pot and put it in the basket | `libero_90/LR_SCENE1_...ketchup...` | `libero_90/K_SCENE3_...moka_pot...` | `libero_object/...butter...` | A: ketchup; B: moka; C: distractor | Ketchup near moka + butter |
| 29 | pick up the milk next to the wine bottle and put it in the basket | `libero_90/LR_SCENE2_...milk...` | `libero_90/K_SCENE4_...wine_bottle...` | `libero_object/...cream_cheese...` | A: milk; B: wine; C: distractor | Milk near wine + cheese |
| 30 | pick up the tomato sauce next to the book and put it in the basket | `libero_90/LR_SCENE1_...tomato_sauce...` | `libero_90/STUDY_SCENE1_...book...` | `libero_object/...orange_juice...` | A: tomato; B: book; C: distractor | Tomato near book + OJ |
| 31 | pick up the black bowl on the butter and place it on the plate | `libero_spatial/...on_ramekin...` | `libero_object/...butter...` | `libero_object/...salad_dressing...` | A: on_relation; B: butter; C: salad | On butter + salad |
| 32 | pick up the black bowl on the cream cheese and place it on the plate | `libero_spatial/...on_cookie_box...` | `libero_object/...cream_cheese...` | `libero_object/...chocolate_pudding...` | A: on_relation; B: cheese; C: pudding | On cheese + pudding |
| 33 | pick up the black bowl between butter and ketchup and place it on plate | `libero_spatial/...between...` | `libero_object/...butter...` | `libero_object/...ketchup...` + `libero_object/...milk...` | A: between; B+C: landmarks+distractor | Between butter/ketchup + milk |
| 34 | pick up the salad dressing next to the frying pan and put it in the basket | `libero_object/...salad_dressing...` | `libero_90/K_SCENE9_...frying_pan...` | `libero_object/...bbq_sauce...` | A: salad; B: frypan; C: bbq | Salad near frypan + bbq |
| 35 | pick up the chocolate pudding next to the tray and put it in the basket | `libero_object/...chocolate_pudding...` | `libero_90/LR_SCENE3_...tray...` | `libero_object/...alphabet_soup...` | A: pudding; B: tray; C: soup | Pudding near tray + soup |
| 36 | pick up the bbq sauce next to the caddy and put it in the basket | `libero_object/...bbq_sauce...` | `libero_90/STUDY_SCENE1_...caddy...` | `libero_object/...butter...` | A: bbq; B: caddy; C: butter | BBQ near caddy + butter |
| 37 | pick up the alphabet soup next to the wine rack and put it in the basket | `libero_object/...alphabet_soup...` | `libero_90/K_SCENE4_...wine_rack...` | `libero_object/...cream_cheese...` | A: soup; B: rack; C: cheese | Soup near rack + cheese |
| 38 | pick up the orange juice next to the stove and put it in the basket | `libero_object/...orange_juice...` | `libero_90/K_SCENE3_...stove...` | `libero_object/...tomato_sauce...` | A: OJ; B: stove; C: tomato | OJ near stove + tomato |
| 39 | pick up the black bowl from left of butter and place it on the plate | `libero_spatial/...table_center...` | `libero_object/...butter...` | `libero_object/...ketchup...` | A: left_of; B: butter; C: ketchup | Left of butter + ketchup |
| 40 | pick up the black bowl from right of ketchup and place it on the plate | `libero_spatial/...table_center...` | `libero_object/...ketchup...` | `libero_object/...milk...` | A: right_of; B: ketchup; C: milk | Right of ketchup + milk |

---

## ER-SEQUENTIAL Suite (40 tasks)

**Principle**: Novel action sequences composed from individual trained actions (action A then action B, where this sequence was never trained together).

### Two-Step Tasks (1-20)

| ID | Instruction | Source A (Step 1) | Source B (Step 2) | Construction | Novelty |
|----|-------------|-------------------|-------------------|--------------|---------|
| 01 | put the bowl on the plate, then put the butter on the cabinet | `libero_90/K_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_object/...butter...` + cabinet goal | A: bowl->plate; B: butter->cabinet | Two-target sequence |
| 02 | turn on the stove and put the butter on it | `libero_90/K_SCENE3_turn_on_the_stove.bddl` | `libero_object/...butter...` + stove goal | A: turn_on; B: butter->stove | Turn-on then place |
| 03 | put the wine bottle on the rack and put the milk on the cabinet | `libero_90/K_SCENE4_put_the_wine_bottle_on_the_wine_rack.bddl` | `libero_object/...milk...` + cabinet goal | A: wine->rack; B: milk->cabinet | Wine + milk sequence |
| 04 | open the drawer and put the ketchup in it | `libero_90/K_SCENE1_open_the_top_drawer_of_the_cabinet.bddl` | `libero_object/...ketchup...` + drawer goal | A: open; B: ketchup->drawer | Open then place inside |
| 05 | put the cream cheese on the plate and close the drawer | `libero_object/...cream_cheese...` + plate goal | `libero_90/K_SCENE5_close_the_top_drawer_of_the_cabinet.bddl` | A: cheese->plate; B: close | Place then close |
| 06 | put the soup in the basket, then put the butter in the basket | `libero_90/LR_SCENE1_...alphabet_soup...basket.bddl` | `libero_object/...butter...` + basket goal | A: soup->basket; B: butter->basket | Two objects to basket |
| 07 | put the milk in the basket, then put the ketchup in the basket | `libero_90/LR_SCENE2_...milk...basket.bddl` | `libero_object/...ketchup...` + basket goal | A: milk->basket; B: ketchup->basket | Two different objects |
| 08 | put the butter in the tray, then put the tomato sauce in the tray | `libero_90/LR_SCENE3_...butter...tray.bddl` | `libero_object/...tomato_sauce...` + tray goal | A: butter->tray; B: tomato->tray | Two objects to tray |
| 09 | put the book in the caddy and put the orange juice on the table | `libero_90/STUDY_SCENE1_...book...caddy.bddl` | `libero_object/...orange_juice...` + table goal | A: book->caddy; B: OJ on table | Study + object |
| 10 | put the frying pan on the stove and turn it on | `libero_90/K_SCENE3_put_the_frying_pan_on_the_stove.bddl` | `libero_90/K_SCENE3_turn_on_the_stove.bddl` | A: pan->stove; B: turn_on | Place then turn-on |
| 11 | put the bowl on the stove and put the butter on the plate | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_object/...butter...` + plate goal | A: bowl->stove; B: butter->plate | Goal + object |
| 12 | put the wine bottle on the rack and put the cream cheese on the cabinet | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | `libero_object/...cream_cheese...` + cabinet goal | A: wine->rack; B: cheese->cabinet | Goal + object |
| 13 | open the middle drawer and put the salad dressing in it | `libero_goal/open_the_middle_drawer_of_the_cabinet.bddl` | `libero_object/...salad_dressing...` + drawer goal | A: open; B: salad->drawer | Goal open + object |
| 14 | turn on the stove and put the chocolate pudding on the plate | `libero_goal/turn_on_the_stove.bddl` | `libero_object/...chocolate_pudding...` + plate goal | A: turn_on; B: pudding->plate | Goal turn-on + object |
| 15 | put the bowl on the plate and put the bbq sauce on the cabinet | `libero_goal/put_the_bowl_on_the_plate.bddl` | `libero_object/...bbq_sauce...` + cabinet goal | A: bowl->plate; B: bbq->cabinet | Goal + object |
| 16 | pick up the bowl next to the ramekin and put butter in basket | `libero_spatial/...next_to_ramekin...plate.bddl` | `libero_object/...butter...` + basket goal | A: spatial pick; B: butter->basket | Spatial + object |
| 17 | pick up the bowl on the stove and put milk in basket | `libero_spatial/...on_the_stove...plate.bddl` | `libero_object/...milk...` + basket goal | A: spatial pick; B: milk->basket | Spatial + object |
| 18 | pick up the bowl from table center and put ketchup on the plate | `libero_spatial/...from_table_center...plate.bddl` | `libero_object/...ketchup...` + plate goal | A: spatial pick; B: ketchup->plate | Spatial + object |
| 19 | put the red mug on the plate and put cream cheese on the table | `libero_90/LR_SCENE5_put_the_red_mug_on_the_left_plate.bddl` | `libero_object/...cream_cheese...` + table goal | A: mug->plate; B: cheese on table | LR + object |
| 20 | put the mug to the right of the caddy and put tomato sauce on the table | `libero_90/STUDY_SCENE1_...mug...caddy.bddl` | `libero_object/...tomato_sauce...` + table goal | A: mug->caddy; B: tomato on table | Study + object |

### Three-Step Tasks (21-40)

| ID | Instruction | Source A (Step 1) | Source B (Step 2) | Source C (Step 3) | Construction | Novelty |
|----|-------------|-------------------|-------------------|-------------------|--------------|---------|
| 21 | open drawer, put bowl on plate, close drawer | `libero_90/K_SCENE1_open_the_top_drawer...` | `libero_90/K_SCENE1_put_the_black_bowl_on_the_plate.bddl` | `libero_90/K_SCENE10_close_the_top_drawer...` | open->place->close | Drawer sandwich |
| 22 | turn on stove, put moka pot on it, put butter on plate | `libero_90/K_SCENE3_turn_on_the_stove.bddl` | `libero_90/K_SCENE3_put_the_moka_pot_on_the_stove.bddl` | `libero_object/...butter...` + plate | stove+moka+butter | Stove + food |
| 23 | put wine on rack, put butter on cabinet, put bowl on plate | `libero_90/K_SCENE4_...wine...rack.bddl` | `libero_object/...butter...` + cabinet | `libero_goal/put_the_bowl_on_the_plate.bddl` | wine+butter+bowl | Three targets |
| 24 | put soup in basket, put butter in basket, put ketchup in basket | `libero_90/LR_SCENE1_...soup...basket.bddl` | `libero_object/...butter...` + basket | `libero_object/...ketchup...` + basket | Three to basket | Triple basket |
| 25 | put milk in basket, put tomato in basket, put cream cheese in basket | `libero_90/LR_SCENE2_...milk...basket.bddl` | `libero_object/...tomato_sauce...` + basket | `libero_object/...cream_cheese...` + basket | Three objects | Triple basket 2 |
| 26 | open drawer, put ketchup in it, close drawer | `libero_90/K_SCENE1_open_the_top_drawer...` | `libero_object/...ketchup...` + drawer | `libero_90/K_SCENE5_close_the_top_drawer...` | open->put->close | Drawer + object |
| 27 | put bowl on plate, put butter on plate, put ketchup on cabinet | `libero_90/K_SCENE1_...bowl...plate.bddl` | `libero_object/...butter...` + plate | `libero_object/...ketchup...` + cabinet | Two on plate | Multi-target |
| 28 | turn on stove, put moka pot on it, put cream cheese on plate | `libero_90/K_SCENE3_turn_on...` | `libero_90/K_SCENE3_put_the_moka_pot...` | `libero_object/...cream_cheese...` + plate | stove+moka+cheese | Stove + dairy |
| 29 | put wine on rack, put bowl on cabinet, close bottom drawer | `libero_90/K_SCENE4_...wine...rack.bddl` | `libero_goal/put_the_bowl_on_top_of_the_cabinet.bddl` | `libero_90/K_SCENE4_close_the_bottom_drawer...` | wine+bowl+close | Complex sequence |
| 30 | put pudding in basket, put butter in basket, put tomato in basket | `libero_object/...chocolate_pudding...` + basket | `libero_object/...butter...` + basket | `libero_object/...tomato_sauce...` + basket | All objects | Object-only combo |
| 31 | put book in caddy, put orange juice on table, put butter on table | `libero_90/STUDY_SCENE1_...book...caddy.bddl` | `libero_object/...orange_juice...` + table | `libero_object/...butter...` + table | Study + objects | Study sequence |
| 32 | put bowl on stove, turn it on, put milk on plate | `libero_goal/put_the_bowl_on_the_stove.bddl` | `libero_goal/turn_on_the_stove.bddl` | `libero_object/...milk...` + plate | goal+goal+object | Goal combo |
| 33 | put wine on rack, put wine on cabinet, put ketchup on plate | `libero_goal/put_the_wine_bottle_on_the_rack.bddl` | `libero_goal/put_the_wine_bottle_on_top_of_the_cabinet.bddl` | `libero_object/...ketchup...` + plate | Same object 2 goals | Wine moves |
| 34 | open middle drawer, put salad in it, put bbq on cabinet | `libero_goal/open_the_middle_drawer...` | `libero_object/...salad_dressing...` + drawer | `libero_object/...bbq_sauce...` + cabinet | Goal + objects | Goal + two objects |
| 35 | put bowl on plate, put cream cheese in bowl, put butter on cabinet | `libero_goal/put_the_bowl_on_the_plate.bddl` | `libero_goal/put_the_cream_cheese_in_the_bowl.bddl` | `libero_object/...butter...` + cabinet | bowl prep + food | Nested + object |
| 36 | pick up bowl next to ramekin, place on plate, put butter in basket | `libero_spatial/...next_to_ramekin...` | implicit plate goal | `libero_object/...butter...` + basket | Spatial + object | Spatial sequence |
| 37 | pick up bowl on stove, place on plate, put milk on cabinet | `libero_spatial/...on_the_stove...` | implicit plate goal | `libero_object/...milk...` + cabinet | Spatial + object | Spatial + cabinet |
| 38 | pick up bowl between plate and ramekin, put butter on plate, put ketchup in basket | `libero_spatial/...between...` | `libero_object/...butter...` + plate | `libero_object/...ketchup...` + basket | Spatial + 2 objects | Complex spatial |
| 39 | put red mug on plate, put butter on plate, put cream cheese on table | `libero_90/LR_SCENE5_...mug...plate.bddl` | `libero_object/...butter...` + plate | `libero_object/...cream_cheese...` + table | LR + objects | Living room combo |
| 40 | put book in caddy, put mug next to caddy, put orange juice on table | `libero_90/STUDY_SCENE1_...book...caddy.bddl` | `libero_90/STUDY_SCENE1_...mug...caddy.bddl` | `libero_object/...orange_juice...` + table | Study combo | Study + object |

---

## Construction Rules Summary

### Two-Source Construction
1. **Source A**: Provides the main action/object/goal
2. **Source B**: Provides the scene context (table, fixtures, layout)
3. **Merge**: Combine scene from B with action objects from A

### Three-Source Construction
1. **Source A**: Main action/object/goal
2. **Source B**: Scene context
3. **Source C**: Distractor objects (placed in scene but not manipulated)
4. **Merge**: Scene from B + action from A + distractors from C

### Validation Rules
- No duplicate objects in the same scene
- Manipulated objects must not be the same as distractors
- All objects must be compatible with table type (kitchen_table, living_room_table, study_table, main_table)
- Sequential tasks must have physically consistent object states between steps
