# Thesis Project

A medical web application featuring a **Flask** API backend, a **PostgreSQL** database connection, machine learning model experiments, and a **Streamlit** role-isolated dashboard.

---

## Project Structure & File Guide

### Project Configuration

* `pyproject.toml` — Contains project metadata and dependency configurations.
* `uv.lock` — Lockfile that records exact package versions for reproducible environments.
* `README.md` — Overview documentation for this repository.

---

### ml_experiments/

* `tensorflow_notebook/` — Jupyter notebooks and scripts for training, testing, and prototyping TensorFlow machine learning models.

---

### backend/

* `rest.py` — The entry point that initializes and runs the Flask REST API server.
* `dbconnect.py` — Database utility file handling connections to the PostgreSQL database.
* `routes/` — Modular API route handlers:
  * **Auth:** User login, registration, and session token verification.
  * **Predictions:** Inferences served from the ML model to the frontend.
  * **Admin:** Administrative database operations and user management.

---

### frontend/

* `login.py` — Main entry point for the Streamlit application handling global session state, authentication checks, and dynamic RBAC routing.
* `assets/` — Static visual resources, including UI styling (CSS) and images.
* `views/` — Role-isolated UI views (rendered dynamically based on authenticated user role to prevent unauthorized sidebar access):
  * `login_view.py` — Authentication view housing login and patient registration forms.
  * `adminpage.py` — Admin control panel for managing users, doctor provisioning, and system data.
  * `doctorpage.py` — Clinician workspace to view patient details, evaluate predictive insights, and submit verified clinical records.
  * `patientpage.py` — Portal for patients to enter family health history and access personal screening results.
