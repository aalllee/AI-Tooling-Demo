#!/usr/bin/env python3
"""
generate.py — Linear Price Puzzles (LLM-heavy, price per kg / L / item)

This script generates a batch of **linear price problems** of the form p = m * x,
where p is total price ($), x is **weight (kg)** or **volume (L)** or **items (pcs)**,
and m is the **unit price** ($ per unit).

It uses the Claude CLI in a single **batched** call to produce:
- prompt text, table (rate/amount/total), graph (axes + two line points),
- equation template (two orientations), draggable tokens (incl. distractors),
- answers (both valid orientations), and a concise explanation.

USAGE
  python generate.py <count> <out_path>

EXAMPLE
  python generate.py 20 data/linear_price.json

REQUIREMENTS
  - Python 3.10+
  - Claude CLI available as `claude` on PATH (or set CLAUDE_CLI=/path/to/claude)

VALIDATION
  Use the companion validate.py to filter/keep only 100% correct items.
"""

import sys
import json
import pathlib
import shutil
import tempfile
import subprocess
import os

# -------------------- CLI --------------------

def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)

if len(sys.argv) != 2 and len(sys.argv) != 3:
    die("Usage: python generate.py <count> <out_path>")

count_raw = sys.argv[1]
try:
    COUNT = int(count_raw)
    assert 1 <= COUNT <= 500
except Exception:
    die("count must be an integer between 1 and 500")

if len(sys.argv) == 3:
    OUT_PATH = pathlib.Path(sys.argv[2])
else:
    OUT_PATH = pathlib.Path("data/linear_price.json")

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
CLAUDE_CLI = os.environ.get("CLAUDE_CLI", "claude")


# -------------------- Batch Prompt --------------------

