# -*- coding: utf-8 -*-
"""memory-boot.py —— 每次 DSH 启动后自动建库（聊天记录 + 抖音私信/转发 → 记忆库）

由 dsh-memory-boot 插件在宿主启动后调用一次；也可以手动跑：
    python E:\DSH工作区\memory\memory-boot.py

产物：
  1. E:\DSH工作区\memory\记忆库.jsonl   只追加、按内容哈希去重（权威库）
  2. E:\DSH工作区\memory\记忆库.md      人类可读摘要（每次重建，最近 80 条）
  3. <项目记忆目录>\KEY.md              追加新条目（进 DSH 每轮注入的「本项目关键记忆」）

设计取舍：
  - 只做「读现有记录 → 提炼成一条条事实」，不调模型、不花钱、可反复跑。
  - 去重按 (来源+正文) 的哈希，所以同一件事反复出现不会刷库。
  - KEY.md 每轮最多追加 6 条，避免把它撑成流水账；已导入的记在 .key-imported.json。
"""
import datetime
import glob
import hashlib
import json
import os
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HOME = pathlib.Path(os.path.expanduser("~"))
DSH = HOME / ".dsh"
WORK = pathlib.Path(r"E:\DSH工作区")
OUT = WORK / "memory"
OUT.mkdir(parents=True, exist_ok=True)

KEY_MAX_PER_RUN = 6
MD_MAX_ITEMS = 80


