#!/usr/bin/env python3
# Usage: python generate.py <count> <difficulty: easy | difficult> <out_path>

import sys, subprocess, pathlib, json, shutil, tempfile, random

def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr)
    sys.exit(code)

if len(sys.argv) != 4:
    die("Usage: python generate.py <count> <difficulty: easy|difficult> <out_path>")

count_raw, difficulty, out_path = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
try:
    count = int(count_raw)
    assert 1 <= count <= 200
except Exception:
    die("count must be an integer between 1 and 200")

if difficulty not in {"easy", "difficult"}:
    die("difficulty must be one of: easy | difficult")

path = pathlib.Path(out_path)
path.parent.mkdir(parents=True, exist_ok=True)


#-------------GLOBALS----------------

SHAPES = ["s", "t", "c"]
SHAPE_WORD = {"s": "square", "t": "triangle", "c": "circle"}


def _pick_distinct(vars_list, n):
    return random.sample(vars_list, n)


#-------------EASY PUZZLES HELPER FUNCTIONS-------

#GENERATE EASY EQUATION IN THE FORM k1X + k3Z = k2Y + k3Z 
def easy_puzzle_proportional_equality():
    shapes = _pick_distinct(SHAPES,3)
    X = shapes[0]
    Y = shapes[1]
    Z = shapes[2]
    k1 = random.randint(1, 6)
    choices = [v for v in range(1, 7) if v != k1]
    k2 = random.choice(choices)
    k3 = 0
    
   
    equality = {
    "left":  { "shapes": {X:k1, Y:0, Z:k3}, "weight": 0 },
    "right": { "shapes": {X:0, Y:k2, Z:k3}, "weight": 0 },
    }
    
  
    #Add third shape to both sides 50/50 chance
    if(random.random() > 0.5):
        k3 = random.randint(1, 4)
        equality["left"]["shapes"][Z] = k3
        equality["right"]["shapes"][Z] = k3
    
    #GEN Inequality
    op = '>'
    if(random.random()>0.5):
        op = '<'
    
    inequality_template = '_'+op+'_'

    answer = []
    if k1 < k2: #X > Y
        if op=='<':
            answer = [Y,X]
        else:
            answer = [X,Y]
    else: #Y > X
        if op=='<':
            answer = [X,Y]
        else:
            answer = [Y,X]


    inequality = {
    "left":  { "shapes": {X:0, Y:0, Z:0}, "weight": 0 },
    "right": { "shapes": {X:0, Y:0, Z:0}, "weight": 0 },
    "op": op
    }

    inequality["left"]["shapes"][answer[0]] = 1
    inequality["right"]["shapes"][answer[1]] = 1

    

    return [equality, inequality_template, inequality, answer]


#Easy puzzle in the form k1X + w1 = k1Y + w2
def easy_puzzle_weighted_equality():
    shapes = _pick_distinct(SHAPES,3)
    X = shapes[0]
    Y = shapes[1]
    Z = shapes[2]
    w1 = random.randint(1, 6)
    choices = [v for v in range(1, 7) if v != w1]
    w2 = random.choice(choices)
    k1 = random.randint(1, 4)

    equality = {
    "left":  { "shapes": {X:k1, Y:0, Z:0}, "weight": w1 },
    "right": { "shapes": {X:0, Y:k1, Z:0}, "weight": w2 },
    }


    #INEQ
    op = '>'
    if(random.random()>0.5):
        op = '<'
    
    inequality_template = '_'+op+'_'

    answer = []
    if w1 < w2:
        answer = [X,Y] if op=='>' else [Y,X]
    else:
        answer = [Y,X] if op=='>' else [X,Y]

   
    inequality = {
    "left":  { "shapes": {X:0, Y:0, Z:0}, "weight": 0 },
    "right": { "shapes": {X:0, Y:0, Z:0}, "weight": 0 },
    "op": op
    }

    inequality["left"]["shapes"][answer[0]] = 1
    inequality["right"]["shapes"][answer[1]] = 1

    return [equality, inequality_template, inequality, answer]
    

#-------------Medium / Difficult PUZZLES HELPER FUNCTIONS-------

