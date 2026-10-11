#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate the public CCAR-F vocabulary Markdown and LaTeX from data/vocabulary.json.

Usage: python3 vocab/gen_vocab.py [output_directory] [--validate-only]
Compile vocab/build/CCAR-F_vocab.tex with LuaLaTeX to generate the PDF.
"""
import argparse
import hashlib
import html
import re
from pathlib import Path

import ccar_data as D

IPA = D.IPA

EXAM = "ccar-f"

# --------------------------------------------------------------- LaTeX escape
ESC = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def tex(s):
    out = []
    for ch in s:
        out.append(ESC.get(ch, ch))
    return "".join(out)


def mark(tag):
    """行頭マーカーは付けない（記号を混ぜると和欧の行高がずれて英語と意味の高さが合わなくなる）。
    タグ k/n/b は収録理由の分類に使う。基礎語 b は用例などの必須情報も検証する。"""
    return ""


def md_mark(tag):
    return ""


def md_text(value):
    """原文中のXMLや記号を、Markdown表では文字として表示する。"""
    if not getattr(D, "PLAIN_TEXT_MARKDOWN", False):
        return value
    return html.escape(value, quote=False).replace("|", "&#124;").replace("\n", "<br>")


def ipa_tex(value):
    """標準IPAは保存し、希望された学習用の配置を表示時に適用する。"""
    if getattr(D, "OVERHEAD_STRESS", False) and "/" in value:
        from ipa_stress import display_parts, mark_offsets
        result = []
        for part, stress in display_parts(value):
            if stress:
                x, y = mark_offsets(part, stress)
                color = "vkey" if stress == "ˈ" else "vhead"
                result.append(r"\ipastress{%s}{%s}{%s}{%.6f}{%.6f}" %
                              (color, stress, tex(part), x, y))
            else:
                result.append(tex(part))
        return "".join(result)
    value = tex(value)
    if getattr(D, "HIGHLIGHT_STRESS", False):
        value = value.replace("ˈ", r"{\color{vkey}\bfseries ˈ}")
        value = value.replace("ˌ", r"{\color{vhead}\bfseries ˌ}")
    return value


def ipa_md(value):
    if getattr(D, "OVERHEAD_STRESS", False) and "/" in value:
        name = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] + ".svg"
        alt = value.replace("[", r"\[").replace("]", r"\]")
        return "![発音（標準IPA: %s）](ccar-ipa/%s)" % (alt, name)
    value = md_text(value)
    if getattr(D, "HIGHLIGHT_STRESS", False):
        value = value.replace("ˈ", "<strong>ˈ</strong>").replace("ˌ", "<strong>ˌ</strong>")
    return value


def entry_context(item):
    """意味と文脈は行データ、用例と和訳は同じ公開用データから生成する。"""
    details = D.ENTRY_DETAILS.get(item[0], {})
    parts = [item[2]]
    if details.get("example"):
        parts.append("用例: " + details["example"])
    if details.get("example_ja"):
        parts.append("訳: " + details["example_ja"])
    for example in details.get("extra_examples", []):
        parts.append("用例: " + example["example"])
        parts.append("訳: " + example["example_ja"])
    return parts


def validate_data():
    """Validate the self-contained public dataset and IPA geometry."""
    entries = D.DATA["entries"]
    words = [entry["word"] for entry in entries]
    if len(words) != len(set(word.casefold() for word in words)):
        raise ValueError("見出し語が重複しています")
    if len(entries) != D.DATA["entry_count"]:
        raise ValueError("項目数が一致しません")
    missing = set(words) - set(IPA)
    if missing != D.IPA_OMISSIONS:
        raise ValueError("発音の省略リストが一致しません")
    from ipa_stress import stress_spans, mark_offsets
    for value in list(IPA.values()) + [ex[1] for ex in D.PRONUNCIATION_GUIDE["examples"]]:
        spans = stress_spans(value)
        if len(spans) != value.count("ˈ") + value.count("ˌ"):
            raise ValueError("強勢記号が母音に対応していません: " + value)
        for _, start, end, stress in spans:
            mark_offsets(value[start:end], stress)
    for entry in entries:
        for field in ("word", "meaning", "pos", "context"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError("項目が不足しています: " + field)
        if not entry.get("examples"):
            raise ValueError("用例がありません: " + entry["word"])
        for example in entry["examples"]:
            if not all(example.get(key, "").strip() for key in ("en", "ja", "target")):
                raise ValueError("用例が不足しています: " + entry["word"])
            if example["target"].casefold() not in example["en"].casefold():
                raise ValueError("用例中に対象語句がありません: " + entry["word"])
    known_sections = {section["id"] for section in D.DATA["sections"]}
    if {entry["section"] for entry in entries} != known_sections:
        raise ValueError("章の対応が不正です")


def row(item):
    en, ja, ctx = item[0], item[1], item[2]
    tag = item[3] if len(item) > 3 else ""
    head = "\\en{%s}" % tex(en)
    ipa = IPA.get(en)
    if ipa:
        strut = r"\ipastrut " if getattr(D, "OVERHEAD_STRESS", False) else ""
        head += "\\newline{\\ipa %s%s}" % (strut, ipa_tex(ipa))
    meaning = r"\pos{" + tex(item[4]) + r"}\newline " + tex(ja)
    context = r"\newline ".join(tex(part) for part in entry_context(item))
    return "%s%s & %s & %s \\\\\n" % (mark(tag), head, meaning, context)


# --------------------------------------------------------------------- LaTeX
PREAMBLE = r"""% !TEX program = lualatex
% CCAR-F 英単語帳（公開版）— gen_vocab.py の自動生成物。手で直さない。
\documentclass[a4paper,10pt]{ltjsarticle}
\usepackage[top=14mm,bottom=16mm,left=14mm,right=14mm]{geometry}

