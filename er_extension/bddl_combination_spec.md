# BDDL Combination Specification for Libero-ER

## 0. BDDL Syntax Reference

### 0.1 Complete BDDL Structure

```lisp
(define (problem PROBLEM_NAME)
  (:domain robosuite)
  
  (:language INSTRUCTION_TEXT)  ; L
  
  (:regions                     ; R
    (region_name (:target fixture_or_object) (:ranges ((x1 y1 x2 y2))))
  )
  
  (:fixtures                    ; F
    fixture_instance - fixture_type
  )
  
  (:objects                     ; O
    object_instance - object_type
  )
  
  (:obj_of_interest             ; I
    object1
    object2_or_region
  )
  
  (:init                        ; N
    (On object region)
    (Open drawer_region)
  )
  
  (:goal                        ; G
    (And 
      (Predicate arg1 arg2)
    )
  )
)
```

### 0.2 Section Abbreviations

| Abbrev | Section | Description |
|--------|---------|-------------|
| **L** | `(:language)` | Natural language instruction |
| **R** | `(:regions)` | Placement regions (fixture/object-based) |
| **F** | `(:fixtures)` | Scene fixtures |
| **O** | `(:objects)` | Manipulable objects |
| **I** | `(:obj_of_interest)` | Task-relevant entities |
| **N** | `(:init)` | Initial state |
| **G** | `(:goal)` | Goal condition |

---

## 1. Region Syntax

### 1.1 Fixture-Based Region (with coordinates)

```lisp
(region_name 
  (:target fixture_instance)
  (:ranges ((x1 y1 x2 y2)))
)
```

**Examples**:
```lisp
(plate_region (:target main_table) (:ranges ((-0.01 -0.21 0.01 -0.19))))
(akita_black_bowl_init_region (:target kitchen_table) (:ranges ((0.0 0.15 0.05 0.20))))
(stove_front_region (:target main_table) (:ranges ((0.05 0.10 0.15 0.20))))
```

### 1.2 Object-Based Region (no coordinates)

```lisp
(region_name (:target object_instance))
```

**Examples**:
```lisp
; Container region (for In predicate)
(contain_region (:target basket_1))
(contain_region (:target wooden_tray_1))

; Surface region on fixture/appliance
(cook_region (:target flat_stove_1))
(top_side (:target microwave_1))

; Drawer region on articulated object
(top_region (:target wooden_cabinet_1))
(middle_region (:target wooden_cabinet_1))
(bottom_region (:target wooden_cabinet_1))
```

---

## 2. Goal Predicate Syntax

### 2.1 On (Surface Placement)

```lisp
; On object surface
(On object_instance target_object)
; Example: (On akita_black_bowl_1 plate_1)

; On fixture region  
(On object_instance fixture_region_name)
; Example: (On plate_1 main_table_stove_front_region)

; On object region
(On moka_pot_1 flat_stove_1_cook_region)
```

### 2.2 In (Container/Drawer)

```lisp
; In container
(In object_instance container_contain_region)
; Example: (In alphabet_soup_1 basket_1_contain_region)

; In drawer
(In object_instance cabinet_drawer_region)
; Example: (In akita_black_bowl_1 wooden_cabinet_1_top_region)
```

### 2.3 State (Articulated Objects)

```lisp
; Drawer/door state
(Open cabinet_drawer_region)
(Closed cabinet_drawer_region)
; Example: (Open wooden_cabinet_1_middle_region)

; Appliance state
(TurnedOn appliance)
(TurnedOff appliance)
; Example: (TurnedOn flat_stove_1)
```

### 2.4 Compound Goals

```lisp
(And
  (Predicate1 arg1 arg2)
  (Predicate2 arg3 arg4)
)
; Example:
(And
  (In akita_black_bowl_1 wooden_cabinet_1_top_region)
  (Closed wooden_cabinet_1_top_region)
)
```

---

## 3. Init Statement Syntax

### 3.1 Object Placement

```lisp
(On object_instance fixture_region_name)
; Example: (On plate_1 main_table_plate_region)
```

### 3.2 Initial States

```lisp
(Open drawer_region)
; Example: (Open wooden_cabinet_1_top_region)

(Closed drawer_region)
; Drawers default to Closed, usually not explicitly stated
```

---

## 4. Task Count Requirements

