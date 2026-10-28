# AccessResQ — Community Intelligence

**Local Knowledge. Coordinated Response. Stronger Communities.**

AccessResQ is an early-stage humanitarian climate-resilience web application prototype designed to organise community-reported hazards, unmet needs, and aid-response updates in one shared interface.

## 🌐 Live Demo

**Try AccessResQ:** https://accessresq.onrender.com

Explore the live prototype to see the interactive map, community reports, report statuses, and dashboard metrics.

> **Responsible use:** Some map records are illustrative demo data, not verified real-world alerts. AccessResQ is not an official emergency alert service and must not be used for life-critical decisions.

## 🎯 The Problem

During floods and other climate-related hazards, local observations, community needs, and response updates may be scattered across different communication channels. This can make it harder to build a shared picture of reported needs.

AccessResQ explores how a community-centred digital platform could make local information easier to report, locate, review, and share.

## 💡 The Solution

AccessResQ provides a web interface for community-reported hazards and needs, location-based viewing, report status tracking, and dashboard summaries.

The goal is to support clearer information sharing and future coordination between communities and relevant response partners. The current project is an MVP prototype, not a deployed emergency-response network.

## ✨ Current Features

- **Interactive map:** View report locations using Leaflet and OpenStreetMap tiles.
- **Community reports:** Submit reports about hazards and unmet needs.
- **Report tracking:** Display report status and verification labels.
- **Dashboard metrics:** Summarise reports, pending verification, and estimated unmet quantities.
- **Reviewer controls:** Token-protected controls when configured.
- **Data persistence:** Store application records in SQLite.
- **API documentation:** Explore backend endpoints through FastAPI documentation.
- **Automated tests:** Run the project's test suite with Pytest.

## 🖥️ Technology Stack

| Component | Technology |
|---|---|
| Backend | Python, FastAPI |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript |
| Interactive map | Leaflet, OpenStreetMap |
| API documentation | FastAPI / OpenAPI |
| Testing | Pytest |
| Deployment | Render |

## 🔄 How It Works

1. **Report:** A user submits information about a local hazard or unmet need.
2. **Locate:** The report can be viewed in a location-based interface.
3. **Review:** Report statuses and verification labels help communicate its current state.
4. **Track:** Dashboard metrics summarise reported information.

These capabilities support an early-stage reporting workflow. They do not guarantee that reports are accurate, verified, or acted upon.

## 🚀 Run Locally on Windows

### 1. Clone the repository

```powershell
git clone https://github.com/nusrat-ahmed/AccessResQ.git
cd AccessResQ
```

### 2. Create and activate a virtual environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

### 4. Start the application

```powershell
uvicorn main:app --reload
```

Open the application at:

http://127.0.0.1:8000

### 5. Open API documentation

http://127.0.0.1:8000/docs

## 🧪 Run Tests

With the virtual environment activated, run:

```powershell
python -m pytest -q
```

## ☁️ Deployment

The live prototype is hosted on Render:

**https://accessresq.onrender.com**

The repository also includes a `render.yaml` configuration. Deployment settings and required environment variables should be reviewed before redeployment.

**Note:** The current deployment may use ephemeral storage. SQLite records may not persist across service restarts or redeployments unless persistent storage is configured.

## 🌍 Climate Resilience and Humanitarian Potential

AccessResQ explores a community-centred approach to organising local hazard reports and unmet needs during climate-related events, including floods.

Potential future directions include:

- Co-designing reporting workflows with affected communities.
- Testing accessibility and usability with intended users.
- Establishing report review and validation procedures with appropriate local partners.
- Improving privacy, security, and data-retention practices.
- Evaluating whether the platform helps users understand reported needs and follow-up status.

These are proposed next steps, not claims of completed pilots, formal partnerships, or measured impact.

## 🔐 Limitations and Responsible Use

- Seeded map records are illustrative demo data, not verified real-world alerts or needs.
- The prototype does not connect to an official emergency alert feed.
- Reports are not guaranteed to be accurate, verified, or acted upon.
- Reviewer controls use a shared token and are not production-grade authentication or role-based access control.
- Public report creation does not currently include CAPTCHA or rate limiting.
- SQLite data may reset on hosting platforms with ephemeral storage.
- OpenStreetMap tiles require an internet connection.
- Do not enter sensitive personal information.
- Do not use this prototype for emergency decisions, life-critical routing, or as a substitute for official emergency guidance.

A real-world pilot would require security improvements, privacy review, community participation, partner validation, and appropriate data storage.

## 🗺️ Project Status

AccessResQ demonstrates an early-stage minimum viable product (MVP). It is intended for demonstration, feedback, and further development.

No real-world pilot, community validation, formal partnership, or measurable humanitarian impact is claimed at this stage.

## 🔗 Project Links

- **Live website:** https://accessresq.onrender.com
- **GitHub repository:** https://github.com/nusrat-ahmed/AccessResQ
- **API documentation:** https://accessresq.onrender.com/docs

---

*AccessResQ — Local Knowledge. Coordinated Response. Stronger Communities.*
