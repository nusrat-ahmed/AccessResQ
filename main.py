from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import os
import hmac

from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "accessresq.db"
STATIC_DIR = BASE_DIR / "static"
ADMIN_TOKEN = os.getenv("ACCESSRESQ_ADMIN_TOKEN", "")

SAMPLE_REPORTS = [
    {
        "title": "Community requests drinking water",
        "category": "water",
        "status": "needed",
        "verification": "sample",
        "description": "DEMO DATA: Example request for bottled drinking water. Confirm with local responders before acting.",
        "area": "Demo Community A",
        "lat": 4.7110, "lng": -74.0721,
        "quantity_needed": 120, "quantity_delivered": 0,
        "people_affected": 60, "source": "Demonstration dataset"
    },
    {
        "title": "First-aid supplies delivery reported",
        "category": "medical",
        "status": "delivered",
        "verification": "sample",
        "description": "DEMO DATA: Example delivery report. It does not mean all needs in this area are met.",
        "area": "Demo Community B",
        "lat": 4.6533, "lng": -74.0837,
        "quantity_needed": 40, "quantity_delivered": 25,
        "people_affected": 25, "source": "Demonstration dataset"
    },
    {
        "title": "Road access concern reported",
        "category": "hazard",
        "status": "in_progress",
        "verification": "sample",
        "description": "DEMO DATA: Example hazard report requiring local verification. Do not use as an emergency warning.",
        "area": "Demo Community C",
        "lat": 4.7485, "lng": -74.0450,
        "quantity_needed": 0, "quantity_delivered": 0,
        "people_affected": 0, "source": "Demonstration dataset"
    },
]

def connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            status TEXT NOT NULL,
            verification TEXT NOT NULL DEFAULT 'pending',
            description TEXT NOT NULL,
            area TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            quantity_needed INTEGER NOT NULL DEFAULT 0,
            quantity_delivered INTEGER NOT NULL DEFAULT 0,
            people_affected INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT 'Community report',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
        count = con.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        if count == 0:
            now = datetime.now(timezone.utc).isoformat()
            for r in SAMPLE_REPORTS:
                con.execute("""
                    INSERT INTO reports
                    (title, category, status, verification, description, area, lat, lng,
                     quantity_needed, quantity_delivered, people_affected, source, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r["title"], r["category"], r["status"], r["verification"], r["description"],
                      r["area"], r["lat"], r["lng"], r["quantity_needed"], r["quantity_delivered"],
                      r["people_affected"], r["source"], now, now))

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="AccessResQ Community Intelligence",
    description="Prototype for structured community risk and aid reporting. Demo data is illustrative only.",
    version="0.1.0",
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

class ReportIn(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    category: str = Field(pattern="^(water|food|shelter|medical|accessibility|hazard|other)$")
    description: str = Field(min_length=10, max_length=1000)
    area: str = Field(min_length=2, max_length=120)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    quantity_needed: int = Field(default=0, ge=0, le=1000000)
    quantity_delivered: int = Field(default=0, ge=0, le=1000000)
    people_affected: int = Field(default=0, ge=0, le=1000000)
    source: str = Field(default="Community report", min_length=2, max_length=120)

class StatusIn(BaseModel):
    status: str = Field(pattern="^(needed|in_progress|delivered|closed)$")
    verification: str = Field(pattern="^(pending|verified|rejected)$")

def serialize(row):
    return dict(row)

@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AccessResQ Community Intelligence", "prototype": True}

@app.get("/api/reports")
def list_reports():
    with connect() as con:
        rows = con.execute("SELECT * FROM reports ORDER BY created_at DESC, id DESC").fetchall()
    return [serialize(r) for r in rows]

@app.post("/api/reports", status_code=201)
def create_report(item: ReportIn):
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        cur = con.execute("""
            INSERT INTO reports
            (title, category, status, verification, description, area, lat, lng,
             quantity_needed, quantity_delivered, people_affected, source, created_at, updated_at)
            VALUES (?, ?, 'needed', 'pending', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (item.title.strip(), item.category, item.description.strip(), item.area.strip(),
              item.lat, item.lng, item.quantity_needed, item.quantity_delivered,
              item.people_affected, item.source.strip(), now, now))
        report_id = cur.lastrowid
        row = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    return serialize(row)

@app.patch("/api/reports/{report_id}/status")
def update_status(report_id: int, item: StatusIn, x_admin_token: str = Header(default="")):
    # Status changes are disabled unless a server-side token is configured.
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Admin review is disabled: configure ACCESSRESQ_ADMIN_TOKEN on the server.")
    if not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid admin token.")
    now = datetime.now(timezone.utc).isoformat()
    with connect() as con:
        row = con.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Report not found")
        con.execute("UPDATE reports SET status=?, verification=?, updated_at=? WHERE id=?",
                    (item.status, item.verification, now, report_id))
        updated = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    return serialize(updated)

@app.get("/api/metrics")
def metrics():
    with connect() as con:
        rows = con.execute("SELECT * FROM reports").fetchall()
    reports = [serialize(r) for r in rows]
    active = [r for r in reports if r["status"] != "closed"]
    unmet = sum(max(0, r["quantity_needed"] - r["quantity_delivered"]) for r in active)
    return {
        "total_reports": len(reports),
        "active_reports": len(active),
        "pending_verification": sum(1 for r in reports if r["verification"] == "pending"),
        "verified_reports": sum(1 for r in reports if r["verification"] == "verified"),
        "areas_with_unmet_needs": sum(1 for r in active if r["quantity_needed"] > r["quantity_delivered"]),
        "estimated_unmet_quantity_units": unmet,
        "demo_warning": "Metrics include illustrative sample data and user-submitted reports; they are not verified real-world totals."
    }
