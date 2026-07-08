"""
JanAwaaz — minimal backend (proof-of-concept)

Run with:  uvicorn main:app --reload --port 8000
Then open: http://127.0.0.1:8000/docs   (auto-generated test UI, no frontend needed)

This is intentionally simple: SQLite (one file, no setup) + FastAPI + a rule-based
classifier (same logic as the browser demo, ported to Python). It's real and it
runs — good enough to demo the backend concept and answer "is there a backend?"
without needing cloud infrastructure in a 2-day window.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import re
from datetime import datetime

app = FastAPI(title="JanAwaaz API")

# Allow the frontend (running from file:// or any localhost port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "janawaaz.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            category TEXT,
            language TEXT,
            urgency INTEGER,
            lat REAL,
            lng REAL,
            ward TEXT,
            upvotes INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT,
            FOREIGN KEY (submission_id) REFERENCES submissions (id)
        )
    """)
    conn.commit()
    conn.close()


init_db()

# ---------- classifier (same rules as the browser JS version) ----------
CATEGORY_KEYWORDS = {
    "Roads": ["road", "pothole", "street", "footpath", "pavement", "traffic", "bridge", "சாலை", "सड़क"],
    "Water": ["water", "tap", "pipeline", "drain", "flood", "waterlog", "tank", "जल", "पानी", "தண்ணீர்"],
    "Electricity": ["power", "light", "electric", "transformer", "streetlight", "cable", "बिजली", "மின்"],
    "Health": ["hospital", "clinic", "doctor", "medicine", "health", "sick", "ambulance", "अस्पताल", "மருத்துவமனை"],
    "Education": ["school", "teacher", "student", "classroom", "education", "शिक्षा", "பள்ளி"],
}
URGENCY_WORDS = [
    "urgent", "emergency", "danger", "accident", "died", "death", "collapsed",
    "flooded", "since weeks", "immediately", "children", "elderly",
    "no water since", "not working since", "हादसा", "जरूरी", "அவசரம்",
]


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "Hindi"
    if re.search(r"[\u0B80-\u0BFF]", text):
        return "Tamil"
    return "English" if text.strip() else "—"


def classify(text: str):
    lower = text.lower()
    best_cat, best_score = "Other", 0
    for cat, words in CATEGORY_KEYWORDS.items():
        hits = sum(1 for w in words if w.lower() in lower)
        if hits > best_score:
            best_score, best_cat = hits, cat

    urgency = 10
    for w in URGENCY_WORDS:
        if w.lower() in lower:
            urgency += 18
    if "!" in text:
        urgency += 8
    if len(text) > 120:
        urgency += 10
    urgency = min(100, urgency)

    return {
        "category": best_cat if text.strip() else "—",
        "language": detect_language(text),
        "urgency": urgency if text.strip() else 0,
    }


# ---------- request/response models ----------
class SubmissionIn(BaseModel):
    text: str
    lat: float | None = None
    lng: float | None = None
    ward: str | None = None


class CommentIn(BaseModel):
    text: str


# ---------- endpoints ----------
@app.get("/")
def root():
    return {"status": "JanAwaaz API running", "docs": "/docs"}


@app.post("/classify")
def classify_endpoint(payload: SubmissionIn):
    """Classify text without saving it — used for the live-preview feature."""
    return classify(payload.text)


@app.post("/submissions")
def create_submission(payload: SubmissionIn):
    """Submit a citizen complaint. Classifies it and stores it."""
    result = classify(payload.text)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO submissions (text, category, language, urgency, lat, lng, ward, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (payload.text, result["category"], result["language"], result["urgency"],
         payload.lat, payload.lng, payload.ward, datetime.utcnow().isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, **result}


@app.get("/submissions")
def list_submissions():
    conn = get_db()
    rows = conn.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/submissions/{submission_id}/upvote")
def upvote_submission(submission_id: int):
    """A citizen clicks 'I have this issue too' — increments the counter."""
    conn = get_db()
    conn.execute("UPDATE submissions SET upvotes = upvotes + 1 WHERE id = ?", (submission_id,))
    conn.commit()
    row = conn.execute("SELECT upvotes FROM submissions WHERE id = ?", (submission_id,)).fetchone()
    conn.close()
    if row is None:
        return {"error": "submission not found"}
    return {"id": submission_id, "upvotes": row["upvotes"]}


@app.get("/submissions/{submission_id}/comments")
def list_comments(submission_id: int):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM comments WHERE submission_id = ? ORDER BY id ASC", (submission_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.post("/submissions/{submission_id}/comments")
def add_comment(submission_id: int, payload: CommentIn):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO comments (submission_id, text, created_at) VALUES (?, ?, ?)",
        (submission_id, payload.text, datetime.utcnow().isoformat()),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return {"id": new_id, "submission_id": submission_id, "text": payload.text}


@app.get("/hotspots")
def get_hotspots():
    """
    Very simple clustering: group submissions by rounded lat/lng (~1km grid)
    and count how many fall in each cell. Good enough to demo the concept;
    swap for DBSCAN/PostGIS when scaling.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT lat, lng, category, urgency FROM submissions WHERE lat IS NOT NULL"
    ).fetchall()
    conn.close()

    clusters = {}
    for r in rows:
        key = (round(r["lat"], 2), round(r["lng"], 2))
        clusters.setdefault(key, {"lat": key[0], "lng": key[1], "count": 0, "avg_urgency": 0, "categories": []})
        c = clusters[key]
        c["count"] += 1
        c["avg_urgency"] += r["urgency"]
        c["categories"].append(r["category"])

    result = []
    for c in clusters.values():
        c["avg_urgency"] = round(c["avg_urgency"] / c["count"])
        c["level"] = "high" if c["avg_urgency"] > 65 else "medium" if c["avg_urgency"] > 35 else "emerging"
        result.append(c)
    return result


@app.get("/ledger")
def get_ledger(w_demand: float = 0.3, w_urgency: float = 0.3, w_impact: float = 0.2, w_feasibility: float = 0.2):
    """
    Priority ranking. Demo version derives 'demand' from submission volume per
    category, 'urgency' from average urgency score, and uses placeholder
    impact/feasibility (replace with real infra/budget data later).
    Weights are adjustable via query params — this is what your slider UI can call.
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT category, COUNT(*) as n, AVG(urgency) as avg_urg FROM submissions GROUP BY category"
    ).fetchall()
    conn.close()

    if not rows:
        return []

    max_n = max(r["n"] for r in rows) or 1
    ranked = []
    for r in rows:
        demand = (r["n"] / max_n) * 100
        urgency = r["avg_urg"] or 0
        impact = min(100, demand * 0.8 + 10)       # placeholder heuristic
        feasibility = 70                            # placeholder until real budget data plugged in
        score = (w_demand * demand + w_urgency * urgency + w_impact * impact + w_feasibility * feasibility) / 10
        ranked.append({
            "category": r["category"], "demand": round(demand), "urgency": round(urgency),
            "impact": round(impact), "feasibility": feasibility, "score": round(score, 1),
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
