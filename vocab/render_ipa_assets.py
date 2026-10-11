#!/usr/bin/env python3
"""Generate self-contained CCAR-F IPA SVGs with stress above the vowel nucleus.

Run with the bundled Python (ReportLab is required):
    python3 vocab/render_ipa_assets.py vocab

The pronunciation data remains standard IPA. Geometry and colors are shared
with the PDF generator through ipa_stress.py. Temporary PDFs embed DejaVu Sans;
pdftocairo converts them to paths, so SVG viewers need no matching fonts.
"""

import argparse
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import ccar_data as DATA
from ipa_stress import MARK_COLORS, METRICS, display_parts, mark_offsets


FONT_SIZE = 10.5
MAX_WIDTH = 150.0
PADDING = 1.5
REGULAR_NAME = "CCAR-Ipa-Regular"
BOLD_NAME = "CCAR-Ipa-Bold"
TEXT_COLOR = "#555555"
SVG_NS = "http://www.w3.org/2000/svg"
RUNTIME = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"


def asset_name(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] + ".svg"


def source_values():
    values = set(DATA.IPA.values())
    values.update(example[1] for example in DATA.PRONUNCIATION_GUIDE.get("examples", []))
    values.discard("")
    if len({asset_name(value) for value in values}) != len(values):
        raise ValueError("IPA asset filenames have a hash collision")
    return sorted(values)


def find_file(explicit, env_name, candidates, description):
    requested = explicit or os.environ.get(env_name)
    if requested:
        path = Path(requested).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"{description} not found: {path}")
        return path
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise FileNotFoundError(f"{description} not found; set {env_name}")


