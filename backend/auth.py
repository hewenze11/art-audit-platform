import os
from fastapi import Header, HTTPException

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")

def require_admin(authorization: str = Header(...)):
    if not authorization.startswith("Bearer ") or authorization[7:] != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def require_worker(authorization: str = Header(...)):
    token = authorization[7:] if authorization.startswith("Bearer ") else ""
    if token not in (WORKER_TOKEN, ADMIN_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")
