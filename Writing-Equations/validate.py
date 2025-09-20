#!/usr/bin/env python3
"""
validate.py — Strict validator for price linear puzzles (p = m * x) with variety:
- per kg  : x_var=w, x_name=weight, x_unit=kg, x_unit_label=kg
- per L   : x_var=v, x_name=volume, x_unit=L,  x_unit_label=L
- per item: x_var=n, x_name=items,  x_unit=pcs, x_unit_label=pc

USAGE
  python validate.py <input.json> [--out <out.json>]

WHAT IT CHECKS (hard gates)
- Schema / required fields
- Context is price-only (p/$ vs chosen x-var and unit mapping)
- Prompt mentions p/price, x_var/x_name, item_name, and "$" + "per {x_unit_label}"
- Table math & displays (rate/amount/total)
- Graph: labels exactly "{x_name} ({x_unit})" and "price ($)"; ticks & line_points
- Equation template orientation (two allowed) and tokens (3..5 incl. distractors)
- Answers.valid_fills match chosen template using actual x_var; canonical_str is 'p=m*x' or 'm*x=p'
- Explanation mentions p, x_var, and either "$" or slope number; equation_str 'p=m×x'
- Basic de-dup on (item_name.lower(), x_unit, slope_m)
"""

import sys
import json
import re
import pathlib
import tempfile
import shutil
from typing import Dict, Any, List, Tuple, Set

def die(msg: str, code: int = 2):
    print(msg, file=sys.stderr); sys.exit(code)

def require(cond: bool, errors: List[str], msg: str):
    if not cond: errors.append(msg)
    return cond

def is_int(x) -> bool:       return isinstance(x, int) and not isinstance(x, bool)
def is_pos_int(x) -> bool:   return is_int(x) and x > 0
def norm(s: str) -> str:     return (s or "").strip()

REQ_ROOT_KEYS = ["id","stem","table","graph","equation_template","tokens","answers","explanation"]

# Allowed mode configurations
MODES = {
    # x_var: (x_name, x_unit, x_unit_label)
    "w": ("weight", "kg", "kg"),
    "v": ("volume", "L",  "L"),
    "n": ("items",  "pcs","pc"),
}

