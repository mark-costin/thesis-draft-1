thesis-draft-1/
├── pyproject.toml
├── uv.lock
├── README.md
│
├── ml_experiments/             # Machine Learning & Notebooks
│   └── tensorflow_notebook/
│
├── backend/                    # Flask API & Data Layer
│   ├── app.py                  # Flask Entry Point
│   ├── dbconnect.py            # PostgreSQL Connection
│   └── routes/                 # API Endpoints (Auth, Predictions, Admin)
│
└── frontend/                   # Streamlit UI Layer
    ├── login.py                # Main Entry Point (st.run)
    ├── assets/                 # Images & CSS
    └── pages/                  # Streamlit Multi-Page Routes
        ├── 01_admin.py
        ├── 02_doctor.py
        └── 03_patient.py
