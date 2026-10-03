# Project Structure & File Guide

---

## Project Configuration & Environment

* **`pyproject.toml`** — Project metadata, python version specifications, and package dependency declarations managed via `uv`.
* **`uv.lock`** — Lockfile capturing exact sub-dependency versions to ensure deterministic, reproducible environments.
* **`.env`** *(Git-ignored)* — Secure local storage for sensitive database credentials (`DATABASE_URL`), Flask environment flags, and secret keys.
* **`.gitignore`** — Rules preventing secret files (`.env`), virtual environments (`.venv/`), and byte-code caches (`__pycache__/`) from committing to Git.
* **`README.md`** — Overview documentation and setup instructions for this repository.

---

## `database/`

* **`schema.sql`** — Base DDL script establishing PostgreSQL tables (`Users`, `PatientsProfile`, `DoctorsProfile`, `AdminsProfile`, `HealthAssessments`).
* **`seed.sql`** — Initial test dataset containing seeded credentials, patient records, and doctor profiles.

---
backend/
├── dbconnect.py                 # Core SQLAlchemy configuration and database pooling
├── rest.py                      # Application instance, blueprint registration & CORS
├── cdss_engine.py               # XGBoost inference, TreeSHAP explainability & fairness auditing
├── test_clinical_pipeline.py    # Verification pipeline for 4 disease domains, cascades & FHRS
├── test_orm.py                  # Integration and cascading tests for relational entities
├── test_vector_search.py        # pgvector cosine similarity (<=>) and embedding search tests
├── middleware/
│   ├── idempotency.py          # Replay-attack prevention & distributed request caching
│   ├── rbac.py                  # Role-Based Access Control and claim authorization
│   ├── sanitizer.py             # Role-aware payload field stripping
│   └── security.py              # Baseline browser security headers & defense-in-depth
├── model_orm/
│   ├── __init__.py              # Unified package exports for database models
│   ├── usr_orm.py               # Master user identity, tokens, and password hashing
│   ├── pat_orm.py               # Patient clinical profiles, 4-modality cascading relationships & HIPAA records
│   ├── doc_orm.py               # Attending clinician profiles and credentials
│   ├── adm_orm.py               # Administrative staff identity models
│   ├── clinic_orm.py            # Clinical telemetry, 4 chronic disease domains, FHRS & cache tables
│   └── clinical_vector.py       # pgvector embeddings for semantic clinical history retrieval
└── routes/
    ├── auth0.py                 # JWT issuance, self-registration, and lockout controls
    ├── doctor.py                # Triage queue queries, patient records, and directives
    ├── admin.py                 # Clinician provisioning and identity directory inspection
    ├── predictions.py           # CDSS diagnostic inference endpoints
    └── health.py                # Database ping and gateway readiness probes


---

## `frontend/`

* **`main.py`** — Entry point for the Streamlit web application managing global session state, top-level navigation, and RBAC workspace routing.
* **`assets/`** — Static visual assets including custom CSS styling stylesheets, icons, and medical branding images.

### `frontend/views/`

* **`login_view.py`** — Unauthenticated landing view hosting login forms and patient self-registration forms.
* **`patientpage.py`** — Patient Portal containing intake surveys (symptoms, BMI, family health history) and interactive ML predictive risk evaluation charts.
* **`doctorpage.py`** — Clinician Workspace featuring patient search lookups, downloadable CDSS diagnostic reports, and verified clinical diagnosis forms.
* **`adminpage.py`** — System Admin Portal displaying real-time user KPI metrics and doctor provisioning tools.

---

## `tensorflow notebook/` (ML Pipeline)

* **`notebook.ipynb`** — Machine learning prototyping notebook for model training, feature engineering, hyperparameter tuning, and model export.
* **`about`** — Documentation covering dataset sources, feature descriptions, and model evaluation metrics.
