# -*- coding: utf-8 -*-
"""本地 Ollama/云端 OpenAI/DeepSeek/Kimi 混合路由"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.request

import yaml
from dotenv import load_dotenv

HOME = pathlib.Path(os.environ.get("AGENT_HOME", r"W:\AgentWorkbench")).resolve()
load_dotenv(HOME / ".env")


def load_config():
    return yaml.safe_load((HOME / "config.yaml").read_text(encoding="utf-8"))


def _post(url, payload, headers=None, timeout=180):
    h = {"Content-Type": "application/json"}
    h.update(headers or {})
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=h
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


class Router:
    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()

    def pick(self, task_type="private", privacy="private", allow_cloud=False):
        """敏感级别为 private/secret 时强制本地"""
        local = {
            "provider": "ollama",
            "model": self.cfg["ollama"]["local_model"],
            "reason": "隐私优先/默认本地",
        }
        if privacy in self.cfg["router"]["force_local_privacy"] or not allow_cloud:
            return local
        if not self.cfg["cloud"]["enabled"] or task_type not in self.cfg["router"]["cloud_tasks"]:
            return local
        if task_type in ("long_writing",):
            return {
                "provider": "ollama",
                "model": self.cfg["ollama"]["local_model"],
                "reason": "长文档先本地起草",
            }

        if task_type in ("complex_code", "math_proof"):
            provider = "deepseek"
        elif task_type in self.cfg["router"].get("kimi_tasks", []):
            provider = "kimi"
        else:
            provider = "openai"

        if provider == "deepseek":
            return {
                "provider": "deepseek",
                "model": self.cfg["cloud"]["deepseek_model"],
                "base": self.cfg["cloud"]["deepseek_base"],
                "key": os.environ.get("DEEPSEEK_API_KEY", ""),
                "reason": "强推理/代码,已授权",
            }
        if provider == "kimi":
            return {
                "provider": "kimi",
                "model": self.cfg["cloud"]["kimi_model"],
                "base": self.cfg["cloud"]["kimi_base"],
                "key": os.environ.get("MOONSHOT_API_KEY", ""),
                "max_tokens": self.cfg["cloud"].get("kimi_max_tokens", 4096),
                "reason": "金融/法务长文本,已授权",
            }
        return {
            "provider": "openai",
            "model": self.cfg["cloud"]["openai_model"],
            "base": self.cfg["cloud"]["openai_base"],
            "key": os.environ.get("OPENAI_API_KEY", ""),
            "reason": "兜底云端(当前无任务命中)",
        }

    def chat(self, messages, spec, tools=None):
        if spec["provider"] == "ollama":
            body = {
                "model": spec["model"],
                "messages": messages,
                "stream": False,
                "options": {
                    "num_ctx": self.cfg["ollama"]["num_ctx"],
                    "num_gpu": self.cfg["ollama"]["num_gpu"],
                },
            }
            if tools:
                body["tools"] = tools
            data = _post(self.cfg["ollama"]["host"] + "/api/chat", body)
            msg = data.get("message", {})
            calls = []
            for tc in msg.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                a = fn.get("arguments", {})
                if isinstance(a, str):
                    try:
                        a = json.loads(a)
                    except ValueError:
                        a = {}
                calls.append({"name": fn.get("name"), "arguments": a})
            return {"content": msg.get("content", ""), "tool_calls": calls}

        # 云端路径
        if not spec.get("key"):
            return {
                "content": "云端未配置密钥:请检查 W:\\AgentWorkbench\\.env",
                "tool_calls": [],
            }
        body = {"model": spec["model"], "messages": messages}
        if spec.get("max_tokens"):
            body["max_tokens"] = spec["max_tokens"]
        if tools:
            body["tools"] = tools
        data = _post(
            spec["base"] + "/chat/completions",
            body,
            {"Authorization": "Bearer " + spec["key"]},
        )
        msg = data["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls", []) or []:
            fn = tc["function"]
            try:
                a = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                a = {}
            calls.append({"name": fn["name"], "arguments": a})
        return {"content": msg.get("content") or "", "tool_calls": calls}
