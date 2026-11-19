"""Extract a fixed selection of installed Git HTML manuals into plain text."""
import argparse
import json
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
COMMANDS = """add am apply archive bisect blame branch bundle checkout cherry-pick
clean clone commit describe diff fetch format-patch gc grep init log merge
mv notes pull push rebase reflog remote reset restore revert show stash tag worktree""".split()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("manual_directory", type=Path)
    args = parser.parse_args()
    pages = {}
    for cmd in COMMANDS:
        source = args.manual_directory / f"git-{cmd}.html"
        soup = BeautifulSoup(source.read_bytes(), "html.parser")
        raw = soup.select_one("#content").get_text(" ", strip=True)
        pages[cmd] = " ".join(raw.replace("\u200b", "").split())
    (ROOT / "pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")