| Group | 2-Source | 3-Source | Total |
|-------|----------|----------|-------|
| ER-OBJECT | 10 | 10 | 20 |
| ER-GOAL | 10 | 10 | 20 |
| ER-SPATIAL | 10 | 10 | 20 |
| ER-SEQUENTIAL | 10 | 10 | 20 |
| **TOTAL** | **40** | **40** | **80** |

---

## 5. ER-OBJECT: Scene Context Composition

### 5.1 Section Operations

```yaml
input:
  source_A:  # Manipulation source
    provides: [L, G, O.manipulation, I]
  source_B:  # Scene source  
    provides: [F, R.fixture_regions, O.background, N.layout]

operations:
  F: REPLACE with B
  R: MERGE(B.fixture_regions, create_regions(A.manipulation_objects))
  O: MERGE(A.manipulation_objects, B.background_objects)
  N: MERGE(B.layout, create_placements(A.manipulation_objects))
  G: ADAPT(A.goal, new_region_names)
  L: KEEP(A.language)
  I: KEEP(A.obj_of_interest)
```

### 5.2 BDDL Generation Template

```lisp
; === ER-OBJECT TEMPLATE ===
(define (problem ER_OBJECT_task_name)
  (:domain robosuite)
  
  ; FROM SOURCE A: Keep language
  (:language {A.language})
  
  (:regions
    ; FROM SOURCE B: All fixture regions
    {for region in B.regions:}
    ({region.name} (:target {region.target}) (:ranges {region.ranges}))
    
    ; ADDED: Regions for A's manipulation objects
    {for obj in A.manipulation_objects:}
    ({obj.type}_init_region (:target {B.main_fixture}) (:ranges {allocated_coords}))
    
    ; ADDED: Container regions if A has containers
    {for container in A.containers:}
    (contain_region (:target {container}))
  )
  
  (:fixtures
    ; FROM SOURCE B: All fixtures
    {for f in B.fixtures:}
    {f.instance} - {f.type}
  )
  
  (:objects
    ; FROM SOURCE A: Manipulation objects
    {for obj in A.manipulation_objects:}
    {obj.instance} - {obj.type}
    
    ; FROM SOURCE B: Background objects (optional)
    {for obj in B.background_objects:}
    {obj.instance} - {obj.type}
  )
  
  (:obj_of_interest
    ; FROM SOURCE A
    {A.obj_of_interest}
  )
  
  (:init
    ; FROM SOURCE B: Fixture placements
    {for init in B.fixture_init:}
    {init}
    
    ; ADDED: A's object placements
    {for obj in A.manipulation_objects:}
    (On {obj.instance} {B.main_fixture}_{obj.type}_init_region)
  )
  
  (:goal
    ; FROM SOURCE A: Adapted goal
    {A.goal with region_names adapted to B}
  )
)
```

### 5.3 Concrete Example

**Source A**: `libero_object/pick_up_the_alphabet_soup_and_place_it_in_the_basket.bddl`
```lisp
(:language pick up the alphabet soup and place it in the basket)
(:fixtures floor_0 - floor)
(:objects alphabet_soup_1 - alphabet_soup, basket_1 - basket)
(:goal (In alphabet_soup_1 basket_1_contain_region))
```

**Source B**: `libero_90/KITCHEN_SCENE1_put_the_black_bowl_on_the_plate.bddl`
```lisp
(:fixtures kitchen_table - kitchen_table, wooden_cabinet_1 - wooden_cabinet)
(:regions 
  (plate_region (:target kitchen_table) (:ranges ...))
  (wooden_cabinet_init_region (:target kitchen_table) (:ranges ...))
)
(:objects akita_black_bowl_1 - akita_black_bowl, plate_1 - plate)
```

