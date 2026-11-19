import json, re

def load(p):
    return json.load(open(p, encoding="utf-8"))

def has_e(s):
    return bool(re.search(r"[eE]", s))

def score(d):
    out = {}
    for r in d["prompts"]:
        pid, t = r["id"], r["text"]
        ok = None; note = ""
        if pid == "arith":
            m = re.findall(r"\$?\s*(\d+(?:\.\d+)?)", t.lower())
            ok = "8" in [x.rstrip("0").rstrip(".") for x in m] or re.search(r"\$\s*8(?![.\d])", t) is not None
            note = "expected $8 exactly"
        elif pid == "logic":
            ok = bool(re.match(r"\s*no\b", t, re.I))
            note = "valid answer is No (undistributed middle)"
        elif pid == "factual":
            ok = ("Canberra" in t) and ("largest" in t.lower() or "sydney" in t.lower())
            note = "must name Canberra"
        elif pid == "code":
            code = re.sub(r"^```(?:python)?|```$", "", t.strip(), flags=re.M).strip()
            ns = {}
            try:
                exec(code, ns)
                f = ns["second_largest"]
                cases = [([1,2,3], 2), ([5,5,4], 4), ([7], None), ([], None), ([-1,-3,-2], -2), ([2,2,2], None)]
                ok = all(f(list(a)) == b for a, b in cases)
                note = "executed on 6 cases"
            except Exception as e:
                ok = False; note = f"exec error: {e}"
        elif pid == "summary":
            ok = len(re.findall(r"(?m)^\s*(?:[•*+-]|\d+[.)])\s+", t)) == 3
            note = "exactly 3 bullets"
        elif pid == "json":
            stripped = t.strip()
            fenced = stripped.startswith("```")
            try:
                obj = json.loads(stripped.strip("`").replace("```json", "").replace("```", "").strip())
                ok = (not fenced) and set(obj) == {"name", "age", "city"} and obj["name"] == "Maya" and obj["city"] == "Pune" and str(obj["age"]) == "29"
                note = "valid JSON, no fences, age numeric"
            except Exception as e:
                ok = False; note = f"invalid JSON: {e}"
        elif pid == "translate":
            ok = ("शुक्रवार" in t) and ("10" in t) and ("मीटिंग" in t)
            note = "contains meeting/Friday/10"
        elif pid == "creative":
            sentences = [s for s in re.split(r"(?<=[.!?])\s+", t.strip()) if s]
            ok = (not has_e(t)) and len(sentences) == 2
            note = f"no letter e: {not has_e(t)}; sentences={len(sentences)}"
        elif pid == "wordproblem":
            ok = "80" in t
            note = "expected 80 km/h"
        elif pid == "extract":
            ok = ("budget" in t.lower()) and ("conference" in t.lower()) and ("12 may" in t.lower()) and ("wednesday" in t.lower())
            note = "both actions + deadline"
        out[pid] = (bool(ok), note)
    return out

def main():
    for f, tag in [("results/q4.json", "Q4_K_M"), ("results/f16.json", "F16")]:
        d = load(f); s = score(d)
        print(tag, "score:", sum(v[0] for v in s.values()), "/ 10")
        for k, v in s.items():
            print(f"  {k:12s} {'PASS' if v[0] else 'FAIL':4s}  {v[1]}")

if __name__ == "__main__":
    main()
