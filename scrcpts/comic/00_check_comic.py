# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  00_check_comic.py
@Time    :  2026-08-19 17:30:00
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Check comic source structure and file numbering
"""
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from env import COMICS, COMIC_SOURCE_DIR, IMAGE_EXTENSIONS

PAGE_STEM_RE = re.compile(r"^[0-9]+$")

EXTS = tuple(ext.lower() for ext in IMAGE_EXTENSIONS)


def is_image(path: Path) -> bool:
    return path.suffix.lower() in EXTS


def resolve_cover(book_dir: Path, comic: dict) -> tuple[Path | None, list[str]]:
    """返回 (封面文件或 None, 检查信息行)。优先 env.COMICS 的 cover 字段，缺省自动探测 cover.*"""
    lines: list[str] = []
    configured = (comic.get("cover") or "").strip()
    if configured:
        cover = book_dir / configured
        if not cover.is_file():
            lines.append(f"  [ERROR] 配置的封面不存在: {configured}")
            return None, lines
        if not is_image(cover):
            lines.append(f"  [ERROR] 配置的封面不是图片: {configured}")
            return None, lines
        lines.append(f"  [OK] 封面(env): {configured}")
        return cover, lines

    auto = [
        p
        for p in book_dir.iterdir()
        if p.is_file() and p.stem.lower() == "cover" and is_image(p)
    ]
    if not auto:
        lines.append("  [WARN] 封面缺失（cover.<ext> 未找到，将使用文本封面）")
        return None, lines
    if len(auto) > 1:
        lines.append(f"  [WARN] 存在多个封面文件: {'/'.join(p.name for p in auto)}（将使用 {auto[0].name}）")
    else:
        lines.append(f"  [OK] 封面: {auto[0].name}")
    return auto[0], lines


def parse_number(name: str) -> Decimal | None:
    try:
        return Decimal(name)
    except InvalidOperation:
        return None


def check_page_set(files: list[Path], lines: list[str], context: str, first: bool) -> None:
    images = [f for f in files if is_image(f)]
    for f in files:
        if not is_image(f):
            lines.append(f"  [WARN] {context} 非图片文件将被忽略: {f.name}")

    if not images:
        lines.append(f"  [ERROR] {context} 无图片")
        return

    numbers: list[int] = []
    bad: list[Path] = []
    for img in images:
        if PAGE_STEM_RE.match(img.stem):
            numbers.append(int(img.stem))
        else:
            bad.append(img)
    if bad:
        lines.append(
            f"  [ERROR] {context} 图片文件名非数字，无法确定顺序: {'/'.join(p.name for p in bad)}"
        )
    if not numbers:
        return

    min_n, max_n = min(numbers), max(numbers)
    lines.append(f"  [INFO] {context} 页面范围: {min_n:03d}~{max_n:03d}（共 {len(numbers)} 页）")

    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        lines.append(f"  [ERROR] {context} 页码重复: {'/'.join(str(n) for n in duplicates)}")
    else:
        lines.append(f"  [OK] {context} 页码无重复")

    if numbers != sorted(numbers):
        lines.append(f"  [WARN] {context} 文件系统枚举顺序与编号序不一致（01 步将按编号排序）")
    else:
        lines.append(f"  [OK] {context} 页码顺序正确")

    expected = set(range(min_n, max_n + 1))
    missing = sorted(expected - set(numbers))
    if missing:
        lines.append(f"  [WARN] {context} 页码缺号: {'/'.join(str(n) for n in missing)}")
    if first and min_n != 1:
        lines.append(f"  [WARN] {context} 页码从 {min_n:03d} 开始（缺 001）")


def check_chapters(subdirs: list[Path], root_files: list[Path], covers: list[Path], lines: list[str]) -> None:
    for p in root_files:
        if p not in covers and is_image(p):
            lines.append(f"  [WARN] 根目录存在非封面图片，将被忽略: {p.name}")
        elif p not in covers:
            lines.append(f"  [WARN] 根目录非图片文件将被忽略: {p.name}")

    parsed: list[tuple[Decimal, Path]] = []
    for d in subdirs:
        num = parse_number(d.name)
        if num is None:
            lines.append(f"  [ERROR] 章目录名非数字: {d.name}")
        else:
            parsed.append((num, d))

    nums = [n for n, _ in parsed]
    duplicates = sorted({str(n) for n in nums if nums.count(n) > 1})
    if duplicates:
        lines.append(f"  [ERROR] 章号重复: {'/'.join(duplicates)}")
    else:
        lines.append("  [OK] 章号无重复")

    if nums != sorted(nums):
        lines.append("  [ERROR] 章顺序非递增")
    else:
        lines.append("  [OK] 章顺序递增")

    if parsed and nums[0] != 1:
        lines.append(f"  [WARN] 章节从 {nums[0]} 开始（缺第 1 章）")

    total_pages = 0
    for i, (num, d) in enumerate(parsed):
        files = sorted(d.iterdir(), key=lambda f: f.name)
        chapter_pages = len([f for f in files if is_image(f)])
        total_pages += chapter_pages
        lines.append(f"  [INFO] 章节 {num}: {d.name}/（{chapter_pages} 页）")
        check_page_set(files, lines, f"章节 {num}", first=(i == 0))
    lines.append(f"  [INFO] 全卷共 {total_pages} 页")


def check_metadata(comic: dict, lines: list[str]) -> None:
    if not comic.get("author"):
        lines.append("  [WARN] 元数据: 作者为空")
    if not comic.get("tags"):
        lines.append("  [WARN] 元数据: 标签为空")
    if not comic.get("description"):
        lines.append("  [WARN] 元数据: 简介为空")


def check_book(comic: dict) -> list[str]:
    lines: list[str] = []
    name = comic["name"]
    if not name:
        return ["  [ERROR] COMICS 条目缺少 name"]

    book_dir = COMIC_SOURCE_DIR / name
    if not book_dir.is_dir():
        return [f"  [ERROR] 目录不存在: {book_dir}"]
    lines.append("  [OK] 目录存在")

    cover, cover_lines = resolve_cover(book_dir, comic)
    lines.extend(cover_lines)
    covers = [cover] if cover is not None else []

    subdirs = sorted([p for p in book_dir.iterdir() if p.is_dir()], key=lambda p: p.name)
    root_files = [p for p in book_dir.iterdir() if p.is_file()]

    if subdirs:
        lines.append(f"  [INFO] 结构: 分章（{len(subdirs)} 个章节目录）")
        check_chapters(subdirs, root_files, covers, lines)
    else:
        lines.append("  [INFO] 结构: 平铺")
        non_cover_files = [p for p in root_files if p not in covers]
        check_page_set(non_cover_files, lines, "根目录", first=True)

    check_metadata(comic, lines)
    return lines


def main() -> int:
    all_ok = True
    for comic in COMICS:
        name = comic["name"]
        print(f"[CHECK] {name}")
        lines = check_book(comic)
        for line in lines:
            print(line)
        if any(line.startswith("  [ERROR]") for line in lines):
            all_ok = False
            print(f"[FAIL] {name}")
        else:
            print(f"[PASS] {name}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
