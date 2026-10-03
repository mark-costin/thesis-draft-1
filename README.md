# Project Structure & File Guide

---

## Project Configuration & Environment

* **`pyproject.toml`** — Project metadata, Python version specifications, and package dependency declarations managed via `uv`.
* **`uv.lock`** — Lockfile capturing exact sub-dependency versions to ensure deterministic, reproducible environments.
* **`.env`** *(Git-ignored)* — Secure local storage for sensitive database credentials (`DATABASE_URL`), Flask environment flags, and secret keys.
* **`.gitignore`** — Rules preventing secret files (`.env`), virtual environments (`.venv/`), and byte-code caches (`__pycache__/`) from committing to Git.
* **`README.md`** — Overview documentation and setup instructions for this repository.

---

## database/

* **`database/schema.sql`** — Base DDL script establishing PostgreSQL tables (`Users`, `PatientsProfile`, `DoctorsProfile`, `AdminsProfile`, `HealthAssessments`).
* **`database/seed.sql`** — Initial test dataset containing seeded credentials, patient records, and doctor profiles.

---

## backend/

### Core Application
* **`backend/dbconnect.py`** — Core SQLAlchemy configuration and database connection pooling.
* **`backend/rest.py`** — Application entry point instance, blueprint registration, and CORS middleware configuration.
* **`backend/cdss_engine.py`** — CDSS logic managing XGBoost inference, TreeSHAP explainability, and algorithmic fairness auditing.

### Validation & Testing
* **`backend/test_clinical_pipeline.py`** — End-to-end verification pipeline for 4 disease domains, cascades, and FHRS.
* **`backend/test_orm.py`** — Integration and data-cascading tests for all relational database entities.
* **`backend/test_vector_search.py`** — Tests for `pgvector` cosine similarity (`<=>`) and semantic embedding lookups.

### backend/middleware/
* **`backend/middleware/idempotency.py`** — Replay-attack prevention and distributed request caching.
* **`backend/middleware/rbac.py`** — Role-Based Access Control and JWT claim authorization checks.
* **`backend/middleware/sanitizer.py`** — Role-aware payload field stripping and request validation.
* **`backend/middleware/security.py`** — Baseline browser security headers and defense-in-depth configurations.

### backend/model_orm/
* **`backend/model_orm/__init__.py`** — Unified package exports for database models.
* **`backend/model_orm/usr_orm.py`** — Master user identity schemas, token verification, and secure password hashing.
* **`backend/model_orm/pat_orm.py`** — Patient clinical profiles, 4-modality cascading relationships, and HIPAA-compliant audit records.
* **`backend/model_orm/doc_orm.py`** — Attending clinician profiles and credentials validation.
* **`backend/model_orm/adm_orm.py`** — Administrative staff identity models.
* **`backend/model_orm/clinic_orm.py`** — Clinical telemetry data, 4 chronic disease domains, FHRS, and cache tables.
* **`backend/model_orm/clinical_vector.py`** — `pgvector` embeddings for semantic clinical history retrieval.

### backend/routes/
* **`backend/routes/auth0.py`** — JWT issuance, self-registration endpoints, and account lockout controls.
* **`backend/routes/doctor.py`** — Triage queue queries, patient record retrieval, and clinical directives.
* **`backend/routes/admin.py`** — Clinician provisioning endpoints and identity directory inspection.
* **`backend/routes/predictions.py`** — CDSS diagnostic inference and model prediction endpoints.
* **`backend/routes/health.py`** — Database connection ping and API gateway readiness probes.

---

## frontend/

* **`frontend/main.py`** — Entry point for the Streamlit web application managing global session state, top-level navigation, and RBAC workspace routing.
* **`frontend/assets/`** — Static visual assets including custom CSS stylesheets, UI icons, and medical branding images.

### frontend/views/
* **`frontend/views/login_view.py`** — Unauthenticated landing view hosting login forms and patient self-registration workflows.
* **`frontend/views/patientpage.py`** — Patient Portal containing intake surveys (symptoms, BMI, family health history) and interactive ML risk charts.
* **`frontend/views/doctorpage.py`** — Clinician Workspace featuring patient search lookups, downloadable CDSS diagnostic reports, and clinical diagnosis forms.
* **`frontend/views/adminpage.py`** — System Admin Portal displaying real-time user KPI metrics and doctor provisioning tools.

---

## tensorflow notebook/

* **`tensorflow notebook/notebook.ipynb`** — Machine learning prototyping notebook for model training, feature engineering, hyperparameter tuning, and model serialization/export.
* **`tensorflow notebook/about`** — Documentation covering dataset sources, target feature descriptions, and model evaluation metrics.
