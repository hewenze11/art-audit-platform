import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.auth import require_admin

router = APIRouter(tags=["audit"])

DATA_DIR = os.getenv("DATA_DIR", "/data")

class ReviewBody(BaseModel):
    action: str
    note: Optional[str] = None

@router.post("/submissions/{sid}/review")
def review_submission(sid: int, body: ReviewBody, _=Depends(require_admin)):
    if body.action not in ("approved", "on_hold", "rejected"):
        raise HTTPException(status_code=422, detail="action 必须为 approved/on_hold/rejected")

    db = get_db()
    sub = db.execute("SELECT * FROM submissions WHERE id=?", (sid,)).fetchone()
    if not sub:
        db.close()
        raise HTTPException(status_code=404, detail="提交记录不存在")

    try:
        if body.action == "approved":
            db.execute(
                "UPDATE submissions SET status='approved', reviewed_at=datetime('now'), review_note=? WHERE id=?",
                (body.note, sid)
            )
            db.execute(
                "UPDATE requirements SET quantity_done=quantity_done+1, updated_at=datetime('now') WHERE id=?",
                (sub["requirement_id"],)
            )
            req = db.execute("SELECT * FROM requirements WHERE id=?", (sub["requirement_id"],)).fetchone()
            if req["quantity_done"] >= req["quantity_total"]:
                db.execute(
                    "UPDATE requirements SET status='completed', updated_at=datetime('now') WHERE id=?",
                    (sub["requirement_id"],)
                )

        elif body.action == "on_hold":
            db.execute(
                "UPDATE submissions SET status='on_hold', reviewed_at=datetime('now'), review_note=? WHERE id=?",
                (body.note, sid)
            )

        elif body.action == "rejected":
            # 物理删除文件
            file_path = sub["file_path"]
            if os.path.exists(file_path):
                os.remove(file_path)
            db.execute(
                "UPDATE submissions SET status='rejected', reviewed_at=datetime('now'), review_note=? WHERE id=?",
                (body.note, sid)
            )

        db.execute(
            "INSERT INTO audit_logs (submission_id, action, note) VALUES (?,?,?)",
            (sid, body.action, body.note)
        )
        db.commit()
    finally:
        db.close()

    return {"ok": True, "new_status": body.action}
