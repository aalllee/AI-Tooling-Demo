# DECISIONS.md

---

## 1) Procedural generation vs. model-led generation
**Decision:** All puzzle logic (equations, templates, answers) is procedurally generated; the LLM is used only for short explanations (when the user presses "WHY?" button).

- **Pros**
  - Deterministic math games - correctness validated by construction.
  - Guaranteed solvability and vast variation; easy to scale and a wide combinatiorial range.
- **Cons**
  - Need to implement new helper functions for each puzzle template (it is still pretty fast).


---

## 2) Batched LLM calls vs. per-item calls
**Decision:** Explanations are requested in a **single batch** and merged by `index`.

- **Pros**
  - Faster and cheaper (1 request instead of N).
  - Stylistically consistent outputs.
- **Cons**
  - Harder to retry only a few items.

---

## 3) Representation: structured scales + template
**Decision:** Use structured **`equality`** / **`inequality`** (per-side shape counts + weight) plus an **`ineq_template`** with two `_` blanks.

- **Pros**
  - UI can render the **top balanced** scale from `equality`.
  - UI can render the **unsolved bottom** from `ineq_template`.
  - `inequality` dict represents the **solved** state; `answer` supplies the draggable tokens.
- **Cons**
  - Slight redundancy (template + solved dict + answer) can be fixed with a more compact UI representation.
---

## 4) Randomness vs. reproducibility
**Decision:** Use `random` ranges for breadth

- **Pros**
  - High variety across runs with no extra work.
  - Easy to widen ranges to expand coverage.
  - Guarantees integer values after equality simplification
- **Cons**
  - Needs a seed for reproducible puzzles.

---

## Summary
- **For this puzzle I found that having procedural functions will significantly minimize error rate.**, so **no extensive validation** is needed for equations or answers.
- **this method generates over 1k unique problems**
- **Only need to check if the LLM explanations make sense**