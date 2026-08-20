# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  02_clean_json.py
@Time    :  2026-08-19 11:41:51
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Clean JSON
"""
import json
import re

from env import BOOKS, DROP_LINE_PATTERNS, OUTPUT_DIR, STRIP_PATTERNS

DROP_LINE_RULES = [re.compile(p) for p in DROP_LINE_PATTERNS]
STRIP_RULES = [re.compile(p) for p in STRIP_PATTERNS]


def clean_paragraph(para: str) -> str | None:
    if any(rule.match(para) for rule in DROP_LINE_RULES):
        return None
    cleaned: str = para
    for rule in STRIP_RULES:
        subbed = rule.sub("", cleaned)
        if isinstance(subbed, str):
            cleaned = subbed
    cleaned = cleaned.strip()
    return cleaned or None


def clean_book(data: dict) -> tuple[int, int, list[str], list[tuple[str, str]]]:
    removed_count = 0
    stripped_count = 0
    removed_list: list[str] = []
    stripped_list: list[tuple[str, str]] = []
    for volume in data.get("volumes", []):
        cleaned_intro: list[str] = []
        for para in volume.get("intro", []):
            result = clean_paragraph(para)
            if result is None:
                removed_count += 1
                removed_list.append(para)
                continue
            cleaned_intro.append(result)
            if result != para:
                stripped_count += 1
                stripped_list.append((para, result))
        if "intro" in volume:
            volume["intro"] = cleaned_intro
        for chapter in volume.get("chapters", []):
            cleaned: list[str] = []
            for para in chapter["contents"]:
                result = clean_paragraph(para)
                if result is None:
                    removed_count += 1
                    removed_list.append(para)
                    continue
                cleaned_para: str = result
                cleaned.append(cleaned_para)
                if cleaned_para != para:
                    stripped_count += 1
                    stripped_list.append((para, cleaned_para))
            chapter["contents"] = cleaned
    return removed_count, stripped_count, removed_list, stripped_list


def main():
    for book_name in BOOKS:
        path = OUTPUT_DIR / f"{book_name}.json"
        if not path.exists():
            print(f"[SKIP] 未找到 JSON: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        removed, stripped, removed_list, stripped_list = clean_book(data)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[OK] {book_name}: 删除 {removed} 段, 剥离 {stripped} 段")
        if removed_list:
            print("  删除内容:")
            for text in removed_list:
                print(f"    - {text}")
        if stripped_list:
            print("  剥离内容:")
            for original, result in stripped_list:
                print(f"    - {original}  =>  {result}")


if __name__ == "__main__":
    main()