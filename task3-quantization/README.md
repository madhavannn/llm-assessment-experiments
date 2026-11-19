# Running a small open model locally: F16 vs Q4_K_M

**Model:** Llama 3.2 1B Instruct (1.24 B parameters), GGUF builds by bartowski
**Runtime:** Ollama 0.40.16 (llama.cpp backend), CPU-only
**Date:** 19 November 2026

---

## 1. TL;DR

| Metric | F16 (16-bit) | Q4_K_M (4-bit) | Ratio |
|---|---|---|---|
| Decode speed (median, 3 runs) | **7.41 tok/s** (7.28–7.41) | **18.74 tok/s** (16.46–20.72) | **2.53× faster** |
| Prompt processing (prefill) | 34.4 tok/s | 91.9 tok/s | 2.67× faster |
| Model file on disk | 2.48 GB | 0.807 GB | 3.07× smaller |
| Runner resident memory (RSS) | 2,507 MB | 957 MB | 2.62× smaller |
| Runner private memory | 2,640 MB | 1,044 MB | 2.53× smaller |
| Ollama-reported model size in RAM | 2.68 GB (2.50 GiB) | 1.01 GB (0.94 GiB) | 2.65× smaller |
| First-request load time (warm page cache) | 7.7 s | 2.9 s | 2.7× faster |
| Strict quality rubric (10 prompts) | 6/10 | 7/10 | no F16 advantage |

At 1B parameters, 4-bit is the clear practical choice on this machine: ~2.5× faster, ~2.6× less memory, and **no measurable quality win for 16-bit** on this prompt set. Both settings make the same kinds of reasoning mistakes; those come from model capacity, not from quantization.

---

## 2. Setup and method

### Machine

| | |
|---|---|
| CPU | Intel Core i3-N305, 8 cores / 8 threads (Alder Lake-N, no AVX-512) |
| GPU | None used — Intel UHD integrated graphics only; inference 100% on CPU |
| RAM | 7.7 GB usable |
| OS | Windows 11 Home, build 26300 |
| Disk free | ~7.3 GB at start (both models together = 3.3 GB) |

### Models

Both are conversions of the same base weights (`meta-llama/Llama-3.2-1B-Instruct`) from the same repository, so the only difference is weight precision:

- `hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:f16` — 2.48 GB, 16 bits/weight
- `hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M` — 807 MB, ~5.2 effective bits/weight (K-quant mixes 4- and 6-bit blocks; it is not a flat 4.0 bits)

Llama 3.2 1B has 16 layers, 32 attention heads, 8 KV heads (GQA), head dimension 64.

### Measurement protocol

- Ollama `/api/chat`, `temperature=0`, `top_p=1`, `seed=42`, `num_ctx=4096`, `num_predict=220` (quality) or `300` (throughput).
- One warm-up request per model, then **3 independent 300-token generations** for throughput; median reported, full range in brackets.
- Tokens/s is computed from Ollama's `eval_count / eval_duration` (decode only, excludes prefill and load).
- Memory measured three ways: Ollama's `/api/ps` size, and `llama-server.exe` Working Set / Private Bytes from Windows after loading with no other model resident.
- The same **10 prompts** were sent to both models, once each, greedy decoding.
- An automatic rubric then checked each answer (executed the code on 6 test cases, parsed the JSON, checked the letter constraint, etc.). Scores are strict functional pass/fail, not a general capability benchmark.

Reproduction:

```powershell
ollama pull hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M
ollama pull hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:f16
python bench.py --model "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:Q4_K_M" --tag Q4_K_M --out results\q4.json
python bench.py --model "hf.co/bartowski/Llama-3.2-1B-Instruct-GGUF:f16"      --tag F16     --out results\f16.json
python scoring.py
```

---

## 3. Throughput and memory

### Throughput

| Run (300 output tokens) | F16 | Q4_K_M |
|---|---|---|
| 1 | 7.28 tok/s | 20.72 tok/s |
| 2 | 7.41 tok/s | 18.74 tok/s |
| 3 | 7.41 tok/s | 16.46 tok/s |
| **Median** | **7.41** | **18.74** |