**Generated Output**:
```lisp
(define (problem ER_OBJECT_alphabet_soup_in_basket_kitchen_scene1)
  (:domain robosuite)
  (:language pick up the alphabet soup and place it in the basket)
  
  (:regions
    ; From B
    (plate_region (:target kitchen_table) (:ranges ((-0.01 -0.21 0.01 -0.19))))
    (wooden_cabinet_init_region (:target kitchen_table) (:ranges ((0.11 0.01 0.165 0.06))))
    ; Added for A's objects
    (alphabet_soup_init_region (:target kitchen_table) (:ranges ((-0.15 0.10 -0.10 0.15))))
    (basket_init_region (:target kitchen_table) (:ranges ((0.10 0.10 0.18 0.18))))
    (contain_region (:target basket_1))
  )
  
  (:fixtures
    kitchen_table - kitchen_table
    wooden_cabinet_1 - wooden_cabinet
  )
  
  (:objects
    alphabet_soup_1 - alphabet_soup
    basket_1 - basket
    plate_1 - plate
  )
  
  (:obj_of_interest
    alphabet_soup_1
    basket_1
  )
  
  (:init
    (On wooden_cabinet_1 kitchen_table_wooden_cabinet_init_region)
    (On alphabet_soup_1 kitchen_table_alphabet_soup_init_region)
    (On basket_1 kitchen_table_basket_init_region)
    (On plate_1 kitchen_table_plate_region)
  )
  
  (:goal
    (And (In alphabet_soup_1 basket_1_contain_region))
  )
)
```

---

## 6. ER-GOAL: Action-Object-Target Binding Composition

### 6.1 Section Operations

```yaml
input:
  source_A:  # Action pattern + scene
    provides: [F, R, O.scene, N, G_pattern, L_pattern]
  source_B:  # Substitute object
    provides: [O.substitute_object]

operations:
  F: KEEP(A.fixtures)
  R: KEEP(A.regions) + ADD_IF_NEW(region for B.object)
  O: KEEP(A.objects) + ADD_IF_NEW(B.object)
  N: KEEP(A.init) + ADD_IF_NEW(placement for B.object)
  G: SUBSTITUTE(A.G_pattern, A.target_object -> B.object)
  L: SUBSTITUTE(A.L_pattern, A.target_object -> B.object)
  I: UPDATE([B.object, A.goal_target])
```

### 6.2 BDDL Generation Template

```lisp
; === ER-GOAL TEMPLATE ===
(define (problem ER_GOAL_task_name)
  (:domain robosuite)
  
  ; FROM SOURCE A: Pattern with substitution
  (:language {A.L_pattern with A.target_object replaced by B.object_name})
  
  (:regions
    ; FROM SOURCE A: All regions
    {A.regions}
    
    ; ADDED IF NEW: Region for B's object
    {if B.object not in A.objects:}
    ({B.object_type}_region (:target {A.main_fixture}) (:ranges {coords}))
  )
  
  (:fixtures
    ; FROM SOURCE A: Same scene
    {A.fixtures}
  )
  
  (:objects
    ; FROM SOURCE A: All objects (B.object may already exist)
    {A.objects + B.object if not present}
  )
  
  (:obj_of_interest
    {B.object}
    {A.goal_target}
  )
  
  (:init
    ; FROM SOURCE A: Same layout
    {A.init}
    ; ADDED IF NEW
    {if B.object not in A.objects:}
    (On {B.object} {A.main_fixture}_{B.object_type}_region)
  )
  
  (:goal
    ; FROM SOURCE A: Pattern with substitution
    {A.G_pattern with A.target_object replaced by B.object}
  )
)
```

### 6.3 Concrete Example

**Source A**: `libero_goal/push_the_plate_to_the_front_of_the_stove.bddl`
```lisp
(:language push the plate to the front of the stove)
(:fixtures main_table - table, flat_stove_1 - flat_stove, ...)
(:regions (stove_front_region (:target main_table) ...))
(:objects plate_1 - plate, akita_black_bowl_1 - akita_black_bowl, ...)
(:goal (On plate_1 main_table_stove_front_region))
```

**Source B**: `libero_goal/put_the_bowl_on_the_plate.bddl`
```lisp
(:objects akita_black_bowl_1 - akita_black_bowl)
; Evidence: bowl is manipulable in training
```

