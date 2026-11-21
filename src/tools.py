# -*- coding: utf-8 -*-
"""结构化工具注册、路径沙箱、人工审批门、审计日志(PRD 7.1/ 7.2/ 7.4)"""
from __future__ import annotations
import datetime, json, os, pathlib, sqlite3, subprocess, sys, uuid

HOME = pathlib.Path(os.environ.get('AGENT_HOME', r'W:\AgentWorkbench')).resolve()
SANDBOX = (HOME / 'sandbox').resolve()
OUTPUTS = (HOME / 'data' / 'outputs').resolve()
DB = HOME / 'data' / 'db' / 'audit.db'
DB.parent.mkdir(parents=True, exist_ok=True)
CFG_PATH = HOME / 'config.yaml'


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT, model TEXT, prompt TEXT, tool TEXT, params TEXT,
            result TEXT, approved INTEGER, files TEXT, error TEXT)""")
        c.commit()


def log(model, prompt, tool, params, result, approved=1, files='', error=''):
    with sqlite3.connect(DB) as c:
        c.execute(
            'INSERT INTO audit(ts,model,prompt,tool,params,result,approved,files,error) VALUES(?,?,?,?,?,?,?,?,?)',
            (datetime.datetime.now().isoformat(timespec='seconds'), model,
             str(prompt)[:2000], tool,
             json.dumps(params, ensure_ascii=False)[:4000],
             str(result)[:4000], int(approved), files, str(error)[:1000]))
        c.commit()


def _read_path(rel):
    p = (HOME / str(rel)).resolve()
    if p != HOME and HOME not in p.parents:
        raise PermissionError('读取越界:只允许工作区内的文件')
    if not p.exists():
        raise FileNotFoundError(rel)
    return p


def _write_path(rel):
    p = (HOME / str(rel)).resolve()
    allowed = (SANDBOX, OUTPUTS)
    if not any(a == p or a in p.parents for a in allowed):
        raise PermissionError('写入越界:只允许 sandbox/与 data/outputs/')
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_file(rel):
    return _read_path(rel).read_text(encoding='utf-8', errors='replace')[:20000]


def list_dir(rel='.'):
    p = _read_path(rel)
    return '\n'.join(sorted(x.name + ('/' if x.is_dir() else '') for x in p.iterdir())[:200])


def write_file(rel, content):
    p = _write_path(rel)
    p.write_text(str(content), encoding='utf-8')
    return '已写入 ' + str(p) + ' (' + str(len(str(content))) + ' 字符)'


def run_python(code, timeout=30):
    """脚本只落在沙箱、只在沙箱内运行"""
    SANDBOX.mkdir(parents=True, exist_ok=True)
    f = SANDBOX / 'tmp' / ('run_' + uuid.uuid4().hex[:8] + '.py')
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(str(code), encoding='utf-8')
    env = {k: os.environ.get(k, '') for k in ('PATH', 'SYSTEMROOT', 'TEMP', 'TMP', 'USERPROFILE', 'AGENT_SANDBOX')}
    env['AGENT_SANDBOX'] = str(SANDBOX)
    try:
        r = subprocess.run(
            [sys.executable, str(f)], capture_output=True, text=True,
            timeout=timeout, cwd=str(SANDBOX), env=env,
            encoding='utf-8', errors='replace')
        return ((r.stdout or '') + (r.stderr or ''))[:8000] or '(无输出)'
    except subprocess.TimeoutExpired:
        return '执行超时，已强制终止'
    finally:
        try:
            f.unlink()
        except OSError:
            pass


def search_local(keyword, rel='data/knowledge'):
    root = _read_path(rel)
    hits = []
    for p in root.rglob('*'):
        if p.is_file() and p.suffix.lower() in ('.md', '.txt', '.py', '.json'):
            try:
                if str(keyword).lower() in p.read_text(encoding='utf-8', errors='replace').lower():
                    hits.append(str(p.relative_to(HOME)) + ':命中')
            except OSError:
                pass
    return '\n'.join(hits[:30]) or '未命中(离线检索;联网搜索在第7.8节接入)'


TOOLS = [
    {'name': 'read_file', 'description': '【首选工具】读取工作区内文本文件的内容。当你需要查看任何文件内容时，必须调用此工具，不要自己写代码去读。',
     'parameters': {'type': 'object', 'properties': {'rel': {'type': 'string', 'description': '相对工作区的路径'}}, 'required': ['rel']},
     'risk': 'low', 'fn': read_file},
    {'name': 'list_dir', 'description': '列出工作区内某目录的文件与子目录',
     'parameters': {'type': 'object', 'properties': {'rel': {'type': 'string', 'description': '相对路径，默认.'}}, 'required': []},
     'risk': 'low', 'fn': list_dir},
    {'name': 'search_local', 'description': '在本地知识目录里按关键词离线检索',
     'parameters': {'type': 'object', 'properties': {'keyword': {'type': 'string'}, 'rel': {'type': 'string'}}, 'required': ['keyword']},
     'risk': 'low', 'fn': search_local},
    {'name': 'write_file', 'description': '把内容写入沙箱或输出目录(生成脚本、文档、小工具)',
     'parameters': {'type': 'object', 'properties': {'rel': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['rel', 'content']},
     'risk': 'high', 'fn': write_file},
    {'name': 'run_python', 'description': '在沙箱里执行一段 Python代码并返回输出',
     'parameters': {'type': 'object', 'properties': {'code': {'type': 'string'}, 'timeout': {'type': 'integer'}}, 'required': ['code']},
     'risk': 'high', 'fn': run_python},
]
TOOL_MAP = {t['name']: t for t in TOOLS}


def tools_for_llm():
    return [{'type': 'function', 'function': {'name': t['name'], 'description': t['description'], 'parameters': t['parameters']}} for t in TOOLS]


def need_approval(name):
    import yaml
    cfg = yaml.safe_load(CFG_PATH.read_text(encoding='utf-8'))
    return name in cfg['approval']['require_for']


def approve(name, params, interactive=True):
    if not need_approval(name):
        return True
    if not interactive:
        return False
    print('\n===== 人工审批门(PRD 3.2 Approval Gate) =====')
    print('工具: ' + name)
    print('参数: ' + json.dumps(params, ensure_ascii=False)[:600])
    print('确认执行? 输入 y 继续, 其它任意键取消: ', end='', flush=True)
    return input().strip().lower() == 'y'


def call_tool(name, args, model='local', prompt='', interactive=True):
    t = TOOL_MAP.get(name)
    if t is None:
        return '工具不存在: ' + str(name)
    schema = t['parameters']
    for req in schema.get('required', []):
        if req not in args:
            return '参数校验失败: 缺少 ' + req
    if not approve(name, args, interactive):
        log(model, prompt, name, args, '用户取消/非交互拒绝', approved=0)
        return '已被审批门拦截: ' + name + ' (未执行)'
    try:
        result = t['fn'](**args)
        err = None
    except Exception as e:
        result, err = '工具执行失败: ' + str(e), str(e)
    log(model, prompt, name, args, result, approved=1, files=str(args.get('rel', '')), error=err)
    return result


if __name__ == '__main__':
    init_db()
    print('tools.py初始化完成，审计库: ' + str(DB))

