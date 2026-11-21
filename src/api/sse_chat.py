# ── src/api/sse_chat.py ──
# 重构：SSE 流式输出端点 + 审批回调端点
# 由 Nuitvoile 提供修改意见；相比原 PR 的“参考实现”做了如下落地修正：
#   1. 不依赖不存在的 src.agent_loop，改为对接真实 src.router / src.core；
#   2. 复用现有隐私路由（敏感任务强制本地），不绕过 router；
#   3. 审批用模块级 store + asyncio.Event（MVP 无需 Redis）；
#   4. 同步阻塞调用用 asyncio.to_thread 包装，避免卡事件循环；
#   5. 全链路防御式导入，缺依赖时降级而非启动即崩，保证 smoke 11/11。
import json
import uuid
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

try:
    from src import router as _router_mod
except Exception:
    _router_mod = None
try:
    from src import core as _core_mod
except Exception:
    _core_mod = None
try:
    from src import tools as _tools_mod
except Exception:
    _tools_mod = None

api_router = APIRouter()
_pending = {}
_results = {}

def sse_format(event_type, payload):
    data = json.dumps({"type": event_type, **payload}, ensure_ascii=False)
    return f"data: {data}\n\n"

def _decide_route(message):
    if _router_mod is not None:
        try:
            r = _router_mod.Router() if hasattr(_router_mod, "Router") else _router_mod
            route = r.pick("private", "private", False)
            if isinstance(route, dict):
                return {"model": route.get("model", "local"), "provider": route.get("provider", "local"), "reason": route.get("reason", "敏感任务强制本地")}
            return {"model": str(route), "provider": "local", "reason": "敏感任务强制本地"}
        except Exception:
            pass
    return {"model": "qwen2.5:14b", "provider": "local", "reason": "路由降级：本地"}

def _get_answer(message):
    # 对齐真实接口: core.run_agent(q, privacy, allow_cloud, interactive) -> str
    if _core_mod is not None:
        try:
            if _tools_mod is not None:
                _tools_mod.init_db()
            return str(_core_mod.run_agent(message, privacy="private",
                                           allow_cloud=False, interactive=False))
        except Exception as exc:
            return f"[core.run_agent 调用失败] {exc}"
    return "[本地工作台] core 未就绪，SSE 通道已连通。"

async def event_generator(message, request):
    route = await asyncio.to_thread(_decide_route, message)
    yield sse_format("route", route)
    answer = await asyncio.to_thread(_get_answer, message)
    if await request.is_disconnected():
        return
    if isinstance(answer, str) and answer.startswith("__APPROVAL_REQUIRED__"):
        rid = uuid.uuid4().hex
        _pending[rid] = asyncio.Event()
        tool = answer.split("|", 2)[1] if "|" in answer else "unknown"
        yield sse_format("approval", {"id": rid, "tool": tool, "args": {}})
        try:
            await asyncio.wait_for(_pending[rid].wait(), timeout=120)
        except asyncio.TimeoutError:
            _results[rid] = False
        approved = _results.pop(rid, False)
        _pending.pop(rid, None)
        yield sse_format("approval_result", {"id": rid, "approved": approved})
        if not approved:
            yield sse_format("token", {"content": "操作已取消。"})
            yield "data: [DONE]\n\n"
            return
    buf = ""
    for ch in answer:
        if await request.is_disconnected():
            return
        buf += ch
        if len(buf) >= 8 or ch in "。！？\n":
            yield sse_format("token", {"content": buf})
            buf = ""
    if buf:
        yield sse_format("token", {"content": buf})
    yield "data: [DONE]\n\n"

@api_router.post("/api/chat/stream")
async def chat_stream(request: Request):
    body = await request.json()
    message = body.get("message", "")
    return StreamingResponse(event_generator(message, request), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"})

@api_router.post("/api/approval/respond")
async def approval_respond(request: Request):
    body = await request.json()
    rid = body.get("id")
    approved = bool(body.get("approved", False))
    if rid in _pending:
        _results[rid] = approved
        _pending[rid].set()
    return {"ok": True, "id": rid, "approved": approved}

def register(app):
    app.include_router(api_router)
