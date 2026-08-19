# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  clean_workspace.py
@Time    :  2026-08-19 19:10:00
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Clean sources/temps/outputs, keep novel/comic dirs and empty their contents
@Usage   :  python clean_workspace.py [--dry-run]
"""
import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
TARGETS = ["sources", "temps", "outputs"]
PRESERVED = {"novel", "comic"}


def remove_item(item: Path, dry_run: bool) -> None:
    action = "预览" if dry_run else "删除"
    if item.is_dir():
        if dry_run:
            print(f"  [DRY] {action}目录: {item}")
        else:
            shutil.rmtree(item)
            print(f"  [OK] 已删除目录: {item}")
    else:
        if dry_run:
            print(f"  [DRY] {action}文件: {item}")
        else:
            item.unlink()
            print(f"  [OK] 已删除文件: {item}")


def clear_dir(root: Path, dry_run: bool) -> None:
    if not root.exists():
        print(f"[SKIP] 不存在: {root}")
        return
    for child in root.iterdir():
        if child.is_dir() and child.name in PRESERVED:
            for item in child.iterdir():
                remove_item(item, dry_run)
            if not dry_run:
                print(f"  [OK] 已清空: {child}")
            else:
                print(f"  [DRY] 将清空: {child}")
        else:
            remove_item(child, dry_run)


def main() -> int:
    parser = argparse.ArgumentParser(description="清理 sources/temps/outputs，保留 novel/comic 目录并清空其内容")
    parser.add_argument("--dry-run", action="store_true", help="仅预览将删除的内容，不实际删除")
    args = parser.parse_args()

    for name in TARGETS:
        root = PROJECT_ROOT / name
        print(f"[CLEAN] {name}/")
        clear_dir(root, args.dry_run)
        if root.exists() and not args.dry_run:
            for sub in PRESERVED:
                (root / sub).mkdir(exist_ok=True)
            print("  [OK] 已确保目录存在: novel/ comic/")
    print("完成。" + ("（预览模式，未实际删除）" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())