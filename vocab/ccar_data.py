"""Load the self-contained vocabulary and independently authored examples."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data/vocabulary.json").read_text(encoding="utf-8"))
LAYOUT = json.loads((ROOT / "data/layout.json").read_text(encoding="utf-8"))
TITLE = "CCAR-F 英単語帳 — 問題文を読み切る"
SUBTITLE = "公開版 2026-10-11 ｜ 620項目 ｜ 品詞・オリジナル例文・和訳・強勢付きIPA"
SOURCE_NOTE = "用例・和訳・使い方の説明は、この公開版のために作成した学習用の内容です。本書は非公式の学習資料です。"
PRONUNCIATION_GUIDE = LAYOUT["PRONUNCIATION_GUIDE"]
COMPACT_TOC = LAYOUT["COMPACT_TOC"]
SEPARATE_TOC = LAYOUT["SEPARATE_TOC"]
HIGHLIGHT_STRESS = LAYOUT["HIGHLIGHT_STRESS"]
OVERHEAD_STRESS = LAYOUT["OVERHEAD_STRESS"]
PLAIN_TEXT_MARKDOWN = LAYOUT["PLAIN_TEXT_MARKDOWN"]
FOUNDATION_PAGES = []
FOUNDATION_NOTE = ""
HOWTO = []
READING_STEPS = []
PAIRS = []
PAIR_POS = {}
IPA_OMISSIONS = set(DATA["ipa_omissions"])
IPA = {entry["word"]: entry["ipa"] for entry in DATA["entries"] if entry["ipa"]}
SECTIONS = [
    {"title": section["title"], "short": section["name"], "intro": "", "rows": [
        (entry["word"], entry["meaning"], entry["context"], "", entry["pos"])
        for entry in DATA["entries"] if entry["section"] == section["id"]
    ]}
    for section in DATA["sections"]
]
ENTRY_DETAILS = {}
for entry in DATA["entries"]:
    examples = [
        {"example": example["en"], "example_ja": example["ja"]}
        for example in entry["examples"]
    ]
    ENTRY_DETAILS[entry["word"]] = {**examples[0], "extra_examples": examples[1:]}