**Generated Output**:
```lisp
(define (problem ER_GOAL_push_bowl_to_stove_front)
  (:domain robosuite)
  (:language push the bowl to the front of the stove)  ; plate -> bowl
  
  (:regions
    ; From A: All regions kept
    (plate_region (:target main_table) (:ranges ...))
    (akita_black_bowl_region (:target main_table) (:ranges ...))
    (stove_front_region (:target main_table) (:ranges ...))
    (wine_bottle_region (:target main_table) (:ranges ...))
    ; ... other regions
  )
  
  (:fixtures
    main_table - table
    wooden_cabinet_1 - wooden_cabinet
    flat_stove_1 - flat_stove
    wine_rack_1 - wine_rack
  )
  
  (:objects
    akita_black_bowl_1 - akita_black_bowl
    plate_1 - plate
    cream_cheese_1 - cream_cheese
    wine_bottle_1 - wine_bottle
  )
  
  (:obj_of_interest
    akita_black_bowl_1              ; B's object (substituted)
    main_table_stove_front_region   ; A's target
  )
  
  (:init
    (On akita_black_bowl_1 main_table_akita_black_bowl_region)
    (On plate_1 main_table_plate_region)
    (On cream_cheese_1 main_table_cream_cheese_region)
    (On wine_bottle_1 main_table_wine_bottle_region)
    (On wooden_cabinet_1 main_table_cabinet_region)
    (On flat_stove_1 main_table_stove_region)
    (On wine_rack_1 main_table_wine_rack_region)
  )
  
  (:goal
    (And (On akita_black_bowl_1 main_table_stove_front_region))  ; plate_1 -> bowl_1
  )
)
```

---

## 7. ER-SPATIAL: Spatial Relationship Composition

### 7.1 Section Operations

```yaml
input:
  source_A:  # Spatial pattern
    provides: [F, R, O.target, G, L_pattern.relation, original_landmark]
  source_B:  # New landmark
    provides: [O.new_landmark]

operations:
  F: KEEP(A.fixtures)
  R: MERGE(A.regions, region_for(B.landmark))
  O: MERGE(A.objects, B.landmark)
  N: REPOSITION(A.target, A.relation, B.landmark)  # Key spatial change
  G: KEEP(A.goal)  # Same destination
  L: SUBSTITUTE(A.L_pattern, A.landmark -> B.landmark)
  I: KEEP(A.obj_of_interest)
```

### 7.2 Spatial Relation Coordinate Offsets

```yaml
spatial_relations:
  next_to:
    offset: [-0.07, 0.0]  # 7cm left of landmark
    
  left_of:
    offset: [-0.10, 0.0]  # 10cm left
    
  right_of:
    offset: [0.10, 0.0]   # 10cm right
    
  in_front_of:
    offset: [0.0, -0.08]  # 8cm in front
    
  behind:
    offset: [0.0, 0.08]   # 8cm behind
    
  between:  # Requires two landmarks
    offset: midpoint(landmark1, landmark2)
```

### 7.3 BDDL Generation Template

```lisp
; === ER-SPATIAL TEMPLATE ===
(define (problem ER_SPATIAL_task_name)
  (:domain robosuite)
  
  ; FROM SOURCE A: Pattern with landmark substitution
  (:language {A.L_pattern with A.landmark replaced by B.landmark_name})
  
  (:regions
    ; FROM SOURCE A: Most regions
    {A.regions except target_object_region}
    
    ; MODIFIED: Target object repositioned
    ({A.target_type}_region 
      (:target {A.main_fixture})
      (:ranges {computed_from(A.relation, B.landmark_position)})
    )
    
    ; ADDED: Region for new landmark
    ({B.landmark_type}_region (:target {A.main_fixture}) (:ranges {B.coords}))
  )
  
  (:fixtures
    {A.fixtures}
  )
  
  (:objects
    ; FROM A + B's landmark
    {A.objects + B.landmark}
  )
  
  (:obj_of_interest
    {A.obj_of_interest}
  )
  
  (:init
    ; MODIFIED: Target repositioned
    (On {A.target} {A.main_fixture}_{A.target_type}_region)
    ; ADDED: Landmark placement
    (On {B.landmark} {A.main_fixture}_{B.landmark_type}_region)
    ; FROM A: Other init
    {A.other_init}
  )
  
  (:goal
    ; FROM SOURCE A: Same destination
    {A.goal}
  )
)
```

### 7.3 Concrete Example

**Source A**: `libero_spatial/pick_up_the_black_bowl_next_to_the_ramekin_and_place_it_on_the_plate.bddl`
```lisp
(:language pick up the black bowl next to the ramekin and place it on the plate)
(:regions 
  (akita_black_bowl_region (:target main_table) (:ranges ((-0.05 0.10 0.00 0.15))))
  (ramekin_region (:target main_table) (:ranges ((0.02 0.10 0.07 0.15))))
  (plate_region (:target main_table) (:ranges ...))
)
(:objects akita_black_bowl_1 - akita_black_bowl, glazed_rim_porcelain_ramekin_1 - glazed_rim_porcelain_ramekin, plate_1 - plate)
(:goal (On akita_black_bowl_1 plate_1))
```

