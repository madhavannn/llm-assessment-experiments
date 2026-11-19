"""NumPy latent semantic analysis, cosine retrieval, and grounded generation."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import numpy as np

ROOT = Path(__file__).resolve().parent
SIZES = (80, 240)
OVERLAP = 16
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"

def read(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def write(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def chunks(pages, size, overlap):
    out = []
    for page, text in pages.items():
        words = text.split()
        for start in range(0, len(words), size - overlap):
            out.append(dict(page=page, start=start, text=" ".join(words[start:start+size])))
            if start + size >= len(words):
                break
    return out

def counts(text):
    return Counter(re.findall(r"--?[\w-]+|[a-z0-9]+", text.lower()))

def normalize(matrix):
    return matrix / np.maximum(np.linalg.norm(matrix, axis=1, keepdims=True), 1e-10)

class LSA:
    """Fit on fixed 100-word corpus blocks independently of the evaluation windows."""
    def __init__(self, pages):
        blocks = [counts(c["text"]) for c in chunks(pages, 100, 0)]
        df = Counter(word for block in blocks for word in block)
        terms = sorted(w for w in df if df[w] >= 2)
        self.vocab = {w:i for i,w in enumerate(terms)}
        self.idf = np.array([1 + np.log((1+len(blocks))/(1+df[w])) for w in terms],
                            dtype=np.float32)
        matrix = self.weights(blocks)
        # Randomized truncated SVD. QR re-orthogonalizes the subspace each pass.
        rng = np.random.default_rng(17)
        sample = rng.standard_normal((len(terms), 108), dtype=np.float32)
        q = np.linalg.qr(matrix @ sample, mode="reduced")[0]
        for _ in range(3):
            z = np.linalg.qr(matrix.T @ q, mode="reduced")[0]
            q = np.linalg.qr(matrix @ z, mode="reduced")[0]
        self.axes = np.linalg.svd(q.T @ matrix, full_matrices=False)[2][:96].T

    def weights(self, documents):
        matrix = np.zeros((len(documents), len(self.vocab)), dtype=np.float32)
        for row, doc in enumerate(documents):
            for word, freq in doc.items():
                if word in self.vocab:
                    matrix[row, self.vocab[word]] = 1 + np.log(freq)
        return normalize(matrix * self.idf)

    def encode(self, texts):
        return normalize(self.weights([counts(t) for t in texts]) @ self.axes)

def index(pages, model, size):
    parts = chunks(pages, size, OVERLAP)
    return parts, model.encode(["git-" + p["page"] + " " + p["text"] for p in parts])

def ranked(query, model, parts, vectors):
    vector = model.encode([query])[0]
    if not vector.any():
        return []
    scores = vectors @ vector
    return [dict(**parts[i], score=float(scores[i])) for i in np.argsort(-scores, kind="stable")]

def evaluate(pages, model):
    questions = read("questions.json")
    assert len({q["question"] for q in questions}) == len(questions) == 15
    results = {}
    for size in SIZES:
        parts, vectors = index(pages, model, size)
        rows = []
        for q in questions:
            assert q["passage"] in pages[q["page"]], q
            ranking = ranked(q["question"], model, parts, vectors)
            rank = next((i for i,c in enumerate(ranking,1)
                         if c["page"] == q["page"] and q["passage"] in c["text"]), None)
            rows.append(dict(id=q["id"], gold_rank=rank, top5=ranking[:5]))
        hits = sum(r["gold_rank"] is not None and r["gold_rank"] <= 5 for r in rows)
        results[size] = dict(chunks=len(parts), hits=hits, recall_at_5=hits/len(rows), rows=rows)
        print(size, len(parts), hits, [r["gold_rank"] for r in rows])
    write("results.json", results)

def extract(question, hits, encoder):
    candidates = {}
    for ref, hit in enumerate(hits, 1):
        for sentence in re.split(r"(?<=[.!?]) +", hit["text"]):
            if len(sentence.split()) >= 5:
                candidates.setdefault(sentence, ref)
    if not candidates:
        return "Insufficient evidence."
    sentences = list(candidates)
    scores = encoder.encode(sentences) @ encoder.encode([question])[0]
    best = np.argsort(-scores, kind="stable")[:2]
    return " ".join(f"{sentences[i]} [{candidates[sentences[i]]}]" for i in best)

def generate(question, hits):
    if not hits:
        return "Insufficient evidence."
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tok = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForCausalLM.from_pretrained(MODEL, revision=REVISION, dtype=torch.float32).eval()
    evidence = "\n\n".join(f"[{i}] git-{c['page']} | {c['text']}" for i,c in enumerate(hits,1))
    messages = [{"role":"system","content":"Answer the question briefly using only these manual excerpts. Cite the supporting excerpt number in brackets. If the answer is missing, say 'Insufficient evidence.'"},
                {"role":"user","content":evidence + "\n\nQuestion: " + question}]
    batch = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=True,
                                    return_tensors="pt", return_dict=True)
    with torch.inference_mode():
        output = model.generate(**batch, do_sample=False, max_new_tokens=96)
    return tok.decode(output[0,batch["input_ids"].shape[1]:], skip_special_tokens=True).strip()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["evaluate","ask"])
    parser.add_argument("question", nargs="?")
    parser.add_argument("--extract", action="store_true", help="Return two cited source sentences instead of loading the generator.")
    parser.add_argument("--size", type=int, choices=SIZES, default=80)
    args = parser.parse_args()
    if args.mode == "ask" and not args.question:
        parser.error("ask requires a question")
    pages = read("pages.json")
    encoder = LSA(pages)
    if args.mode == "evaluate":
        evaluate(pages, encoder)
    else:
        hits = ranked(args.question, encoder, *index(pages, encoder, args.size))[:5]
        answer = extract(args.question, hits, encoder) if args.extract else generate(args.question, hits)
        result = dict(question=args.question, size=args.size, answer=answer, evidence=hits)
        print(json.dumps(result, ensure_ascii=True, indent=2))
