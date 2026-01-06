# Libero-ER Grouping Rules & Definitions

This document defines the strict criteria for categorizing tasks into the four Experience Recombination (ER) dimensions using BDDL language.

## 0. BDDL Task Structure

Every LIBERO task is defined by these BDDL sections:

```lisp
(define (problem PROBLEM_NAME)
  (:domain robosuite)
  (:language L)        ; L = Language instruction
  (:regions R)         ; R = Placement and goal regions
  (:fixtures F)        ; F = Scene fixtures (table, cabinet, stove)
  (:objects O)         ; O = Manipulable objects
  (:obj_of_interest I) ; I = Task-relevant objects
  (:init N)            ; N = Initial state (object positions)
  (:goal G)            ; G = Goal condition
)
```

**Section Abbreviations**: F=Fixtures, R=Regions, O=Objects, N=Init, G=Goal, L=Language, I=Interest

---

## 1. Core ER Definition

**Experience Recombination** requires:
1. **All atomic components exist in training BDDL files**
2. **The complete test task is NOT in training**
3. **Test = novel RECOMBINATION of trained BDDL components**
4. **Each task combines 2 or 3 source BDDL files explicitly**

---

## 2. Task Count Requirements

| Group | 2-Source Tasks | 3-Source Tasks | Total |
|-------|---------------|----------------|-------|
| ER-OBJECT | 10 | 10 | 20 |
| ER-GOAL | 10 | 10 | 20 |
| ER-SPATIAL | 10 | 10 | 20 |
| ER-SEQUENTIAL | 10 (2-step) | 10 (3-step) | 20 |
| **TOTAL** | **40** | **40** | **80** |

---

## 3. ER Group Definitions (BDDL-Based)

### 3.1 Summary: What Changes vs What Stays

| Group | Changes | Stays Same | Novelty |
|-------|---------|------------|---------|
| **ER-OBJECT** | F, R(fixtures) | L, G, O(target) | Scene context |
| **ER-GOAL** | G, L, I | F, R, N | Action-object binding |
| **ER-SPATIAL** | L(landmark), N(positions) | F, G | Spatial query |
| **ER-SEQUENTIAL** | G→(And G1 G2), L→concat | Atomic actions | Temporal chain |

---

## 4. ER-OBJECT: Scene Context Composition

### Definition
**Maintain**: (Action × Object × Target) manipulation from Source A  
**Change**: (Fixtures × Regions) scene context from Source B

### BDDL Section Operations

| Section | Source A | Source B | Operation |
|---------|----------|----------|-----------|
| F (Fixtures) | — | ✓ | Replace with B |
| R (Regions) | Adapt | ✓ base | Merge + Adapt |
| O (Objects) | ✓ manip. | ✓ background | Merge |
| N (Init) | Adapt | ✓ layout | Merge + Adapt |
| G (Goal) | ✓ | — | Adapt region names |
| L (Language) | ✓ | — | Keep |
| I (Interest) | ✓ | — | Keep |

### Combination Pattern
```yaml
source_A:  # Provides MANIPULATION
  provides: [L, G, O.manipulation_objects, I]
  
source_B:  # Provides SCENE
  provides: [F, R.fixture_regions, O.background, N.fixture_init]

output:
  F: B.fixtures
  R: B.fixture_regions ∪ create_regions(A.objects, B.main_fixture)
  O: A.manipulation_objects ∪ B.background_objects
  N: B.fixture_init ∪ create_init(A.objects, B.main_fixture)
  G: adapt(A.goal, B.region_names)
  L: A.language
  I: A.obj_of_interest
```

### Task Numbers
- **10 two-source tasks**: A(manipulation) + B(scene)
- **10 three-source tasks**: A(action) + B(object) + C(scene)

### Example
```
Training A: put alphabet_soup in basket (floor scene)
Training B: KITCHEN_SCENE1 layout (kitchen fixtures)
Test: put alphabet_soup in basket (kitchen scene) ← Same manipulation, different F
```

---

## 5. ER-GOAL: Action-Object-Target Binding Composition

### Definition
**Maintain**: (Fixtures × Regions) scene from Source A  
**Change**: (Goal predicate) with object substitution

### BDDL Section Operations