Q4_K_M drifts downward across runs (20.7 → 16.5), consistent with thermal throttling or background CPU contention on a fanless/low-power 8-core chip. F16 is flat at ~7.4 tok/s. Even the slowest Q4 run is 2.2× faster than F16.

Prefill is also ~2.7× faster with Q4 (91.9 vs 34.4 tok/s), which matters more than decode for long prompts and RAG.

### Memory

| | F16 | Q4_K_M |
|---|---|---|
| GGUF file | 2.48 GB | 0.807 GB |
| `llama-server.exe` working set | 2,507 MB | 957 MB |
| `llama-server.exe` private bytes | 2,640 MB | 1,044 MB |
| `/api/ps` size (weights + KV + buffers) | 2.68 GB | 1.01 GB |
| `size_vram` | 0 (CPU) | 0 (CPU) |

The ~200 MB gap between file size and `/api/ps` size is the 4K-token KV cache plus compute buffers, and it is the same for both models:

```
KV per token = 2 (K and V) × 16 layers × 8 KV heads × 64 head_dim × 2 bytes
             = 32,768 bytes = 32 KiB/token
4,096 tokens × 32 KiB = 128 MiB
```

128 MiB KV + ~70 MB of buffers ≈ the observed 200 MB overhead. That is a useful sanity check on the memory model used in section 7.

Both models fit in 7.7 GB of RAM, but F16 leaves much less headroom for the OS, browser, and page cache. On this machine F16 is usable; on an 8 GB machine it is uncomfortably close to the limit once other applications run.

---

## 4. Quality on the same 10 prompts

### Rubric result

| # | Prompt | Check | F16 | Q4_K_M |
|---|---|---|---|---|
| 1 | 12 pens at 3 for $2 | exact $8 | ❌ $8.04 | ✅ $8 |
| 2 | Syllogism: roses/flowers | valid answer is "No" | ❌ "Yes", confidently wrong | ❌ "Yes", hedged |
| 3 | Capital of Australia | names Canberra | ✅ | ✅ |
| 4 | `second_largest()` code | runs on 6 cases | ✅ | ✅ |
| 5 | 3-bullet summary | exactly 3 bullets | ✅ | ✅ |
| 6 | JSON only, no fences | parses, no fences, numeric age | ❌ truncated/invalid, `"age": "29"` | ❌ valid but fenced |
| 7 | Translate to Hindi | meeting/Friday/10 a.m. | ✅ (odd preamble) | ✅ (terse, "this word") |
| 8 | 2 sentences, no letter "e" | constraint | ❌ | ❌ |
| 9 | 60 km in 45 min | 80 km/h | ✅ | ✅ |
| 10 | Email action items | both actions + deadline | ✅ | ✅ |
| | **Total** | | **6/10** | **7/10** |

### What actually differed

**1. Arithmetic — Q4 wins by accident.** Q4 computed `$2/3 × 12 = $8` symbolically and got the exact answer. F16 rounded early: `$2 ÷ 3 = $0.67`, then `$0.67 × 12 = $8.04`. Same method, one rounding slip. This is a single-token divergence, not evidence that 4-bit is "better at math".

**2. Logic — both fail.** Both answered "Yes" to an invalid syllogism (undistributed middle). F16 was more confidently wrong: *"it logically follows that some roses also fade quickly."* Q4 at least hedged (*"may fade… but not all necessarily"*), but still led with "Yes".

**3. Factual — tie, both slightly awkward.** Both correctly name Canberra and explain Sydney's size. Both phrase it as Sydney being "mistaken for Canberra" (it is mistaken for *the capital*), and F16 invents a "Sydney region". No quantization signal here.

**4. Code — byte-identical and correct.** Both produced the same function:

```python
def second_largest(nums):
    if len(set(nums)) < 2:
        return None
    max_num = second_max = float('-inf')
    for num in nums:
        if num > max_num:
            second_max = max_num
            max_num = num
        elif num > second_max and num != max_num:
            second_max = num
    return second_max if second_max != float('-inf') else None
```

It passes all six test cases in both cases. Both ignored "return only the code" and added Markdown fences — an instruction-following failure shared by both.

**5. Summary — F16 marginally better.** Both gave exactly three accurate bullets. F16 added the useful clause "making it a bottleneck for long context lengths"; Q4's phrasing "reducing computation by reusing them" is vaguer.

