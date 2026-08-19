# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  02_generate_comic.py
@Time    :  2026-08-19 18:40:00
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Generate EPUB structure from comic JSON and template
"""
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from env import (
    BUILD_DIR,
    CHAPTER_TITLE_TEMPLATE,
    COMICS,
    COMIC_SOURCE_DIR,
    IMAGE_EXTENSIONS,
    IMAGE_MEDIA_TYPES,
    OUTPUT_DIR,
    SHOW_INDEX,
    TEMPLATE_DIR,
)

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+}}")

XHTML_TYPE = "application/xhtml+xml"


def chapter_label(ch: dict) -> str:
    """章节目录名称：优先使用原始章号 source（如 1.5），缺省回退到调整后 order"""
    number = (ch.get("source") or "").strip() or str(ch["order"])
    return CHAPTER_TITLE_TEMPLATE.format(number=number, title="").strip()


def render_text(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(0)[2:-2]
        value = values.get(key)
        return value if value is not None else match.group(0)

    return PLACEHOLDER_RE.sub(replace, template)


def find_cover_info(book_dir: Path, comic: dict) -> tuple[str, str, Path] | None:
    """返回 (images 内目标文件名, media_type, 源路径)；无封面返回 None。env cover 字段优先。"""
    configured = (comic.get("cover") or "").strip()
    if configured:
        p = book_dir / configured
        if p.is_file():
            ext = p.suffix.lower()
            return f"cover{ext}", IMAGE_MEDIA_TYPES[ext], p
        return None
    auto = [
        p
        for p in book_dir.iterdir()
        if p.is_file() and p.stem.lower() == "cover" and p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not auto:
        return None
    p = auto[0]
    ext = p.suffix.lower()
    return f"cover{ext}", IMAGE_MEDIA_TYPES[ext], p


def build_page_xhtml(template: str, title: str, alt: str, file_name: str) -> str:
    return render_text(
        template,
        {"PAGE_TITLE": escape(title), "PAGE_ALT": escape(alt), "PAGE_FILE": file_name},
    )


def build_opf(
    template: str,
    values: dict,
    manifest_entries: list[tuple[str, str, str]],
    spine_ids: list[str],
    has_cover: bool,
    show_index: bool,
) -> str:
    manifest_items = "\n".join(
        f'    <item id="{cid}" href="{href}" media-type="{mtype}"/>'
        for cid, href, mtype in manifest_entries
    )
    spine_items = "\n".join(f'    <itemref idref="{cid}"/>' for cid in spine_ids)
    return render_text(
        template,
        {
            **values,
            "MANIFEST_ITEMS": manifest_items,
            "SPINE_ITEMS": spine_items,
            "NAV_ITEMREF": '    <itemref idref="nav"/>' if show_index else "",
            "COVER_ITEM": (
                f'    <item id="cover-image" href="images/{values["COVER_FILE"]}" '
                f'media-type="{values["COVER_MEDIA_TYPE"]}" properties="cover-image"/>'
                if has_cover
                else ""
            ),
        },
    )


def build_book(comic: dict) -> None:
    book_name = comic["name"]
    json_path = OUTPUT_DIR / f"{book_name}.json"
    if not json_path.exists():
        print(f"[SKIP] 未找到 JSON: {json_path}")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    build_dir = BUILD_DIR / book_name
    if build_dir.exists():
        shutil.rmtree(build_dir)
    (build_dir / "META-INF").mkdir(parents=True)
    (build_dir / "EPUB" / "text").mkdir(parents=True)
    (build_dir / "EPUB" / "images").mkdir(parents=True)
    (build_dir / "EPUB" / "styles").mkdir(parents=True)

    shutil.copy(TEMPLATE_DIR / "mimetype", build_dir / "mimetype")
    shutil.copy(TEMPLATE_DIR / "META-INF" / "container.xml", build_dir / "META-INF" / "container.xml")
    shutil.copy(TEMPLATE_DIR / "EPUB" / "styles" / "base.css", build_dir / "EPUB" / "styles" / "base.css")

    book_dir = COMIC_SOURCE_DIR / book_name
    cover_info = find_cover_info(book_dir, comic)
    if cover_info is not None:
        cover_file, cover_mtype, cover_path = cover_info
        has_cover = True
        shutil.copy(cover_path, build_dir / "EPUB" / "images" / cover_file)
    else:
        cover_file, cover_mtype, has_cover = "", "", False

    values = {
        "BOOK_UUID": str(uuid.uuid4()),
        "BOOK_MODIFIED": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "BOOK_TITLE": escape(data["title"]),
        "BOOK_AUTHOR": escape(data["author"]),
        "BOOK_DESCRIPTION": "&#10;".join(escape(line) for line in data["description"]),
        "BOOK_SUBJECTS": "\n".join(f"    <dc:subject>{escape(tag)}</dc:subject>" for tag in data["tags"]),
        "COVER_FILE": cover_file,
        "COVER_MEDIA_TYPE": cover_mtype,
    }

    chapters = data["chapters"]
    structure = data.get("structure", "chaptered")
    multi = structure == "chaptered"
    total_pages = sum(len(ch["pages"]) for ch in chapters)

    page_template = (TEMPLATE_DIR / "EPUB" / "text" / "page-template.xhtml").read_text(encoding="utf-8")

    manifest_entries: list[tuple[str, str, str]] = []
    spine_ids: list[str] = []

    for ch in chapters:
        src_dir = book_dir / ch["source"] if ch["source"] else book_dir
        for page in ch["pages"]:
            porder = page["order"]
            src = src_dir / page["file"]
            ext = src.suffix.lower()
            image_name = f"page-{porder:04d}{ext}"
            if src.exists():
                shutil.copy(src, build_dir / "EPUB" / "images" / image_name)
            else:
                print(f"    [WARN] 源图片缺失: {src}")

            phref = f"text/page-{porder:04d}.xhtml"
            title = f"第{porder}页"
            alt = f"{data['title']} 第{porder}页"
            xhtml = build_page_xhtml(page_template, title, alt, image_name)
            (build_dir / "EPUB" / "text" / f"page-{porder:04d}.xhtml").write_text(xhtml, encoding="utf-8")

            manifest_entries.append((f"pg{porder:04d}", phref, XHTML_TYPE))
            manifest_entries.append((f"img{porder:04d}", f"images/{image_name}", IMAGE_MEDIA_TYPES.get(ext, "image/jpeg")))
            spine_ids.append(f"pg{porder:04d}")

    nav_template = (TEMPLATE_DIR / "EPUB" / "nav.xhtml").read_text(encoding="utf-8")
    toc_items: list[str] = []
    if multi:
        toc_items = [
            f'      <li><a href="text/page-{ch["pages"][0]["order"]:04d}.xhtml">{escape(chapter_label(ch))}</a></li>'
            for ch in chapters if ch["pages"]
        ]
    toc_list = "\n".join(toc_items)
    first_page: int | None = None
    if chapters and chapters[0]["pages"]:
        first_page = int(chapters[0]["pages"][0]["order"])
    first_href = "cover.xhtml"
    if first_page is not None:
        first_href = f"text/page-{first_page:04d}.xhtml"
    landmarks = '      <li><a epub:type="cover" href="cover.xhtml">封面</a></li>'
    if SHOW_INDEX:
        landmarks += '\n      <li><a epub:type="toc" href="nav.xhtml#toc">目录</a></li>'
    landmarks += f'\n      <li><a epub:type="bodymatter" href="{first_href}">开始阅读</a></li>'
    nav_html = render_text(nav_template, {"CHAPTER_TOC_LIST": toc_list, "LANDMARKS_LIST": landmarks})
    (build_dir / "EPUB" / "nav.xhtml").write_text(nav_html, encoding="utf-8")

    cover_template = (TEMPLATE_DIR / "EPUB" / "cover.xhtml").read_text(encoding="utf-8")
    cover_block = (
        f'    <img src="images/{values["COVER_FILE"]}" alt="{values["BOOK_TITLE"]}"/>'
        if has_cover
        else f'    <p class="book-title">{values["BOOK_TITLE"]}</p>'
    )
    cover_html = render_text(cover_template, {**values, "COVER_BLOCK": cover_block})
    (build_dir / "EPUB" / "cover.xhtml").write_text(cover_html, encoding="utf-8")

    opf_template = (TEMPLATE_DIR / "EPUB" / "content.opf").read_text(encoding="utf-8")
    opf = build_opf(opf_template, values, manifest_entries, spine_ids, has_cover, SHOW_INDEX)
    (build_dir / "EPUB" / "content.opf").write_text(opf, encoding="utf-8")

    cover_note = f" 封面={cover_file}" if has_cover else " 封面=缺失(文本封面)"
    chapter_note = f"{len(chapters)} 章 " if multi else ""
    print(f"[OK] {book_name}: {structure} {chapter_note}{total_pages} 页 -> {build_dir}{cover_note}")


def main() -> None:
    for comic in COMICS:
        build_book(comic)


if __name__ == "__main__":
    main()