\usepackage{luatexja-fontspec}
\setmainfont{TeX Gyre Pagella}
\setsansfont{TeX Gyre Heros}
\setmainjfont{Noto Serif CJK JP}
\setsansjfont{Noto Sans CJK JP}
% 発音記号用（IPA 拡張を全部持っているフォント。TeX Live 同梱の DejaVu を使う）
\newfontfamily\ipafont{DejaVu Sans}[Scale=0.78]
% θ などギリシャ文字を和文扱いにしない（既定では range 2 が JAchar になり、発音記号の中で字間が開く）
\ltjsetparameter{jacharrange={-2}}

\usepackage{xcolor}
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{booktabs}
\usepackage{array}
\usepackage{enumitem}
\usepackage{tcolorbox}
\usepackage{fancyhdr}

\definecolor{vhead}{HTML}{1F3A5F}
\definecolor{vrule}{HTML}{9AA7B5}
\definecolor{vkey}{HTML}{B3261E}
\definecolor{vnote}{HTML}{8A6D1F}
\definecolor{vband}{HTML}{EDF1F6}
\definecolor{vgray}{HTML}{5A5A5A}

% 見出し
\usepackage{needspace}
\usepackage{titlesec}
\titleformat{\section}{\sffamily\large\bfseries\color{vhead}}{}{0pt}{}
\titlespacing*{\section}{0pt}{1.6em}{0.6em}
\titleformat{\subsection}{\sffamily\normalsize\bfseries\color{vhead}}{}{0pt}{}
\titlespacing*{\subsection}{0pt}{1.0em}{0.4em}
% titlesec が設定した見出し処理に、hyperref のリンク先処理を適用する。
\usepackage[hidelinks]{hyperref}

\pagestyle{fancy}
\fancyhf{}
\fancyhead[L]{\footnotesize\sffamily\color{vgray}CCAO-F 英単語帳}
\fancyhead[R]{\footnotesize\sffamily\color{vgray}\thepage}
\renewcommand{\headrulewidth}{0.2pt}

\setcounter{secnumdepth}{0}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0.4\baselineskip}
\setlist{itemsep=0.15em, parsep=0pt, topsep=0.25em, leftmargin=1.2em}

