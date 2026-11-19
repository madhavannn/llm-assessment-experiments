import argparse, json, os, statistics, subprocess, sys, threading, time, urllib.request

API = "http://127.0.0.1:11434"

PROMPTS = [
    ("arith", "A shop sells pens at 3 for $2. If I buy 12 pens, how much do I pay? Show your reasoning briefly."),
    ("logic", "All roses are flowers. Some flowers fade quickly. Can we conclude that some roses fade quickly? Answer yes or no, then explain in one sentence."),
    ("factual", "What is the capital of Australia, and why is Sydney often mistaken for it? Answer in 2-3 sentences."),
    ("code", "Write a Python function second_largest(nums) that returns the second-largest unique number in a list. It must handle lists with fewer than two unique values. Return only the code."),
    ("summary", "Summarise the following in exactly 3 bullet points:\n\nA KV cache stores the key and value tensors for every token already processed, so the model does not recompute attention over the whole prefix for each new token. Its size grows linearly with context length, batch size, number of layers and KV heads. Because it can dominate GPU memory at long context, systems use paged allocation, grouped-query attention and KV quantisation to fit more concurrent requests."),
    ("json", "Return ONLY valid JSON with keys name, age, city for this text: 'Maya is 29 and lives in Pune.' No markdown fences, no explanation."),
    ("translate", "Translate this sentence into Hindi: 'The meeting has been moved to Friday at 10 a.m.'"),
    ("creative", "Write exactly two sentences about the sea. Do not use the letter 'e' anywhere in your answer."),
    ("wordproblem", "A train travels 60 km in 45 minutes. What is its average speed in km/h? Show the calculation."),
    ("extract", "From this email, list the action items and the deadline:\n\nHi team, please send me your budget estimates by Wednesday. Also book the conference room for the client demo on 12 May. Thanks, Priya"),
]

THROUGHPUT_PROMPT = "Write a detailed explanation of how a refrigerator works, covering the compressor, refrigerant, evaporator and condenser. At least 300 words."

def post(path, payload, timeout=900):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def get(path, timeout=60):
    with urllib.request.urlopen(API + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def mem_total_kb():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq ollama.exe", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, timeout=10).stdout
        total = 0
        for line in out.splitlines():
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 5:
                try:
                    total += int(parts[-1].replace(",", "").replace(" K", "").replace("K", ""))
                except ValueError:
                    pass
        return total
    except Exception:
        return None

class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.peak = 0
        self.stop = False
    def run(self):
        while not self.stop:
            v = mem_total_kb()
            if v:
                self.peak = max(self.peak, v)
            time.sleep(0.15)

def chat(model, prompt, num_predict=220):
    sampler = Sampler(); sampler.start()
    t0 = time.perf_counter()
    resp = post("/api/chat", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": "20m",
        "options": {"temperature": 0, "top_p": 1, "seed": 42,
                    "num_predict": num_predict, "num_ctx": 4096},
    })
    wall = time.perf_counter() - t0
    sampler.stop = True; sampler.join(timeout=2)
    ev = resp.get("eval_count", 0)
    evd = resp.get("eval_duration", 1) / 1e9
    pev = resp.get("prompt_eval_count", 0)
    pevd = resp.get("prompt_eval_duration", 1) / 1e9
    return {
        "text": resp.get("message", {}).get("content", ""),
        "eval_count": ev,
        "eval_duration_s": round(evd, 3),
        "tok_per_s": round(ev / evd, 2) if evd else None,
        "prompt_eval_count": pev,
        "prompt_eval_tok_per_s": round(pev / pevd, 2) if pevd else None,
        "load_duration_s": round(resp.get("load_duration", 0) / 1e9, 2),
        "wall_s": round(wall, 2),
        "peak_ollama_rss_mb": round(sampler.peak / 1024, 1) if sampler.peak else None,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", required=True)
    args = ap.parse_args()

    results = {"model": args.model, "tag": args.tag, "machine": {}, "warmup": None,
               "throughput": [], "prompts": [], "ps": None}

    # baseline memory
    results["machine"]["idle_ollama_rss_mb"] = round(mem_total_kb() / 1024, 1) if mem_total_kb() else None

    # load + warmup
    print("warmup...", flush=True)
    results["warmup"] = chat(args.model, "Say hello in one short sentence.", 32)
    results["ps"] = get("/api/ps")

    # throughput: 3 runs, fixed generation length
    for i in range(3):
        print(f"throughput run {i+1}...", flush=True)
        r = chat(args.model, THROUGHPUT_PROMPT, 300)
        results["throughput"].append(r)

    # quality prompts
    for pid, prompt in PROMPTS:
        print(f"prompt {pid}...", flush=True)
        r = chat(args.model, prompt, 220)
        r["id"] = pid
        r["prompt"] = prompt
        results["prompts"].append(r)

    results["ps_after"] = get("/api/ps")
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("saved", args.out, flush=True)

if __name__ == "__main__":
    main()