def build_batch_prompt(n: int) -> str:
    """
    Batched prompt for Claude (price problems with variety):
      - Always p = m * x with p in dollars ($).
      - Choose exactly one mode per item from:
          * per_kg  : x_var=w, x_name=weight, x_unit=kg, unit label "/kg"
          * per_L   : x_var=v, x_name=volume, x_unit=L,  unit label "/L"
          * per_item: x_var=n, x_name=items,  x_unit=pcs, unit label "/pc"
      - Two templates allowed: "_ = _ * _" OR "_ * _ = _" (flipped).
      - 3..5 tokens: must include p, chosen x_var, and const m; optional distractor consts.
      - Graph uses integer ticks: 5 x-ticks and corresponding y-ticks = m * x.
    """
    return f"""
You are generating Brilliant-style **price** linear problems (p = m * x). Output **JSON ONLY**.

CONTEXT (price-only; do NOT use distance/time/speed/etc.)
- y (dependent) is **price p** with unit **$**.
- x (independent) is **one** of:
  1) **weight w** in **kg**   (per_kg)
  2) **volume v** in **L**    (per_L)
  3) **items n** in **pcs**   (per_item)
- Realistic items measurable in kg/L/pcs:
  bananas, apples, rice, flour, oats, beans, sugar, coffee, tea, cheese, tomatoes, potatoes, onions, butter, water, milk, juice, yogurt, canned beans, pencils, screws.

GOAL
Produce N={n} **unique, solvable** items that include: prompt, table, graph, equation template,
drag tokens (with distractor constants), answers, and a concise explanation.

STRICT OUTPUT
Return **ONE JSON ARRAY** of length {n}. No commentary, no markdown.

SCHEMA (each element)
{{
  "id": "lin-###",   // unique id (zero-padded ok)

  "stem": {{
    "prompt_text": "Create an equation that relates the price p and the {{x_name}} {{x_var}}. {{item_name}} costs ${{slope_m}} per {{x_unit_label}}.",
    "context": {{
      "y_var": "p", "y_name": "price", "y_unit": "$",

      // Choose exactly one mode and keep consistent everywhere below:
      // per_kg   → x_var="w", x_name="weight", x_unit="kg", x_unit_label="kg"
      // per_L    → x_var="v", x_name="volume", x_unit="L",  x_unit_label="L"
      // per_item → x_var="n", x_name="items",  x_unit="pcs",x_unit_label="pc"
      "x_var": "w",
      "x_name": "weight",
      "x_unit": "kg",
      "x_unit_label": "kg",

      "item_name": "bananas",
      "slope_m": 8        // integer 1..20 (unit price)
    }}
  }},

  "table": {{
    // Treat unit_price as the 'rate' row: display string MUST include ${{slope_m}} and '/{{x_unit_label}}'
    "unit_price": {{ "value": 8, "display": "$8.00/kg" }},
    // amount is an x-value
    "amount":     {{ "value": 2, "display": "2 kg" }},
    // total is a y-value = slope_m * amount
    "total":      {{ "value": 16, "display": "$16.00" }}
  }},

  "graph": {{
    "x_axis": {{ "label": "{{x_name}} ({{x_unit}})", "ticks": [2,4,6,8,10] }},
    "y_axis": {{ "label": "price ($)",               "ticks": [8,16,24,32,40] }},
    "line_points": [[0,0],[10,80]]    // any two distinct integer points on p = m*x
  }},

  // EITHER "_ = _ * _" OR "_ * _ = _"
  "equation_template": "_ = _ * _",

  // 3..5 tokens total. MUST include var "p", var x_var, and const slope_m.
  // Extra tokens are distractor consts (1..20, not equal to slope_m). No duplicate labels.
  "tokens": [
    {{ "type":"const", "label":"8", "value":8 }},
    {{ "type":"var",  "label":"p" }},
    {{ "type":"var",  "label":"w" }},
    {{ "type":"const", "label":"5", "value":5 }}
  ],

  "answers": {{
    // valid_fills must match template orientation using actual x_var:
    // For "_ = _ * _" → [["p","{{slope_m}}","x_var"], ["p","x_var","{{slope_m}}"]]
    // For "_ * _ = _" → [["{{slope_m}}","x_var","p"], ["x_var","{{slope_m}}","p"]]
    "valid_fills": [["p","8","w"], ["p","w","8"]],
    // canonical_str is always "p={{slope_m}}*x_var" (no spaces) OR "{{slope_m}}*x_var=p"
    "canonical_str": "p=8*w"
  }},

  "explanation": {{
    "equation_str": "p=8×w",
    "text": "Get price p by multiplying {{x_name}} {{x_var}} by $8 per {{x_unit_label}}."   // ≤ 2 short sentences
  }}
}}

CONSTRAINTS (hard)
- This is **price-only**: y_var='p', y_unit='$'. Do **not** produce non-price relationships.
- Exactly one mode per item:
  * per_kg   → x_var='w', x_name='weight', x_unit='kg', x_unit_label='kg'
  * per_L    → x_var='v', x_name='volume', x_unit='L',  x_unit_label='L'
  * per_item → x_var='n', x_name='items',  x_unit='pcs',x_unit_label='pc'
- slope_m ∈ [1..20]. amount.value ∈ [1..10]. total.value == slope_m * amount.value.
- unit_price.display MUST include '${{slope_m}}' and '/{{x_unit_label}}' (e.g., '$8.00/kg', '$5.00/L', '$3.00/pc').
- amount.display MUST include '{{amount.value}} {{x_unit}}' (e.g., '3 kg', '4 L', '5 pcs').
- total.display MUST start with '$' and include total.value (e.g., '$16.00').
- graph:
  * x_axis.label == '{{x_name}} ({{x_unit}})' exactly.
  * y_axis.label == 'price ($)' exactly.
  * x_ticks: exactly 5 positive, strictly increasing integers.
  * y_ticks: exactly 5 integers with y_ticks[i] == slope_m * x_ticks[i].
  * line_points: two distinct integer points (x,y) with y == slope_m * x.
- equation_template ∈ {{"_ = _ * _", "_ * _ = _"}}.
- tokens length ∈ [3..5]. Must include var 'p', var x_var, and const slope_m; distractors are const 1..20 != slope_m; labels unique.
- answers.valid_fills MUST include both correct orderings for the chosen template orientation (using actual x_var).
- answers.canonical_str MUST be either "p={{slope_m}}*x_var" or "{{slope_m}}*x_var=p".
- explanation: ≤ 2 short sentences; must mention p, the chosen x_var, and either "$" or the numeric slope (e.g., '$8 per kg').

STYLE & VARIETY
- Vary item_name among foods/goods measurable in kg/L/pcs.
- Vary which mode (per_kg / per_L / per_item), slope_m, amount, and tick steps.
- Keep axes clean (exactly 5 ticks each); integers only; concise voice.

EXAMPLES (do not copy numbers verbatim)
[
  {{
    "id": "lin-kg-001",
    "stem": {{
      "prompt_text": "Create an equation that relates the price p and the weight w. Apples cost $6 per kilogram.",
      "context": {{"y_var":"p","y_name":"price","y_unit":"$","x_var":"w","x_name":"weight","x_unit":"kg","x_unit_label":"kg","item_name":"apples","slope_m":6}}
    }},
    "table": {{"unit_price":{{"value":6,"display":"$6.00/kg"}},"amount":{{"value":3,"display":"3 kg"}},"total":{{"value":18,"display":"$18.00"}}}},
    "graph": {{
      "x_axis": {{"label":"weight (kg)","ticks":[2,4,6,8,10]}},
      "y_axis": {{"label":"price ($)","ticks":[12,24,36,48,60]}},
      "line_points": [[0,0],[10,60]]
    }},
    "equation_template": "_ * _ = _",
    "tokens": [
      {{"type":"const","label":"6","value":6}},
      {{"type":"var","label":"p"}},
      {{"type":"var","label":"w"}},
      {{"type":"const","label":"4","value":4}}
    ],
    "answers": {{"valid_fills":[["6","w","p"],["w","6","p"]],"canonical_str":"p=6*w"}},
    "explanation": {{"equation_str":"p=6×w","text":"Get price p by multiplying weight w by $6 per kg."}}
  }},
  {{
    "id": "lin-L-002",
    "stem": {{
      "prompt_text": "Create an equation that relates the price p and the volume v. Milk costs $5 per liter.",
      "context": {{"y_var":"p","y_name":"price","y_unit":"$","x_var":"v","x_name":"volume","x_unit":"L","x_unit_label":"L","item_name":"milk","slope_m":5}}
    }},
    "table": {{"unit_price":{{"value":5,"display":"$5.00/L"}},"amount":{{"value":4,"display":"4 L"}},"total":{{"value":20,"display":"$20.00"}}}},
    "graph": {{
      "x_axis": {{"label":"volume (L)","ticks":[2,4,6,8,10]}},
      "y_axis": {{"label":"price ($)","ticks":[10,20,30,40,50]}},
      "line_points": [[0,0],[10,50]]
    }},
    "equation_template": "_ = _ * _",
    "tokens": [
      {{"type":"const","label":"5","value":5}},
      {{"type":"var","label":"p"}},
      {{"type":"var","label":"v"}}
    ],
    "answers": {{"valid_fills":[["p","5","v"],["p","v","5"]],"canonical_str":"p=5*v"}},
    "explanation": {{"equation_str":"p=5×v","text":"Get price p by multiplying volume v by $5 per L."}}
  }},
  {{
    "id": "lin-pc-003",
    "stem": {{
      "prompt_text": "Create an equation that relates the price p and the items n. Pencils cost $3 per item.",
      "context": {{"y_var":"p","y_name":"price","y_unit":"$","x_var":"n","x_name":"items","x_unit":"pcs","x_unit_label":"pc","item_name":"pencils","slope_m":3}}
    }},
    "table": {{"unit_price":{{"value":3,"display":"$3.00/pc"}},"amount":{{"value":5,"display":"5 pcs"}},"total":{{"value":15,"display":"$15.00"}}}},
    "graph": {{
      "x_axis": {{"label":"items (pcs)","ticks":[2,4,6,8,10]}},
      "y_axis": {{"label":"price ($)","ticks":[6,12,18,24,30]}},
      "line_points": [[0,0],[10,30]]
    }},
    "equation_template": "_ = _ * _",
    "tokens": [
      {{"type":"const","label":"3","value":3}},
      {{"type":"var","label":"p"}},
      {{"type":"var","label":"n"}},
      {{"type":"const","label":"7","value":7}}
    ],
    "answers": {{"valid_fills":[["p","3","n"],["p","n","3"]],"canonical_str":"p=3*n"}},
    "explanation": {{"equation_str":"p=3×n","text":"Get price p by multiplying items n by $3 per pc."}}
  }}
]

GENERATE NOW
- Produce exactly {n} items; JSON array only.
""".strip()