**Source B**: `libero_90/KITCHEN_SCENE10_put_the_butter_on_top_of_the_cabinet.bddl`
```lisp
(:objects cookies_1 - cookies)
; cookie_box exists as landmark
```

**Generated Output**:
```lisp
(define (problem ER_SPATIAL_bowl_next_to_cookies)
  (:domain robosuite)
  (:language pick up the black bowl next to the cookie box and place it on the plate)
  
  (:regions
    ; MODIFIED: Bowl repositioned next_to cookies
    (akita_black_bowl_region 
      (:target main_table) 
      (:ranges ((-0.12 -0.05 -0.07 0.00)))  ; next_to offset from cookies
    )
    ; ADDED: Cookies region
    (cookies_region 
      (:target main_table) 
      (:ranges ((-0.05 -0.05 0.00 0.00)))
    )
    ; FROM A: Other regions
    (plate_region (:target main_table) (:ranges ((0.10 0.20 0.15 0.25))))
    ; ...
  )
  
  (:fixtures
    main_table - table
    wooden_cabinet_1 - wooden_cabinet
    flat_stove_1 - flat_stove
  )
  
  (:objects
    akita_black_bowl_1 - akita_black_bowl
    cookies_1 - cookies             ; From B
    plate_1 - plate
  )
  
  (:obj_of_interest
    akita_black_bowl_1
    plate_1
  )
  
  (:init
    (On akita_black_bowl_1 main_table_akita_black_bowl_region)  ; repositioned
    (On cookies_1 main_table_cookies_region)                     ; added
    (On plate_1 main_table_plate_region)
    ; ... fixture init
  )
  
  (:goal
    (And (On akita_black_bowl_1 plate_1))  ; Same goal
  )
)
```

---

## 8. ER-SEQUENTIAL: Temporal Composition

### 8.1 Section Operations

```yaml
input:
  source_A:  # Action 1
    provides: [F, R, O, N, G1, L1]
  source_B:  # Action 2
    provides: [O, G2, L2]
  source_C:  # Action 3 (optional)
    provides: [G3, L3]

operations:
  F: COMPATIBLE(A, B, C)  # Must share compatible fixtures
  R: MERGE(A.regions, B.regions, C.regions)
  O: MERGE(A.objects, B.objects, C.objects)
  N: MERGE(A.init, B.init, C.init)
  G: CONJOIN("(And G1 G2 G3)")  # Note: intermediate goals may be excluded
  L: CONCATENATE("L1 and L2 and L3")
  I: MERGE(A.I, B.I, C.I)
```

### 8.2 Goal Conjunction Rules

```yaml
goal_rules:
  # Intermediate goals that are undone are excluded
  exclude_if_undone:
    - "(Open drawer)" if followed by "(Closed drawer)"
    - "(TurnedOff X)" if followed by "(TurnedOn X)"
  
  # Final goal includes:
  include:
    - Object placement goals (In, On)
    - Final state of articulated objects
```

### 8.3 BDDL Generation Template (2-step)

```lisp
; === ER-SEQUENTIAL TEMPLATE (2-step) ===
(define (problem ER_SEQ_task_name)
  (:domain robosuite)
  
  ; CONCATENATED
  (:language {L1} and {L2})
  
  (:regions
    ; MERGED from all sources
    {A.regions ∪ B.regions}
  )
  
  (:fixtures
    ; COMPATIBLE scene
    {compatible_fixtures(A, B)}
  )
  
  (:objects
    ; MERGED
    {A.objects ∪ B.objects}
  )
  
  (:obj_of_interest
    ; MERGED
    {A.I ∪ B.I}
  )
  
  (:init
    ; MERGED initial states
    {A.init ∪ B.init}
  )
  
  (:goal
    ; CONJOINED (excluding undone intermediate states)
    (And 
      {G1 if not undone}
      {G2}
    )
  )
)
```

### 8.4 BDDL Generation Template (3-step)

