MedicoTourism Backend (FastAPI + PyMongo)

Setup

1. Create a virtualenv (recommended) and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure environment variables:

- Copy `.env.example` to `.env` and update values as needed.

```bash
cp .env.example .env
```

3. Run the server:

```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.

Endpoints

- POST `/api/auth/signup` — create user account
- POST `/api/auth/login` — get JWT token

Notes

- Requires MongoDB running (local or Atlas). Update `MONGODB_URI` accordingly.
- CORS is enabled for Vite dev origin `http://localhost:5173` by default. Adjust in `.env`.
