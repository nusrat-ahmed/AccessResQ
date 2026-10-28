# AccessResQ Community Intelligence

AccessResQ is an early-stage web application prototype for community-reported hazards, aid delivery updates, and transparent tracking of unmet needs.

## Current Features

- Interactive map using Leaflet and OpenStreetMap tiles
- Community hazard and needs reports
- SQLite database persistence
- Report status and verification labels
- Token-protected reviewer controls when configured
- Dashboard metrics for reports, pending verification, and estimated unmet quantities
- FastAPI backend with API documentation
- Automated tests

## Technology Stack

- Python and FastAPI
- SQLite
- HTML, CSS, and JavaScript
- Leaflet and OpenStreetMap
- Pytest

## Run Locally on Windows

Create and activate a virtual environment:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the application:

```powershell
uvicorn main:app --reload
```

Open the application at http://127.0.0.1:8000.

API documentation is available at http://127.0.0.1:8000/docs.

## Run Tests

```powershell
python -m pytest -q
```

## Deployment

The repository includes a `render.yaml` configuration for deployment to Render. Review the deployment settings and configure any required environment variables before deploying.

## Limitations and Responsible Use

- Seeded map records are illustrative demo data, not verified real-world alerts or needs.
- The prototype does not connect to an official emergency alert feed.
- Reviewer controls use a shared token and are not production-grade authentication or role-based access control.
- Public report creation does not currently include CAPTCHA or rate limiting.
- SQLite data may reset on hosting platforms with ephemeral storage.
- OpenStreetMap tiles require an internet connection.
- Do not enter sensitive personal information or rely on this prototype for emergency decisions or life-critical routing.

A real-world pilot would require security improvements, privacy review, community participation, partner validation, and appropriate data storage.

## Project Status

This repository demonstrates the current MVP implementation. It does not claim that a real-world pilot, community validation, or formal partnership has already taken place.