#Equality form k1X+w1=k1Y+w2 and Inequality form X + Z + w3 > Y + Z + w4
def difficult_puzzle_weighted_equality():
    shapes = _pick_distinct(SHAPES,3)
    X = shapes[0]
    Y = shapes[1]
    Z = shapes[2]
    k1 = random.randint(1, 3)
    

    w = random.randint(1,4)
    w_offset = random.randint(2,4)

    weights = [k1*w, k1*(w+w_offset)]
    weights = _pick_distinct(weights,2)
    
   
    equality = {
    "left":  { "shapes": {X:k1, Y:0, Z:0}, "weight": weights[0] },
    "right": { "shapes": {X:0, Y:k1, Z:0}, "weight": weights[1] },
    }

    d = (weights[1] - weights[0]) / k1

    inequality_weight = int(abs(d) - 1)


    inequality_template = "_>_+"+str(inequality_weight)


    inequality = {
    "left":  { "shapes": {X:0, Y:0, Z:0}, "weight": 0 },
    "right": { "shapes": {X:0, Y:0, Z:0}, "weight": inequality_weight },
    }



    answer = []
    if d>0:
        answer=[X,Y]
    else:
        answer=[Y,X]
    

    inequality["left"]["shapes"][answer[0]] = 1
    inequality["right"]["shapes"][answer[1]] = 1

    #increase difficulty level
    if(random.random()>0.5):
       inequality["left"]["shapes"][Z] = 1
       inequality["right"]["shapes"][Z] = 1
       weight_offset = random.randint(1, 5)
       inequality["left"]["weight"] += weight_offset
       inequality["right"]["weight"] += weight_offset
       inequality_template = "_+"+Z+"+"+str(weight_offset)+">_+"+Z+"+"+str(inequality_weight+weight_offset)
       


    return [equality, inequality_template, inequality, answer]




#---------------------GENERATE PUZZLE ITEMS--------------

puzzles = []
if difficulty == "easy":
    for i in range(1, count + 1):
        if(random.random() > 0.5):
            puzzles.append(easy_puzzle_proportional_equality())
        else:
            puzzles.append(easy_puzzle_weighted_equality())
else:
    for i in range(1, count + 1):
        puzzles.append(difficult_puzzle_weighted_equality())





# -------------------- PROMPTS (BATCH) --------------------

BATCH_PROMPT_EASY = lambda n: f"""
You will receive JSON with an array "items" of length {n}. Each element has:
- "index": integer (keep it unchanged in your output),
- "equality": balanced scale (left/right shapes + weight),
- "inequality": final comparison content + "op" (>,<),
- "ineq_template": string with two "_" blanks (e.g., "_>_","_<_"),
- "answer": array — IGNORE it completely (grader use only).

Shapes: s=square, t=triangle, c=circle.

YOUR JOB
For each item, DERIVE which symbols go into the two blanks (left → right) and return ONLY a JSON array of length {n}:
[
  {{"index": <same index>, "explanation": "<MAX 2 very short sentences; end with the exact filled inequality, no spaces>", "reasoned_answer": "<filled inequality, no spaces>"}},
  ...
]

HARD RULES (no preamble, no steps)
- Decide placement yourself (ignore "answer").
- Proportional (k1*X = k2*Y): if fewer X than Y are needed, X>Y; if more, X<Y.
- Weighted equal-k (k*X + w1 = k*Y + w2): the side needing the heavier added weight has the lighter unit → if X-side heavier add-on, X<Y; if Y-side heavier add-on, X>Y.
- Explanation must be ONLY a plain sentence applying one of the two lines above (shapes/weights), then finish with the exact inequality (no spaces).
- Keep template tokens and operator exactly; fill the two "_" with your chosen symbols.
- Output ONLY the JSON array; no extra text, no code fences.
""".strip()