# -------------------- LLM Call --------------------

def call_claude(prompt: str) -> str:
    try:
        res = subprocess.run(
            [CLAUDE_CLI, "-p", "--output-format", "text", prompt],
            capture_output=True, text=True
        )
    except FileNotFoundError:
        die("Claude CLI not found. Install it or set CLAUDE_CLI=/path/to/claude", 127)

    if res.returncode != 0:
        die(f"Claude CLI failed:\n{res.stderr}\n{res.stdout}", res.returncode)
    return res.stdout.strip()


# -------------------- MAIN --------------------

def main():
    prompt = build_batch_prompt(COUNT)
    raw = call_claude(prompt)

    # Extract the largest JSON array substring if extra text slips in
    try:
        start = raw.find("[")
        end = raw.rfind("]")
        assert start != -1 and end != -1 and end > start
        payload = raw[start:end+1]
        items = json.loads(payload)
    except Exception as e:
        die(f"Failed to parse JSON array from LLM output: {e}\n--- RAW BEGIN ---\n{raw[:1200]}\n--- RAW END ---", 5)

    # (No validation here) — write as-is
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(OUT_PATH.parent)) as tf:
        tmp = tf.name
        json.dump(items, tf, ensure_ascii=False, indent=2)
        tf.write("\n")
    shutil.move(tmp, OUT_PATH)
    print(f"Wrote {OUT_PATH.resolve()} (items: {len(items)})")

if __name__ == "__main__":
    main()