% 英語見出し語と、その下に置く発音記号
\newcommand{\en}[1]{\textsf{\textbf{#1}}}
\newcommand{\ipa}{\ipafont\color{vgray}}
\newcommand{\pos}[1]{{\sffamily\mdseries\scriptsize\color{vhead}#1}}

% 語彙表
\newlength{\vocabrowspace}
\newenvironment{vtab}{%
  \footnotesize
  % 表の中では baselineskip が変わるため、本文1行分を先に保存する。
  \setlength{\vocabrowspace}{\baselineskip}
  \setlength{\tabcolsep}{4pt}
  \renewcommand{\arraystretch}{1.18}
  \begin{longtable}{@{}>{\raggedright}p{0.265\textwidth}>{\raggedright}p{0.205\textwidth}>{\raggedright\arraybackslash}p{0.475\textwidth}@{}}
  \toprule
  \sffamily\bfseries 英語 & \sffamily\bfseries 品詞・意味 & \sffamily\bfseries 使い方・オリジナル例文 \\
  \midrule
  \endfirsthead
  \toprule
  \sffamily\bfseries 英語 & \sffamily\bfseries 品詞・意味 & \sffamily\bfseries 使い方・オリジナル例文 \\
  \midrule
  \endhead
  \bottomrule
  \endfoot
}{%
  \end{longtable}
}

\newtcolorbox{vbx}[1]{colback=vband,colframe=vrule,boxrule=0.3pt,arc=1pt,
  left=5pt,right=5pt,top=4pt,bottom=4pt,
  fonttitle=\sffamily\bfseries\small,title={#1}}

\begin{document}
"""


def emit_tex():
    preamble = PREAMBLE.replace("CCAO-F", EXAM.upper())
    if getattr(D, "HIGHLIGHT_STRESS", False):
        preamble = preamble.replace("[Scale=0.78]", "[Scale=0.94]")
    if getattr(D, "OVERHEAD_STRESS", False):
        commands = r"""
% Stress glyph ink centers are aligned over the vowel nucleus; offsets are em.
\newcommand{\ipastress}[5]{\mbox{\rlap{\kern#4em\raisebox{#5em}{{\color{#1}\bfseries#2}}}#3}}
\newcommand{\ipastrut}{\rule{0pt}{1.45em}}
"""
        preamble = preamble.replace(r"\begin{document}", commands + r"\begin{document}")
    L = [preamble]
    a = L.append
    a(r"\begin{center}" "\n")
    a(r"{\sffamily\bfseries\Large\color{vhead} " + tex(D.TITLE) + r"}\\[0.4em]" "\n")
    a(r"{\footnotesize\sffamily\color{vgray} " + tex(D.SUBTITLE) + r"}" "\n")
    a(r"\end{center}" "\n\n")
    if D.HOWTO:
        a(r"\begin{vbx}{この単語帳の使い方}" "\n")
        for line in D.HOWTO:
            a(r"\textbullet\ " + tex(line) + r"\\" "\n")
        a(r"\end{vbx}" "\n\n")
    if getattr(D, "PRONUNCIATION_GUIDE", None):
        guide = D.PRONUNCIATION_GUIDE
        a(r"\begin{vbx}{発音記号と強勢の読み方}" "\n")
        a(r"\small" "\n")
        for line in guide["intro"]:
            text = tex(line)
            for symbol in ("ˈ", "ˌ"):
                text = text.replace(symbol, r"{\ipa " + ipa_tex(symbol) + "}")
            a(text + r"\par" "\n")
        for word, pronunciation, explanation in guide["examples"]:
            strut = r"\ipastrut " if getattr(D, "OVERHEAD_STRESS", False) else ""
            a(r"\en{" + tex(word) + r"}\quad {\ipa " + strut + ipa_tex(pronunciation)
              + r"}\quad " + tex(explanation) + r"\par" "\n")
        a(tex(guide["note"]) + "\n")
        if guide.get("reference"):
            label, url = guide["reference"]
            a(r"\par{\scriptsize 参考: \href{" + tex(url) + "}{" + tex(label) + "}}\n")
        a(r"\end{vbx}" "\n\n")
    if getattr(D, "READING_STEPS", None):
        a(r"\begin{vbx}{問題文を読む順番}" "\n")
        a(r"\small" "\n")
        for line in D.READING_STEPS:
            a(tex(line) + r"\par" "\n")
        a(r"\end{vbx}" "\n\n")
    a(r"{\footnotesize " + tex(D.SOURCE_NOTE) + r"}" "\n\n")
    if getattr(D, "SEPARATE_TOC", False):
        a(r"\clearpage" "\n")
    if getattr(D, "COMPACT_TOC", False):
        a(r"\begingroup\setlength{\parskip}{0pt}" "\n")
        a(r"\tableofcontents" "\n")
        a(r"\endgroup" "\n")
    else:
        a(r"\tableofcontents" "\n")
    a(r"\clearpage" "\n")


    for sec in D.SECTIONS:
        a(r"\Needspace{14\baselineskip}" "\n")
        a("\n" + r"\section{%s}" % tex(sec["title"]) + "\n")
        if sec.get("intro"):
            a(r"{\footnotesize " + tex(sec["intro"]) + r"}" "\n\n")
        for box in sec.get("boxes", []):
            a(r"\begin{vbx}{%s}" % tex(box[0]) + "\n")
            a(r"\footnotesize" "\n")
            for line in box[1]:
                a(r"\textbullet\ " + tex(line) + r"\\" "\n")
            a(r"\end{vbx}" "\n\n")
        if sec.get("rows"):
            a(r"\begin{vtab}" "\n")
            for index, item in enumerate(sec["rows"]):
                if index:
                    a(r"\addlinespace[\vocabrowspace]" "\n")
                a(row(item))
            a(r"\end{vtab}" "\n")

    a("\n" + r"\end{document}" "\n")
    return "".join(L)


# ------------------------------------------------------------------ Markdown
def emit_md():
    L = []
    a = L.append
    a("# %s\n\n" % D.TITLE)
    a("> %s\n" % D.SUBTITLE)
    a("> 生成物：[PDF版](../build/%s_vocab.pdf)。このMarkdownとPDFは `data/vocabulary.json` から生成。\n" % EXAM.upper())
    a("\n")
    if D.HOWTO:
        a("**使い方**\n\n")
        for line in D.HOWTO:
            a("- %s\n" % line)
    if getattr(D, "PRONUNCIATION_GUIDE", None):
        guide = D.PRONUNCIATION_GUIDE
        a("\n**発音記号と強勢の読み方**\n\n")
        for line in guide["intro"]:
            a(ipa_md(line) + "\n\n")
        for word, pronunciation, explanation in guide["examples"]:
            a("- **%s** %s：%s\n" % (word, ipa_md(pronunciation), explanation))
        a("\n" + guide["note"] + "\n")
        if guide.get("reference"):
            label, url = guide["reference"]
            a("\n参考: [%s](%s)\n" % (label, url))
    if getattr(D, "READING_STEPS", None):
        a("\n**問題文を読む順番**\n\n")
        for line in D.READING_STEPS:
            a("- " + line + "\n")
    a("\n" + D.SOURCE_NOTE + "\n")
    a("\n---\n")
    for sec in D.SECTIONS:
        a("\n## %s\n\n" % sec["title"])
        if sec.get("intro"):
            a("%s\n\n" % sec["intro"])
        for box in sec.get("boxes", []):
            a("**%s**\n\n" % box[0])
            for line in box[1]:
                a("- %s\n" % line)
            a("\n")
        if sec.get("rows"):
            a("| 英語 | 品詞・意味 | 使い方・オリジナル例文 |\n|---|---|---|\n")
            for index, item in enumerate(sec["rows"]):
                tag = item[3] if len(item) > 3 else ""
                head = md_text(item[0])
                if IPA.get(item[0]):
                    head += "<br>" + ipa_md(IPA[item[0]])
                context = "<br>".join(md_text(part) for part in entry_context(item))
                meaning = "［" + md_text(item[4]) + "］<br>" + md_text(item[1])
                gap = "<br><br>" if index < len(sec["rows"]) - 1 else ""
                a("| %s%s%s | %s%s | %s%s |\n" % (md_mark(tag), head, gap, meaning, gap, context, gap))
    return "".join(L)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parent), help="出力先")
    parser.add_argument("--validate-only", action="store_true", help="出力せず語彙・用例・発音を検証")
    args = parser.parse_args()
    validate_data()
    if not args.validate_only:
        root = Path(args.root)
        (root / "build").mkdir(parents=True, exist_ok=True)
        (root / "entries").mkdir(parents=True, exist_ok=True)
        (root / "build/CCAR-F_vocab.tex").write_text(emit_tex(), encoding="utf-8")
        (root / "entries/ccar-f.md").write_text(emit_md(), encoding="utf-8")
    print("entries=%d sections=%d" % (len(D.DATA["entries"]), len(D.SECTIONS)))


if __name__ == "__main__":
    main()
