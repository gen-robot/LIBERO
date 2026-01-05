# LIBERO-ER (Embodied Reasoning) Benchmark

Compositional Generalization benchmarks built on the Libero dataset suite, utilizing Experience Recombination to evaluate embodied reasoning ability.

## Core Definition

**Experience Recombination** requires:
1. **All atomic components seen in training** (actions, objects, targets, relations, scenes)
2. **The complete test task NOT in training**
3. **Test = novel RECOMBINATION of trained components**

---

## ER Dimensions (4 Dimensions)

| Dimension | Suite | Question Answered | Count |
|-----------|-------|-------------------|-------|
| **Sequential** | ER-SEQUENTIAL | Can agent chain primitives into novel sequences? | 36 |
| **Spatial** | ER-SPATIAL | Can agent understand spatial relations and positional attributes? | 25 |
| **Goal** | ER-GOAL | Can agent achieve goals with novel action/object/target bindings? | 23 |
| **Object** | ER-OBJECT | Can agent manipulate objects in novel contexts? | 21 |

---

## Unified Training Set (116 tasks)

| Source | Count | Purpose |
|--------|-------|---------|
| **L90** | 90 | Base primitives |
| **L10 subset** | 4 | Sequential + multi-object pattern |
| **L-Object (ALL)** | 10 | All objects including bbq_sauce |
| **L-Goal** | 7 | Scene + push + middle_drawer + bowl_receptacle |
| **L-Spatial exposure** | 5 | Novel objects + relations |
| **Total** | **116** | |

---

## ER Test Suites

^ tasks)

**Dimension**: Temporal/sequential composition
**Tests**: Can the agent chain primitives into novel sequences?

| Type | Count | Examples |
|------|-------|----------|
| **Multi-step (existing)** | 6 | put_both_soup_and_cream_in_basket |
| **2-step novel** | 4 | open_middle_drawer + put_bowl_inside |
| **3-step novel** | 4 | open + place + close, turn_on + place + turn_off |
| **Multi-object pairs** | 8 | put_milk_and_butter, put_ketchup_and_pudding |
| **Cross-scene pattern** | 2 | open+place pattern from SCENE4→SCENE1 |
| **Explicit Chains** | 8 | open_drawer_and_put_mug, turn_off_and_put_bowl |

**Key Change**: "Multi-object pair" tasks (Put A and Put B) are now categorized here as they represent a sequence of two atomic tasks.

U tasks)

**Dimension**: Spatial/positional understanding
**Tests**: Can agent understand spatial relations AND positional attributes?

| Category | Count | Examples |
|----------|-------|----------|
| **Relation × Landmark** | 13 | next_to × cookie_box, left_of × ramekin |
| **Attribute × Object** | 12 | **white_mug × right_plate**, **book × back_caddy** |

**Focus**: The discriminator is the spatial query (identifying the correct target), not the manipulation complexity.

S tasks)

**Dimension**: Goal/action/target binding
**Tests**: Can agent achieve goals with novel action/object/target combinations?

| Category | Count | Examples |
|----------|-------|----------|
| **Action × Object** | 5 | push × bowl, push × wine_bottle |
| **Object × Target** | 18 | bowl → middle_drawer, moka_pot → middle_drawer, butter → top_cabinet |

**Refinement**: Removed explicit multi-step sequences. Added novel object placements on stove, cabinet, and shelves.

Q tasks)

**Dimension**: Object context composition
**Tests**: Can agent manipulate objects in novel contexts or combinations?

| Category | Count | Examples |
|----------|-------|----------|
| **Object-scene swaps** | 25 | butter in SCENE1, wine in SCENE1, bowl on stove (SCENE3) |

**Definition**: Strictly single-step tasks where the complexity is the novel object appearance or scene context for a known skill.

---

## File Structure

```
Libero-ER/
├── README.md              # This file
├── unified_training.csv   # Training set (116 tasks)
├── ER_sequential.csv      # Temporal composition
├── ER_spatial.csv         # Spatial understanding
├── ER_goal.csv            # Goal/action binding
├── ER_object.csv          # Object contexts
└── task_issues_and_proposals.md # Notes on physical constraints
```
