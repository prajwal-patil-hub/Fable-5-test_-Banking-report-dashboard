"""Extraction-quality gate: the stress PDF replicates hostile real-report
patterns; every ground-truth figure must come out exactly right.

This is the guard rail for extractor changes — if a tweak to aliases, regexes
or resolution breaks a real-world pattern, this test names the exact KPI.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import make_stress_pdf
from app.modules.document_intelligence.extractors import DEFAULT_EXTRACTORS, resolve
from app.modules.document_intelligence.pipeline import read_pdf


def test_stress_pdf_full_ground_truth(tmp_path):
    pdf_path = tmp_path / "stress.pdf"
    make_stress_pdf.build(str(pdf_path))

    pages = read_pdf(pdf_path.read_bytes())
    candidates = []
    for extractor in DEFAULT_EXTRACTORS:
        candidates.extend(extractor.extract(pages))
    resolved = resolve(candidates)

    wrong = {}
    missing = []
    for code, expected in make_stress_pdf.EXPECTED.items():
        got = resolved.get(code)
        if got is None:
            missing.append(code)
        elif abs(got.value - expected) > 0.005:
            wrong[code] = (expected, got.value, got.source_text)

    assert not missing, f"not extracted: {missing}"
    assert not wrong, f"wrong values: {wrong}"


def test_stress_tricky_patterns_specifically(tmp_path):
    pdf_path = tmp_path / "stress.pdf"
    make_stress_pdf.build(str(pdf_path))
    pages = read_pdf(pdf_path.read_bytes())
    candidates = []
    for extractor in DEFAULT_EXTRACTORS:
        candidates.extend(extractor.extract(pages))
    resolved = resolve(candidates)

    # movement-then-level: must take 3.85 (the level), not 0.25 (25 bps move)
    assert resolved["nim"].value == 3.85
    # "per cent" spelled out
    assert resolved["roa"].value == 1.42
    # multi-year table: current year is the LAST column, not the first numeric
    assert resolved["nii"].value == 33410.0
    assert resolved["gnpa"].value == 5400.0
    # ratio table with unit in the label, bare numeric cells
    assert resolved["crar"].value == 17.1
