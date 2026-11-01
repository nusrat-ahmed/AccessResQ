# AccessResQ NET v1.1 — Community Flood Response & Offline SOS Prototype

**Better information. Safer communities.**

AccessResQ is a Bangladesh-focused web application prototype for community flood reporting, location-aware assistance requests, safe-place information, preparedness guidance, and private document management. Version 1.1 adds an **offline SOS queue** and a **protected Rescue Desk** for controlled demonstrations.

## Live Project Links

- 🌐 **Live Demo:** [https://accessresq.onrender.com](https://accessresq.onrender.com)
- 📚 **API Documentation:** [https://accessresq.onrender.com/docs](https://accessresq.onrender.com/docs)
- 💻 **GitHub Repository:** [https://github.com/nusrat-ahmed/AccessResQ](https://github.com/nusrat-ahmed/AccessResQ)

> **Safety notice:** This is a research and hackathon prototype, **not** an official flood warning, emergency dispatch, or rescue service. An SOS accepted by the server is **not** automatically delivered to emergency responders. Example reports are clearly marked as demonstration data. In a real emergency, contact the appropriate local emergency services and authorities.

> **Deployment notice:** The public links may still show the previous version until the v1.1 changes are merged into the deployed branch and Render completes a successful deployment.

## What's New in v1.1

| Feature | What it does | Current status |
|---|---|---|
| Offline SOS (`#sos`) | Saves a consent-based SOS request to the browser's IndexedDB queue when the server cannot be reached | Implemented prototype |
| Online reconciliation | Retries pending SOS requests when connectivity returns and shows a server-issued receipt on successful acceptance | Implemented prototype |
| Optional GPS | Includes coordinates only after the browser grants location permission; an area description can be used without GPS | Implemented prototype |
| Protected Rescue Desk (`#rescue`) | Lets a reviewer with an admin token view submitted SOS records and update their review status | Implemented prototype |
| Explainable triage | Displays a rule-based score and reasons from reported conditions; **not a trained AI model** | Implemented prototype |
| PWA app shell | Caches selected static application files for limited offline access | Implemented prototype |
| Relay gateway API | Accepts authenticated JSON SOS messages through a separate server endpoint; a Python bridge can read line-delimited JSON | Software interface only |
| Bluetooth / LoRa mesh | Would relay SOS messages between nearby phones or radio devices without an internet connection | **Not implemented** |

**Important:** An SOS labelled **pending** exists only on the user's device. It has **not** reached the server or a rescuer. After a successful sync, the server confirms receipt, but that still does **not** mean a rescue team was contacted.

## Core Features

- **Community Dashboard:** Overview of reports, action-needed items, pending verification, and verified safe places.
- **Flood Intelligence Map:** Interactive Bangladesh community-report map using Leaflet and OpenStreetMap. Reports can be filtered by category and status; sample records are identified as demos.
- **Request Help:** Submit a community report with an area, coordinates, needs, affected people, and urgency. Public report responses exclude the submitter's contact details.
- **Safe Places:** Display verified listings only; reviewer-controlled APIs can add and verify locations. The verified directory is initially empty.
- **Safety Guide:** Preparedness and flood-safety information, with reminders to follow official sources.
- **User Accounts:** Registration and login using PBKDF2-SHA256 password hashing and signed HTTP-only session cookies.
- **Private Document Vault:** Account-owned PDF, JPEG, PNG, and WEBP uploads, downloads, and deletion, with a 10 MB per-file limit and basic file-signature checks.
- **Rescue Desk:** Token-protected SOS list, optional reported GPS locations, rule-based triage explanations, and manual status changes (`unreviewed`, `reviewing`, `contacted`, `closed`). These are reviewer-entered statuses, not proof of a real dispatch.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI, Uvicorn |
| Frontend | HTML, CSS, JavaScript |
| Maps | Leaflet, OpenStreetMap tiles |
| Database | SQLite |
| Offline storage | Browser IndexedDB and a Service Worker |
| API testing | Pytest and HTTPX |
| Deployment | Render web service |
| Optional receiver bridge | Python CLI (`bridge/relay_gateway.py`); serial support requires `pyserial` |

## Getting Started (Windows)

**Requirements:** Python 3.11+ and Git (if cloning the repository).

1. Clone or download the repository:

   ```powershell
   git clone https://github.com/nusrat-ahmed/AccessResQ.git
   cd AccessResQ
   ```

2. Double-click `run_windows.bat` in File Explorer, or run it in PowerShell:

   ```powershell
   .\run_windows.bat
   ```

   The script creates `.venv` if needed, installs dependencies, copies `.env.example` to `.env` if the latter does not exist, and starts the local server.

3. Before using admin-only features, open `.env` and replace its example secret values with **different, randomly generated secrets**. Keep this file private, then restart the server so it loads the new values.

4. Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

For a manual repeat start after activating your virtual environment:

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## Environment Variables and Security

Create a local `.env` from `.env.example`. **Never commit `.env`, real API tokens, personal documents, or the SQLite database to GitHub.** The included `.gitignore` excludes the usual local secret, database, upload, and virtual-environment paths.

| Variable | Purpose |
|---|---|
| `ACCESSRESQ_SECRET_KEY` | Strong random secret for signing user sessions; required for a secure deployment |
| `ACCESSRESQ_ADMIN_TOKEN` | Separate random credential for reviewer-only APIs and Rescue Desk access |
| `ACCESSRESQ_RELAY_TOKEN` | Optional separate credential for the receiver/relay ingestion endpoint; needed only when testing that integration |
| `ACCESSRESQ_DB_PATH` | Optional SQLite database path; use persistent storage when deployed |
| `ACCESSRESQ_UPLOAD_DIR` | Optional private file storage path; use persistent storage when deployed |
| `ENVIRONMENT=production` | Disables account registration if the session secret is missing |

To generate a secret locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Use a **different generated value for each secret**. Set production environment variables in the Render dashboard, not in source code. Do not use the example placeholders in a public deployment. Reviewer API requests use the `X-Admin-Token` header; relay ingestion uses the `X-Relay-Token` header.

## API Overview

| Method | Endpoint | Purpose | Access |
|---|---|---|---|
| GET | `/api/health` | Service health check | Public |
| GET | `/api/metrics` | Aggregate report metrics | Public |
| GET | `/api/reports` | Filterable community report list | Public; contact omitted |
| POST | `/api/reports` | Create a community report | Public or signed-in |
| GET | `/api/reports/mine` | View the current user's reports | Signed-in |
| PATCH | `/api/reports/{report_id}/status` | Update report status and verification | Reviewer token |
| GET | `/api/shelters` | List safe places; optional `verified_only=true` | Public |
| POST | `/api/shelters` | Add a pending safe-place record | Reviewer token |
| PATCH | `/api/shelters/{shelter_id}/verify` | Review safe-place verification | Reviewer token |
| POST | `/api/auth/register` | Create an account | Public |
| POST | `/api/auth/login` | Sign in | Public |
| POST | `/api/auth/logout` | Sign out | Public |
| GET | `/api/me` | Read current session information | Public |
| GET / POST | `/api/documents` | List or upload private documents | Signed-in |
| GET | `/api/documents/{public_id}/download` | Download an owned document | Signed-in |
| DELETE | `/api/documents/{public_id}` | Delete an owned document | Signed-in |
| GET | `/api/safety-guide` | Read preparedness information | Public |
| POST | `/api/sos` | Submit a consent-based SOS | Public |
| GET | `/api/rescue/sos` | List SOS requests and triage details | Reviewer token |
| PATCH | `/api/rescue/sos/{public_id}` | Update SOS review status | Reviewer token |
| POST | `/api/relay/ingest` | Ingest a gateway-originated SOS | Relay token |

Interactive OpenAPI documentation is available at `/docs` while the server is running.

## Testing the Offline SOS Workflow

Use **fictional, non-sensitive test information only**.

1. Open the site while online so the static files and service worker can load.
2. In your browser's Developer Tools, simulate offline connectivity.
3. Open **Offline SOS** (`#sos`), complete the form, approve consent, and submit.
4. Confirm that the request appears in **My device queue** as **pending**. It has **not** been delivered.
5. Restore connectivity and select **Sync queued SOS now** (or allow the app to retry when the connection returns).
6. Confirm that the server returns an `SOS-...` receipt; the entry should then leave the pending queue.
7. Open **Rescue Desk** (`#rescue`) using your configured reviewer token to inspect the test record and change its review status.

Offline browser storage can be cleared or lost with the device. Some external resources, including map tiles and fonts, still require network access. This is **offline device storage and later server sync**, not phone-to-phone offline communication.

## Optional Relay Bridge (Experimental)

The backend exposes an authenticated `POST /api/relay/ingest` endpoint, and the repository includes `bridge/relay_gateway.py` for sending line-delimited JSON from standard input or a compatible serial receiver to the server.

An example local CLI run is:

```powershell
python bridge/relay_gateway.py --stdin --url http://127.0.0.1:8000
```

Configure a unique `ACCESSRESQ_RELAY_TOKEN` on the server and supply the matching value as an environment variable to the bridge process (for example, in PowerShell: `$env:ACCESSRESQ_RELAY_TOKEN = "YOUR_TEST_RELAY_SECRET"`). The standalone bridge reads this process environment variable; it does not load `.env` automatically. Serial operation additionally requires `pyserial` and a suitable device. **No physical ESP32/LoRa radio firmware, radio transport security, Bluetooth mesh, or end-to-end field-tested rescue network is included.**

## Run Automated Tests

```powershell
python -m pip install -r requirements.txt
python -m pytest -q
```

The project includes tests for core APIs and new SOS/reviewer/relay behaviors. Passing tests does not establish real-world emergency reliability or security certification.

## Deployment on Render

The repository includes `render.yaml` with the following service configuration:

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Health-check path: `/api/health`

For an existing Render service, confirm that it points to the correct GitHub repository and branch (normally `main`), and that the relevant environment secrets are set in Render. After merging a pull request, confirm that Render completes a successful deployment before expecting the new version at the existing live URL.

**Persistence warning:** By default, local SQLite records and uploaded files may be lost when an ephemeral hosting instance restarts or redeploys. Persistent disk storage (or an appropriately designed managed database and private object storage) is needed for reliable retention. This prototype should not be used for real personal emergency records without appropriate privacy, backup, access control, retention, and operational safeguards.

## Known Limitations and Roadmap

**Current limitations**

- No official real-time flood forecast, government flood-gauge feed, or satellite-based flood prediction.
- No automatic emergency notification, ambulance dispatch, or confirmed rescue-team integration.
- No working Bluetooth/Nearby Connections mesh or deployed LoRa rescue-node network.
- The triage score is a transparent heuristic, **not** a trained or clinically validated AI system.
- Pending SOS data is stored locally in the browser and is not end-to-end encrypted.
- Maps require external tiles; offline map navigation is not implemented.
- The Rescue Desk currently relies on a shared reviewer token, not individual staff accounts with audit logs.

**Potential next steps**

1. Build and test a native Android nearby-device relay prototype.
2. Add ESP32/LoRa sender-receiver firmware and measure delivery rate, range, delay, and power consumption.
3. Improve reviewer identity, access logging, and secure handling of personal information.
4. Integrate verified public environmental data with clear source attribution.
5. Conduct supervised usability and reliability testing with appropriate local partners.

## Sustainable Development Goals

The project's intended areas of relevance include:

- **SDG 11 — Sustainable Cities and Communities:** Community resilience, accessible information, and disaster preparedness.
- **SDG 13 — Climate Action:** Awareness and response planning for climate-related hazards.

These are project objectives, **not measured claims of disaster impact**.

---

**AccessResQ NET v1.1 is a working educational prototype, not an operational emergency response platform.**