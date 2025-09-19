# AI-tooling-demo
# Tilted-Scales Puzzle Generator
 
Procedural generator for “balanced vs. tipped scale” logic puzzles with **batched** LLM explanations.  
Single entry point: `generate.py`.
 

 
## What this does
 
- **Generates** a JSON array of practice puzzles for two difficulties:
- **easy** — proportional or equal-k weighted balances; clean inequality.
- **difficult** — equal-k weighted balances; inequalities may include the **same extra shape on both sides** plus fixed weights.
- **Batches one LLM call** (Claude CLI) for all items to produce, per item:
- `explanation` — **≤ 2 short sentences**, plain shape/weight wording.
- `reasoned_answer` — the **filled inequality string** the LLM derives **on its own** (no spaces).
 
The output is **UI-ready**: the **top (balanced)** scale comes from `equality`, the **bottom (tipped)** scale from `inequality` + `ineq_template`, and `answer` holds the ground-truth variable order for the two blanks.
 

 
## Quick start
 
```bash
#Create 200 easy puzzles
python generate.py 200 easy data/easy.json

#Create 200 difficult puzzles
python generate.py 200 difficult data/difficult.json
```

**CLI**

| Arg          | Type | Values                 | Meaning                                   |
|--------------|------|------------------------|-------------------------------------------|
| `count`      | int  | 1–200                  | Number of puzzles to generate             |
| `difficulty` | str  | `easy` \| `difficult`  | Generator family                          |
| `out_path`   | str  | e.g., `data/easy.json` | Output file (parent directories created)  |
 
**Prereqs**

- Python ≥ 3.10  
- (Optional) Claude CLI on `PATH` as `claude` (if absent, items still generate; `explanation`/`reasoned_answer` may be empty).
 
---
 
## How generation works (logic)
 
### Shapes & terms
- Shapes: `s` = square, `t` = triangle, `c` = circle.  
- A pan (left/right) is `{ "shapes": {"s": INT, "t": INT, "c": INT}, "weight": INT }`.
 
### Equality (balanced top scale)
- **Proportional**: `k1*X = k2*Y` (no fixed weights).  
   “Needing fewer copies” ⇒ **heavier per unit**.
- **Equal-k weighted**: `k*X + wL = k*Y + wR`.  
  **Heavier added weight** ⇒ that side’s **unit shape is lighter**.
 
### Inequality (tipped bottom scale)
- Rendered via `ineq_template` with **two `_` blanks** (left, right).  
  Template may include literal add-ons like `+c`, `+t`, `+3`, etc.  
- `answer = ["X","Y"]` is the **true** variable order to fill the blanks (left→right).  
- The LLM **ignores** `answer` and derives its own `reasoned_answer`. You can later compare them in a validator.
 
---
 
## Output format (schema)
 
Each element of the output array:
 
```json
{
   "id": "difficult-007",
   "difficulty": "difficult",
   "equality": {
    "left":  { "shapes": { "s": 2, "t": 0, "c": 0 }, "weight": 8 },
    "right": { "shapes": { "s": 0, "t": 2, "c": 0 }, "weight": 14 }
  },
  "inequality": {
    "left":  { "shapes": { "s": 0, "t": 0, "c": 1 }, "weight": 3 },
    "right": { "shapes": { "s": 1, "t": 0, "c": 1 }, "weight": 5 },
    "op": ">"
  },
  "ineq_template": "_+c+3>_+c+5",
  "answer": ["s", "t"],
  "explanation": "Since s=t+3, cancel c; left adds 3 and right adds 5, square stays heavier. So s+c+3>t+c+5.",
  "reasoned_answer": "s+c+3>t+c+5"
}
```
 
### Fields and UI mapping
- **`equality`** → render as the **top balanced scale**.  
- **`inequality` + `ineq_template`** → render as the **bottom tipped scale**; fill the two `_` with variables to test.  
- **`answer`** → correct variable order for the two blanks (**left→right**).  
- **`explanation`** → ≤ 2 short sentences; **ends** with the final inequality (no spaces).  
- **`reasoned_answer`** → exact filled inequality string LLM derived (e.g., `s+c+3>t+c+5`).

---
 
## Batched explanations (fast path)
 
- The script builds a `{"items":[...]}` payload and calls Claude **once** with a batch prompt.  
- Expected LLM response: a JSON **array** of objects  
  `{ "index", "explanation", "reasoned_answer" }`.  
- The script merges by `index` back into your items and writes the final JSON.
 
> Because the LLM **derives** `reasoned_answer` without using `answer`, you can add a separate `validate.py` to flag items where `reasoned_answer` ≠ the inequality filled from `answer` + `ineq_template`.

---

## Suggested repo layout (agent-friendly)

```
.
├── generate.py
├── output/
│   ├── easy.json
│   └── difficult.json
├── SUMMARY.md      # ≤1 page: decisive metrics (e.g., items, % non-empty explanations, match rates)
├── DECISIONS.md    # 5–8 key trade-offs (batch vs. per-item LLM, representation, difficulty)
├── SPEC.md         # Problem representation spec + 3–5 examples (you can copy from this README)
└── docs/
    └── commands.md # one-shot commands for agents (generate, validate, summarize)
```

