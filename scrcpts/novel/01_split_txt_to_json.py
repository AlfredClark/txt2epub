# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  01_split_txt_to_json.py
@Time    :  2026-08-19 10:50:13
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Split txt to JSON
"""
import json
import re
from pathlib import Path

import cn2an

from env import BOOKS, OUTPUT_DIR, SOURCE_DIR

_NUMBER = r"[0-9０-９一二三四五六七八九十百千零〇]+"


def _unit_re(unit: str) -> re.Pattern:
    return re.compile(rf"^第\s*{_NUMBER}\s*{unit}")


def _unit_prefix_re(unit: str) -> re.Pattern:
    return re.compile(rf"^第\s*{_NUMBER}\s*{unit}\s*")


CHAPTER_RE = _unit_re("章")
VOLUME_RE = _unit_re("卷")
CHAPTER_PREFIX_RE = _unit_prefix_re("章")
VOLUME_PREFIX_RE = _unit_prefix_re("卷")


def _extract_number(header: str, unit: str) -> int:
    m = re.search(rf"第\s*({_NUMBER})\s*{unit}", header)
    if not m:
        return 0
    token = m.group(1)
    if token.isdigit():
        return int(token)
    return int(cn2an.cn2an(token, "normal"))


def extract_order(title: str) -> int:
    return _extract_number(title, "章")


def extract_volume_order(title: str) -> int:
    return _extract_number(title, "卷")


def extract_title(header: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", header).strip() or header.strip()


def extract_volume_title(header: str) -> str:
    return VOLUME_PREFIX_RE.sub("", header).strip() or header.strip()


def parse_txt(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    book_name = ""
    author = ""
    tags = ""
    intro_lines = []
    body_lines = []
    in_intro = False
    body_started = False

    for line in lines:
        stripped = line.strip()
        if line.startswith("书名："):
            book_name = line[len("书名："):].strip()
        elif line.startswith("作者："):
            author = line[len("作者："):].strip()
        elif line.startswith("标签："):
            tags = line[len("标签："):].strip()
        elif stripped == "简介：":
            in_intro = True
        elif in_intro:
            if stripped.startswith("正文"):
                in_intro = False
                body_started = True
            else:
                intro_lines.append(line)
        elif stripped.startswith("正文"):
            body_started = True
        elif body_started:
            body_lines.append(line)

    volumes: list[dict] = []
    current_volume: dict | None = None
    current_chapter: dict | None = None

    def flush_chapter() -> None:
        nonlocal current_chapter
        if current_chapter is not None:
            if current_volume is not None:
                current_volume["chapters"].append(current_chapter)
            current_chapter = None

    def flush_volume() -> None:
        nonlocal current_volume
        flush_chapter()
        if current_volume is not None:
            volumes.append(current_volume)
            current_volume = None

    for line in body_lines:
        if VOLUME_RE.match(line):
            flush_volume()
            current_volume = {
                "order": extract_volume_order(line),
                "title": extract_volume_title(line),
                "chapters": [],
            }
        elif CHAPTER_RE.match(line):
            flush_chapter()
            if current_volume is None:
                current_volume = {"order": 0, "title": book_name, "chapters": []}
            current_chapter = {"order": extract_order(line), "title": extract_title(line), "contents": []}
        elif current_chapter is not None:
            stripped = line.strip()
            if stripped:
                current_chapter["contents"].append(stripped)
    flush_volume()

    if not volumes and body_lines:
        volumes.append({"order": 0, "title": book_name, "chapters": []})

    for volume in volumes:
        volume["chapters"].sort(key=lambda chapter: chapter["order"])
    volumes.sort(key=lambda vol: vol["order"])

    return {
        "title": book_name,
        "author": author,
        "tags": tags.split("/"),
        "description": [line.strip() for line in intro_lines if line.strip()],
        "volumes": volumes,
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for book_name in BOOKS:
        src = SOURCE_DIR / f"{book_name}.txt"
        if not src.exists():
            print(f"[SKIP] 未找到源文件: {src}")
            continue
        data = parse_txt(src)
        if data["title"] != book_name:
            print(f"[WARN] 源文件书名({data['title']})与常量({book_name})不一致")
        out = OUTPUT_DIR / f"{book_name}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        total = sum(len(v["chapters"]) for v in data["volumes"])
        print(f"[OK] {book_name}: {len(data['volumes'])} 卷 {total} 章 -> {out}")


if __name__ == "__main__":
    main()