import os
import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
from backend.database import get_db
from backend.auth import require_worker

router = APIRouter(tags=["submissions"])

DATA_DIR = os.getenv("DATA_DIR", "/data")

ALLOWED_MIMES = {
    "image/png", "image/jpeg", "image/webp",
    "audio/mpeg", "audio/wav", "audio/ogg"
}

MIME_TO_EXT = {
    "image/png": "png", "image/jpeg": "jpg", "image/webp": "webp",
    "audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg"
}

@router.post("/submissions", status_code=201)
async def upload_submission(
    requirement_id: int = Form(...),
    submitted_by: Optional[str] = Form(None),
    file: UploadFile = File(...),
    _=Depends(require_worker)
):
    mime = file.content_type
    if mime not in ALLOWED_MIMES:
        raise HTTPException(status_code=422, detail=f"不支持的文件格式：{mime}")

    content = await file.read()
    file_hash = hashlib.sha256(content).hexdigest()

    db = get_db()
    existing = db.execute("SELECT id FROM submissions WHERE file_hash=?", (file_hash,)).fetchone()
    if existing:
        db.close()
        raise HTTPException(status_code=409, detail="文件已存在，禁止重复提交")

    ext = MIME_TO_EXT.get(mime, "bin")
    new_filename = f"{uuid.uuid4().hex}.{ext}"
    save_dir = os.path.join(DATA_DIR, "uploads", str(requirement_id))
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, new_filename)

    with open(save_path, "wb") as f:
        f.write(content)

    cur = db.execute(
        """INSERT INTO submissions
           (requirement_id, original_filename, filename, file_path, file_hash, file_size, mime_type, submitted_by)
           VALUES (?,?,?,?,?,?,?,?)""",
        (requirement_id, file.filename, new_filename, save_path, file_hash, len(content), mime, submitted_by)
    )
    db.commit()
    row = db.execute("SELECT * FROM submissions WHERE id=?", (cur.lastrowid,)).fetchone()
    db.close()
    return dict(row)

@router.get("/submissions/pending")
def list_pending(_=Depends(require_worker)):
    db = get_db()
    rows = db.execute("""
        SELECT s.*,
               r.title AS requirement_title,
               r.project_id,
               p.name AS project_name
        FROM submissions s
        JOIN requirements r ON s.requirement_id = r.id
        JOIN projects p ON r.project_id = p.id
        WHERE s.status = 'pending'
        ORDER BY s.submitted_at DESC
    """).fetchall()
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        d["preview_url"] = f"/uploads/{d['requirement_id']}/{d['filename']}"
        result.append(d)
    return result
