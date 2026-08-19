# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  00_check_txt.py
@Time    :  2026-08-19 11:16:09
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Check txt
"""
import re
import sys
from pathlib import Path

import cn2an

from env import BOOKS, SOURCE_DIR, TXT_FILE_NAME

_NUMBER = r"[0-9０-９一二三四五六七八九十百千零〇]+"


def _unit_re(unit: str) -> re.Pattern:
    return re.compile(rf"^第\s*{_NUMBER}\s*{unit}")


CHAPTER_RE = _unit_re("章")
VOLUME_RE = _unit_re("卷")

REQUIRED_ATTRS = ("书名", "作者", "标签")
REQUIRED_SECTIONS = ("简介", "正文")


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


def parse_structure(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8-sig").splitlines()

    attrs = {name: "" for name in REQUIRED_ATTRS}
    sections_seen: set[str] = set()
    intro_lines: list[str] = []
    body_lines: list[str] = []
    in_intro = False
    body_started = False

    for line in lines:
        stripped = line.strip()
        if line.startswith("书名："):
            attrs["书名"] = line[len("书名："):].strip()
        elif line.startswith("作者："):
            attrs["作者"] = line[len("作者："):].strip()
        elif line.startswith("标签："):
            attrs["标签"] = line[len("标签："):].strip()
        elif stripped == "简介：":
            sections_seen.add("简介")
            in_intro = True
        elif in_intro:
            if stripped.startswith("正文"):
                sections_seen.add("正文")
                in_intro = False
                body_started = True
            else:
                intro_lines.append(line)
        elif stripped.startswith("正文"):
            sections_seen.add("正文")
            body_started = True
        elif body_started:
            body_lines.append(line)

    volume_orders: list[int] = []
    chapters_by_volume: list[list[int]] = []
    current_bucket: list[int] | None = None

    for line in body_lines:
        if VOLUME_RE.match(line):
            if current_bucket is not None:
                chapters_by_volume.append(current_bucket)
            volume_orders.append(extract_volume_order(line))
            current_bucket = []
        elif CHAPTER_RE.match(line):
            bucket = current_bucket if current_bucket is not None else []
            bucket.append(extract_order(line))
            current_bucket = bucket
    if current_bucket is not None:
        chapters_by_volume.append(current_bucket)

    return {
        "attrs": attrs,
        "sections_seen": sections_seen,
        "description_non_empty": bool([ln.strip() for ln in intro_lines if ln.strip()]),
        "body_non_empty": bool(body_lines),
        "volume_orders": volume_orders,
        "chapters_by_volume": chapters_by_volume,
    }


def _check_sequence(title: str, orders: list[int]) -> list[str]:
    lines: list[str] = []
    expected = set(range(1, max(orders) + 1))
    missing = sorted(expected - set(orders))
    if missing:
        lines.append(f"  [ERROR] {title}编号缺失: {'/'.join(f'第{n}{title}' for n in missing)}")
    else:
        lines.append(f"  [OK] {title}编号无缺失: 第1{title}~第{max(orders)}{title}")

    duplicates = sorted({n for n in orders if orders.count(n) > 1})
    if duplicates:
        lines.append(f"  [ERROR] {title}编号重复: {'/'.join(f'第{n}{title}' for n in duplicates)}")
    else:
        lines.append(f"  [OK] {title}编号无重复")

    if orders != sorted(orders):
        lines.append(f"  [ERROR] {title}顺序错乱（非递增）")
    else:
        lines.append(f"  [OK] {title}顺序递增")
    return lines


def check_book(book_name: str) -> list[str]:
    lines: list[str] = []
    src = SOURCE_DIR / book_name / TXT_FILE_NAME

    if not src.exists():
        return [f"  [ERROR] 文件不存在: {src}"]
    lines.append("  [OK] 文件存在")

    info = parse_structure(src)

    present_attrs = [name for name in REQUIRED_ATTRS if info["attrs"][name]]
    missing_attrs = [name for name in REQUIRED_ATTRS if not info["attrs"][name]]
    missing_sections = [name for name in REQUIRED_SECTIONS if name not in info["sections_seen"]]
    missing_all = missing_attrs + missing_sections
    if missing_all:
        lines.append(f"  [ERROR] 缺少属性: {'/'.join(missing_all)}")
    if present_attrs:
        lines.append(f"  [OK] 属性齐全: {'/'.join(present_attrs)}")

    if info["description_non_empty"]:
        lines.append("  [OK] 简介内容非空")
    else:
        lines.append("  [ERROR] 简介内容为空")

    if info["body_non_empty"]:
        lines.append("  [OK] 正文内容非空")
    else:
        lines.append("  [ERROR] 正文内容为空")

    if info["attrs"]["书名"] and info["attrs"]["书名"] != book_name:
        lines.append(f"  [ERROR] 源文件书名({info['attrs']['书名']})与常量({book_name})不一致")
    elif info["attrs"]["书名"]:
        lines.append("  [OK] 源文件书名与常量一致")

    volume_orders: list[int] = info["volume_orders"]
    chapters_by_volume: list[list[int]] = info["chapters_by_volume"]

    if volume_orders:
        lines.extend(_check_sequence("卷", volume_orders))
        if len(chapters_by_volume) != len(volume_orders):
            lines.append(f"  [ERROR] 卷与章节分组数量不匹配（{len(chapters_by_volume)}组/{len(volume_orders)}卷）")
        for i, bucket in enumerate(chapters_by_volume):
            if not bucket:
                if i < len(volume_orders):
                    lines.append(f"  [ERROR] 第{volume_orders[i]}卷内无章节")
                continue
            lines.extend(_check_sequence("章", bucket))
        total = sum(len(b) for b in chapters_by_volume)
        lines.append(f"  [INFO] 卷范围: 第{min(volume_orders)}卷~第{max(volume_orders)}卷（共{len(volume_orders)}卷{total}章）")
    else:
        flat_orders = chapters_by_volume[0] if chapters_by_volume else []
        if not flat_orders:
            lines.append("  [ERROR] 未检测到任何章节")
        else:
            lines.extend(_check_sequence("章", flat_orders))
            lines.append(f"  [INFO] 章节范围: 第{min(flat_orders)}章~第{max(flat_orders)}章（共{len(flat_orders)}章）")

    return lines


def main() -> int:
    all_ok = True
    for book_name in BOOKS:
        print(f"[CHECK] {book_name}")
        lines = check_book(book_name)
        for line in lines:
            print(line)
        if any(line.startswith("  [ERROR]") for line in lines):
            all_ok = False
            print(f"[FAIL] {book_name}")
        else:
            print(f"[PASS] {book_name}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())