from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.auth import require_admin

router = APIRouter(tags=["requirements"])

class ReqCreate(BaseModel):
    title: str
    category: str
    quantity_total: int = 1
    description: Optional[str] = None
    ai_prompt: Optional[str] = None

class ReqUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    ai_prompt: Optional[str] = None
    quantity_total: Optional[int] = None
    status: Optional[str] = None

@router.get("/projects/{project_id}/requirements")
def list_requirements(project_id: int):
    db = get_db()
    rows = db.execute(
        "SELECT * FROM requirements WHERE project_id=? ORDER BY id",
        (project_id,)
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]

@router.post("/projects/{project_id}/requirements", status_code=201)
def create_requirement(project_id: int, body: ReqCreate, _=Depends(require_admin)):
    if body.category not in ("image", "audio"):
        raise HTTPException(status_code=422, detail="category 必须为 image 或 audio")
    db = get_db()
    cur = db.execute(
        "INSERT INTO requirements (project_id, title, category, quantity_total, description, ai_prompt) VALUES (?,?,?,?,?,?)",
        (project_id, body.title, body.category, body.quantity_total, body.description, body.ai_prompt)
    )
    db.commit()
    row = db.execute("SELECT * FROM requirements WHERE id=?", (cur.lastrowid,)).fetchone()
    db.close()
    return dict(row)

@router.patch("/requirements/{rid}")
def update_requirement(rid: int, body: ReqUpdate, _=Depends(require_admin)):
    db = get_db()
    row = db.execute("SELECT * FROM requirements WHERE id=?", (rid,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(status_code=404, detail="需求不存在")
    fields = {
        "title": body.title if body.title is not None else row["title"],
        "description": body.description if body.description is not None else row["description"],
        "ai_prompt": body.ai_prompt if body.ai_prompt is not None else row["ai_prompt"],
        "quantity_total": body.quantity_total if body.quantity_total is not None else row["quantity_total"],
        "status": body.status if body.status is not None else row["status"],
    }
    db.execute(
        "UPDATE requirements SET title=?,description=?,ai_prompt=?,quantity_total=?,status=?,updated_at=datetime('now') WHERE id=?",
        (*fields.values(), rid)
    )
    db.commit()
    row = db.execute("SELECT * FROM requirements WHERE id=?", (rid,)).fetchone()
    db.close()
    return dict(row)

@router.delete("/requirements/{rid}")
def delete_requirement(rid: int, _=Depends(require_admin)):
    db = get_db()
    count = db.execute("SELECT COUNT(*) FROM submissions WHERE requirement_id=?", (rid,)).fetchone()[0]
    if count > 0:
        db.close()
        raise HTTPException(status_code=409, detail="需求下存在提交记录，无法删除")
    db.execute("DELETE FROM requirements WHERE id=?", (rid,))
    db.commit()
    db.close()
    return {"ok": True}