def validate_item(item: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errs: List[str] = []

    # 1) Root keys
    for k in REQ_ROOT_KEYS:
        require(k in item, errs, f"missing key: {k}")
    if errs: return False, errs

    # 2) Context (price-only + one mode)
    stem = item["stem"]
    ctx = stem.get("context", {})
    y_var   = norm(ctx.get("y_var",""))
    y_name  = norm(ctx.get("y_name",""))
    y_unit  = norm(ctx.get("y_unit",""))
    x_var   = norm(ctx.get("x_var",""))
    x_name  = norm(ctx.get("x_name",""))
    x_unit  = norm(ctx.get("x_unit",""))
    x_ulab  = norm(ctx.get("x_unit_label",""))
    item_nm = norm(ctx.get("item_name",""))
    slope_m = ctx.get("slope_m", None)

    require(y_var == "p", errs, "y_var must be 'p'")
    require(y_name.lower() == "price", errs, "y_name must be 'price'")
    require(y_unit == "$", errs, "y_unit must be '$'")
    require(x_var in MODES, errs, f"x_var must be one of {list(MODES.keys())}")
    if x_var in MODES:
        exp_name, exp_unit, exp_lab = MODES[x_var]
        require(x_name.lower() == exp_name, errs, f"x_name must be '{exp_name}'")
        require(x_unit == exp_unit,         errs, f"x_unit must be '{exp_unit}'")
        require(x_ulab == exp_lab,          errs, f"x_unit_label must be '{exp_lab}'")

    require(item_nm != "", errs, "item_name empty")
    require(is_int(slope_m) and 1 <= slope_m <= 20, errs, "slope_m must be int in [1..20]")

    prompt_text = norm(stem.get("prompt_text",""))
    require(("p" in prompt_text or "price" in prompt_text.lower()), errs, "prompt must reference price/p")
    require((x_var in prompt_text or x_name in prompt_text.lower()), errs, "prompt must reference x_var/x_name")
    require("$" in prompt_text, errs, "prompt should mention currency '$'")
    require(item_nm.lower() in prompt_text.lower(), errs, "prompt should mention item_name")

    # 3) Table
    table = item["table"]
    up_val = table.get("unit_price",{}).get("value",None)
    up_disp= norm(table.get("unit_price",{}).get("display",""))
    amt_val= table.get("amount",{}).get("value",None)
    amt_disp=norm(table.get("amount",{}).get("display",""))
    tot_val= table.get("total",{}).get("value",None)
    tot_disp=norm(table.get("total",{}).get("display",""))

    require(is_pos_int(up_val) and up_val == slope_m, errs, "unit_price.value must equal slope_m")
    require(up_disp.startswith("$") and (f"/{x_ulab}" in up_disp) and str(slope_m) in up_disp,
            errs, "unit_price.display must include '$', slope_m, and '/{x_unit_label}'")
    require(is_pos_int(amt_val) and 1 <= amt_val <= 10, errs, "amount.value must be 1..10")
    require(amt_disp.endswith(f" {x_unit}") and str(amt_val) in amt_disp,
            errs, "amount.display must be '<amount> {x_unit}'")
    require(is_pos_int(tot_val) and tot_val == slope_m * amt_val, errs,
            "total.value must equal slope_m * amount.value")
    require(tot_disp.startswith("$") and str(tot_val) in tot_disp,
            errs, "total.display must start with '$' and include total value")

    # 4) Graph
    graph = item["graph"]
    xaxis = graph.get("x_axis",{})
    yaxis = graph.get("y_axis",{})
    x_ticks = xaxis.get("ticks",[])
    y_ticks = yaxis.get("ticks",[])
    require(norm(xaxis.get("label","")).lower() == f"{x_name} ({x_unit})".lower(),
            errs, "x_axis.label must match '{x_name} ({x_unit})'")
    require(norm(yaxis.get("label","")).lower() == "price ($)", errs,
            "y_axis.label must be 'price ($)'")
    require(isinstance(x_ticks,list) and len(x_ticks)==5, errs, "x_ticks must be length 5")
    require(isinstance(y_ticks,list) and len(y_ticks)==5, errs, "y_ticks must be length 5")
    if len(x_ticks)==5 and len(y_ticks)==5:
        def inc_pos(seq): 
            return all(is_pos_int(seq[i]) and (i==0 or seq[i]>seq[i-1]) for i in range(len(seq)))
        require(inc_pos(x_ticks), errs, "x_ticks must be positive increasing integers")
        require(inc_pos(y_ticks), errs, "y_ticks must be positive increasing integers")
        for xi, yi in zip(x_ticks, y_ticks):
            require(yi == slope_m * xi, errs, "y_ticks must equal slope_m * x_ticks")
    # line points on p = m*x
    line_pts = graph.get("line_points",[])
    require(isinstance(line_pts,list) and len(line_pts)==2, errs, "line_points must have exactly 2 points")
    if len(line_pts)==2:
        p1, p2 = line_pts
        def pt_ok(p): return isinstance(p,list) and len(p)==2 and all(is_int(v) for v in p) and p[1]==slope_m*p[0]
        require(pt_ok(p1) and pt_ok(p2) and p1!=p2, errs, "line_points must lie on p=m*x and be distinct")

    # 5) Equation template & tokens
    eq_tmpl = norm(item.get("equation_template",""))
    require(eq_tmpl in ("_ = _ * _","_ * _ = _"), errs, "equation_template must be '_ = _ * _' or '_ * _ = _'")

    tokens = item.get("tokens",[])
    require(isinstance(tokens,list) and 3 <= len(tokens) <= 5, errs, "tokens must have 3..5 entries")
    if isinstance(tokens,list):
        has_p = any(t.get("type")=="var"  and t.get("label")=="p" for t in tokens)
        has_x = any(t.get("type")=="var"  and t.get("label")==x_var for t in tokens)
        has_m = any(t.get("type")=="const" and t.get("label")==str(slope_m) and t.get("value")==slope_m for t in tokens)
        require(has_p and has_x and has_m, errs, "tokens must include var 'p', var x_var, and const slope_m")
        seen_labels = set()
        for t in tokens:
            lbl = t.get("label","")
            require(lbl not in seen_labels, errs, "duplicate token label not allowed")
            seen_labels.add(lbl)
            if t.get("type")=="const" and t.get("label")!=str(slope_m):
                v = t.get("value",None)
                require(is_int(v) and 1<=v<=20 and v!=slope_m, errs,
                        "distractor const must be 1..20 and != slope_m")

    # 6) Answers orientation & canonical
    answers = item.get("answers",{})
    fills = answers.get("valid_fills",[])
    canon = norm(answers.get("canonical_str",""))

    require(isinstance(fills,list) and len(fills)>=2, errs, "answers.valid_fills must include both orientations")
    token_labels = {t.get("label") for t in tokens}
    for f in fills:
        require(isinstance(f,list) and len(f)==3, errs, "each valid_fills entry must have 3 symbols")
        for sym in f:
            require(sym in token_labels, errs, f"valid_fills symbol '{sym}' not in tokens")

    if eq_tmpl == "_ = _ * _":
        expect_main = [["p", str(slope_m), x_var], ["p", x_var, str(slope_m)]]
    else:
        expect_main = [[str(slope_m), x_var, "p"], [x_var, str(slope_m), "p"]]
    for ex in expect_main:
        require(ex in fills, errs, f"valid_fills must include {ex}")

    expect_canon_a = f"p={slope_m}*{x_var}"
    expect_canon_b = f"{slope_m}*{x_var}=p"
    require(canon in (expect_canon_a, expect_canon_b), errs,
            "answers.canonical_str must be 'p=m*x' or 'm*x=p'")

    # 7) Explanation
    expl = item.get("explanation",{})
    eq_str = norm(expl.get("equation_str",""))
    e_txt  = norm(expl.get("text",""))
    require(eq_str == f"p={slope_m}×{x_var}", errs, "explanation.equation_str must be 'p=m×x_var'")
    require("p" in e_txt and x_var in e_txt, errs, "explanation.text must mention 'p' and x_var")
    rate_ok = "$" in e_txt or str(slope_m) in e_txt or ("per " + ctx.get("x_unit_label","")) in e_txt
    require(rate_ok, errs, "explanation.text should indicate price rate ($ or number)")

    return len(errs)==0, errs

# ---------- de-dup ----------

def dedupe_items(items: List[Dict[str,Any]]) -> Tuple[List[Dict[str,Any]], int]:
    seen: Set[Tuple[str,str,int]] = set()
    kept: List[Dict[str,Any]] = []
    dropped = 0
    for it in items:
        try:
            c = it["stem"]["context"]
            key = (c["item_name"].lower().strip(), c["x_unit"], int(c["slope_m"]))
        except Exception:
            kept.append(it); continue
        if key in seen:
            dropped += 1
            continue
        seen.add(key)
        kept.append(it)
    return kept, dropped

# ---------- main ----------

def main():
    if len(sys.argv) < 2:
        die("Usage: python validate.py <input.json> [--out <out.json>]")

    in_path = pathlib.Path(sys.argv[1])
    if "--out" in sys.argv:
        i = sys.argv.index("--out")
        out_path = pathlib.Path(sys.argv[i+1])
    else:
        out_path = in_path.with_suffix(".passed.json")

    try:
        items = json.loads(in_path.read_text(encoding="utf-8"))
        assert isinstance(items, list)
    except Exception as e:
        die(f"Failed to read/parse JSON array from {in_path}: {e}", 3)

    items, dropped_dupes = dedupe_items(items)

    passed, failed = [], []
    for it in items:
        ok, reasons = validate_item(it)
        if ok: passed.append(it)
        else:  failed.append((str(it.get("id","<no-id>")), reasons))

    # Write passed-only
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=str(out_path.parent)) as tf:
        tmp = tf.name
        json.dump(passed, tf, ensure_ascii=False, indent=2)
        tf.write("\n")
    shutil.move(tmp, out_path)

    total = len(items)
    kept  = len(passed)
    bad   = len(failed)
    pct   = (kept / total * 100.0) if total else 0.0

    print("----- VALIDATION REPORT -----")
    print(f"Input file         : {in_path}")
    print(f"After de-dup       : {total} items (dropped {dropped_dupes} duplicates before validation)")
    print(f"Passed             : {kept}")
    print(f"Failed             : {bad}")
    print(f"Pass rate          : {pct:.1f}%")
    print(f"Output (passed)    : {out_path}")

    if failed:
        print("\n--- Failures (first 20) ---")
        for i, (pid, reasons) in enumerate(failed[:20], 1):
            print(f"{i:02d}. id={pid}")
            for r in reasons:
                print(f"    - {r}")

if __name__ == "__main__":
    main()
