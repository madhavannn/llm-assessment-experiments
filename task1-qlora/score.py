"""Re-score the saved generations with the original held-out answer key."""
import json
from pathlib import Path

root = Path(__file__).resolve().parent
test = [json.loads(line) for line in (root / "data/test.jsonl").read_text(encoding="utf-8").splitlines()]
for setting in ("baseline", "finetuned"):
    rows = (root / f"{setting}.jsonl").read_text(encoding="utf-8").splitlines()
    exact = 0
    valid = 0
    for line, gold in zip(rows, test, strict=True):
        row = json.loads(line)
        assert row["input"] == gold["input"] and row["expected"] == gold["output"]
        try:
            prediction = json.loads(row["raw"])
        except json.JSONDecodeError:
            prediction = None
        valid += isinstance(prediction, dict)
        exact += prediction == gold["output"]
    print(f"{setting}: {exact}/{len(test)} exact, {valid}/{len(test)} valid objects")

