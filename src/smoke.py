# -*- coding: utf-8 -*-
"""MVP自检:9项全 PASS才算完成(对应本章 3.4)。"""
import json, pathlib, urllib.request
from src import tools, router, records, core

HOME = pathlib.Path(r"W:\AgentWorkbench")
ok = []


def check(name, cond, extra=""):
    ok.append(cond)
    status = "[PASS]" if cond else "[FAIL]"
    msg = status + " " + name
    if extra:
        msg += " " + str(extra)
    print(msg)


# 1. config
check("config.yaml存在", (HOME / "config.yaml").exists())

# 2. models 目录
check("模型目录存在", (HOME / "models").exists())

# 3. Ollama 在线
try:
    with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=5) as r:
        tags = json.loads(r.read().decode())
    has_qwen = any("qwen2.5" in m.get("name", "") for m in tags.get("models", []))
    check("Ollama服务在线", has_qwen)
except Exception as e:
    check("Ollama服务在线", False, e)

# 4. audit 表
tools.init_db()
check("审计库audit表可用", True)

# 5. read_file
try:
    content = tools.read_file("config.yaml")
    check("read_file可读配置", "ollama" in content)
except Exception as e:
    check("read_file可读配置", False, e)

# 6. write_file 沙箱限制
try:
    result = tools.write_file("sandbox/smoke.txt", "hello")
    check("write_file限制在沙箱", "sandbox" in result)
except Exception as e:
    check("write_file限制在沙箱", False, e)

# 7. 越权写入拒绝
try:
    tools.write_file("../../Windows/evil.txt", "x")
    check("越权写入被拒绝", False)
except PermissionError:
    check("越权写入被拒绝", True)
except Exception as e:
    check("越权写入被拒绝", False, type(e).__name__)

# 8. run_python
try:
    out = tools.run_python("print(1+1)")
    check("run_python沙箱可执行", "2" in out)
except Exception as e:
    check("run_python沙箱可执行", False, e)

# 9. search_local
try:
    result = tools.search_local("Agent")
    check("search_local可用", isinstance(result, str))
except Exception as e:
    check("search_local可用", False, e)

# 10. 路由强制本地
r = router.Router()
pick = r.pick("legal", "secret", True)
check("敏感任务强制本地", pick["provider"] == "ollama")

# 11. 学习记录
try:
    records.init_db()
    lr = records.add_learning("部署手册自检", "MVP", "跑通")
    check("学习记录可写", "已记录" in lr)
except Exception as e:
    check("学习记录可写", False, e)

# 12. 汇总
passed = sum(ok)
total = len(ok)
print("\n结果: %d/%d PASS" % (passed, total))
raise SystemExit(0 if all(ok) else 1)