def prepare_tools(args):
    regular = find_file(args.font, "VOCAB_IPA_FONT", [
        RUNTIME / "native/poppler/poppler/fonts/DejaVuSans.ttf",
        RUNTIME / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ], "DejaVu Sans regular font")
    bold = find_file(args.bold_font, "VOCAB_IPA_BOLD_FONT", [
        RUNTIME / "native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/Resources/fonts/truetype/DejaVuSans-Bold.ttf",
        RUNTIME / "native/poppler/poppler/fonts/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ], "DejaVu Sans bold font")
    converter = find_file(args.pdftocairo, "VOCAB_PDFTOCAIRO", [
        RUNTIME / "native/poppler/poppler/bin/pdftocairo",
        RUNTIME / "native/poppler/bin/pdftocairo",
        shutil.which("pdftocairo"),
    ], "pdftocairo")
    # The ink-center offsets were measured from these exact font files.
    for path, key in ((regular, "regular_sha256"), (bold, "bold_sha256")):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != METRICS[key]:
            raise ValueError(f"Font differs from the shared IPA metrics ({key}): {path}")
    pdfmetrics.registerFont(TTFont(REGULAR_NAME, str(regular)))
    pdfmetrics.registerFont(TTFont(BOLD_NAME, str(bold)))
    return converter


def part_width(parts):
    return sum(pdfmetrics.stringWidth(text, REGULAR_NAME, FONT_SIZE) for text, _ in parts)


def word_tokens(parts):
    """Keep marked nuclei intact, and allow breaks only at source whitespace."""
    tokens = []
    word = []
    for text, mark in parts:
        if mark:
            if any(char.isspace() for char in text):
                raise ValueError("A marked nucleus cannot contain whitespace")
            word.append((text, mark))
            continue
        for chunk in re.findall(r"\s+|\S+", text):
            if chunk.isspace():
                if word:
                    tokens.append((False, word))
                    word = []
                tokens.append((True, [(chunk, None)]))
            else:
                word.append((chunk, None))
    if word:
        tokens.append((False, word))
    return tokens


def wrap_parts(parts):
    """Return lines no wider than MAX_WIDTH, including the outer padding."""
    lines = []
    current = []
    pending_space = []
    content_limit = MAX_WIDTH - 2 * PADDING
    for is_space, token in word_tokens(parts):
        if is_space:
            if current:
                pending_space.extend(token)
            continue
        if part_width(token) > content_limit + 1e-6:
            raise ValueError("An IPA word is wider than the asset: " + "".join(t for t, _ in token))
        proposed = current + pending_space + token
        if current and part_width(proposed) > content_limit + 1e-6:
            lines.append(current)
            current = token
        else:
            current = proposed
        pending_space = []
    if current:
        lines.append(current)
    if not lines:
        raise ValueError("Cannot render an empty IPA")
    return lines


def render_pdf(value, destination):
    parts = display_parts(value)
    lines = wrap_parts(parts)
    width = min(MAX_WIDTH, max(part_width(line) for line in lines) + 2 * PADDING)
    # Reserve a conservative 1.28 em above the baseline. The actual mark
    # position follows each nucleus's ink top through the shared offsets.
    mark_top = max(mark_offsets(nucleus, mark)[1] + METRICS["marks"][mark]["top"]
                   for nucleus in METRICS["nuclei"] for mark in MARK_COLORS)
    top = max(1.28, mark_top)
    bottom = 0.30
    leading = (top + bottom + 0.15) * FONT_SIZE
    height = (top + bottom) * FONT_SIZE + (len(lines) - 1) * leading + 2 * PADDING
    pdf = canvas.Canvas(str(destination), pagesize=(width, height), invariant=1)
    baseline = height - PADDING - top * FONT_SIZE
    placements = []
    for line_number, line in enumerate(lines):
        x = PADDING
        y = baseline - line_number * leading
        for text, mark in line:
            pdf.setFont(REGULAR_NAME, FONT_SIZE)
            pdf.setFillColor(HexColor(TEXT_COLOR))
            pdf.drawString(x, y, text)
            if mark:
                dx, dy = mark_offsets(text, mark)
                pdf.setFont(BOLD_NAME, FONT_SIZE)
                pdf.setFillColor(HexColor(MARK_COLORS[mark]))
                pdf.drawString(x + dx * FONT_SIZE, y + dy * FONT_SIZE, mark)
                nucleus = METRICS["nuclei"][text]
                glyph = METRICS["marks"][mark]
                center = x + (nucleus["left"] + nucleus["right"]) * FONT_SIZE / 2
                mark_center = x + (dx + (glyph["left"] + glyph["right"]) / 2) * FONT_SIZE
                if abs(center - mark_center) > 1e-7:
                    raise ValueError("A stress mark is not centered on its vowel nucleus")
                if y + (dy + glyph["top"]) * FONT_SIZE > height - PADDING + 1e-7:
                    raise ValueError("A stress mark exceeds the asset height")
                placements.append((text, mark, line_number))
            x += pdfmetrics.stringWidth(text, REGULAR_NAME, FONT_SIZE)
    pdf.save()
    expected_marks = sum(mark is not None for _, mark in parts)
    if len(placements) != expected_marks:
        raise ValueError("An IPA stress mark was lost during line wrapping")
    return {"lines": len(lines), "marks": expected_marks, "width": width, "height": height}


def validate_svg(path):
    """Reject font-dependent text, external resources, and oversized output."""
    document = ET.parse(path)
    root = document.getroot()
    if root.tag != f"{{{SVG_NS}}}svg":
        raise ValueError(f"Not an SVG: {path}")
    dimensions = []
    for attribute in ("width", "height"):
        value = root.get(attribute, "")
        match = re.fullmatch(r"([0-9.]+)pt", value)
        if not match or float(match.group(1)) <= 0:
            raise ValueError(f"Invalid SVG {attribute}: {path}")
        dimensions.append(float(match.group(1)))
    if dimensions[0] > MAX_WIDTH + 0.001:
        raise ValueError(f"SVG is wider than {MAX_WIDTH} pt: {path}")
    forbidden = {"text", "script", "image", "foreignObject", "font", "font-face"}
    paths = 0
    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1]
        if local_name in forbidden:
            raise ValueError(f"Non-outline SVG element {local_name}: {path}")
        paths += local_name == "path"
        for name, value in element.attrib.items():
            if name.rsplit("}", 1)[-1] == "href" and not value.startswith("#"):
                raise ValueError(f"External SVG resource: {path}")
            if "font-" in name or "font-" in value:
                raise ValueError(f"SVG still depends on a font: {path}")
            for target in re.findall(r"url\(([^)]+)\)", value):
                if not target.strip("\"' ").startswith("#"):
                    raise ValueError(f"External SVG style resource: {path}")
    if not paths:
        raise ValueError(f"SVG contains no glyph paths: {path}")
    return dimensions


def generate(root, converter):
    values = source_values()
    target = root / "entries" / "ccar-ipa"
    target.mkdir(parents=True, exist_ok=True)
    stats = []
    with tempfile.TemporaryDirectory(prefix="ccar-ipa-assets-") as temporary:
        working = Path(temporary)
        for value in values:
            pdf_path = working / "pronunciation.pdf"
            svg_path = working / "pronunciation.svg"
            stats.append(render_pdf(value, pdf_path))
            result = subprocess.run([str(converter), "-svg", str(pdf_path), str(svg_path)],
                                    capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"pdftocairo failed for {value!r}: {result.stderr.strip()}")
            validate_svg(svg_path)
            # A failed conversion cannot overwrite a previously valid asset.
            os.replace(svg_path, target / asset_name(value))
    expected = {asset_name(value) for value in values}
    # This directory belongs to the generator. Only remove its hash-named files.
    for path in target.glob("*.svg"):
        if re.fullmatch(r"[0-9a-f]{16}\.svg", path.name) and path.name not in expected:
            path.unlink()
    actual = {path.name for path in target.glob("*.svg")}
    if actual != expected:
        raise ValueError("Unexpected SVG files in generated IPA directory: " + ", ".join(sorted(actual - expected)))
    dimensions = [validate_svg(target / filename) for filename in sorted(expected)]
    print(f"Generated {len(values)} IPA SVG files in {target}; "
          f"{sum(s['marks'] for s in stats)} centered stress marks; "
          f"{sum(s['lines'] > 1 for s in stats)} wrapped; "
          f"max width {max(d[0] for d in dimensions):.3f} pt. "
          "All SVGs are self-contained glyph outlines.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path(__file__).resolve().parent,
                        help="vocab output directory (default: this script's directory)")
    parser.add_argument("--font", help="DejaVuSans.ttf matching the shared glyph metrics")
    parser.add_argument("--bold-font", help="DejaVuSans-Bold.ttf matching the shared glyph metrics")
    parser.add_argument("--pdftocairo", help="Poppler pdftocairo executable")
    args = parser.parse_args()
    converter = prepare_tools(args)
    generate(args.root.resolve(), converter)


if __name__ == "__main__":
    main()