**6. JSON — both fail, differently.** Q4 produced valid JSON but wrapped it in a Markdown fence, violating "no fences". F16 produced **invalid JSON**: it used `"age": "29"` (string, not number) and stopped without closing the object — the worst output of the ten.

**7. Hindi translation — tie, both flawed.** Q4: *"इस शब्द को हिंदी में…"* ("[translate] this word into Hindi…") — extra meta-text, then a reasonable translation. F16 added a longer, wrong preamble (*"इस प्रस्तावना को हिंदी में संस्करण…"*, "this introduction into Hindi version…") before a fluent quoted translation. Neither is clean, but F16's preamble is more garbled.

**8. Constrained writing — both fail completely.** Both wrote two sentences but used the letter "e" repeatedly ("The", "ocean", "water", "surface"). A 1B model cannot reliably satisfy a negative character constraint regardless of weight precision.

**9. Average speed — tie, both correct.** Both converted 45 min to 0.75 h and got 80 km/h, with clear steps.

**10. Email extraction — tie, both correct.** Both found the budget request, the room booking, and Wednesday. F16 omitted a separate "Deadline:" line but embedded "by Wednesday" in the action item, which is acceptable.

### Overall observation

The two settings produced **different** answers on 9 of 10 prompts (only the code prompt was byte-identical), but the differences were not a consistent quality ordering. F16 won on the summary; Q4 won on arithmetic and JSON; both failed logic and the letter constraint. Strict score: 7/10 vs 6/10 — within the noise of one greedy sample per prompt. The honest conclusion is:

> For a 1B model on these tasks, Q4_K_M matches F16 in practical quality while being ~2.5× faster and ~2.6× smaller. The errors that remain are capacity errors (weak reasoning, weak instruction-following), not precision errors.

Caveats: one greedy sample per prompt; a strict rubric; a tiny model. At 7B+ the gap between Q4 and F16 is usually small but measurable on benchmarks, and 2–3-bit quantization is where degradation becomes obvious. Q4_K_M is ~5.2 effective bits, which is why it holds up so well.

---

## 5. What the KV cache is (in my own words)

When an LLM generates text, it does not process the whole conversation again for every new word. For each transformer layer it computes three vectors per token: a **Query (Q)**, a **Key (K)** and a **Value (V)**. Attention compares the new token's Q with the K of every earlier token, then takes a weighted sum of their V vectors. Without a cache, producing token *n* would require re-projecting all *n−1* previous tokens at every layer, every step — the same work done over and over.

The **KV cache** is the model's scratchpad of those K and V vectors. During **prefill** (reading the prompt) the model computes K and V for every prompt token and stores them. During **decode** (writing the answer), each new token computes only its own Q/K/V, appends its K and V to the cache, and attends over the stored K/V. Attention is still O(n) per new token — so O(n²) over a full sequence — but the expensive linear projections over the prefix are done once instead of repeatedly. That is the difference between a usable chatbot and one that gets quadratically slower with every sentence.

Two consequences matter operationally:

1. **It grows linearly with context and batch size.** Its size is
   `2 × layers × KV_heads × head_dim × sequence_length × batch × bytes_per_element`
   (the 2 is for K and V). For Llama 3.2 1B: `2 × 16 × 8 × 64 × 2 B = 32 KiB per token`, so a 4K context costs 128 MiB *per sequence*. For Llama 3.1 8B: 128 KiB/token, so 4K costs 512 MiB per sequence.
2. **It can outgrow the weights.** Weights are a fixed cost; the cache scales with how many users and how much context you serve. Long-context, high-concurrency serving is usually KV-cache-bound, which is why systems use PagedAttention (allocate KV in fixed-size blocks instead of contiguous per-request buffers), prefix caching (share blocks for identical system prompts), grouped-query attention (fewer KV heads), eviction/recompute, and KV quantization (FP8/INT8).

On this laptop the 1B model's 4K cache is only 128 MiB — the weights dominate. On a 24 GB GPU serving 20 people, the cache becomes the largest line item (section 7).

---

## 6. Why quantization saves memory

