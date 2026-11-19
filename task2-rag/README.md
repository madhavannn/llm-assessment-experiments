# Task 2 · Retrieval from scratch

Open REPORT.md for the findings, all 15 questions, annotated source passages and ranks. The corpus contains 36 separate public Git reference pages (140,129 whitespace-delimited words). The corpus snapshot is included. Page identifiers are Git command names. HTML manuals have no stable printed page numbers.

## Reproduce

Run these commands from the extracted directory using Python. The evaluation needs only NumPy and runs on CPU. The question-answering command additionally loads the pinned Qwen model from Hugging Face on first use. Allow approximately 1 GB for the download.

```bash
python -m pip install numpy
python rag.py evaluate
python diagnose.py
python -m pip install torch transformers
python rag.py ask "What is the default age cutoff for ordinary reflog expiration when I leave the configuration alone?"
```

The default index uses 80 words. Pass `--size 240` to use the second index. Each answer is printed with its five numbered source excerpts in retrieval order, cosine scores, manual names and zero-based word offsets. To reproduce the recorded environment see versions.txt. Minor floating-point differences across builds can affect nearly tied scores.

## Included files

- pages.json contains the normalized manual text from Git for Windows 2.56.0.windows.4. Each key maps to https://git-scm.com/docs/git-COMMAND where COMMAND is the key. The bundled snapshot fixes the version for scoring.
- prepare.py regenerates the text when supplied the HTML manual directory. This optional step requires beautifulsoup4. GIT-LICENSE.txt reproduces the distributed license.
- questions.json records the 15 original evaluation prompts, reference answers and verified evidence spans. The questions were drafted for this exercise with AI assistance.
- rag.py fits the embedding model, builds the indexes, evaluates retrieval and answers arbitrary questions. Gold answers and passages are used only by evaluation.
- results.json preserves the top five passages and scores for every query and both configurations, plus the first full-span gold rank in the entire index.
- diagnostics.json and diagnose.py contain the two post-evaluation vocabulary probes.
- demo.json and demo-reflog.json preserve actual generator outputs and their evidence. The report discusses generation separately from retrieval.
For an extractive answer with no LLM download, append --extract to the ask command. It selects two distinct sentence spans from the five retrieved excerpts using the same embedding model. demo-extract.json records a correct answer to the stash question. demo-describe.json records a third generator check.
