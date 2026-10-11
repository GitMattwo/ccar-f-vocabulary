# CCAR-F 英単語帳

英語の設問を読むための、620項目の日本語単語帳です。語の意味、品詞、発音記号、オリジナルの例文と和訳を収録しています。

- **[PDFを読む](vocab/build/CCAR-F_vocab.pdf)**
- **[Markdownを読む](vocab/entries/ccar-f.md)**
- [語彙データ（JSON）](data/vocabulary.json)

動詞には自動詞・他動詞などの情報を付けています。発音は原則アメリカ英語で、英国発音にはUKと記しています。主強勢 `ˈ` と副強勢 `ˌ` は、対応する母音の真上に配置しています。

例文・和訳・使い方の説明は、この公開版のために作成しました。本書は非公式の学習資料です。

## 内容を修正する

`data/vocabulary.json` が本文の正本です。各項目の `word`（見出し）、`meaning`（意味）、`pos`（品詞）、`ipa`（標準IPA）、`context`（使い方）、`examples`（例文と和訳）を編集します。`examples` の `target` は、その例文で学習する実際の語句です。

MarkdownとLaTeXは、Python 3の標準ライブラリだけで再生成できます。

```sh
python3 vocab/gen_vocab.py --validate-only
python3 vocab/gen_vocab.py
```

## PDFを生成する

LuaLaTeX、luatexja、Noto Serif/Sans CJK JP、DejaVu Sansが必要です。表や見出しの組版には `tcolorbox`、`booktabs`、`longtable`、`titlesec`、`needspace`、`fancyhdr` などのTeXパッケージを使います。

```sh
cd vocab/build
lualatex -interaction=nonstopmode -halt-on-error CCAR-F_vocab.tex
lualatex -interaction=nonstopmode -halt-on-error CCAR-F_vocab.tex
lualatex -interaction=nonstopmode -halt-on-error CCAR-F_vocab.tex
```

3回実行すると目次のページ番号が確定します。強勢記号の位置は、`vocab/ipa_glyph_metrics.json` に記録したDejaVu Sansの字形に基づきます。

## 発音のSVGを再生成する

既存のSVGは同梱しています。発音を変更した場合は、ReportLab、Popplerの `pdftocairo`、DejaVu Sansの通常体・太字体を用意して、リポジトリのルートで実行します。

```sh
python3 -m pip install reportlab
python3 vocab/render_ipa_assets.py vocab \
  --font /path/to/DejaVuSans.ttf \
  --bold-font /path/to/DejaVuSans-Bold.ttf \
  --pdftocairo /path/to/pdftocairo
```

SVGには字形をパスとして保存しているため、読む側にフォントのインストールは不要です。再生成時には、フォントのSHA-256が字形の測定値と一致することを検証します。
