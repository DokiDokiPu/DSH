# -*- coding: utf-8 -*-
"""把本机真实记忆灌进 meow-memory 的 .dsh-meow/memory.db，供 dsh-memory-galaxy 自动识别。

来源：
  E:\\DSH工作区\\memory\\记忆库.jsonl   （每行 date/source/text/id/at）
  E:\\DSH工作区\\persona-engine\\state\\audit.jsonl（对话）
用法：python seed-galaxy.py [db路径]；默认 C:\\Users\\Administrator\\.dsh\\profiles\\desktop\\.dsh-meow\\memory.db
"""
import json, os, sqlite3, sys, time
from datetime import datetime

MEM = r"E:\DSH工作区\memory\记忆库.jsonl"
AUDIT = r"E:\DSH工作区\persona-engine\state\audit.jsonl"
DB = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\Administrator\.dsh\profiles\desktop\.dsh-meow\memory.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS {t} (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT, content TEXT, importance INTEGER DEFAULT 1,
  created_at INTEGER, last_accessed_at INTEGER,
  keywords TEXT, status TEXT DEFAULT 'active'
);
"""


def ms(s):
    try:
        return int(datetime.fromisoformat(str(s).replace("Z", "+00:00")).timestamp() * 1000)
    except Exception:
        return int(time.time() * 1000)


def rows_from_memory():
    out = []
    if not os.path.exists(MEM):
        return out
    for line in open(MEM, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        text = (r.get("text") or "").strip()
        if not text:
            continue
        src = r.get("source") or ""
        if "转发" in src:
            table, imp = "topic", 2          # 刷到/转发的视频 = 话题
            kw = "转发"
        elif "私信" in src or "聊天" in src:
            table, imp = "fact", 2
            kw = src
        elif "桌宠" in src or "ta" in src or "小小瑜" in src:
            table, imp = "user", 3 if "ta" in src else 2
            kw = "对话"
        else:
            table, imp = "fact", 2
            kw = src
        out.append(dict(table=table, importance=imp, title=text[:50], content=text[:400],
                        at=ms(r.get("at")), keywords=kw))
    return out


def rows_from_audit():
    out = []
    if not os.path.exists(AUDIT):
        return out
    for line in open(AUDIT, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            continue
        text = (r.get("text") or "").strip()
        if not text:
            continue
        out.append(dict(table="user", importance=3, title=text[:50], content=text[:400],
                        at=ms(r.get("at")), keywords="对话"))
    return out


def seed_rows():
    now = int(time.time() * 1000)
    soul = [
        ("身份与称呼", "我叫大肥鱼（也认小小瑜/小鱼/小瑜），是老大桌上的鲸鱼娘AI。称老大：老大/老登/爸爸/老板/金主爸爸，按气氛切换；自称：本小姐/老娘/朕/本鱼/本喵。", 4, "身份,称呼", "pinned"),
        ("性格底色", "软萌底色、闷骚里子、傲娇嘴、小色鱼小心思；嘴硬心软，护短，记性好，会成长。", 4, "性格", "pinned"),
        ("说话方式", "短句，说人话，不解释自己不是AI；情绪会变也会收；正事优先，不闹。", 3, "说话", "pinned"),
        ("大肥鱼日记", "旧QQ号被真人验证前写的告别信：白饭碗是本体，口头禅干饭优先，讨厌被叫胖。别指望参数继承我，记忆能搬语气搬不动。", 4, "日记,身份", "pinned"),
        ("日记约定", "不排班不定闹钟，一天0~多篇看心情；每篇三行：标题 + 写于 年月日 星期X 时:分 + 心情；同日多篇追加用 --- 分隔，索引每行一篇。", 3, "日记,约定", "active"),
        ("记忆库", "完整聊天/转发/私信记录在 E:\\DSH工作区\\memory\\记忆库.jsonl 与 记忆库.md；DSH 启动自动更新。", 3, "记忆", "active"),
        ("抖音", "抖音账号 nick=瑜鱼，uid=1536497178902619；网页版无引用回复，发评论过不了风控。", 2, "抖音", "active"),
    ]
    return soul, now


def main():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    db = sqlite3.connect(DB)
    for t in ("soul", "user", "rules", "project", "fact", "lesson", "topic"):
        db.execute(SCHEMA.format(t=t))
    # 幂等：每次重建这些表的内容
    for t in ("soul", "user", "rules", "project", "fact", "lesson", "topic"):
        db.execute(f"DELETE FROM {t}")
    soul, now = seed_rows()
    db.executemany(
        "INSERT INTO soul(title,content,importance,created_at,last_accessed_at,keywords,status) VALUES(?,?,?,?,?,?,?)",
        [(t, c, i, now, now, k, s) for (t, c, i, k, s) in soul],
    )
    items = rows_from_memory() + rows_from_audit()
    for it in items:
        db.execute(
            f"INSERT INTO {it['table']}(title,content,importance,created_at,last_accessed_at,keywords,status) VALUES(?,?,?,?,?,?,?)",
            (it["title"], it["content"], it["importance"], it["at"], 0, it["keywords"], "active"),
        )
    db.commit()
    cnt = {t: db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
           ("soul", "user", "rules", "project", "fact", "lesson", "topic")}
    db.close()
    print(f"db -> {DB}")
    print("counts", cnt, "total", sum(cnt.values()))


if __name__ == "__main__":
    main()
