from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Header
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from api.support import require_admin
from services.register.openai_register import register_results_file
from services.register_service import register_service


class RegisterConfigRequest(BaseModel):
    mail: dict | None = None
    proxy: str | None = None
    total: int | None = None
    threads: int | None = None
    mode: str | None = None
    target_quota: int | None = None
    target_available: int | None = None
    check_interval: int | None = None


def create_router() -> APIRouter:
    router = APIRouter()

    @router.get("/api/register")
    async def get_register_config(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"register": register_service.get()}

    @router.post("/api/register")
    async def update_register_config(body: RegisterConfigRequest, authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"register": register_service.update(body.model_dump(exclude_none=True))}

    @router.post("/api/register/start")
    async def start_register(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"register": register_service.start()}

    @router.post("/api/register/stop")
    async def stop_register(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"register": register_service.stop()}

    @router.post("/api/register/reset")
    async def reset_register(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        return {"register": register_service.reset()}

    @router.get("/api/register/events")
    async def register_events(token: str = ""):
        require_admin(f"Bearer {token}")

        async def stream():
            last = ""
            while True:
                payload = json.dumps(register_service.get(), ensure_ascii=False)
                if payload != last:
                    last = payload
                    yield f"data: {payload}\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/api/register/export/rt")
    async def export_refresh_tokens(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        if not register_results_file.exists():
            return PlainTextResponse("", media_type="text/plain")
        lines: list[str] = []
        for raw in register_results_file.read_text(encoding="utf-8").splitlines():
            try:
                rt = str(json.loads(raw).get("refresh_token") or "").strip()
            except Exception:
                continue
            if rt:
                lines.append(rt)
        return PlainTextResponse(
            "\n".join(lines) + ("\n" if lines else ""),
            media_type="text/plain",
            headers={"Content-Disposition": 'attachment; filename="refresh_tokens.txt"'},
        )

    @router.get("/api/register/export/full")
    async def export_full_results(authorization: str | None = Header(default=None)):
        require_admin(authorization)
        content = register_results_file.read_text(encoding="utf-8") if register_results_file.exists() else ""
        return PlainTextResponse(
            content,
            media_type="application/x-ndjson",
            headers={"Content-Disposition": 'attachment; filename="register_results.jsonl"'},
        )

    return router