BATCH_PROMPT_DIFFICULT = lambda n: f"""
You will receive JSON with an array "items" of length {n}. Each element has:
- "index": integer (keep it unchanged in your output),
- "equality": balanced scale (left/right shapes + weight),
- "inequality": final comparison content + "op" (>,<),
- "ineq_template": string with two "_" blanks (may include "+<shape>" and/or "+<number>"),
- "answer": array — IGNORE it completely (grader use only).

Shapes: s=square, t=triangle, c=circle.

OUTPUT (JSON ONLY)
Return a JSON array of length {n}. Each element:
{{"index": <same index>, "explanation": "<MAX 2 very short sentences; end with the exact filled inequality, no spaces>", "reasoned_answer": "<filled inequality, no spaces>"}}

HARD RULES
- Use only simple words about shapes and weights (e.g., "cancel c", "remove 1 weight", "square 3 heavier"). No algebra steps.
- If the same extra shape appears on both sides (e.g., "+t"), say it cancels; then compare remaining numeric adds with the per-unit gap implied by the equality.
- MAX 2 short sentences; last sentence must be just the final inequality (e.g., "So s+c+3>t+c+5."). No spaces inside it.
- "reasoned_answer" must be identical to that final inequality and non-empty.
- Output ONLY the JSON array; no extra text.

PRACTICAL EXAMPLES (style to imitate; do not copy numbers)
Example 1:
Input equality: 2s+8 = 2t+14 | template: _+c+3>_+c+5
Desired element:
{{"index": 0, "explanation": "Since s=t+3, cancel c; left adds 3 and right adds 5, square stays heavier. So s+c+3>t+c+5.", "reasoned_answer": "s+c+3>t+c+5"}}

Example 2:
Reduced equality: s=c+2 | template intent: _>_+1
Desired element:
{{"index": 1, "explanation": "Since s=c+2, removing 1 on the right still leaves square heavier. So s>c+1.", "reasoned_answer": "s>c+1"}}
""".strip()



# -------------------- BATCH CALL --------------------

# Build the batch payload array (keep source order via index)
batch_items = []
for i, (equality_dict, inequality_template, inequality_dict, answer) in enumerate(puzzles, start=1):
    batch_items.append({
        "index": i,
        "equality": equality_dict,
        "inequality": inequality_dict,
        "ineq_template": inequality_template,
        "answer": answer  # LLM will ignore it per prompt
    })

# Pick batch prompt by difficulty
prompt = (BATCH_PROMPT_EASY(len(batch_items)) if difficulty == "easy"
          else BATCH_PROMPT_DIFFICULT(len(batch_items)))

# Single Claude call with the entire array
batched_prompt = prompt + "\n\nJSON INPUT:\n" + json.dumps({"items": batch_items}, ensure_ascii=False)

explanations = {}  # index -> {"explanation": ..., "reasoned_answer": ...}
try:
    res = subprocess.run(
        ["claude", "-p", "--output-format", "text", batched_prompt],
        capture_output=True, text=True
    )
    if res.returncode == 0:
        resp = res.stdout.strip()
        try:
            arr = json.loads(resp)
            if isinstance(arr, list):
                for obj in arr:
                    if isinstance(obj, dict) and "index" in obj:
                        explanations[obj["index"]] = {
                            "explanation": (obj.get("explanation") or "").strip(),
                            "reasoned_answer": (obj.get("reasoned_answer") or "").strip()
                        }
        except Exception:
            # If JSON parse fails, leave explanations empty; downstream will store raw LLM text if needed
            pass
    else:
        # Non-zero return; no explanations
        pass
except Exception:
    # CLI failure; no explanations
    pass

# Build final items with merged explanations (fallback to empty strings if missing)
items = []
for i, (equality_dict, inequality_template, inequality_dict, answer) in enumerate(puzzles, start=1):
    info = explanations.get(i, {"explanation": "", "reasoned_answer": ""})
    items.append({
        "id": f"{difficulty}-{i:03d}",
        "difficulty": difficulty,
        "equality": equality_dict,
        "inequality": inequality_dict,
        "ineq_template": inequality_template,
        "answer": answer,                    # ground truth from generator
        "explanation": info["explanation"],  # LLM batch output (as-is)
        "reasoned_answer": info["reasoned_answer"]
    })

# -------------------- WRITE --------------------
with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(path.parent)) as tf:
    tmp = tf.name
    json.dump(items, tf, ensure_ascii=False, indent=2)
    tf.write("\n")
shutil.move(tmp, path)
print(f"Wrote {path.resolve()}")