# Thesis Project

A medical web application featuring a **Flask** API backend, a **PostgreSQL** database connection, machine learning model experiments, and a **Streamlit** multi-page dashboard.

---

##  Project Structure & File Guide

###  Project Configuration
* **`pyproject.toml`** — Contains project metadata and dependency configurations.
* **`uv.lock`** — Lockfile that records exact package versions for reproducible environments.
* **`README.md`** — Overview documentation for this repository.

---

###  `ml_experiments/`
* **`tensorflow_notebook/`** — Jupyter notebooks and scripts for training, testing, and prototyping TensorFlow machine learning models.

---

###  `backend/`
* **`rest.py`** — The entry point that initializes and runs the Flask REST API server.
* **`dbconnect.py`** — Database utility file handling connections to the PostgreSQL database.
* **`routes/`** — Modular API route handlers:
  * **Auth:** User login and session verification.
  * **Predictions:** Inferences served from the ML model to the frontend.
  * **Admin:** Administrative database operations and user management.

---

### `frontend/`
* **`login.py`** — Main entry point for the Streamlit dashboard handling initial authentication.
* **`assets/`** — Static visual resources, including UI styling (CSS) and images.
* **`pages/`** — Role-specific multi-page dashboards:
  * **`01_admin.py`** — Admin control panel for managing users and system data.
  * **`02_doctor.py`** — Clinician workspace to view patient details and generate model predictions.
  * **`03_patient.py`** — Portal for patients to access personal health records and results.
