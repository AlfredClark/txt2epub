# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  04_build_epub.py
@Time    :  2026-08-19 12:52:12
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Build EPUB and validate with epubcheck
"""
import re
import subprocess
import zipfile
from pathlib import Path

from env import BOOKS, BUILD_DIR

MIMETYPE = "application/epub+zip"


def build_epub(build_dir: Path, epub_path: Path) -> None:
    with zipfile.ZipFile(epub_path, "w") as zf:
        zf.write(build_dir / "mimetype", "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(build_dir.rglob("*")):
            if path.is_dir() or path.name == "mimetype":
                continue
            arcname = path.relative_to(build_dir).as_posix()
            zf.write(path, arcname, compress_type=zipfile.ZIP_DEFLATED)


def run_epubcheck(epub_path: Path) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            ["epubcheck", str(epub_path)],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError:
        return -1, "epubcheck 命令不可用"
    except subprocess.TimeoutExpired:
        return -1, "epubcheck 校验超时"
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def count_lines(output: str, kind: str) -> int:
    pattern = re.compile(rf"^\s*{kind}\b", re.MULTILINE)
    return len(pattern.findall(output))


def main() -> int:
    all_ok = True
    for book_name in BOOKS:
        build_dir = BUILD_DIR / book_name
        epub_path = BUILD_DIR / f"{book_name}.epub"
        if not build_dir.exists():
            print(f"[SKIP] 结构目录不存在: {build_dir}")
            continue

        build_epub(build_dir, epub_path)
        size_mb: float = epub_path.stat().st_size / 1024 / 1024

        code, output = run_epubcheck(epub_path)
        errors = count_lines(output, "ERROR")
        warnings = count_lines(output, "WARNING")
        size_note = f"{size_mb:.1f}MB"

        if code == 0:
            print(f"[OK] {book_name} -> {epub_path} ({size_note}) | ERROR {errors}, WARNING {warnings}")
        elif code == -1:
            all_ok = False
            print(f"[WARN] {book_name} -> {epub_path} ({size_note}) | {output}")
        else:
            all_ok = False
            print(f"[FAIL] {book_name} -> {epub_path} ({size_note}) | ERROR {errors}, WARNING {warnings}")
            for line in output.splitlines():
                if re.match(r"^\s*ERROR\b", line):
                    print(f"    {line}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())