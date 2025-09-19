# DECISIONS.md

Key trade-offs for the Tilted-Scales puzzle generator.

---

## 1) Procedural generation vs. model-led generation
**Decision:** All puzzle logic (equations, templates, answers) is **procedurally generated**; the LLM is used only for short explanations (when the user presses "WHY?" button).

- **Pros**
  - Deterministic math → minimal validation for correctness.
  - Guaranteed solvability; easy to scale and control coverage.
- **Cons**
  - Variety limited to implemented patterns.
  - Adding new puzzle families requires code changes.

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
  - `inequality` mirrors the **solved** state; `answer` supplies the draggable tokens.
- **Cons**
  - Slight redundancy (template + solved dict + answer).
---

## 4) Randomness vs. reproducibility
**Decision:** Use `random` ranges for breadth; allow optional seeding.

- **Pros**
  - High variety across runs with no extra work.
  - Easy to widen ranges to expand coverage.
- **Cons**
  - Non-deterministic by default (hard to diff).
  - Needs a seed for reproducible CI.

---

## Summary
- **Most logic is procedural and deterministic**, so **no extensive validation** is needed for equations or answers.
- **Only validate the LLM output**: ensure `reasoned_answer` matches the true solution (filled from `answer` + `ineq_template`).
