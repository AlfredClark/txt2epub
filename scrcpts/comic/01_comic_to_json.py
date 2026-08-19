# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  01_comic_to_json.py
@Time    :  2026-08-19 18:10:00
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Scan comic source and write cover/chapters/adjusted numbers to JSON
"""
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from env import COMICS, COMIC_SOURCE_DIR, IMAGE_EXTENSIONS, OUTPUT_DIR

PAGE_STEM_RE = re.compile(r"^[0-9]+$")

EXTS = tuple(ext.lower() for ext in IMAGE_EXTENSIONS)


def is_image(path: Path) -> bool:
    return path.suffix.lower() in EXTS


def parse_number(name: str) -> Decimal | None:
    try:
        return Decimal(name)
    except InvalidOperation:
        return None


def find_cover_file(book_dir: Path, comic: dict) -> str:
    """封面文件名（env cover 字段优先，缺省探测 cover.*）；无封面返回空串"""
    configured = (comic.get("cover") or "").strip()
    if configured:
        return configured if (book_dir / configured).is_file() else ""
    auto = sorted(
        p for p in book_dir.iterdir()
        if p.is_file() and p.stem.lower() == "cover" and is_image(p)
    )
    return auto[0].name if auto else ""


def collect_pages(directory: Path) -> list[tuple[int, str]]:
    """按原始数字值排序的 (页码, 文件名) 列表；非数字图片跳过并提示"""
    pages: list[tuple[int, str]] = []
    for f in directory.iterdir():
        if not f.is_file() or not is_image(f):
            continue
        if PAGE_STEM_RE.match(f.stem):
            pages.append((int(f.stem), f.name))
        else:
            print(f"    [WARN] 跳过非数字图片: {f.name}")
    return sorted(pages, key=lambda item: item[0])


def build_flat_chapters(book_dir: Path, cover_file: str) -> list[dict]:
    pages = [
        {"order": idx, "file": name}
        for idx, (_, name) in enumerate(
            (p for p in collect_pages(book_dir) if p[1] != cover_file),
            start=1,
        )
    ]
    if not pages:
        print("    [WARN] 根目录无图片")
    return [{"order": 1, "source": None, "pages": pages}]


def build_chaptered_chapters(book_dir: Path) -> list[dict]:
    subdirs: list[tuple[Decimal, Path]] = []
    for d in book_dir.iterdir():
        if not d.is_dir():
            continue
        num = parse_number(d.name)
        if num is None:
            print(f"    [WARN] 跳过非数字章目录: {d.name}")
        else:
            subdirs.append((num, d))

    chapters: list[dict] = []
    for adjusted, (_, d) in enumerate(sorted(subdirs, key=lambda item: item[0]), start=1):
        pages = [{"order": idx, "file": name} for idx, (_, name) in enumerate(collect_pages(d), start=1)]
        if not pages:
            print(f"    [WARN] 章节 {d.name} 无图片")
        chapters.append({"order": adjusted, "source": d.name, "pages": pages})
    return chapters


def renumber_pages_globally(chapters: list[dict]) -> None:
    """页码全书全局连续 1..N（按章顺序与章内页码顺序）"""
    counter = 1
    for chapter in chapters:
        for page in chapter["pages"]:
            page["order"] = counter
            counter += 1


def build_json(comic: dict) -> tuple[dict, str, int]:
    book_dir = COMIC_SOURCE_DIR / comic["name"]
    cover_file = find_cover_file(book_dir, comic)

    subdirs = [p for p in book_dir.iterdir() if p.is_dir()]
    if subdirs:
        chapters = build_chaptered_chapters(book_dir)
        structure = "chaptered"
    else:
        chapters = build_flat_chapters(book_dir, cover_file)
        structure = "flat"

    renumber_pages_globally(chapters)
    total_pages = sum(len(ch["pages"]) for ch in chapters)

    return {
        "title": comic["name"],
        "author": comic.get("author", ""),
        "tags": comic.get("tags", []),
        "description": comic.get("description", []),
        "cover": cover_file,
        "structure": structure,
        "chapters": chapters,
    }, structure, total_pages


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for comic in COMICS:
        name = comic["name"]
        book_dir = COMIC_SOURCE_DIR / name
        if not book_dir.is_dir():
            print(f"[SKIP] 未找到源目录: {book_dir}")
            continue
        data, structure, total_pages = build_json(comic)
        out = OUTPUT_DIR / f"{name}.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        chapter_note = f"{len(data['chapters'])} 章 " if structure == "chaptered" else ""
        print(f"[OK] {name}: {structure} {chapter_note}{total_pages} 页 -> {out}")


if __name__ == "__main__":
    main()
