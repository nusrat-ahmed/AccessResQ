# AccessResQ Community Intelligence (MVP)

A prototype for community-reported hazards, aid delivery updates, and transparent tracking of unmet needs.

## What works
- Interactive map (Leaflet + OpenStreetMap tiles)
- Create community reports
- SQLite persistence
- Status and verification labels with token-protected reviewer controls (when configured)
- Dashboard metrics for reports, pending verification, and estimated unmet quantities
- Basic API validation and tests
- Fixed asynchronous form-reset handling in the report submission flow
- FastAPI API documentation at `/docs`

## Documentation pack

- `docs/TECHNICAL_DOCUMENTATION.md` — architecture, API, data model, tests and deployment notes
- `docs/SECURITY_AND_PRIVACY.md` — current security gaps and requirements before any real pilot
- `docs/QBE_SUBMISSION_CHECKLIST.md` — official pilot fit, evidence checklist and truthful positioning
- `docs/EVIDENCE_SCREENSHOT_GUIDE.md` — exact screenshot checklist and capture steps for competition evidence
- `docs/PILOT_PLAN_TEMPLATE.md` — template for co-design, metrics, risks and budget assumptions
- `docs/PITCH_DECK_OUTLINE.md` — pitch structure and a 90-second demo script

These documents are planning aids, not proof that planned features are implemented or that a partnership exists.

## Important limitations
- Seeded map records are **illustrative demo data**, not real alerts or verified needs.
- The prototype does not connect to an official emergency alert feed.
- Status updates require the server-side `ACCESSRESQ_ADMIN_TOKEN`; without it, review updates are disabled. This simple shared-token control is not production-grade identity or role-based access.
- Do not use this prototype for life-critical routing or emergency decisions.
- Do not enter sensitive personal information. Production deployment needs authentication, role-based permissions, abuse prevention, secure audit logs, privacy review, backups, and partner validation.
- A map marker does not mean a whole locality is fully served. Unmet needs are tracked separately.
- OpenStreetMap tiles require internet and are not an offline map solution.

## Run on Windows (PowerShell)
```powershell
cd path\to\accessresq_mvp
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload
```
Open `http://127.0.0.1:8000` and API docs at `http://127.0.0.1:8000/docs`.

If PowerShell blocks activation, use:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Test
In a second terminal with the venv active:
```powershell
python -m pytest -q
```

## Deploy to Render
1. Push this folder to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect the repository.
3. Review the service from `render.yaml` and deploy.
4. In Render Environment, set a strong `ACCESSRESQ_ADMIN_TOKEN` if reviewer controls are needed; do not put the token in source code or screenshots.
5. Open the deployed `/api/health` endpoint and homepage.
6. Note: this starter uses a local SQLite database. On free ephemeral hosting, data may reset on redeploy/restart. For a serious pilot, use managed persistent storage or a hosted PostgreSQL database and secure the admin endpoints.

## Suggested QBE application evidence
- Live demo URL and GitHub repository
- Short demo video (60–120 seconds)
- Screenshots of map, report creation, verification status, and unmet-needs dashboard
- A realistic pilot plan with a local partner, user feedback plan, and measurable outcomes
- Clearly separate prototype capabilities from planned features


## Public demo safety notice
This is a competition demonstration, not a production service. Public report creation is currently open and has no CAPTCHA or rate limiting; deploy only as a clearly labelled demo and monitor it. Do not collect sensitive or identifying information. The SQLite database may reset on free ephemeral hosting. Do not use real emergency reports or rely on this system for emergency response.

## Repository files to include
Push the source code, docs, tests, submission assets, `render.yaml`, and `.github/workflows/tests.yml`. Do not push `.venv/`, `.env`, `accessresq.db`, passwords, admin tokens, or personal data.
