import json, statistics

for f, tag in [("results/q4.json", "Q4_K_M"), ("results/f16.json", "F16")]:
    d = json.load(open(f, encoding="utf-8"))
    t = [r["tok_per_s"] for r in d["throughput"]]
    print(tag, "median", round(statistics.median(t), 2), "mean", round(statistics.mean(t), 2),
          "min", min(t), "max", max(t), "prefill", d["throughput"][0]["prompt_eval_tok_per_s"])
    print("  per-prompt:", " ".join(f"{r['id']}={r['tok_per_s']}" for r in d["prompts"]))
    print("  tokens:", sum(r["eval_count"] for r in d["prompts"]))
