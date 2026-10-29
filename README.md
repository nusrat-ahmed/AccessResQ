# AccessResQ — Community Flood Response Prototype

**Better information. Safer communities.** AccessResQ is a Bangladesh-focused web prototype for community flood-related reporting, location-aware help requests, locally verified safe-place listings, preparedness guidance, and a private account-based document vault.

> **Safety and demo notice:** AccessResQ is not an emergency dispatch service, official flood forecast, or rescue coordination system. It does not automatically alert responders. Seed reports are illustrative demo records and must never be treated as live incidents. The safe-place directory intentionally starts empty: a place is not shown as verified until an authorised reviewer verifies it.

## Features

- Modern responsive dashboard and separate pages for overview, flood intelligence map, request help, safe places, safety guide, documents and account.
- Interactive Bangladesh map using Leaflet and OpenStreetMap tiles.
- Community reports with location, category, urgency, affected people, children, mobility support, requested needs, verification state and status tracking.
- Public report listing omits the submitter's private contact field.
- Account registration and sign-in with PBKDF2-SHA256 password hashing and signed, HTTP-only session cookies.
- Private document upload/download/delete for PDF, JPEG, PNG and WEBP files, maximum 10 MB, with account ownership checks and basic file-signature checks.
- Reviewer-token-protected report status updates and shelter creation/verification API.
- SQLite storage, health/metrics endpoints, API tests and deployment template.

## Quick start (Windows)

1. Install Python 3.11 or newer.
2. Extract this ZIP into a normal folder (not inside a protected Windows system directory).
3. Double-click `run_windows.bat` or run it from a terminal. It creates a virtual environment, installs requirements and starts the server.
4. Open `http://127.0.0.1:8000` in your browser.

For a repeat start, activate the environment and run `python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000`.

## Configuration

Copy `.env.example` to `.env` and set strong unique values before deployment. The app loads a local `.env` file if present; hosting secrets should be configured in the provider dashboard. For local evaluation, the app uses a development-only signing secret if `ACCESSRESQ_SECRET_KEY` is absent. **Never use that fallback in production.**

Important environment variables:

- `ACCESSRESQ_SECRET_KEY`: long, random secret used to sign sessions.
- `ACCESSRESQ_ADMIN_TOKEN`: separate long, random reviewer token required by reviewer-only APIs.
- `ACCESSRESQ_DB_PATH`: optional path for SQLite database.
- `ACCESSRESQ_UPLOAD_DIR`: optional path for uploaded private files.
- `ENVIRONMENT=production`: prevents account registration when no session secret is configured.

Reviewer API calls use the `X-Admin-Token` header. There is no public reviewer dashboard in this prototype; do not expose the reviewer token in frontend code.

## API overview

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/api/health` | Health check | Public |
| GET | `/api/metrics` | Aggregate report counts | Public |
| GET | `/api/reports` | Filterable report list | Public; contact hidden |
| POST | `/api/reports` | Submit a community report | Public or signed-in |
| GET | `/api/reports/mine` | Current user's submitted reports | Signed-in |
| PATCH | `/api/reports/{id}/status` | Change report status and verification | Reviewer token |
| GET | `/api/shelters?verified_only=true` | Verified safe places only | Public |
| POST | `/api/shelters` | Add a pending shelter record | Reviewer token |
| PATCH | `/api/shelters/{id}/verify` | Verify/reject a shelter | Reviewer token |
| POST | `/api/auth/register` | Create account | Public |
| POST | `/api/auth/login` | Sign in | Public |
| POST | `/api/auth/logout` | Sign out | Public |
| GET | `/api/me` | Current session | Public |
| GET/POST | `/api/documents` | List/upload private documents | Signed-in |
| GET/DELETE | `/api/documents/{public_id}/download` / `/api/documents/{public_id}` | Download/delete own document | Signed-in |
| GET | `/api/safety-guide` | Preparedness guidance | Public |

Interactive OpenAPI docs are available at `/docs` when the server is running.

## Run tests

```bash
python -m pip install -r requirements.txt
python -m pytest -q
```

## Deployment and persistence

`render.yaml` describes a basic Render web service. Set a strong `ACCESSRESQ_SECRET_KEY` and a separate `ACCESSRESQ_ADMIN_TOKEN` in the hosting dashboard. **The SQLite database and uploaded files must be stored on a persistent disk/volume** if you expect them to survive redeploys and be available across devices. Configure both `ACCESSRESQ_DB_PATH` and `ACCESSRESQ_UPLOAD_DIR` to paths on that persistent volume. Without persistent storage, files and database records can be lost when the host restarts or redeploys.

For real user documents, also configure HTTPS, access monitoring, regular encrypted backups, a privacy/retention policy and incident-response procedures. The prototype stores files on server disk; it does not provide end-to-end encryption or a managed cloud object-storage integration.

## Data sources and limitations

- Map tiles come from OpenStreetMap; an internet connection is needed for tiles.
- Report pins come from user submissions and explicitly marked illustrative demo records.
- There is no live government flood-gauge feed, satellite analysis, predictive flood model, rescue dispatch integration, or guaranteed safe-route engine in this release.
- Verified safe-place listings remain empty until reviewed data is added through the reviewer API.
- Browser geolocation requires permission and usually a secure context (HTTPS or localhost).
- Reviewer actions use a shared server-side token rather than individual reviewer accounts and audit identities.
- SQLite and local disk storage are appropriate for a demonstrator, not a high-availability emergency platform.

## SDG alignment

The project is designed to support discussion of **SDG 11: Sustainable Cities and Communities** and **SDG 13: Climate Action** through community information sharing and preparedness. This is a design contribution, not evidence that the prototype has reduced disaster impact. Pilot outcomes would need to be measured with local partners.

## Suggested live demo flow

1. Open Overview and explain that the sample reports are illustrative.
2. Open Flood intelligence, filter reports and open a marker's detail modal.
3. Submit a new report with a Bangladesh location; show its generated report ID and status.
4. Open Safe places and explain that no shelter is marked verified without review.
5. Show Safety guide.
6. Create a demo account, upload a non-sensitive sample PDF/image, refresh the page, then download and delete it.
7. Finish with the limitations and a plan for official data integration and a supervised community pilot.

Use a throwaway demo account and non-sensitive test document during judging.
