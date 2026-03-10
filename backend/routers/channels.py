from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db
from backend.auth import require_admin

router = APIRouter(tags=["channels"])

class ChannelCreate(BaseModel):
    name: str
    type: str
    provider: str
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    default_params: Optional[str] = None
    note: Optional[str] = None
    enabled: int = 1

class ChannelUpdate(BaseModel):
    name: Optional[str] = None
    api_url: Optional[str] = None
    api_key: Optional[str] = None
    default_params: Optional[str] = None
    note: Optional[str] = None
    enabled: Optional[int] = None

PRESET_CHANNELS = [
    {
        "name": "Stability AI (SDXL)",
        "type": "ai_image",
        "provider": "stability_ai",
        "api_url": "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
        "api_key": "",
        "default_params": '{"cfg_scale":7,"steps":30,"width":1024,"height":1024}',
        "note": "官方文档：https://platform.stability.ai | 注册后在 Account→API Keys 获取 Key。计费：~$0.002/张。推荐用于：游戏角色、场景、特效图标。",
        "enabled": 0,
    },
    {
        "name": "OpenAI DALL-E 3",
        "type": "ai_image",
        "provider": "openai",
        "api_url": "https://api.openai.com/v1/images/generations",
        "api_key": "",
        "default_params": '{"model":"dall-e-3","size":"1024x1024","quality":"standard","n":1}',
        "note": "官方文档：https://platform.openai.com/docs/guides/images | 在 platform.openai.com 充值后使用。计费：$0.04/张(standard)。推荐用于：高质量概念图、角色立绘。",
        "enabled": 0,
    },
    {
        "name": "Replicate (FLUX.1)",
        "type": "ai_image",
        "provider": "replicate",
        "api_url": "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions",
        "api_key": "",
        "default_params": '{"num_outputs":1,"aspect_ratio":"1:1","output_format":"png"}',
        "note": "官方文档：https://replicate.com/black-forest-labs/flux-schnell | 注册即送免费额度。计费：按GPU秒计，约$0.003/张。FLUX速度快，质量接近SDXL。",
        "enabled": 0,
    },
    {
        "name": "Freesound.org（免费音效库）",
        "type": "ai_audio",
        "provider": "freesound",
        "api_url": "https://freesound.org/apiv2/search/text/",
        "api_key": "",
        "default_params": '{"format":"wav","license":"Creative Commons"}',
        "note": "官方文档：https://freesound.org/docs/api/ | 免费注册后在 Profile→API credentials 获取 Key。海量CC授权音效，支持关键词搜索。推荐用于：环境音、UI音效。",
        "enabled": 0,
    },
    {
        "name": "ElevenLabs（AI音频生成）",
        "type": "ai_audio",
        "provider": "elevenlabs",
        "api_url": "https://api.elevenlabs.io/v1/sound-generation",
        "api_key": "",
        "default_params": '{"duration_seconds":15,"prompt_influence":0.3}',
        "note": "官方文档：https://elevenlabs.io/docs/api-reference/sound-generation | 免费套餐每月10000字符。计费：按字符。支持文字描述生成音效，适合环境音、特效音。",
        "enabled": 0,
    },
    {
        "name": "OpenGameArt.org（开源游戏素材）",
        "type": "asset_library",
        "provider": "opengameart",
        "api_url": "https://opengameart.org/",
        "api_key": "",
        "default_params": '{"license":"GPL,CC-BY,CC0"}',
        "note": "完全免费的开源游戏素材库，无需 API Key，直接浏览下载。包含精灵图、地图块、音效等。许可证包含 GPL/CC，商用需注意授权。适合：原型阶段快速填充。",
        "enabled": 1,
    },
    {
        "name": "Itch.io 素材包",
        "type": "asset_library",
        "provider": "itchio",
        "api_url": "https://itch.io/game-assets",
        "api_key": "",
        "default_params": '{"filter":"free"}',
        "note": "Itch.io 游戏素材区，大量独立作者上传的免费/付费素材包。搜索关键词可找到像素风、像素怪物、UI等。商用需查看每个包的具体授权。",
        "enabled": 1,
    },
]

def seed_presets(db):
    count = db.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
    if count == 0:
        for ch in PRESET_CHANNELS:
            db.execute(
                "INSERT OR IGNORE INTO channels (name,type,provider,api_url,api_key,default_params,note,enabled) VALUES (?,?,?,?,?,?,?,?)",
                (ch["name"], ch["type"], ch["provider"], ch["api_url"], ch["api_key"], ch["default_params"], ch["note"], ch["enabled"])
            )
        db.commit()

@router.get("/channels")
def list_channels(_=Depends(require_admin)):
    db = get_db()
    seed_presets(db)
    rows = db.execute("SELECT * FROM channels ORDER BY type, id").fetchall()
    db.close()
    result = []
    for r in rows:
        d = dict(r)
        # 脱敏：api_key 只返回末4位
        if d.get("api_key"):
            d["api_key_masked"] = "****" + d["api_key"][-4:] if len(d["api_key"]) > 4 else "****"
        else:
            d["api_key_masked"] = ""
        d.pop("api_key")
        result.append(d)
    return result

@router.post("/channels", status_code=201)
def create_channel(body: ChannelCreate, _=Depends(require_admin)):
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO channels (name,type,provider,api_url,api_key,default_params,note,enabled) VALUES (?,?,?,?,?,?,?,?)",
            (body.name, body.type, body.provider, body.api_url, body.api_key, body.default_params, body.note, body.enabled)
        )
        db.commit()
        row = db.execute("SELECT * FROM channels WHERE id=?", (cur.lastrowid,)).fetchone()
        db.close()
        return dict(row)
    except Exception as e:
        db.close()
        if "UNIQUE" in str(e):
            raise HTTPException(409, "渠道名已存在")
        raise

@router.patch("/channels/{cid}")
def update_channel(cid: int, body: ChannelUpdate, _=Depends(require_admin)):
    db = get_db()
    row = db.execute("SELECT * FROM channels WHERE id=?", (cid,)).fetchone()
    if not row:
        db.close()
        raise HTTPException(404, "渠道不存在")
    fields = dict(row)
    if body.name is not None: fields["name"] = body.name
    if body.api_url is not None: fields["api_url"] = body.api_url
    if body.api_key is not None: fields["api_key"] = body.api_key
    if body.default_params is not None: fields["default_params"] = body.default_params
    if body.note is not None: fields["note"] = body.note
    if body.enabled is not None: fields["enabled"] = body.enabled
    db.execute(
        "UPDATE channels SET name=?,api_url=?,api_key=?,default_params=?,note=?,enabled=?,updated_at=datetime('now') WHERE id=?",
        (fields["name"], fields["api_url"], fields["api_key"], fields["default_params"], fields["note"], fields["enabled"], cid)
    )
    db.commit()
    row = db.execute("SELECT * FROM channels WHERE id=?", (cid,)).fetchone()
    db.close()
    return dict(row)

@router.delete("/channels/{cid}")
def delete_channel(cid: int, _=Depends(require_admin)):
    db = get_db()
    db.execute("DELETE FROM channels WHERE id=?", (cid,))
    db.commit()
    db.close()
    return {"ok": True}
