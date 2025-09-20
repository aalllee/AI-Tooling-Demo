# Tilted-Scales Puzzle Generator
 
Procedural generator for “balanced vs. tipped scale” logic puzzles with **batched** LLM explanations.  
Single entry point: `generate.py`.
 
 
## What this does
 
- **Generates** a JSON array of practice puzzles
 
## Quick start

```bash
#generate.py arguments: count (int), difficulty (easy | difficult), output path

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
- Claude CLI on `PATH` as `claude`.
 
---
 
## How generation works (logic)
 
### Shapes & terms
- Shapes: `s` = square, `t` = triangle, `c` = circle.  
- A pan (left/right) is `{ "shapes": {"s": INT, "t": INT, "c": INT}, "weight": INT }`.

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
- **`id`** → unique puzzle id
- **`difficulty`** → easy | difficult
- **`equality`** → render as the **top balanced scale**.  
- **`ineq_template`** → render as the **bottom tipped scale**; the `_` characters represent values to be filled in by the player.  
- **`answer`** → Interactive answer components. The answer array stores correct answer placement from left to right (can be randomized before rendering UI) (**left→right**).  
- **`explanation`** → ≤ 2 short sentences explaining Why? the solution is correct.  
- **`reasoned_answer`** → inequality string derived by the LLM (e.g., `s+c+3>t+c+5`). If this string doesn't match with the reasoned_answer then most likely the explanation part is incorrect. Can be used for validation.

---

## Example puzzles

## Proportional relationship puzzle 
```json
{
  "id": "easy-001",
  "difficulty": "easy",
  "equality": {
    "left":  { "shapes": { "s": 2, "t": 0, "c": 0 }, "weight": 0 },
    "right": { "shapes": { "s": 0, "t": 3, "c": 0 }, "weight": 0 }
  },
  "inequality": {
    "left":  { "shapes": { "s": 1, "t": 0, "c": 0 }, "weight": 0 },
    "right": { "shapes": { "s": 0, "t": 1, "c": 0 }, "weight": 0 },
    "op": ">"
  },
  "ineq_template": "_>_",
  "answer": ["s", "t"],
  "explanation": "It takes fewer squares than triangles to balance, so s>t. So s>t.",
  "reasoned_answer": "s>t"
}

```
- equality (top scale): `2*s = 3*t`
- inequality (tipped scale): `s>t`
- inequality template: `_>_`
- answer: `s (left), t (right) (the array ordering fills the template with the correct values from left to right)`
- LLM explanation: `It takes fewer squares than triangles to balance, so s>t. So s>t.`
- reasoned_answer: `s>t (we can check if it matches with the correct inequality var for validation)`

## Weighted offset puzzle 

```json
{
    "id": "easy-003",
    "difficulty": "easy",
    "equality": {
      "left": {"shapes": { "s": 1, "c": 0, "t": 0 }, "weight": 1},
      "right": { "shapes": {"s": 0,"c": 1,"t": 0}, "weight": 5}
    },
    "inequality": {
      "left": {"shapes": {"s": 0,"c": 1,"t": 0},"weight": 0},
      "right": {"shapes": {"s": 1,"c": 0,"t": 0},"weight": 0},
      "op": "<"
    },
    "ineq_template": "_<_",
    "answer": ["c","s"],
    "explanation": "From s+1=c+5, we get s=c+4, so s needs less added weight than c. c<s",
    "reasoned_answer": "c<s"
  }
```
- equality (top scale): `s + 1 = c + 5`
- inequality (tipped scale solution): `c<s`
- inequality template: `_<_`
- answer: `c (left), s (right) (the array ordering fills the template with the correct values from left to right)`
- LLM explanation: `From s+1=c+5, we get s=c+4, so s needs less added weight than c. c<s`
- reasoned_answer: `c<s (we can check if it matches with the correct inequality var for validation)`

## DIFFICULT PUZZLE EXAMPLE 

```json
{
    "id": "difficult-010",
    "difficulty": "difficult",
    "equality": {
      "left": {"shapes": {"c": 2,"t": 0,"s": 0}, "weight": 4},
      "right": {"shapes": {"c": 0,"t": 2,"s": 0},"weight": 8}
    },
    "inequality": {
      "left": {"shapes": {"c": 1, "t": 0,"s": 1}, "weight": 3},
      "right": {"shapes": {"c": 0,"t": 1,"s": 1}, "weight": 4}
    },
    "ineq_template": "_+s+3>_+s+4",
    "answer": [
      "c",
      "t"
    ],
    "explanation": "Since 2c+4=2t+8, circle is 2 lighter than triangle. Cancel s; left adds 3, right adds 4, circle still lighter. So c+s+3>t+s+4.",
    "reasoned_answer": "c+s+3>t+s+4"
  },
```

- equality: `2*c+4 = 2*t+8`
- inequality: `c+s+3 > t+c+4`
- inequality_template: `_+c+2>_+c+4`
- answer: `c (left), t (right)`


