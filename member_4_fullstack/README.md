# Member 4 -- Full-Stack Lead

## Your Responsibility
Integrate everything into a running application. You wire Member 2's predictions
and Member 3's Digital Twin into a FastAPI backend, then display results on a
React dashboard.

## Your Workspace
```
member_4_fullstack/
├── api/
│   ├── main.py        -- FastAPI app: /forecast, /simulate, /alerts endpoints
│   └── schemas.py     -- Pydantic request/response models
├── dashboard/         -- Symlink or copy of frontend/src/ for local iteration
└── README.md
```

The canonical frontend lives at:    frontend/src/BloodIQDashboard.jsx
The canonical backend entry lives at: backend/main.py

## Quick Start
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

## API Endpoints You Own
| Method | Path          | Description                                       |
|--------|---------------|---------------------------------------------------|
| GET    | /health       | Liveness probe                                    |
| POST   | /simulate     | Run one Digital Twin simulation day               |
| GET    | /forecast     | Return 30-day demand forecast                     |
| GET    | /alerts       | Return all active risk alerts                     |
| GET    | /inventory    | Return current stock levels per product           |

## What You Hand Off
- A working local demo at http://localhost:5173
- Publication-ready screenshots for the paper (Section VI: System Demo)
- API documentation at http://localhost:8000/docs

## Key Decisions You Own
- Dashboard chart library (Recharts already configured)
- Alert colour coding (HIGH=red, MEDIUM=amber, LOW=green)
- API rate limiting and error handling

## Paper Section You Write
**Section VI: System Architecture and Dashboard**
**Figure 3**: Dashboard screenshot
**Figure 4**: API response structure diagram