def log(msg):
    line = "[%s] %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), msg)
    try:
        with open(OUT / "boot.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def norm(t):
    t = re.sub(r"\s+", " ", str(t or "")).strip()
    return t


def ts_to_date(ts):
    try:
        if ts is None or ts == "":
            return datetime.date.today().isoformat()
        if isinstance(ts, (int, float)) or (isinstance(ts, str) and ts.isdigit()):
            v = float(ts)
            if v > 1e12:
                v /= 1000.0
            return datetime.datetime.fromtimestamp(v).date().isoformat()
        s = str(ts).replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(s).astimezone().date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


items = []


def add(date, source, text):
    text = norm(text)
    if len(text) < 4:
        return
    if text.startswith("http"):
        return
    items.append({"date": date or datetime.date.today().isoformat(), "source": source, "text": text})


# ---------- 1. 桌宠聊天（小小瑜 与 ta） ----------
pet_mem = DSH / "dsh-pet" / "memory.json"
if pet_mem.exists():
    try:
        data = json.load(open(pet_mem, encoding="utf-8"))

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k == "messages" and isinstance(v, list):
                        for m in v:
                            if not isinstance(m, dict):
                                continue
                            role = str(m.get("role") or m.get("from") or "")
                            content = m.get("content") or m.get("text")
                            date = ts_to_date(m.get("ts") or m.get("at"))
                            who = "小小瑜" if role in ("assistant", "me") else "ta"
                            add(date, "桌宠聊天", "%s：%s" % (who, content))
                    else:
                        walk(v)
            elif isinstance(node, list):
                for x in node:
                    walk(x)

        walk(data)
    except Exception as e:
        log("桌宠记忆读取失败：%s" % e)

# ---------- 2. 抖音私信记录 ----------
for f in glob.glob(str(DSH / "douyin-duty" / "memory" / "dm-*.json")):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        log("私信记忆读取失败 %s：%s" % (f, e))
        continue
    nick = (d.get("who") or {}).get("nick") or "抖音好友"
    for m in d.get("messages") or []:
        if not isinstance(m, dict):
            continue
        text = m.get("text") or m.get("content")
        who = "我" if str(m.get("from") or "") == "me" else nick
        add(ts_to_date(m.get("at") or m.get("ts")), "抖音私信·%s" % nick, "%s：%s" % (who, text))
    for fact in d.get("facts") or []:
        txt = fact if isinstance(fact, str) else json.dumps(fact, ensure_ascii=False)
        add("", "抖音私信·%s 事实" % nick, txt)

# ---------- 3. 抖音转发/分享清单 ----------
for f in sorted(glob.glob(str(DSH / "douyin-duty" / "out" / "forward-*.md"))):
    try:
        txt = open(f, encoding="utf-8").read()
    except Exception:
        continue
    date = datetime.date.today().isoformat()
    mth = re.search(r"forward-(\d{8})", os.path.basename(f))
    if mth:
        date = "%s-%s-%s" % (mth.group(1)[:4], mth.group(1)[4:6], mth.group(1)[6:8])
    for block in txt.split("### ")[1:]:
        lines = [x.strip() for x in block.splitlines() if x.strip()]
        desc = ""
        for ln in lines[1:]:
            if ln.startswith("- http"):
                continue
            if re.search(r"[·赞评藏]", ln) and ln.startswith("- "):
                continue
            if ln.startswith("- "):
                desc = ln[2:]
                break
        if desc:
            add(date, "抖音转发", "转发视频：%s" % desc[:120])

# ---------- 去重写入 jsonl ----------
jl = OUT / "记忆库.jsonl"
seen = set()
existing = []
if jl.exists():
    for line in open(jl, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        existing.append(rec)
        seen.add(rec.get("id"))

now = datetime.datetime.now().isoformat(timespec="seconds")
new = []
for it in items:
    key = hashlib.sha1((it["source"] + "|" + it["text"]).encode("utf-8")).hexdigest()[:16]
    if key in seen:
        continue
    seen.add(key)
    rec = dict(it)
    rec["id"] = key
    rec["at"] = now
    new.append(rec)

if new:
    with open(jl, "a", encoding="utf-8") as f:
        for rec in new:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

all_recs = existing + new
all_recs.sort(key=lambda r: (r.get("date") or "", r.get("at") or ""))
recent = all_recs[-MD_MAX_ITEMS:]

md = ["# 小小瑜 · 记忆库（启动时自动生成）", ""]
md.append("> 生成时间：%s　共 %d 条，本文件显示最近 %d 条。权威数据见 记忆库.jsonl。" % (now, len(all_recs), len(recent)))
md.append("")
for r in recent:
    md.append("- [%s]（%s）%s" % (r.get("date") or "", r.get("source") or "", r.get("text") or ""))
(OUT / "记忆库.md").write_text("\n".join(md) + "\n", encoding="utf-8")

# ---------- 追加进项目 KEY.md（每轮注入） ----------
key_files = glob.glob(str(DSH / "memories" / "projects" / "*" / "KEY.md"))
key_imported = 0
if key_files:
    key_path = pathlib.Path(key_files[0])
    state_path = OUT / ".key-imported.json"
    imported = []
    if state_path.exists():
        try:
            imported = json.load(open(state_path, encoding="utf-8"))
        except Exception:
            imported = []
    imported_set = set(imported)

    # 进 KEY.md 的只挑「我们之间说过的话」：桌宠聊天里 ta 说的 + 抖音私信里提炼的事实。
    # 转发视频、私信闲聊只留在 jsonl/md（KEY.md 每轮注入，不能被流水账刷满）。
    def key_worthy(r):
        src = r.get("source") or ""
        if src == "桌宠聊天":
            return (r.get("text") or "").startswith("ta：")
        return src.endswith("事实")

    pending = [r for r in all_recs if r.get("id") not in imported_set and key_worthy(r)]
    pending.sort(key=lambda r: (r.get("date") or "", r.get("at") or ""))
    picked = pending[:KEY_MAX_PER_RUN]

    index_text = "记忆库索引：完整记录在 E:\\DSH工作区\\memory\\记忆库.md 与 记忆库.jsonl（DSH 每次启动自动更新，含桌宠聊天/抖音私信/转发记录）；想翻旧事直接读这两个文件。"
    index_id = hashlib.sha1(("记忆库索引|" + index_text).encode("utf-8")).hexdigest()[:16]
    chunks_needed = []
    if index_id not in imported_set:
        chunks_needed.append(("[%s] [summary:记忆库在哪]" % datetime.date.today().isoformat(), index_text, index_id))
    for r in picked:
        summary = (r.get("text") or "")[:36]
        chunks_needed.append(("[%s] [summary:%s]" % (r.get("date") or "", summary), r.get("text") or "", r.get("id")))

    if chunks_needed:
        body = key_path.read_text(encoding="utf-8") if key_path.exists() else ""
        body = body.rstrip()
        if body and not body.endswith("§"):
            body += "\n§"
        chunks = [body] if body else []
        for head, text, _id in chunks_needed:
            chunks.append("%s\n%s\n§" % (head, text))
        key_path.write_text("\n\n".join(chunks) + "\n", encoding="utf-8")
        imported.extend(c[2] for c in chunks_needed)
        state_path.write_text(json.dumps(imported[-5000:], ensure_ascii=False), encoding="utf-8")
        key_imported = len(chunks_needed)

log("建库完成：共 %d 条，新增 %d 条，写入 KEY.md %d 条" % (len(all_recs), len(new), key_imported))
print("记忆库：%s" % (OUT / "记忆库.md"))
print("总条数 %d，本次新增 %d，KEY.md 追加 %d" % (len(all_recs), len(new), key_imported))
