# Libero-ER Grouping Rules & Definitions

This document defines the strict criteria for categorizing tasks into the four Embodied Reasoning (ER) dimensions. The goal is to ensure each suite tests a distinct capability of the agent.

## 1. ER-SEQUENTIAL (Temporal Composition)

**Definition**: Tasks where the *primary* challenge is executing a chain of multiple atomic primitives in a specific order.

**Rule**:
- **Must involve 2+ distinct atomic actions** (e.g., `open` then `put`, `pick` then `place` then `turn_off`).
- **OR involve multiple object manipulations** where the sequence matters or creates a long-horizon dependency (e.g., "put A in basket AND put B in basket").

**Why it belongs**:
- Even if the objects are novel, if the failure mode is likely "forgetting the second step" or "doing steps out of order", it is a Sequential test.
- We moved "Multi-object pairs" (Put A & Put B) here because they are fundamentally about sequencing two pick-and-place operations.

**Examples**:
- `open_the_middle_drawer_and_put_the_bowl_inside`: Combines `open` (atomic) + `put` (atomic).
- `put_both_milk_and_butter_in_basket`: Combines `put_milk` + `put_butter`.

---

## 2. ER-OBJECT (Object Context Composition)

**Definition**: Tasks where the *primary* challenge is recognizing and manipulating a known object in a novel visual context or recognizing a novel object instance for a known action.

**Rule**:
- **Action must be a SINGLE primitive** (e.g., `put_on`, `pick_up`).
- **Must be a SIGNIFICANT Context Shift**:
    - **Cross-Suite Swap**: Object trained in `Libero-Object` (clean background) tested in `Libero-90` (cluttered/textured background), or vice-versa.
    - **Cross-Domain Swap**: Object trained in `Kitchen` tested in `Living Room` or `Study`.
    - *Note*: Small swaps (e.g., Scene 1 to Scene 2 within the same room type) are **NOT sufficient** if visual similarity is high.

**Why it belongs**:
- Tests visual robustness (invariance to lighting/background) and object segmentation in clutter.

**Examples**:
- `KITCHEN_SCENE1_pick_up_alphabet_soup_...`:
    - *Training*: `alphabet_soup` seen on grey tabletop (Libero-Object).
    - *Test*: `alphabet_soup` seen on wooden kitchen counter (Libero-90). **Strong visual shift.**
- `libero_object_pick_up_moka_pot_and_place_in_basket`:
    - *Training*: `moka_pot` seen in Kitchen scenes.
    - *Test*: `moka_pot` seen on clean tabletop.

---

## 3. ER-GOAL (Goal/Binding Composition)

**Definition**: Tasks where the *primary* challenge is creating a novel logical binding between a known action and a known target/object.

**Rule**:
- **Action must be SINGLE primitive**.
- **Must be a novel (Action, Object) or (Object, Target) pair**:
    - **Action x Object**: Agent knows `push(plate)` and `pick(bowl)`. Test: `push(bowl)`.
    - **Object x Target**: Agent knows `put(bowl, shelf)` and `open(drawer)`. Test: `put(bowl, drawer)`.

**Difference from ER-OBJECT**:
- ER-OBJECT tests *perception* ("Can I see the bowl here?").
- ER-GOAL tests *policy logic* ("Can I apply the 'push' motor primitive to the 'bowl' object?").

**Examples**:
- `put_the_bowl_in_the_middle_drawer`:
    - *Training*: `put_bowl` (on plate/shelf), `open_middle_drawer`.
    - *Test*: Binding `bowl` to `middle_drawer` container.
- `push_the_bowl_to_the_front_of_the_stove`:
    - *Training*: `push_plate`.
    - *Test*: Applying `push` dynamics to `bowl`.

---

## 4. ER-SPATIAL (Spatial Composition)

**Definition**: Tasks where the *primary* challenge is resolving a spatial query to identify the correct target or destination.

**Rule**:
- **Action is standard (usually Pick-Place)**.
- **Discriminator must be spatial**: The target is defined *relative* to another object (`next_to`, `between`) or by an intrinsic attribute (`top` vs `bottom` drawer) that requires geometric understanding.

**Why it belongs**:
- The difficulty isn't the manipulation (it's just pick-place) or the object identity (usually simple blocks/bowls), but parsing "left of the plate" vs "right of the plate".

**Examples**:
- `pick_up_the_black_bowl_next_to_the_cookie_box`:
    - *Training*: `next_to` seen with ramekin. `cookie_box` seen as object.
    - *Test*: Generalizing the `next_to` relation to a new landmark (`cookie_box`).
- `put_the_white_mug_on_the_right_plate`:
    - Requires distinguishing `right_plate` from `left_plate`.

---

## Summary Matrix

| Dimension | Complexity Source | Key Question |
|-----------|-------------------|--------------|
| **SEQUENTIAL** | Time / Steps | Can you chain A then B? |
| **OBJECT** | Perception / Context | Can you recognize X in a new place (Cross-Domain)? |
| **GOAL** | Logic / Binding | Can you do action A on object B? |
| **SPATIAL** | Geometry / Relations | Can you find X relative to Y? |
