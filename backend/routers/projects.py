from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.auth import require_admin

router = APIRouter(tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

@router.get("/projects")
def list_projects():
    db = get_db()
    rows = db.execute("SELECT * FROM projects ORDER BY id").fetchall()
    db.close()
    return [dict(r) for r in rows]

@router.post("/projects", status_code=201)
def create_project(body: ProjectCreate, _=Depends(require_admin)):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (body.name, body.description)
        )
        db.commit()
        row = db.execute("SELECT * FROM projects WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row)
    except Exception as e:
        if "UNIQUE" in str(e):
            raise HTTPException(status_code=409, detail="项目名已存在")
        raise
    finally:
        db.close()

@router.patch("/projects/{pid}")
def update_project(pid: int, body: ProjectUpdate, _=Depends(require_admin)):
    db = get_db()
    row = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="项目不存在")
    name = body.name if body.name is not None else row["name"]
    desc = body.description if body.description is not None else row["description"]
    db.execute(
        "UPDATE projects SET name=?, description=?, updated_at=datetime('now') WHERE id=?",
        (name, desc, pid)
    )
    db.commit()
    row = db.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    db.close()
    return dict(row)

@router.delete("/projects/{pid}")
def delete_project(pid: int, _=Depends(require_admin)):
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM requirements WHERE project_id=?", (pid,)).fetchone()[0]
    if count > 0:
        db.close()
        raise HTTPException(status_code=409, detail="项目下存在需求，无法删除")
    db.execute("DELETE FROM projects WHERE id=?", (pid,))
    db.commit()
    db.close()
    return {"ok": True}
