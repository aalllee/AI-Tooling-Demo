# Writing equations

LLM generator for building linear equation problems of the form p = m × x (price = unit-price × quantity), with batched LLM explanations.
Single entry point: `generate.py`

Generates an array of UI ready practice problems in the same visual style as examples

## Quick start

```bash
# generate.py arguments: count (int), out_path (path)

# Create 200 practice problems 
python generate.py 200 output/problems.json

#validate generated items
#python validate.py <input.json> [--out <out.json>]

```

**Prereqs**

- Python ≥ 3.10  
- Claude CLI on `PATH` as `claude`.
 
---

# How generation works (logic)

- Always price on the y-axis: p (unit $).

- Choose one x-var per generated item: (kg, L, ...)

- Slope m is the unit price (integer 1–20).

- Table: unit_price ($m/x_unit), amount (x), total ($m·x).

- Graph: 5 integer x-ticks; y-ticks = m × x_ticks; two integer line_points on p = m x.

- Equation template: either "_ = _ * _" or "_ * _ = _".

- Tokens: 3–5 tokens; must include p, the chosen x_var, and const m; extra consts are incorrect choices.

- Answers: both valid orderings for the chosen template orientation

- Explanation: ≤ 2 short sentences; ends with the equation idea and mentions rate.

# Output format (shema)

Each element of the output array in JSON

```json
{
  "id": "lin-kg-001",
  "stem": {
    "prompt_text": "Create an equation that relates the price p and the weight w. Apples cost $6 per kilogram.",
    "context": {
      "y_var": "p", "y_name": "price", "y_unit": "$",
      "x_var": "w", "x_name": "weight", "x_unit": "kg", "x_unit_label": "kg",
      "item_name": "apples",
      "slope_m": 6
    }
  },
  "table": {
    "unit_price": { "value": 6, "display": "$6.00/kg" },
    "amount":     { "value": 3, "display": "3 kg" },
    "total":      { "value": 18, "display": "$18.00" }
  },
  "graph": {
    "x_axis": { "label": "weight (kg)", "ticks": [2,4,6,8,10] },
    "y_axis": { "label": "price ($)",   "ticks": [12,24,36,48,60] },
    "line_points": [[0,0],[10,60]]
  },
  "equation_template": "_ * _ = _",
  "tokens": [
    { "type":"const","label":"6","value":6 },
    { "type":"var","label":"p" },
    { "type":"var","label":"w" },
    { "type":"const","label":"4","value":4 }
  ],
  "answers": {
    "valid_fills": [["6","w","p"],["w","6","p"]],
    "canonical_str": "p=6*w"
  },
  "explanation": {
    "equation_str": "p=6×w",
    "text": "Get price p by multiplying weight w by $6 per kg."
  },
  "reasoned_answer": "6*w=p"
}

```

# Fields and UI mapping

- id → unique item id

- stem → Initial prompt / question

- table → rate/amount/total (formatted displays)

- graph → labels, ticks (5 per axis), and two points on the line p=m×x

- equation_template → two blanks the learner fills (orientation varies)

- tokens → draggable tiles; may include distractor constants

- answers → correct fill order(s) for the chosen template

- explanation → ≤ 2 sentences; concise, numeric; mentions variables and rate

- reasoned_answer → model-derived filled equation (e.g., 6*w=p) 

---
# Examples
Price per kg
```json
{
  "id":"lin-kg-001",
  "stem":{"prompt_text":"Create an equation that relates the price p and the weight w. Apples cost $6 per kilogram.",
          "context":{"y_var":"p","y_name":"price","y_unit":"$","x_var":"w","x_name":"weight","x_unit":"kg","x_unit_label":"kg","item_name":"apples","slope_m":6}},
  "table":{"unit_price":{"value":6,"display":"$6.00/kg"},"amount":{"value":3,"display":"3 kg"},"total":{"value":18,"display":"$18.00"}},
  "graph":{"x_axis":{"label":"weight (kg)","ticks":[2,4,6,8,10]},"y_axis":{"label":"price ($)","ticks":[12,24,36,48,60]},"line_points":[[0,0],[10,60]]},
  "equation_template":"_ * _ = _",
  "tokens":[{"type":"const","label":"6","value":6},{"type":"var","label":"p"},{"type":"var","label":"w"}],
  "answers":{"valid_fills":[["6","w","p"],["w","6","p"]],"canonical_str":"p=6*w"},
  "explanation":{"equation_str":"p=6×w","text":"Get price p by multiplying weight w by $6 per kg."},
  "reasoned_answer":"6*w=p"
}

```

price per Item

```json
{
  "id":"lin-pc-003",
  "stem":{"prompt_text":"Create an equation that relates the price p and the items n. Pencils cost $3 per item.",
          "context":{"y_var":"p","y_name":"price","y_unit":"$","x_var":"n","x_name":"items","x_unit":"pcs","x_unit_label":"pc","item_name":"pencils","slope_m":3}},
  "table":{"unit_price":{"value":3,"display":"$3.00/pc"},"amount":{"value":5,"display":"5 pcs"},"total":{"value":15,"display":"$15.00"}},
  "graph":{"x_axis":{"label":"items (pcs)","ticks":[2,4,6,8,10]},"y_axis":{"label":"price ($)","ticks":[6,12,18,24,30]},"line_points":[[0,0],[10,30]]},
  "equation_template":"_ = _ * _",
  "tokens":[{"type":"const","label":"3","value":3},{"type":"var","label":"p"},{"type":"var","label":"n"},{"type":"const","label":"7","value":7}],
  "answers":{"valid_fills":[["p","3","n"],["p","n","3"]],"canonical_str":"p=3*n"},
  "explanation":{"equation_str":"p=3×n","text":"Get price p by multiplying items n by $3 per pc."},
  "reasoned_answer":"p=3*n"
}

```