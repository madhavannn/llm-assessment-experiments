import json, re, sys, unicodedata

def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return re.findall(r"[a-z0-9]+", s)

def jaccard(a, b):
    A, B = set(norm(a)), set(norm(b))
    return len(A & B) / len(A | B) if (A | B) else 1.0

def main(a_path, b_path, out_path):
    a = json.load(open(a_path, encoding="utf-8"))
    b = json.load(open(b_path, encoding="utf-8"))
    lines = [f"# Output comparison: {a['tag']} vs {b['tag']}", ""]
    lines.append("| # | Prompt | Word counts | Exact match | Token Jaccard |")
    lines.append("|---|--------|-------------|-------------|---------------|")
    for pa, pb in zip(a["prompts"], b["prompts"]):
        wa, wb = len(pa["text"].split()), len(pb["text"].split())
        em = "yes" if pa["text"].strip() == pb["text"].strip() else "no"
        lines.append(f"| {pa['id']} | {pa['prompt'][:60].replace('|','/')}... | {wa} / {wb} | {em} | {jaccard(pa['text'], pb['text']):.2f} |")
    lines.append("")
    for pa, pb in zip(a["prompts"], b["prompts"]):
        lines.append(f"## {pa['id']}")
        lines.append(f"**Prompt:** {pa['prompt']}")
        lines.append("")
        lines.append(f"### {a['tag']} ({wa if False else ''}{pa['tok_per_s']} tok/s)")
        lines.append("```")
        lines.append(pa["text"].strip())
        lines.append("```")
        lines.append(f"### {b['tag']} ({pb['tok_per_s']} tok/s)")
        lines.append("```")
        lines.append(pb["text"].strip())
        lines.append("```")
        lines.append("")
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))
    print("wrote", out_path)

if __name__ == "__main__":
    main(*sys.argv[1:4])
