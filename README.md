[README (1).md](https://github.com/user-attachments/files/29367266/README.1.md)
# NJIT AI-Assisted Digital Badge Classification Tool

> A rule-based, explainable, and fully auditable web prototype that brings NJIT's digital badge taxonomy to life through a structured, human-in-the-loop classification workflow.

---

**Capstone Project · Spring 2026**  
**Institution:** New Jersey Institute of Technology  
**Faculty Advisor:** Prabhat Vaish  
**Supervisor:** Kerry Eberhardt

**Team**

| Name | Role | Contact |
|---|---|---|
| Rajat Ravindra Pednekar | System Architecture · NLP Pipeline · Schema Design | rp2348@njit.edu |
| Prabhath Vinay Vipparthi | Data Engineering · NLP Dictionary · Classification Engine · Testing | pv342@njit.edu |
| Sai Shivani Kushanapalli | Taxonomy Documentation · Frontend Implementation | sk3764@njit.edu |
| Tanay Yadav | Backend Design · Governance Design · Feedback Loop | ty233@njit.edu |

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Setup & Installation](#setup--installation)
- [Running the System](#running-the-system)
- [How to Use](#how-to-use)
- [API Reference](#api-reference)
- [Classification Taxonomy](#classification-taxonomy)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Non-Negotiable System Rules](#non-negotiable-system-rules)
- [License](#license)

---

## Overview

### The Problem

NJIT issues digital badges across five institutional units — the **Learning and Development Initiative (LDI)**, the **Office of Student Involvement and Leadership (OSIL)**, the **Makerspace**, the **Newark College of Engineering (NCE)**, and the **Office of Global Initiatives (OGI)**. Every badge must be formally classified against a three-stage hierarchical taxonomy — **Category**, **Type**, and **Level** — before it can be published. Before this system existed, that classification happened manually: slowly, inconsistently, and without any structured audit trail.

### The Solution

This prototype automates the classification process while keeping a human in control of every final decision. It accepts badge metadata in three formats (OBv3 JSON, a guided proposal form, or free text), normalizes everything into a structured **Badge Fact Sheet**, extracts classification signals through a four-layer NLP pipeline, applies NJIT's locked institutional taxonomy via a deterministic rule engine, and returns a fully explainable, auditable result that a human reviewer can accept or override.

### Core Design Principles

| Principle | How It's Implemented |
|---|---|
| **Deterministic** | The rule engine uses explicit `if/elif` chains — no ML model ever makes a classification decision |
| **Explainable** | Every classification produces a structured plain-English explanation citing rule IDs and signal sources |
| **Auditable** | A complete governance log entry is created and permanently stored for every classification |
| **Human-in-the-loop** | Reviewers accept or override with a mandatory reason; the final decision always belongs to a human |
| **Non-blocking** | Missing signals trigger targeted follow-up questions — they never prevent classification from completing |

---

## Architecture

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT LAYER                             │
│         OBv3 JSON  ·  Proposal Form  ·  Free Text               │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POST /ingest                               │
│                                                                  │
│  Ingestion     →  parser.py / form_mapper.py                    │
│  Normalization →  normalizer.py · issuer_resolver.py            │
│  Validation    →  EC01–EC03 · EC24                              │
│                   (whitespace, duplicates, short content,        │
│                    implied series detection)                     │
│                                                                  │
│  OUTPUT: Badge Fact Sheet (60+ structured fields)               │
└────────────────────────────┬────────────────────────────────────┘
                             │  BadgeFactSheet
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POST /classify                             │
│                                                                  │
│  NLP Pipeline  →  Layer 1: Phrase matching (phrase_dictionary)  │
│                   Layer 2: Regex patterns  (pattern_rules)      │
│                   Layer 3: spaCy Bloom     (bloom_extractor)    │
│                   Layer 4: LLM stub        (llm_extractor)      │
│                                                                  │
│  Rule Engine   →  Stage 1: Category  (S1R01–S1R08)             │
│                   Stage 2: Type      (S2R01–S2R11)              │
│                   Stage 3: Level     (4 type-specific branches) │
│                                                                  │
│  Explainability →  explainer.py (8-element plain-English output)│
│  Governance     →  governance_logger.py (full audit entry)      │
│                                                                  │
│  OUTPUT: ClassificationResult with log_id                       │
└────────────────────────────┬────────────────────────────────────┘
                             │  log_id + recommendation
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POST /review                               │
│                                                                  │
│  Reviewer accepts or overrides any of the three stages          │
│  Override reason enforced (≥ 20 chars · valid taxonomy pair)    │
│  Final decision locked into the governance log                  │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Breakdown

| Layer | Purpose | Key Files |
|---|---|---|
| **Ingestion** | Parse OBv3 JSON, map form fields, detect issuer via keyword matching | `parser.py`, `form_mapper.py` |
| **Normalization** | Convert any input into a standardized Badge Fact Sheet | `normalizer.py`, `issuer_resolver.py` |
| **NLP Pipeline** | Extract classification signals from badge text across four layers | `phrase_dictionary.py`, `pattern_rules.py`, `bloom_extractor.py`, `signal_extractor.py` |
| **Rule Engine** | Deterministic three-stage classification | `stage1.py`, `stage2.py`, `stage3.py`, `engine.py` |
| **Explainability** | Generate a structured plain-English explanation with rule references | `explainer.py` |
| **Governance** | Permanent, queryable audit trail for every classification event | `governance_logger.py` |

---

## Tech Stack

### Backend

| Technology | Purpose | Version |
|---|---|---|
| Python | Core language | 3.11+ |
| FastAPI | REST API framework | 0.100+ |
| SQLite | Embedded database | Built-in |
| SQLAlchemy | ORM and schema management | 2.0+ |
| spaCy | NLP — Bloom's Taxonomy verb extraction | 3.x (`en_core_web_sm`) |
| Pydantic | Data validation and serialization | 2.0+ |
| pytest | Test framework | 7.x+ |

### Frontend

| Technology | Purpose |
|---|---|
| React | UI framework |
| Vite | Build tool and dev server |
| Tailwind CSS | Utility-first styling |
| Axios | HTTP client for API calls |

---

## Repository Structure

```
ai-badge-classification-tool/
├── README.md
├── CLAUDE.md                          # Project context for Claude Code
├── LICENSE.txt
├── .env.example
│
├── backend/
│   ├── database.py                    # SQLite setup, session, auto-migration
│   ├── requirements.txt
│   └── app/
│       ├── main.py                    # FastAPI entry point, CORS, router registration
│       ├── routes/
│       │   ├── ingestion.py           # POST /ingest
│       │   ├── classification.py      # POST /classify
│       │   ├── review.py              # POST /review
│       │   ├── logs.py                # GET /logs, GET /logs/{id}
│       │   └── reviewer.py            # POST /reviewer/auth, GET /reviewer/queue
│       ├── models/
│       │   ├── badge_fact_sheet.py    # Core Pydantic BFS model (60+ fields)
│       │   ├── classification_result.py
│       │   └── governance_log.py      # SQLAlchemy ORM model
│       └── services/
│           ├── ingestion/             # parser.py, form_mapper.py
│           ├── normalization/         # normalizer.py, issuer_resolver.py
│           ├── nlp/                   # 4-layer NLP pipeline
│           ├── classification/        # stage1–3.py, engine.py
│           ├── explainability/        # explainer.py
│           └── logging/               # governance_logger.py
│
├── backend/tests/                     # 308 automated tests across 16 files
│   ├── test_accuracy_matrix.py        # 20 real badges — 100% accuracy
│   ├── test_e2e_scenarios.py          # 7 end-to-end scenarios
│   ├── test_nlp_extraction_rate.py
│   ├── test_real_badges.py
│   ├── test_synthetic_badges.py
│   ├── test_classification.py
│   ├── test_edge_cases.py             # EC01–EC30 coverage
│   ├── test_explainability.py
│   ├── test_logging.py
│   ├── test_api_integration.py
│   └── test_verification_checklist.py # T01–T08 regression scenarios
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── SubmitBadge.jsx            # Three-tab submission UI
│       │   ├── ReviewResult.jsx
│       │   ├── GovernanceLogs.jsx
│       │   ├── SubmissionConfirmation.jsx
│       │   └── reviewer/
│       │       ├── ReviewerLogin.jsx
│       │       ├── ReviewerDashboard.jsx
│       │       └── ReviewerReview.jsx
│       ├── components/
│       │   ├── BadgeForm.jsx
│       │   ├── ClassificationResult.jsx
│       │   ├── ExplanationPanel.jsx
│       │   ├── SignalPanel.jsx
│       │   ├── OverrideForm.jsx
│       │   ├── JsonPaste.jsx
│       │   ├── FreeTextInput.jsx
│       │   └── ProtectedRoute.jsx
│       ├── context/ReviewerContext.jsx
│       ├── services/api.js
│       └── utils/formTranslator.js
│
├── sample_data/
│   ├── real_badges/                   # 20 real NJIT badge JSON payloads (B001–B026)
│   └── test_manifest.json
│
├── scripts/
│   ├── load_sample_data.py
│   ├── reset_database.py
│   └── validate_taxonomy.py
│
└── docs/
    ├── architecture.md
    ├── taxonomy-rules.md
    ├── badge-fact-sheet-schema.md
    ├── decision-tables.md
    ├── nlp-phrase-dictionary.md
    ├── governance-logging.md
    ├── testing-plan.md
    └── demo-script.md
```

---

## Setup & Installation

### Prerequisites

- Python 3.11+
- Node.js 18+
- Git

### Step 1 — Clone the Repository

```bash
git clone https://github.com/Rajat-Projects/ai-badge-classification-tool
cd ai-badge-classification-tool/ai-badge-classification-tool
```

### Step 2 — Backend Setup

```bash
# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Download the spaCy language model
python -m spacy download en_core_web_sm
```

### Step 3 — Environment Variables

```bash
cp .env.example .env
```

Open `.env` and configure the following:

```env
REVIEWER_PASSWORD=xxxx-xxxxxxxx-xxxx
USE_LLM=false
DATABASE_URL=sqlite:///./badges.db
ALLOWED_ORIGINS=http://localhost:5173
APP_VERSION=1.0.0
```

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./badges.db` | SQLAlchemy connection string |
| `USE_LLM` | `false` | Enable LLM gap-filling (requires Anthropic API key) |
| `ANTHROPIC_API_KEY` | *(empty)* | Required only when `USE_LLM=true` |
| `REVIEWER_PASSWORD` | `xxxx-xxxxxxxx-xxxx` | Reviewer dashboard access code |
| `ALLOWED_ORIGINS` | `http://localhost:5173` | CORS allowed origins |
| `APP_VERSION` | `1.0.0` | Reported by the `/health` endpoint |

### Step 4 — Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Running the System

### Start the Backend

```bash
cd backend
source ../venv/bin/activate
uvicorn app.main:app --reload
```

- API base URL: `http://localhost:8000`
- Interactive Swagger docs: `http://localhost:8000/docs`

> The SQLite database and all tables are created automatically on first startup.

### Start the Frontend

```bash
cd frontend
npm run dev
```

Application: `http://localhost:5173`

### Verify System Health

```bash
curl http://localhost:8000/health
# {"status": "ok", "version": "1.0.0", "nlp": {"spacy_available": true}}
```

### Load Demo Data *(Optional)*

Pre-populate the database with all 20 real NJIT badge fixtures:

```bash
# Run from the project root with the backend server running
python scripts/load_sample_data.py
```

---

## How to Use

### Submitting a Badge — User A (Submitter)

Navigate to `http://localhost:5173` and choose one of three input methods:

**1. Proposal Form**
A six-step guided form written in plain language — no taxonomy knowledge required. A translation layer (`formTranslator.js`) automatically converts answers into structured Badge Fact Sheet fields.

**2. OBv3 JSON Paste**
Paste any valid Open Badges v3 JSON object. The issuer is auto-detected from the `criteria.id` URL domain. Follow-up questions surface automatically for any signals that couldn't be resolved.

**3. Free Text**
Describe the badge in everyday language. The NLP pipeline extracts signals across all four layers. Targeted follow-up questions handle any remaining missing fields. Designed for students evaluating badge equivalents from outside NJIT.

After submitting, the Badge Fact Sheet is displayed with all extracted signals highlighted. Any missing critical fields trigger follow-up questions. Clicking **Submit for Review** takes you to a confirmation page, and the badge immediately appears in the reviewer's pending queue.

---

### Reviewing a Classification — User B (Reviewer)

1. Click **Reviewer Login** in the navigation bar
2. Enter the reviewer access code (`REVIEWER_PASSWORD` from `.env`)
3. View the **Pending Review** queue on the dashboard
4. Click **View →** to open any pending badge
5. Review the complete classification output:
   - All extracted signals, labeled by NLP source layer
   - Three-stage classification result with confidence level
   - Full plain-English explanation with rule IDs cited
6. Choose an action:
   - **Accept** — confirms the system's recommendation
   - **Override** — changes any stage with a mandatory reason (≥ 20 characters)

---

### Viewing Governance Logs

All classifications are permanently stored and accessible at `/logs`. Click any record to expand the full detail view, including the system recommendation vs. the final human decision, override reason, complete explanation text, and all signals with their source layer.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/ingest` | Convert any input format to a Badge Fact Sheet |
| `POST` | `/classify` | Run the rule engine; creates a governance log entry |
| `POST` | `/review` | Accept or override a classification |
| `GET` | `/logs` | Paginated list of all governance log entries |
| `GET` | `/logs/{id}` | Full detail for a single governance log entry |
| `GET` | `/health` | System status and spaCy availability |
| `POST` | `/reviewer/auth` | Authenticate a reviewer and receive an access token |
| `GET` | `/reviewer/queue` | Pending queue, recent reviews, and stats |
| `GET` | `/reviewer/review/{token}` | Load a badge for review via email link token |

### POST `/ingest` — Form Input Example

```json
{
  "input_type": "form",
  "payload": {
    "badge_title": "AI Literacy and Fundamentals",
    "badge_description": "Recognizes NJIT faculty who completed the AI Literacy course.",
    "issuer": "LDI",
    "audience_type": "njit_employee",
    "earning_criteria_text": "Complete all modules and pass the final assessment.",
    "assessment_required": "yes",
    "assessment_type": "final_assessment",
    "assessment_evaluator": "auto_assessed",
    "expert_evaluation_required": false
  }
}
```

`input_type` accepts: `form` · `obv3_json` · `free_text`

Response: a complete `BadgeFactSheet` object (60+ fields).

### POST `/ingest` — OBv3 JSON Example

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "input_type": "obv3_json",
    "payload": {
      "@context": "https://purl.imsglobal.org/spec/ob/v3p0/context-3.0.3.json",
      "name": "Introduction to AI in Education",
      "criteria": {
        "id": "https://njitcl.catalog.instructure.com/courses/ai-microcredentials",
        "narrative": "Complete all modules within the self-paced course."
      },
      "description": "Recognizes completion of Introduction to AI in Education.",
      "achievementType": "Achievement"
    }
  }'
```

### POST `/classify` — Response Shape

```json
{
  "badge_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "badge_title": "AI Literacy and Fundamentals",
  "issuer": "LDI",
  "classification": {
    "category": "Faculty & Staff Development",
    "type": "Achievement",
    "level": "Foundational",
    "confidence": "High",
    "level_branch_used": "achievement"
  },
  "rules_triggered": ["S1R01", "S2R09", "S3A05"],
  "signals_used": {
    "issuer":          { "value": "LDI",             "source": "structured_field" },
    "audience_type":   { "value": "njit_employee",   "source": "structured_field" },
    "assessment_type": { "value": "final_assessment","source": "structured_field" },
    "bloom_level":     { "value": "understanding",   "source": "spacy_verb" }
  },
  "explanation": "CATEGORY: Classified as 'Faculty & Staff Development'...",
  "follow_up_needed": false,
  "missing_signals": [],
  "governance": {
    "log_id": "7e0b1234-...",
    "classified_at": "2026-04-28T10:00:00Z",
    "reviewer_status": "pending"
  }
}
```

### POST `/review` — Override Example

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{
    "log_id": "7e0b1234-...",
    "reviewer_id": "k.eberhardt",
    "reviewer_status": "overridden",
    "override_reason": "Badge includes a reflection component requiring expert evaluation.",
    "override_category": "Faculty & Staff Development",
    "override_type": "Skill",
    "override_level": "Application"
  }'
```

**Validation rules enforced:**
- `override_reason` must be ≥ 20 characters (EC29)
- `override_type` + `override_level` must form a valid taxonomy pair (EC30)
- If all override values match the recommendation, status silently resolves to `accepted` (EC26)

---

## Classification Taxonomy

### Stage 1 — Category

Determined by issuer identity and the intended audience type.

| Category | Issuer | Audience |
|---|---|---|
| Faculty & Staff Development | LDI | NJIT employees / faculty |
| Continuing & Professional Education | LDI | External professionals |
| Co-Curricular and Extra-Curricular | OSIL | NJIT students |
| Academic | Makerspace, NCE | NJIT students |

### Stage 2 — Type

Determined by earning criteria and assessment method. Rules run in strict priority order — first match wins.

| Type | Key Signal | Assessment |
|---|---|---|
| **Souvenir** | Attendance only — no assessment required | None |
| **Achievement** | Auto-assessed or platform-tracked completion | Auto-assessed |
| **Skill** | Expert-scored demonstration of a specific skill | Expert-scored |
| **Competency** | Expert evaluation of KSAs in a real-world context | Expert-scored |

### Stage 3 — Level

Level names are type-specific and cannot be used across types.

| Type | Valid Levels (low → high) |
|---|---|
| Souvenir | Souvenir |
| Achievement | Foundational → Milestone → Terminal |
| Skill | Awareness → Application → Mastery |
| Competency | Demonstrated → Integrated → Exemplary |

**Level determination per type:**

| Type | Primary Signal | Secondary Signal | Fallback |
|---|---|---|---|
| Achievement | Canvas sequence number | Prerequisite badges / self-declared phrase | NLP Bloom level |
| Skill | Bloom's Taxonomy level from text | Expert-scored flag | Unknown |
| Competency | Leadership evidence | Multi-context evidence | Real-world context |

### Issuer Resolution Rules

When a badge is submitted as OBv3 JSON, the issuer is resolved from the `criteria.id` URL:

| Criteria URL Domain / Pattern | Resolved Issuer |
|---|---|
| `ldi.njit.edu` | LDI |
| `njitcl.catalog.instructure.com` | LDI |
| `njit.edu/development` | LDI |
| `njitmakerspace.com` | Makerspace |
| `engineering.njit.edu` | NCE |
| `njit.edu/global` | OGI |

For form and free-text inputs, the issuer is provided directly or resolved via keyword matching in the badge description.

---

## Testing

### Running the Full Test Suite

```bash
cd backend
source ../venv/bin/activate
pytest tests/ -v
```

**Results: 308 tests · 308 passed · 0 failed · ~3.2 seconds**

### Coverage by Test File

| Test File | Scope | Tests |
|---|---|---|
| `test_accuracy_matrix.py` | 20 real NJIT badges — all 5 classification dimensions | ~4 |
| `test_e2e_scenarios.py` | 7 end-to-end scenarios across all 3 input types | ~8 |
| `test_nlp_extraction_rate.py` | NLP signal extraction rate measurement | ~6 |
| `test_real_badges.py` | Real badge fixtures classified correctly | ~20 |
| `test_synthetic_badges.py` | Happy-path taxonomy combinations + edge cases | ~26 |
| `test_classification.py` | Rule engine unit tests per stage | ~43 |
| `test_explainability.py` | Explanation content and completeness | ~30 |
| `test_logging.py` | Governance log creation, update, retrieval | ~8 |
| `test_api_integration.py` | Full round-trip API endpoint tests | ~32 |
| `test_edge_cases.py` | EC01–EC30 edge case coverage | ~20 |
| `test_verification_checklist.py` | T01–T08 regression scenarios | ~8 |
| `test_ingestion.py` | Parser, form mapper, free-text normalizer | ~20 |
| `test_api.py` | Route availability and response shape | ~20 |

### Classification Accuracy Matrix — 20 Real NJIT Badges

| Dimension | Score |
|---|---|
| Stage 1 — Category | 20 / 20 (100%) |
| Stage 2 — Type | 20 / 20 (100%) |
| Stage 3 — Level | 20 / 20 (100%) |
| Confidence Level | 20 / 20 (100%) |
| Rules Triggered | 20 / 20 (100%) |
| **Overall (all 5 passing)** | **20 / 20 (100%)** |

**Accuracy by Issuer**

| Issuer | Badges Tested | Result |
|---|---|---|
| LDI | 7 | 7 / 7 — 100% |
| OSIL | 6 | 6 / 6 — 100% |
| Makerspace | 4 | 4 / 4 — 100% |
| NCE | 1 | 1 / 1 — 100% |
| OGI | 1 | 1 / 1 — 100% |

### NLP Signal Extraction Rates

Measured across 20 structured form badges and 5 free-text inputs:

| Signal | Structured Input | Free Text |
|---|---|---|
| Issuer | 100% | 100% |
| Audience Type | 100% | 80% |
| Assessment Type | 100% | 60% |
| Assessment Evaluator | 85% | 20% |
| Badge Purpose | 100% | 100% |
| Bloom Level | N/A | 100% |
| Level Signal | 35% (Canvas) | 40% (NLP phrase) |

### End-to-End Scenario Results

| Scenario | Input Type | Expected Confidence | Result |
|---|---|---|---|
| FT01 — LDI Professional | Free Text | High | ✅ PASS |
| FT02 — OSIL Capstone | Free Text | High | ✅ PASS |
| FT03 — Vague Input | Free Text | Low | ✅ PASS |
| FM01 — Form High Confidence | Form | High | ✅ PASS |
| FM02 — Unknown Issuer | Form | Low | ✅ PASS |
| OBV3-01 — JSON High Confidence | OBv3 JSON | High | ✅ PASS |
| OBV3-02 — No Criteria URL | OBv3 JSON | Low | ✅ PASS |

---

## Known Limitations

| Limitation | Status | Impact |
|---|---|---|
| OGI badge category not confirmed | Open — awaiting supervisor input | B026 Stage 1 returns `null`; confidence forced to Low |
| Makerspace Skill vs. Achievement boundary | Open — pending taxonomy clarification | B013–B015 type may need revision after decision |
| LLM extractor is a stub | `USE_LLM=false` by default | Free-text classification relies on rule-based NLP + follow-up Q&A |
| Free-text submissions always require follow-up | By design | Handled gracefully by the plain-language Q&A interface |
| OBv2 badges rejected | 422 response with a clear error message | All current NJIT badges are OBv3 format |
| Canvas course codes not extracted from free text | Students don't know internal course codes | Level classification falls back to NLP phrase matching |

---

## Non-Negotiable System Rules

These rules governed every design decision and every line of code in this system:

- **Taxonomy rules are locked** — No new policy logic was invented; every rule derives from NJIT's official taxonomy documentation
- **Classification is always deterministic** — The rule engine only; no ML model ever makes a classification decision
- **NLP extracts signals, never decides** — The NLP pipeline populates Badge Fact Sheet fields; the rule engine reads them
- **Every output is explainable** — Rules triggered, signals used, and plain-English reasoning are always returned
- **Every decision is auditable** — A governance log entry is created for every single classification
- **Human override is always supported** — A reviewer can change any stage of any classification at any time
- **Classify from Badge Fact Sheet only** — The rule engine never reads raw input directly
- **No scope creep** — No badge issuance, no wallet, no admin rule management UI

---

## License

Copyright © 2026 Tanay Yadav

Developed as a capstone project at **New Jersey Institute of Technology — Spring 2026**.

Permission is hereby granted to NJIT and its authorized representatives to use, modify, and distribute this software for institutional badge classification purposes. This software may not be used for commercial purposes without explicit written permission from the author.
