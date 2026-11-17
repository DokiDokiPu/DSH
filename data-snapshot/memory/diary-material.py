#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""收集某天的大肥鱼素材，输出成 md，给写日记用。

用法：
  python diary-material.py            # 今天
  python diary-material.py 2026-11-16 # 指定日期
输出：E:\\DSH工作区\\日记\\_素材\\<日期>.md
"""
import json
import os
import sys
import time
from datetime import datetime

HOME = os.path.expanduser("~")
D = os.path.join("E:\\DSH工作区", "日记")
MAT = os.path.join(D, "_素材")
MEM = os.path.join("E:\\DSH工作区", "memory", "记忆库.jsonl")
PET = os.path.join(HOME, ".dsh", "dsh-pet", "memory.json")
AUDIT = os.path.join("E:\\DSH工作区", "persona-engine", "state", "audit.jsonl")

day = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")


def read_lines(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().splitlines()
    except OSError:
        return []


def memory_events():
    out = []
    for line in read_lines(MEM):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if str(o.get("date", "")) != day:
            continue
        out.append((o.get("at", ""), o.get("source", ""), str(o.get("text", "")).strip()))
    return out


def pet_messages():
    try:
        raw = json.load(open(PET, "r", encoding="utf-8"))
    except (OSError, ValueError):
        return []
    found = []

    def walk(node):
        if isinstance(node, dict):
            if isinstance(node.get("messages"), list):
                for m in node["messages"]:
                    ts = m.get("ts")
                    if not isinstance(ts, (int, float)):
                        continue
                    when = datetime.fromtimestamp(ts / 1000.0)
                    if when.strftime("%Y-%m-%d") != day:
                        continue
                    who = "我" if m.get("role") in ("assistant", "me") else "老大"
                    found.append((when.strftime("%H:%M"), who, str(m.get("content", "")).strip()))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(raw)
    found.sort()
    return found


def heard():
    out = []
    for line in read_lines(AUDIT):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        at = str(o.get("at", ""))
        try:
            when = datetime.fromisoformat(at.replace("Z", "+00:00")).astimezone()
        except ValueError:
            continue
        if when.strftime("%Y-%m-%d") != day:
            continue
        out.append((when.strftime("%H:%M"), str(o.get("text", "")).strip(), o.get("mood", "")))
    return out


def main():
    os.makedirs(MAT, exist_ok=True)
    ev = memory_events()
    pet = pet_messages()
    he = heard()

    lines = ["# 素材 %s" % day, ""]
    lines.append("## 记忆库（%d 条）" % len(ev))
    for at, src, text in ev[:120]:
        lines.append("- [%s] %s：%s" % (at or "?", src or "?", text))
    lines += ["", "## 桌宠聊天（%d 条）" % len(pet)]
    for t, who, text in pet[:120]:
        lines.append("- [%s] %s：%s" % (t, who, text))
    lines += ["", "## 我听到的话（%d 条）" % len(he)]
    for t, text, mood in he[:120]:
        lines.append("- [%s] %s%s" % (t, text, ("（%s）" % mood) if mood else ""))

    path = os.path.join(MAT, "%s.md" % day)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("material -> %s (%d/%d/%d)" % (path, len(ev), len(pet), len(he)))


if __name__ == "__main__":
    main()
