from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import hashlib, hmac, os, secrets, sqlite3, uuid, mimetypes

from fastapi import FastAPI, HTTPException, Header, Request, UploadFile, File, Form, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
STATIC_DIR = BASE_DIR / "static"
DB_PATH = Path(os.getenv("ACCESSRESQ_DB_PATH", str(BASE_DIR / "accessresq.db")))
UPLOAD_DIR = Path(os.getenv("ACCESSRESQ_UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SECRET_KEY = os.getenv("ACCESSRESQ_SECRET_KEY", "")
ADMIN_TOKEN = os.getenv("ACCESSRESQ_ADMIN_TOKEN", "")
SESSION_COOKIE = "accessresq_session"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=20)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_hex, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 310_000).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def serializer():
    key = SECRET_KEY or "development-only-change-this-secret-key"
    return URLSafeTimedSerializer(key, salt="accessresq-session-v1")


def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            phone TEXT NOT NULL DEFAULT '',
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            urgency TEXT NOT NULL DEFAULT 'high',
            status TEXT NOT NULL DEFAULT 'needed',
            verification TEXT NOT NULL DEFAULT 'pending',
            description TEXT NOT NULL,
            area TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            people_affected INTEGER NOT NULL DEFAULT 1,
            children_count INTEGER NOT NULL DEFAULT 0,
            mobility_support INTEGER NOT NULL DEFAULT 0,
            needs TEXT NOT NULL DEFAULT '',
            contact TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            public_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL,
            mime_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shelters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            lat REAL NOT NULL,
            lng REAL NOT NULL,
            contact TEXT NOT NULL DEFAULT '',
            verification TEXT NOT NULL DEFAULT 'pending',
            source TEXT NOT NULL DEFAULT 'Community submission',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_reports_created ON reports(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_reports_verification ON reports(verification);
        CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id);
        """)
        # Safe, clearly labelled Bangladesh demo reports to make the demo immediately explorable.
        count = con.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        if count == 0:
            stamp = now_iso()
            demo = [
                ("DEMO-AR-1001", "Drinking water needed", "water", "critical", "needed", "sample", "Illustrative demo report only. Verify locally before responding.", "Demo area, Sunamganj", 25.0658, 91.3950, 24, 3, 0, "Drinking water, dry food", "", stamp, stamp),
                ("DEMO-AR-1002", "Family needs evacuation support", "evacuation", "critical", "in_progress", "sample", "Illustrative demo report only. This is not a live rescue request.", "Demo area, Sylhet", 24.8949, 91.8687, 7, 2, 1, "Boat support, drinking water", "", stamp, stamp),
                ("DEMO-AR-1003", "Road access concern", "hazard", "high", "needed", "sample", "Illustrative demo report only. Not an official warning.", "Demo area, Feni", 23.0159, 91.3976, 0, 0, 0, "Road access check", "", stamp, stamp),
            ]
            con.executemany("""INSERT INTO reports(public_id,title,category,urgency,status,verification,description,area,lat,lng,people_affected,children_count,mobility_support,needs,contact,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", demo)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="AccessResQ", description="Community flood reporting, help requests and private document vault.", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    phone: str = Field(default="", max_length=30)
    password: str = Field(min_length=10, max_length=128)

    @field_validator("email")
    @classmethod
    def email_valid(cls, v):
        v = v.strip().lower()
        if "@" not in v or "." not in v.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return v


class LoginIn(BaseModel):
    email: str
    password: str


class ReportIn(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    category: str = Field(pattern="^(water|food|shelter|medical|evacuation|hazard|accessibility|other)$")
    urgency: str = Field(default="high", pattern="^(critical|high|moderate|low)$")
    description: str = Field(min_length=10, max_length=1200)
    area: str = Field(min_length=2, max_length=160)
    lat: float = Field(ge=20.5, le=26.8)
    lng: float = Field(ge=88.0, le=92.8)
    people_affected: int = Field(default=1, ge=0, le=10000)
    children_count: int = Field(default=0, ge=0, le=10000)
    mobility_support: int = Field(default=0, ge=0, le=10000)
    needs: str = Field(default="", max_length=500)
    contact: str = Field(default="", max_length=80)


class StatusIn(BaseModel):
    status: str = Field(pattern="^(needed|in_progress|delivered|closed)$")
    verification: str = Field(pattern="^(pending|verified|rejected)$")


class ShelterIn(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    address: str = Field(min_length=3, max_length=240)
    lat: float = Field(ge=20.5, le=26.8)
    lng: float = Field(ge=88.0, le=92.8)
    contact: str = Field(default="", max_length=80)
    source: str = Field(default="Community submission", max_length=160)


def current_user(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    try:
        data = serializer().loads(token, max_age=60 * 60 * 24 * 14)
        with connect() as con:
            row = con.execute("SELECT id,name,email,phone,created_at FROM users WHERE id=?", (data.get("uid"),)).fetchone()
        return dict(row) if row else None
    except (BadSignature, SignatureExpired, TypeError, ValueError):
        return None


def require_user(request: Request):
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    return user


def public_report(row):
    d = dict(row)
    d.pop("contact", None)
    d.pop("user_id", None)
    return d


@app.get("/")
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "AccessResQ", "version": "1.0.0", "database": "sqlite", "demo_data_is_illustrative": True}


@app.get("/api/me")
def me(request: Request):
    user = current_user(request)
    return {"authenticated": bool(user), "user": user}


@app.post("/api/auth/register", status_code=201)
def register(item: RegisterIn, request: Request):
    if not SECRET_KEY and os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise HTTPException(status_code=503, detail="Configure ACCESSRESQ_SECRET_KEY before enabling account registration in production.")
    now = now_iso()
    with connect() as con:
        try:
            cur = con.execute("INSERT INTO users(name,email,phone,password_hash,created_at) VALUES(?,?,?,?,?)",
                              (item.name.strip(), item.email, item.phone.strip(), hash_password(item.password), now))
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="An account with this email already exists.")
        uid = cur.lastrowid
    response = JSONResponse({"ok": True, "user": {"id": uid, "name": item.name.strip(), "email": item.email}}, status_code=201)
    response.set_cookie(SESSION_COOKIE, serializer().dumps({"uid": uid}), httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=60 * 60 * 24 * 14, path="/")
    return response


@app.post("/api/auth/login")
def login(item: LoginIn, request: Request):
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (item.email.strip(),)).fetchone()
    if not row or not verify_password(item.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    response = JSONResponse({"ok": True, "user": {"id": row["id"], "name": row["name"], "email": row["email"]}})
    response.set_cookie(SESSION_COOKIE, serializer().dumps({"uid": row["id"]}), httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=60 * 60 * 24 * 14, path="/")
    return response


@app.post("/api/auth/logout")
def logout():
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/api/reports")
def list_reports(category: Optional[str] = None, status: Optional[str] = None, limit: int = 100):
    limit = max(1, min(limit, 250))
    sql = "SELECT * FROM reports WHERE 1=1"
    params = []
    if category:
        sql += " AND category=?"; params.append(category)
    if status:
        sql += " AND status=?"; params.append(status)
    sql += " ORDER BY created_at DESC, id DESC LIMIT ?"; params.append(limit)
    with connect() as con:
        rows = con.execute(sql, params).fetchall()
    return [public_report(r) for r in rows]


@app.post("/api/reports", status_code=201)
def create_report(item: ReportIn, request: Request):
    user = current_user(request)
    stamp = now_iso()
    public_id = "AR-" + secrets.token_hex(4).upper()
    with connect() as con:
        cur = con.execute("""INSERT INTO reports(public_id,user_id,title,category,urgency,status,verification,description,area,lat,lng,people_affected,children_count,mobility_support,needs,contact,created_at,updated_at)
        VALUES(?,?,?,?,?,'needed','pending',?,?,?,?,?,?,?,?,?,?,?)""",
        (public_id, user["id"] if user else None, item.title.strip(), item.category, item.urgency, item.description.strip(), item.area.strip(), item.lat, item.lng, item.people_affected, item.children_count, item.mobility_support, item.needs.strip(), item.contact.strip(), stamp, stamp))
        row = con.execute("SELECT * FROM reports WHERE id=?", (cur.lastrowid,)).fetchone()
    return public_report(row)


@app.get("/api/reports/mine")
def my_reports(user=Depends(require_user)):
    with connect() as con:
        rows = con.execute("SELECT * FROM reports WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return [public_report(r) for r in rows]


@app.patch("/api/reports/{report_id}/status")
def update_status(report_id: int, item: StatusIn, x_admin_token: str = Header(default="")):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Reviewer updates are disabled until ACCESSRESQ_ADMIN_TOKEN is configured on the server.")
    if not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid reviewer token.")
    with connect() as con:
        row = con.execute("SELECT id FROM reports WHERE id=?", (report_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found.")
        con.execute("UPDATE reports SET status=?,verification=?,updated_at=? WHERE id=?", (item.status, item.verification, now_iso(), report_id))
        updated = con.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    return public_report(updated)


@app.get("/api/shelters")
def list_shelters(verified_only: bool = False):
    sql = "SELECT * FROM shelters" + (" WHERE verification='verified'" if verified_only else "") + " ORDER BY name"
    with connect() as con:
        rows = con.execute(sql).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/shelters", status_code=201)
def add_shelter(item: ShelterIn, x_admin_token: str = Header(default="")):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="Shelter management is disabled until ACCESSRESQ_ADMIN_TOKEN is configured.")
    if not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Invalid reviewer token.")
    with connect() as con:
        cur = con.execute("INSERT INTO shelters(name,address,lat,lng,contact,verification,source,created_at) VALUES(?,?,?,?,?,'pending',?,?)",
                          (item.name.strip(), item.address.strip(), item.lat, item.lng, item.contact.strip(), item.source.strip(), now_iso()))
        row = con.execute("SELECT * FROM shelters WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.patch("/api/shelters/{shelter_id}/verify")
def verify_shelter(shelter_id: int, verification: str = Form(...), x_admin_token: str = Header(default="")):
    if not ADMIN_TOKEN or not hmac.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Reviewer authorization required.")
    if verification not in {"verified", "rejected", "pending"}:
        raise HTTPException(status_code=422, detail="Invalid verification state.")
    with connect() as con:
        cur = con.execute("UPDATE shelters SET verification=? WHERE id=?", (verification, shelter_id))
        if not cur.rowcount:
            raise HTTPException(status_code=404, detail="Shelter not found.")
        row = con.execute("SELECT * FROM shelters WHERE id=?", (shelter_id,)).fetchone()
    return dict(row)


@app.get("/api/metrics")
def metrics():
    with connect() as con:
        reports = con.execute("SELECT * FROM reports").fetchall()
        verified_shelters = con.execute("SELECT COUNT(*) FROM shelters WHERE verification='verified'").fetchone()[0]
    rows = [dict(r) for r in reports]
    return {
        "total_reports": len(rows),
        "active_reports": sum(1 for r in rows if r["status"] not in {"closed", "delivered"}),
        "pending_verification": sum(1 for r in rows if r["verification"] == "pending"),
        "verified_reports": sum(1 for r in rows if r["verification"] == "verified"),
        "critical_reports": sum(1 for r in rows if r["urgency"] == "critical" and r["status"] not in {"closed", "delivered"}),
        "verified_shelters": verified_shelters,
        "demo_warning": "Includes illustrative demo reports. This is not an official emergency dispatch or live flood prediction service."
    }


@app.get("/api/documents")
def list_documents(user=Depends(require_user)):
    with connect() as con:
        rows = con.execute("SELECT public_id,original_name,mime_type,size_bytes,created_at FROM documents WHERE user_id=? ORDER BY created_at DESC", (user["id"],)).fetchall()
    return [dict(r) for r in rows]


@app.post("/api/documents", status_code=201)
async def upload_document(file: UploadFile = File(...), user=Depends(require_user)):
    name = Path(file.filename or "document").name
    if not name or len(name) > 180:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    mime = file.content_type or mimetypes.guess_type(name)[0] or "application/octet-stream"
    if mime not in ALLOWED_MIME:
        raise HTTPException(status_code=415, detail="Only PDF, JPG, PNG and WEBP files are allowed.")
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Maximum file size is 10 MB.")
    # Check basic file signatures rather than trusting the browser-provided MIME type alone.
    signatures = {"application/pdf": content.startswith(b"%PDF-"), "image/jpeg": content.startswith(b"\xff\xd8\xff"),
                  "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"), "image/webp": len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"}
    if not signatures.get(mime, False):
        raise HTTPException(status_code=415, detail="File content does not match an allowed document type.")
    public_id = "DOC-" + secrets.token_hex(6).upper()
    stored = f"{uuid.uuid4().hex}{Path(name).suffix.lower()}"
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    (UPLOAD_DIR / stored).write_bytes(content)
    try:
        with connect() as con:
            con.execute("INSERT INTO documents(public_id,user_id,original_name,stored_name,mime_type,size_bytes,created_at) VALUES(?,?,?,?,?,?,?)",
                        (public_id, user["id"], name, stored, mime, len(content), now_iso()))
    except Exception:
        (UPLOAD_DIR / stored).unlink(missing_ok=True)
        raise
    return {"public_id": public_id, "original_name": name, "mime_type": mime, "size_bytes": len(content), "created_at": now_iso()}


@app.get("/api/documents/{public_id}/download")
def download_document(public_id: str, user=Depends(require_user)):
    with connect() as con:
        row = con.execute("SELECT * FROM documents WHERE public_id=? AND user_id=?", (public_id, user["id"])).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found.")
    path = UPLOAD_DIR / row["stored_name"]
    if not path.is_file():
        raise HTTPException(status_code=410, detail="Document file is missing from server storage.")
    return FileResponse(path, media_type=row["mime_type"], filename=row["original_name"], content_disposition_type="attachment", headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"})


@app.delete("/api/documents/{public_id}")
def delete_document(public_id: str, user=Depends(require_user)):
    with connect() as con:
        row = con.execute("SELECT * FROM documents WHERE public_id=? AND user_id=?", (public_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Document not found.")
        con.execute("DELETE FROM documents WHERE id=?", (row["id"],))
    (UPLOAD_DIR / row["stored_name"]).unlink(missing_ok=True)
    return {"ok": True}


@app.get("/api/safety-guide")
def safety_guide():
    return {"items": [
        {"title": "Move to higher ground when advised", "body": "Follow official local warnings. Avoid waiting until water surrounds your home.", "kind": "before"},
        {"title": "Never walk or drive through floodwater", "body": "Depth and current can be deceptive; hidden drains and damaged roads may be present.", "kind": "during"},
        {"title": "Keep drinking water safe", "body": "Use sealed or officially treated water. Follow local public-health guidance for disinfection.", "kind": "during"},
        {"title": "Protect essential documents", "body": "Keep copies in a sealed waterproof pouch and a private digital vault. Do not upload sensitive files to public reports.", "kind": "before"},
        {"title": "Help vulnerable neighbours safely", "body": "Check on children, older adults and people with mobility needs only when it is safe to do so.", "kind": "during"},
        {"title": "Use official emergency channels", "body": "This prototype does not dispatch rescue teams. Contact local emergency services and authorities for urgent danger.", "kind": "always"}
    ]}


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(STATIC_DIR / "index.html")
