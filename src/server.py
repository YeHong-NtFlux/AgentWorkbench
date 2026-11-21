
import os
_MODELS_PATH_CHECK = os.environ.get("OLLAMA_MODELS", "")
_EXPECTED = r"W:\AgentWorkbench\models"
if _EXPECTED.lower() not in _MODELS_PATH_CHECK.lower():
    import sys
    print("=" * 60, file=sys.stderr)
    print("  [FATAL] Ollama models path mismatch!", file=sys.stderr)
    print("  Expected to contain: " + _EXPECTED, file=sys.stderr)
    print("  Current OLLAMA_MODELS: " + (_MODELS_PATH_CHECK or "(empty)"), file=sys.stderr)
    print("  Workbench REFUSES to start with D: drive models.", file=sys.stderr)
    print("  Run restore_d.bat or fix the path, then retry.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)
del os, _MODELS_PATH_CHECK, _EXPECTED
# -*- coding: utf-8 -*-
"""过渡用本地网页控制台后端:只开放低风险工具，高风险动作请在 CLI审批。"""
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse

from src import core, tools, router
from src.api.sse_chat import register as _register_sse

app = FastAPI(title="Local Agent Workbench MVP")
_register_sse(app)  # 挂载 /api/chat/stream 与 /api/approval/respond


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "console.html")


@app.get("/api/status")
def status():
    r = router.Router()
    return {
        "model": r.pick("private", "private", False)["model"],
        "tools": [t["name"] for t in tools.TOOLS],
        "note": "网页模式禁用高风险工具，写文件/执行脚本请在命令行控制台审批",
    }


@app.post("/api/chat")
async def chat(req: Request):
    body = await req.json()
    q = str(body.get("message", ""))
    tools.init_db()
    reply = core.run_agent(q, privacy="private", allow_cloud=False, interactive=False)
    return {"reply": reply}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765)

