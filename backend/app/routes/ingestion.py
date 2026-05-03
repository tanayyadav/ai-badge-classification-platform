"""
NJIT AI-Assisted Digital Badge Classification Tool
Author: R
Institution: New Jersey Institute of Technology
Capstone Project — Spring 2026

POST /ingest — accepts raw badge input and returns a normalised BadgeFactSheet.

Input contract (docs/architecture.md):
    {
        "input_type": "obv3_json" | "form" | "free_text",
        "payload": { ... } | "..."
    }

Response: BadgeFactSheet JSON
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.badge_fact_sheet import BadgeFactSheet
from app.services.normalization.normalizer import normalize

router = APIRouter()


class IngestRequest(BaseModel):
    input_type: str
    payload: Any


@router.post("/ingest", response_model=BadgeFactSheet)
def ingest_badge(request: IngestRequest) -> BadgeFactSheet:
    """
    Normalise raw badge input into a BadgeFactSheet.

    The returned BFS can be inspected, corrected, and then passed
    to POST /classify.
    """
    try:
        bfs = normalize(request.input_type, request.payload)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return bfs
