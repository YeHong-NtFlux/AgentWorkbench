# -*- coding: utf-8 -*-
"""命令行控制台 — Agent 主交互界面"""
from __future__ import annotations
import sys
from src import core, router, records


def _clean_input(raw: str) -> str:
    """清洗复制粘贴带来的 >>> 前缀"""
    cleaned = raw.strip()
    # 去掉行首的 >>> 和多余空格（支持 >>>> 或 >>> >>> 等情况）
    while cleaned.startswith(">"):
        cleaned = cleaned[1:].lstrip()
    return cleaned.strip()


def show_welcome():
    r = router.Router()
    spec = r.pick("private", "private", core.ALLOW_CLOUD)
    print("=" * 60)
    print("  本地 Agent 工作台 — MVP 命令行控制台")
    print("  当前模型: " + spec["provider"] + " / " + spec["model"])
    print("  隐私策略: " + spec.get("reason", ""))
    print("=" * 60)
    print("  命令: /learn 来源|主题|摘要")
    print("        /digest    — 消息摘要")
    print("        /cloud on  — 开启云端(需授权)")
    print("        /cloud off — 关闭云端(回归本地)")
    print("        /exit      — 退出")
    print("-" * 60)


def main():
    for arg in sys.argv[1:]:
        if arg == "--cloud":
            core.ALLOW_CLOUD = True

    show_welcome()
    records.init_db()

    while True:
        try:
            raw = input("\n>>> ")
        except (EOFError, KeyboardInterrupt):
            print("\n再见!")
            break

        user_input = _clean_input(raw)
        if not user_input:
            continue

        # ---- 内置命令（现在能正确匹配了）----
        if user_input.startswith("/exit") or user_input.startswith("/quit"):
            print("再见!")
            break

        if user_input.startswith("/cloud"):
            parts = user_input.split()
            if len(parts) >= 2 and parts[1].lower() == "on":
                core.ALLOW_CLOUD = True
                print("[系统] 云端已授权开启(仅限 cloud_tasks 列表内任务)")
            else:
                core.ALLOW_CLOUD = False
                print("[系统] 已回归纯本地模式")
            spec = router.Router().pick("private", "private", core.ALLOW_CLOUD)
            print("[系统] 当前模型: " + spec["provider"] + " / " + spec["model"])
            continue

        if user_input.startswith("/digest"):
            print("\n" + records.message_digest())
            continue

        if user_input.startswith("/learn"):
            rest = user_input[len("/learn"):].strip()
            parts = [x.strip() for x in rest.split("|")]
            if len(parts) < 3:
                print("[用法] /learn 来源|主题|摘要")
                continue
            result = records.add_learning(parts[0], parts[1], parts[2])
            print("[学习记录] " + result)
            continue

        # ---- 普通对话 ----
        print("")
        try:
            reply = core.run_agent(
                user_input,
                privacy="private",
                allow_cloud=core.ALLOW_CLOUD,
                interactive=True,
            )
            print(reply)
        except Exception as e:
            print("[错误] " + str(e))


if __name__ == "__main__":
    main()
