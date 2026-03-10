import os
import io
import zipfile
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
from backend.database import get_db
from backend.auth import require_admin

router = APIRouter(tags=["assets"])

DATA_DIR = os.getenv("DATA_DIR", "/data")

def _query_assets(db, project_id=None, category=None, requirement_id=None):
    sql = """
        SELECT s.*, r.title AS requirement_title, r.project_id, r.category AS req_category,
               p.name AS project_name
        FROM submissions s
        JOIN requirements r ON s.requirement_id = r.id
        JOIN projects p ON r.project_id = p.id
        WHERE s.status = 'approved'
    """
    params = []
    if project_id:
        sql += " AND r.project_id=?"
        params.append(project_id)
    if category:
        sql += " AND r.category=?"
        params.append(category)
    if requirement_id:
        sql += " AND s.requirement_id=?"
        params.append(requirement_id)
    sql += " ORDER BY s.reviewed_at DESC"
    return db.execute(sql, params).fetchall()

@router.get("/assets")
def list_assets(
    project_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    requirement_id: Optional[int] = Query(None),
    _=Depends(require_admin)
):
    db = get_db()
    rows = _query_assets(db, project_id, category, requirement_id)
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        d["download_url"] = f"/uploads/{d['requirement_id']}/{d['filename']}"
        d["approved_at"] = d.get("reviewed_at")
        result.append(d)
    return result

@router.get("/assets/download-zip")
def download_zip(
    project_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    requirement_id: Optional[int] = Query(None),
    _=Depends(require_admin)
):
    db = get_db()
    rows = _query_assets(db, project_id, category, requirement_id)
    db.close()

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            d = dict(r)
            path = d["file_path"]
            if os.path.exists(path):
                zf.write(path, arcname=d["original_filename"])
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=assets.zip"}
    )
