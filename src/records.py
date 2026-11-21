# -*- coding: utf-8 -*-
"""学习记录与消息摘要占位(PRD 11.1-7/8)"""
from __future__ import annotations
import datetime, json, pathlib, sqlite3

HOME = pathlib.Path(r'W:\AgentWorkbench')
DB = HOME / 'data' / 'db' / 'learning.db'


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS learning(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, source TEXT, topic TEXT, summary TEXT
        )""")
        c.commit()


def add_learning(source, topic, summary):
    init_db()
    with sqlite3.connect(DB) as c:
        c.execute(
            'INSERT INTO learning(ts, source, topic, summary) VALUES(?,?,?,?)',
            (datetime.datetime.now().isoformat(timespec='seconds'),
             str(source)[:200], str(topic)[:200], str(summary)[:1000])
        )
        c.commit()
    return '已记录: ' + str(topic)


# ---- 消息摘要 ----

IMPORTANT_KW = ['答辩', '截止', '考试', '提交', '三点', '明天', '报告']


def message_digest():
    p = HOME / 'data' / 'messages' / 'sample.json'
    if not p.exists():
        return '无消息归档'

    raw = p.read_bytes()
    # 去掉 UTF-8 BOM
    if raw[:3] == b'\xef\xbb\xbf':
        raw = raw[3:]
    text = raw.decode('utf-8', errors='replace').strip()

    if not text:
        return '消息归档为空，请放入消息数据'

    # 尝试 1: 标准 JSON 数组
    try:
        msgs = json.loads(text)
        if isinstance(msgs, list):
            return _summarize(msgs)
    except json.JSONDecodeError:
        pass

    # 尝试 2: JSONL（每行一个对象）
    lines = [l.strip().rstrip(',') for l in text.splitlines() if l.strip()]
    msgs = []
    for line in lines:
        try:
            msgs.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    if not msgs:
        return '消息解析失败: 归档格式无法识别(需要 JSON 数组或 JSONL)'

    return _summarize(msgs)


def _summarize(msgs):
    counts = {}
    important = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        txt = m.get('text', '')
        tag = '重要通知' if any(k in txt for k in IMPORTANT_KW) else '可稍后处理'
        counts[tag] = counts.get(tag, 0) + 1
        if tag == '重要通知':
            important.append(m.get('from', '?') + ': ' + txt[:60])

    out = ['消息摘要(本地规则版)']
    out += ['%s: %d条' % (k, v) for k, v in counts.items()]
    out += ['', '待回复队列:']
    out += ['- ' + s for s in important[:10]]
    out += ['', '发送行为未执行: 所有回复需人工确认(PRD 4.3.4)']
    return '\n'.join(out)


if __name__ == '__main__':
    init_db()
    print('records.py初始化完成')
