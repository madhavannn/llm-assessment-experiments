"""Post-evaluation vocabulary probes. These do not change baseline recall."""
from rag import LSA, index, ranked, read, write

pages = read("pages.json")
questions = read("questions.json")
encoder = LSA(pages)
parts, vectors = index(pages, encoder, 80)
rows = []
for qid, extra in [(3, "git clean untracked nested -f"), (5, "linked worktree prune administrative files portable device")]:
    q = questions[qid - 1]
    ranks = []
    for query in [q["question"], q["question"] + " " + extra]:
        full = ranked(query, encoder, parts, vectors)
        ranks.append(next(i for i,c in enumerate(full,1) if c["page"]==q["page"] and q["passage"] in c["text"]))
    rows.append(dict(id=qid, added_terms=extra, original_rank=ranks[0], expanded_rank=ranks[1]))
print(rows)
write("diagnostics.json",rows)