| Section | Source A | Source B | Operation |
|---------|----------|----------|-----------|
| F (Fixtures) | ✓ | — | Keep |
| R (Regions) | ✓ | Add if needed | Keep + Add |
| O (Objects) | ✓ scene | ✓ substitute | Merge |
| N (Init) | ✓ | Add placement | Keep + Add |
| G (Goal) | pattern | ✓ object | Substitute |
| L (Language) | pattern | ✓ object | Substitute |
| I (Interest) | — | ✓ | Update |

### Combination Pattern
```yaml
source_A:  # Provides ACTION PATTERN + SCENE
  provides: [F, R, O.scene_objects, N, G_pattern, L_pattern]
  
source_B:  # Provides SUBSTITUTE OBJECT
  provides: [O.substitute_object]

output:
  F: A.fixtures
  R: A.regions ∪ region_if_new(B.object)
  O: A.objects ∪ {B.object}
  N: A.init ∪ placement_if_new(B.object)
  G: A.G_pattern[target := B.object]  # Substitution
  L: A.L_pattern[target := B.object]  # Substitution
  I: [B.object, A.goal_target]
```

### Task Numbers
- **10 two-source tasks**: A(action+scene) + B(object)
- **10 three-source tasks**: A(action) + B(object) + C(target)

### Example
```
Training A: push plate to stove_front (Goal scene)
Training B: bowl manipulation exists
Test: push bowl to stove_front ← G[plate:=bowl], L[plate:=bowl]
```

---

## 6. ER-SPATIAL: Spatial Relationship Composition

### Definition
**Maintain**: (Goal destination) where object ends up  
**Change**: (Language spatial query) with landmark substitution, (Init positions) repositioned

### BDDL Section Operations

| Section | Source A | Source B | Operation |
|---------|----------|----------|-----------|
| F (Fixtures) | ✓ | — | Keep |
| R (Regions) | ✓ | Add landmark | Merge |
| O (Objects) | ✓ target | ✓ landmark | Merge |
| N (Init) | — | — | Reposition |
| G (Goal) | ✓ | — | Keep |
| L (Language) | relation | ✓ landmark | Substitute |
| I (Interest) | ✓ | — | Keep |

### Combination Pattern
```yaml
source_A:  # Provides SPATIAL RELATION
  provides: [F, R, O.target_object, G, L_pattern.relation]
  
source_B:  # Provides NEW LANDMARK
  provides: [O.landmark]

output:
  F: A.fixtures
  R: A.regions ∪ region_for(B.landmark)
  O: A.objects ∪ {B.landmark}
  N: reposition(A.target, A.relation, B.landmark)  # Spatial repositioning
  G: A.goal  # Same destination
  L: A.L_pattern[landmark := B.landmark]
  I: A.obj_of_interest
```

### Task Numbers
- **10 two-source tasks**: A(relation) + B(landmark)
- **10 three-source tasks**: A(relation) + B(landmark1) + C(landmark2) for "between"

### Example
```
Training A: bowl next_to ramekin
Training B: cookie_box exists
Test: bowl next_to cookie_box ← L[ramekin:=cookie_box], N repositioned
```

---

## 7. ER-SEQUENTIAL: Temporal Composition

### Definition
**Maintain**: Each atomic action exists in training  
**Change**: (Goal) becomes conjunction, (Language) becomes concatenation

### BDDL Section Operations (2-step)

| Section | Source A | Source B | Operation |
|---------|----------|----------|-----------|
| F (Fixtures) | ✓ compat | ✓ compat | Intersect |
| R (Regions) | ✓ | ✓ | Merge |
| O (Objects) | ✓ | ✓ | Merge |
| N (Init) | ✓ | ✓ | Merge |
| G (Goal) | G1 | G2 | `(And G1 G2)` |
| L (Language) | L1 | L2 | "L1 and L2" |
| I (Interest) | ✓ | ✓ | Merge |

### BDDL Section Operations (3-step)

| Section | Source A | Source B | Source C | Operation |
|---------|----------|----------|----------|-----------|
| G (Goal) | G1 | G2 | G3 | `(And G1 G2 G3)` |
| L (Language) | L1 | L2 | L3 | "L1, L2, and L3" |

