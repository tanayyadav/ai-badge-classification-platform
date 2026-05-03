"""
Shared pytest fixtures for all backend tests.
"""

import os
import sys

import pytest

# Ensure backend/ is on the path for all tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.chdir(os.path.join(os.path.dirname(__file__), ".."))


from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.nlp.signal_extractor import SignalExtractor
from app.utils.canvas_code_parser import parse_canvas_code


@pytest.fixture(scope="session")
def extractor():
    """Single SignalExtractor instance shared across all tests."""
    return SignalExtractor(use_llm=False)


def classify(bfs: BadgeFactSheet, extractor: SignalExtractor) -> object:
    """
    Helper that mirrors the classify route's operation order:
      1. Parse canvas code if not yet parsed
      2. Run NLP extraction
      3. Run classification engine
    """
    from app.services.classification.engine import run_classification

    if bfs.canvas_course_code and bfs.canvas_sequence_number is None:
        parsed = parse_canvas_code(bfs.canvas_course_code)
        if parsed:
            bfs.canvas_pathway_code = parsed.get("canvas_pathway_code")
            bfs.canvas_sequence_number = parsed.get("canvas_sequence_number")
            bfs.is_capstone = bfs.is_capstone or parsed.get("is_capstone", False)

    bfs = extractor.extract_all(bfs)
    return run_classification(bfs)
