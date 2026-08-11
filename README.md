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

## `backend/`

### Gateway Core & Scripts

* **`rest.py`** — Primary entry point for the Flask REST API Gateway. Applies global CORS policies, attaches security headers, and mounts API blueprints.
* **`dbconnect.py`** — Centralized infrastructure file loading `.env` variables and configuring SQLAlchemy connection pooling (`pool_size`, `max_overflow`, `pool_recycle`).
* **`test_orm.py`** — Automated validation script verifying bidirectional ORM navigation and `ON DELETE CASCADE` relationships.

### `backend/middleware/`

* **`idempotency.py`** — Intercepts state-changing HTTP operations (`POST`, `PUT`, `PATCH`, `DELETE`) with an `Idempotency-Key` cache to prevent replay attacks and duplicate submissions.
* **`rbac.py`** — Role-Based Access Control middleware enforcing cryptographic token/session checks prior to route execution.
* **`sanitizer.py`** — Recursively strips sensitive fields (`password_hash`, `secret_key`) from JSON payloads prior to returning responses to the frontend.
* **`security.py`** — Injects defense headers (`X-Content-Type-Options`, `X-Frame-Options`, `Content-Security-Policy`) into outgoing responses to prevent XSS and Clickjacking.

### `backend/model_orm/`

* **`usr_orm.py`** — Declarative SQLAlchemy model mapping for base `Users` (authentication credentials, roles).
* **`pat_orm.py`** — Declarative ORM model mapping for `PatientsProfile` (demographics, foreign key to `Users`).
* **`doc_orm.py`** — Declarative ORM model mapping for `DoctorsProfile` (medical licenses, specializations).
* **`adm_orm.py`** — Declarative ORM model mapping for `AdminsProfile` (system management metadata).

### `backend/routes/`

* **`health.py`** — Diagnostic endpoints (`GET /api/health`, `GET /api/health/db`, `POST /api/health/test-idempotency`) to monitor API gateway readiness and database connectivity.
* **`auth0.py`** — Authentication blueprints handling user logins, password hashing verification, and token generation.
* **`predictions.py`** — Inference endpoints serving ML predictive risk assessments to authorized callers.
* **`admin.py`** — Administrative endpoints for system user metrics, doctor account provisioning, and audit logs.

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