```lisp
; === ER-SEQUENTIAL TEMPLATE (3-step) ===
(define (problem ER_SEQ_task_name)
  (:domain robosuite)
  
  (:language {L1}, {L2}, and {L3})
  
  (:regions
    {A.regions ∪ B.regions ∪ C.regions}
  )
  
  (:fixtures
    {compatible_fixtures(A, B, C)}
  )
  
  (:objects
    {A.objects ∪ B.objects ∪ C.objects}
  )
  
  (:obj_of_interest
    {A.I ∪ B.I ∪ C.I}
  )
  
  (:init
    {A.init ∪ B.init ∪ C.init}
  )
  
  (:goal
    (And 
      {final_goals_only}
    )
  )
)
```

### 8.5 Concrete Example (3-step)

**Source A**: `libero_90/KITCHEN_SCENE1_open_the_top_drawer_of_the_cabinet.bddl`
```lisp
(:language open the top drawer of the cabinet)
(:fixtures kitchen_table - kitchen_table, wooden_cabinet_1 - wooden_cabinet)
(:regions (top_region (:target wooden_cabinet_1)))
(:goal (Open wooden_cabinet_1_top_region))
```

**Source B**: `libero_90/KITCHEN_SCENE10_put_the_black_bowl_in_the_top_drawer_of_the_cabinet.bddl`
```lisp
(:language put the black bowl in the top drawer of the cabinet)
(:objects akita_black_bowl_1 - akita_black_bowl)
(:goal (In akita_black_bowl_1 wooden_cabinet_1_top_region))
```

**Source C**: `libero_90/KITCHEN_SCENE5_close_the_top_drawer_of_the_cabinet.bddl`
```lisp
(:language close the top drawer of the cabinet)
(:goal (Closed wooden_cabinet_1_top_region))
```

**Generated Output**:
```lisp
(define (problem ER_SEQ_open_put_bowl_close_drawer)
  (:domain robosuite)
  (:language open the top drawer, put the bowl in, and close it)
  
  (:regions
    ; From A+B: Drawer regions
    (top_region (:target wooden_cabinet_1))
    (middle_region (:target wooden_cabinet_1))
    (bottom_region (:target wooden_cabinet_1))
    ; From B: Bowl placement
    (akita_black_bowl_init_region (:target kitchen_table) (:ranges ((0.0 0.10 0.05 0.15))))
    ; Cabinet placement
    (wooden_cabinet_init_region (:target kitchen_table) (:ranges ((0.11 0.01 0.165 0.06))))
  )
  
  (:fixtures
    kitchen_table - kitchen_table
    wooden_cabinet_1 - wooden_cabinet
  )
  
  (:objects
    akita_black_bowl_1 - akita_black_bowl
  )
  
  (:obj_of_interest
    akita_black_bowl_1
    wooden_cabinet_1_top_region
  )
  
  (:init
    (On akita_black_bowl_1 kitchen_table_akita_black_bowl_init_region)
    (On wooden_cabinet_1 kitchen_table_wooden_cabinet_init_region)
  )
  
  (:goal
    (And 
      ; (Open ...) excluded - it's undone by Close
      (In akita_black_bowl_1 wooden_cabinet_1_top_region)  ; From B
      (Closed wooden_cabinet_1_top_region)                  ; From C (final state)
    )
  )
)
```

---

## 9. Summary Tables

### 9.1 Section Operations by Group

| Group | F | R | O | N | G | L | I |
|-------|---|---|---|---|---|---|---|
| **ER-OBJECT** | Replace(B) | Merge+Add | Merge | Merge+Add | Adapt | Keep(A) | Keep(A) |
| **ER-GOAL** | Keep(A) | Keep+Add | Keep+Add | Keep+Add | Substitute | Substitute | Update |
| **ER-SPATIAL** | Keep(A) | Merge | Merge | Reposition | Keep(A) | Substitute | Keep(A) |
| **ER-SEQUENTIAL** | Compatible | Merge | Merge | Merge | Conjoin | Concatenate | Merge |

### 9.2 What Changes vs What Stays

| Group | Changes | Stays Same | Tested Ability |
|-------|---------|------------|----------------|
| **ER-OBJECT** | F, R(fixture) | L, G, O(manip) | Visual context |
| **ER-GOAL** | G, L, I | F, R, N | Action binding |
| **ER-SPATIAL** | L(landmark), N | F, G | Spatial query |
| **ER-SEQUENTIAL** | G→And, L→concat | Atomic actions | Temporal chain |

---

## 10. Task Specification Format

### 10.1 YAML Schema