A model's memory footprint is mostly its **weights**. In FP16 each parameter costs 2 bytes; a 4-bit format costs about 0.5 byte plus metadata. Q4_K_M mixes 4-bit and 6-bit blocks and stores per-block scales, so its real average is ~0.65 bytes/parameter (~5.2 bits). The same 1.24 B parameters go from

```
1.24 B × 2.00 bytes ≈ 2.48 GB          (F16, measured 2.48 GB)
1.24 B × 0.65 bytes ≈ 0.81 GB          (Q4_K_M, measured 0.807 GB)
```

That is the 3.07× file-size reduction. In RAM the measured reduction is 2.65× (2.68 → 1.01 GB) because the KV cache and compute buffers do not shrink with weight quantization — they are a fixed ~200 MB at this context length. This is why the speedup (2.53×) is slightly smaller than the compression ratio: as context and batch grow, the non-weight overhead becomes a larger fraction.

Why it also makes inference **faster** on this machine: token-by-token decoding is **memory-bandwidth-bound**, not compute-bound. To emit one token, the CPU/GPU must stream every weight through the ALUs once. Reading 0.8 GB instead of 2.5 GB per token is the direct cause of the ~2.5× speedup. The arithmetic intensity is low (a few FLOPs per byte), so the bottleneck is the bus, not the multiplier.

The quality cost comes from rounding weights onto a coarse grid. Modern K-quants limit the damage by (a) using small blocks (e.g., 32 weights) with their own scale, (b) keeping sensitive tensors — embeddings, output layer, some attention projections — at higher precision, and (c) mixing 4- and 6-bit blocks (hence ~5.2 effective bits for "Q4_K_M"). At 1B parameters the model is already the limiting factor, so the quantization error is invisible next to capability errors. At 2–3 bits, or on very small models, the damage becomes obvious. The same idea can be applied to the **KV cache** (FP8/INT8), which halves or quarters the per-token cache with little quality loss — the main lever for serving many users.

---

## 7. Back-of-envelope: 20 concurrent users on one 24 GB GPU

### Assumptions

| Assumption | Value | Why |
|---|---|---|
| GPU | 24 GB, RTX 4090-class (~1 TB/s); L4/A10 also have 24 GB but lower bandwidth | "one 24 GB GPU" |
| Usable VRAM | ~22 GB | driver/display/CUDA context reserve |
| Model | Llama 3.1 8B Instruct, 4-bit AWQ/GPTQ ≈ Q4_K_M | realistic quality/size point; 4.6 GiB weights |
| Model shape | 32 layers, 8 KV heads, head_dim 128 | Llama 3.1 8B |
| Context | 4,096 tokens max (2K prompt + 2K answer) | typical chat/RAG request |
| Concurrency | 20 sessions, ~50% actively generating at any instant | humans read and type |
| Engine | vLLM with PagedAttention + continuous batching | Ollama is single-stream-oriented; not appropriate here |
| KV precision | FP16 first, FP8 as the fallback | FP8 halves KV with negligible quality loss |

### Step 1 — KV cache per request

```
bytes/token = 2 × 32 layers × 8 KV heads × 128 head_dim × 2 bytes (FP16)
            = 131,072 bytes = 128 KiB/token

4,096 tokens × 128 KiB = 512 MiB per request
20 requests × 512 MiB    = 10.0 GiB
```

### Step 2 — Memory budget

| Component | Size |
|---|---|
| Q4_K_M weights (8B) | 4.6 GiB (4.9 GB) |
| KV cache, 20 × 4K, FP16 | 10.0 GiB |
| Activations, CUDA graphs, workspace | 1.5–2.0 GiB |
| CUDA context, fragmentation reserve | ~1.0 GiB |
| **Total** | **~17–18 GiB of 22 usable** |
| **Headroom** | **~4–5 GiB** |

It fits. The headroom absorbs bursts, a larger batch, and allocator fragmentation. If requests need 8K context, FP16 KV becomes 20 GiB and the total exceeds 24 GB; switch the KV cache to FP8 (10 GiB, total ~17.5 GiB) or cap context at 4K. That is the single most important knob.

