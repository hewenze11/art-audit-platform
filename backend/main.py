import os
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from backend.database import init_db
from backend.auth import require_worker
from backend.routers import projects, requirements, submissions, audit, assets

DATA_DIR = os.getenv("DATA_DIR", "/data")

app = FastAPI(title="美术审计平台", version="1.0.0")

@app.on_event("startup")
def on_startup():
    init_db()
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)

@app.get("/health")
def health():
    return {"status": "ok"}

# Tasks 接口（按项目分组，含 remaining）
from backend.database import get_db

@app.get("/api/tasks")
def get_tasks(_=Depends(require_worker)):
    db = get_db()
    projects_rows = db.execute("SELECT * FROM projects ORDER BY id").fetchall()
    result = []
    for p in projects_rows:
        reqs = db.execute(
            "SELECT * FROM requirements WHERE project_id=? AND status='open' ORDER BY id",
            (p["id"],)
        ).fetchall()
        if not reqs:
            continue
        result.append({
            "project_id": p["id"],
            "project_name": p["name"],
            "requirements": [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "category": r["category"],
                    "quantity_total": r["quantity_total"],
                    "quantity_done": r["quantity_done"],
                    "remaining": max(0, r["quantity_total"] - r["quantity_done"]),
                    "ai_prompt": r["ai_prompt"],
                    "description": r["description"],
                }
                for r in reqs
            ]
        })
    db.close()
    return result

app.include_router(projects.router, prefix="/api")
app.include_router(requirements.router, prefix="/api")
app.include_router(submissions.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(assets.router, prefix="/api")

# 静态文件（最后挂载）
uploads_dir = os.path.join(DATA_DIR, "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