```yaml
# task_specs/er_{group}_tasks.yaml
version: "1.0"
group: ER-OBJECT | ER-GOAL | ER-SPATIAL | ER-SEQUENTIAL
task_count: 20

tasks:
  - id: unique_task_id
    num_sources: 2 | 3
    evaluated_ability: "description"
    
    sources:
      - id: A
        file: "libero_suite/task_name.bddl"
        role: manipulation_source | action_pattern | spatial_pattern | action_1
        provides:
          L: "language"
          G: "(goal predicate)"
          O: [object_list]
          I: [interest_list]
          
      - id: B  
        file: "libero_suite/task_name.bddl"
        role: scene_source | substitute_object | landmark | action_2
        provides:
          F: [fixture_list]
          R: [region_list]
          O: [object_list]
          
      - id: C  # optional for 3-source
        file: "libero_suite/task_name.bddl"
        role: ...
        provides: ...
    
    output:
      language: "final instruction"
      goal: "(And (Predicate ...))"
      
      regions:
        keep: [region_names from sources]
        add:
          - name: region_name
            target: fixture_or_object
            ranges: [[x1, y1, x2, y2]]  # if fixture-based
            
      objects:
        keep: [object_instances]
        add:
          - instance: object_1
            type: object_type
            
      init:
        keep: [init_statements]
        add:
          - "(On object region)"
        modify:
          - object: target_object
            new_region: repositioned_region
            
      obj_of_interest:
        - entity_1
        - entity_2
        
    validation:
      sources_exist: true
      objects_trained: true
      task_novel: true
      physically_feasible: true
```

### 10.2 Example Task Specification

```yaml
- id: er_goal_push_bowl_to_stove
  num_sources: 2
  evaluated_ability: "Apply push action to bowl instead of plate"
  
  sources:
    - id: A
      file: "libero_goal/push_the_plate_to_the_front_of_the_stove.bddl"
      role: action_pattern
      provides:
        L_pattern: "push the {X} to the front of the stove"
        G_pattern: "(On {X} main_table_stove_front_region)"
        original_target: plate_1
        F: [main_table, wooden_cabinet_1, flat_stove_1, wine_rack_1]
        R: [all regions]
        O: [plate_1, akita_black_bowl_1, cream_cheese_1, wine_bottle_1]
        N: [all init]
        
    - id: B
      file: "libero_goal/put_the_bowl_on_the_plate.bddl"
      role: substitute_object
      provides:
        O: [akita_black_bowl_1]
        substitute_for: plate_1
  
  output:
    language: "push the bowl to the front of the stove"
    goal: "(And (On akita_black_bowl_1 main_table_stove_front_region))"
    
    regions:
      keep: all_from_A
      
    objects:
      keep: all_from_A  # bowl already present
      
    init:
      keep: all_from_A
      
    obj_of_interest:
      - akita_black_bowl_1
      - main_table_stove_front_region
```

---

## 11. Validation Rules

```yaml
validation_checklist:
  pre_generation:
    - "All source BDDL files exist"
    - "All referenced objects exist in training"
    - "All region targets exist (fixtures or objects)"
    
  post_generation:
    - "BDDL syntax is valid"
    - "Goal predicates reference existing entities"
    - "Init placements use valid regions"
    - "Task is novel (not in training set)"
    - "Physical feasibility (no collisions, reachable)"
```

---

## 12. Generation Pipeline

```python
def generate_er_bddl(task_spec: dict) -> str:
    """Generate BDDL file from task specification."""
    
    # 1. Load source BDDL files
    sources = {}
    for src in task_spec['sources']:
        sources[src['id']] = parse_bddl(src['file'])
    
    # 2. Determine group-specific operations
    group = task_spec['group']
    
    # 3. Build output BDDL sections
    output = {
        'problem_name': f"ER_{group}_{task_spec['id']}",
        'domain': 'robosuite',
        'language': compute_language(task_spec, sources),
        'regions': compute_regions(task_spec, sources),
        'fixtures': compute_fixtures(task_spec, sources),
        'objects': compute_objects(task_spec, sources),
        'obj_of_interest': task_spec['output']['obj_of_interest'],
        'init': compute_init(task_spec, sources),
        'goal': task_spec['output']['goal'],
    }
    
    # 4. Validate
    validate_bddl(output)
    
    # 5. Render to string
    return render_bddl(output)
```