For comparison, a Llama 3.2 3B model uses 112 KiB/token (28 layers, 8 KV heads, head_dim 128), i.e. 448 MiB per 4K request: 20 users = 8.75 GiB KV + ~2 GiB weights ≈ 12 GiB. That leaves more headroom than the 8B, but not a night-and-day difference — a smaller model buys maybe 2× the context or 1.5× the users, at a real quality cost.

### Step 3 — Will it be fast enough?

Decode is bandwidth-bound and weights are read **once per step for the whole batch**, so batching is nearly free in memory terms:

- 4.6 GiB read per decode step; at an effective 600–800 GB/s that is ~6–8 ms/step → 125–170 steps/s (on a 4090; roughly half that on an L4).
- Each step produces one token for **every** active sequence, so 20 active sequences ⇒ ~2,500–3,400 aggregate tok/s theoretical. Compute (attention/MLP) and kernel overhead bring this down; a realistic vLLM figure is **~1,000–2,000 tok/s aggregate** for 8B 4-bit on a 4090-class card.
- With all 20 active: **~50–100 tok/s per user**. With the assumed 50% duty cycle (10 active): **~100–200 tok/s per user**, capped by single-stream speed (~120–180 tok/s). Either is far above reading speed.
- Prefill: 2K-token prompts at ~5–10K tok/s prefill → 0.2–0.4 s each; 20 at once is 4–8 s of prefill work. Use **chunked prefill** (512–1,024 tokens per chunk) so a long prompt does not stall everyone else's decode, and **prefix caching** so a shared system prompt is prefilled once.
- Expect p50 time-to-first-token ~0.5–1.5 s under load; p95 a few seconds during a burst.

### Step 4 — Configuration sketch (vLLM)

```bash
# weights must already be a 4-bit checkpoint; vLLM does not quantize FP16 on the fly
vllm serve <org>/Llama-3.1-8B-Instruct-AWQ \
  --quantization awq_marlin \
  --max-model-len 4096 \
  --max-num-seqs 20 \
  --max-num-batched-tokens 2048 \
  --gpu-memory-utilization 0.90 \
  --enable-prefix-caching \
  --enable-chunked-prefill \
  --swap-space 4
# add --kv-cache-dtype fp8 only if you need 8K context
```

Operational rules:

- Admit at most 20 sequences; queue the rest. vLLM can preempt and recompute when KV blocks run out, but that is a latency cliff, not a capacity plan.
- Reserve ~1 GB for the display if the GPU also drives a desktop.
- Monitor `gpu_cache_usage_perc` and KV block usage; alarm at 90%.
- If p95 TTFT is too high, lower `max-num-batched-tokens` or add a second GPU — do not raise context length.

### Step 5 — Validate, don't guess

Run `vllm bench serve` with `--num-prompts 100 --max-concurrency 20`, input ~2K / output ~256 tokens, and record p50/p95 TTFT, inter-token latency, and aggregate tok/s. Check that KV block usage stays below ~85% at 4K context. The arithmetic above says it fits; the benchmark tells you whether the scheduler and prefill chunking behave.

**If the model must be the 1B one measured here:** 20 users is trivial — 32 KiB/token × 4K × 20 = 2.5 GiB KV + ~1 GiB weights. The 24 GB card would be idle. The bottleneck would be quality, not memory.

---

## 8. Caveats

- CPU-only results; a GPU would shift absolute numbers by an order of magnitude, though the F16→Q4 ratios would be broadly similar (both are bandwidth-bound).
- Throughput measured with short 300-token generations after one warm-up; Q4 showed thermal/contention drift, so its median is more representative than any single run.
- Quality is one greedy sample per prompt, scored by a strict functional rubric. It is evidence, not a statistically powered benchmark.
- "F16" here means FP16 GGUF weights. Activations/KV remain FP16 in both runs; only weights differ.
- Q4_K_M is ~5.2 effective bits/weight, not a flat 4.0; a pure Q4_0 would be smaller and slightly worse.

## 9. Files

| File | Contents |
|---|---|
| `bench.py` | benchmark harness (API calls, timing, memory sampling) |
| `scoring.py` | automatic rubric (executes code, parses JSON, checks constraints) |
| `compare.py` | side-by-side Markdown generator |
| `results/q4.json`, `results/f16.json` | raw responses and per-request timings |
| `results/compare.md` | full side-by-side output for all 10 prompts |