### Combination Pattern
```yaml
source_A:  # Provides ACTION_1
  provides: [F, R.action1, O.action1, N, G1, L1]
  
source_B:  # Provides ACTION_2
  provides: [O.action2, G2, L2]

source_C:  # (Optional) Provides ACTION_3
  provides: [G3, L3]

output:
  F: compatible_fixtures(A, B, C)
  R: A.regions ∪ B.regions ∪ C.regions
  O: A.objects ∪ B.objects ∪ C.objects
  N: merge_init(A, B, C)
  G: "(And G1 G2 G3)"  # Conjoined
  L: "L1 and L2 and L3"  # Concatenated
  I: merge(A.I, B.I, C.I)
```

### Task Numbers
- **10 two-source tasks**: 2-step sequences (A→B)
- **10 three-source tasks**: 3-step sequences (A→B→C)

### Example
```
Training A: open middle drawer
Training B: put bowl in drawer  
Training C: close drawer
Test: open drawer, put bowl in, and close it ← G=(And G1 G2 G3)
```

---

## 8. Region Types in BDDL

```yaml
region_types:
  fixture_region:
    target: fixture (main_table, floor, kitchen_table)
    has_ranges: true
    example: "(plate_region (:target main_table) (:ranges ((x1 y1 x2 y2))))"
    
  container_region:
    target: container object (basket_1, wooden_tray_1)
    has_ranges: false
    example: "(contain_region (:target basket_1))"
    goal_use: "(In object basket_1_contain_region)"
    
  surface_region:
    target: surface object (flat_stove_1)
    has_ranges: false
    example: "(cook_region (:target flat_stove_1))"
    goal_use: "(On object flat_stove_1_cook_region)"
    
  drawer_region:
    target: articulated object (wooden_cabinet_1)
    has_ranges: false
    example: "(middle_region (:target wooden_cabinet_1))"
    goal_use: "(In object wooden_cabinet_1_middle_region)"
```

---

## 9. Goal Predicates in BDDL

```yaml
goal_predicates:
  On:
    usage: "Object on surface/region"
    examples:
      - "(On bowl_1 plate_1)"                        # on surface object
      - "(On bowl_1 main_table_stove_front_region)"  # on fixture region
      - "(On pan_1 flat_stove_1_cook_region)"        # on object region
      
  In:
    usage: "Object inside container"
    examples:
      - "(In soup_1 basket_1_contain_region)"        # in container
      - "(In bowl_1 wooden_cabinet_1_top_region)"    # in drawer
      
  State:
    usage: "Object state change"
    examples:
      - "(Open wooden_cabinet_1_top_region)"
      - "(Closed wooden_cabinet_1_top_region)"
      - "(TurnedOn flat_stove_1)"
      - "(TurnedOff flat_stove_1)"
```

---

## 10. Task Definition Template

```yaml
task_id: unique_name
group: ER-OBJECT | ER-GOAL | ER-SPATIAL | ER-SEQUENTIAL
num_sources: 2 | 3
evaluated_ability: "What generalization is tested"

sources:
  - id: A
    file: path/to/bddl_A.bddl
    role: base_template | action_source | object_source | scene_source | landmark_source
    provides:
      sections: [F, R, O, N, G, L, I]  # which BDDL sections
      specific: [list of specific elements]
      
  - id: B
    file: path/to/bddl_B.bddl
    role: ...
    provides: ...
    
  - id: C  # for 3-source tasks
    file: path/to/bddl_C.bddl
    role: ...
    provides: ...

combination:
  F: "from A | from B | merge"
  R: 
    keep: [regions from sources]
    add: [{name, target, ranges}]
  O:
    keep: [objects]
    add: [{instance, type, placement}]
  N:
    keep: [init statements]
    add: [new placements]
    modify: [repositioned objects]
  G:
    operation: keep | substitute | conjoin
    result: "(BDDL goal)"
  L:
    operation: keep | substitute | concatenate
    result: "language instruction"
  I: [obj_of_interest list]

validation:
  sources_exist: true
  components_in_training: true
  task_not_in_training: true
  physically_feasible: true
```

---

## 11. Summary Matrix

| Dimension | BDDL Changes | Key Question | Novelty Type |
|-----------|--------------|--------------|--------------|
| **ER-OBJECT** | F, R(fixture) | Same manipulation in new scene? | Context shift |
| **ER-GOAL** | G, L, I | New (action×object) or (object×target)? | Binding |
| **ER-SPATIAL** | L(landmark), N | New (relation×landmark)? | Spatial query |
| **ER-SEQUENTIAL** | G→And, L→concat | New sequence of actions? | Temporal chain |
