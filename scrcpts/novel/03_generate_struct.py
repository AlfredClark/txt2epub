# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  03_generate_struct.py
@Time    :  2026-08-19 12:01:41
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Generate EPUB directory structure from JSON
"""
import json
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import cn2an

from env import (
    BOOKS,
    BUILD_DIR,
    CHAPTER_NUMBER_FORMAT,
    CHAPTER_TITLE_TEMPLATE,
    COVER_EXTENSIONS,
    COVER_FILE_STEM,
    COVER_MEDIA_TYPES,
    OUTPUT_DIR,
    SHOW_INDEX,
    SOURCE_DIR,
    TEMPLATE_DIR,
    VOLUME_NUMBER_FORMAT,
    VOLUME_TITLE_TEMPLATE,
)

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+}}")


def _format_number(order: int, pad_width: int, fmt: str) -> str:
    if fmt == "arabic":
        return str(order)
    if fmt == "arabic_padded":
        return str(order).zfill(pad_width)
    if fmt == "chinese_lower":
        return cn2an.an2cn(order, "low")
    if fmt == "chinese_upper":
        return cn2an.an2cn(order, "up")
    return str(order)


def format_chapter_number(order: int, pad_width: int) -> str:
    return _format_number(order, pad_width, CHAPTER_NUMBER_FORMAT)


def format_volume_number(order: int, pad_width: int) -> str:
    return _format_number(order, pad_width, VOLUME_NUMBER_FORMAT)


def numbered_title(order: int, title: str, pad_width: int) -> str:
    return CHAPTER_TITLE_TEMPLATE.format(number=format_chapter_number(order, pad_width), title=title)


def volume_title(order: int, title: str, pad_width: int) -> str:
    return VOLUME_TITLE_TEMPLATE.format(number=format_volume_number(order, pad_width), title=title)


def render_text(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        key = match.group(0)[2:-2]
        value = values.get(key)
        return value if value is not None else match.group(0)

    return PLACEHOLDER_RE.sub(replace, template)


def find_cover(book_name: str) -> tuple[str, str, Path] | None:
    for ext in COVER_EXTENSIONS:
        cover = SOURCE_DIR / book_name / f"{COVER_FILE_STEM}{ext}"
        if cover.exists():
            return f"cover{ext}", COVER_MEDIA_TYPES[ext], cover
    return None


def chapter_file_name(volume_order: int, chapter_order: int, multi_volume: bool) -> str:
    if multi_volume:
        return f"chapter-{volume_order:03d}-{chapter_order:04d}.xhtml"
    return f"chapter-{chapter_order:04d}.xhtml"


def volume_file_name(volume_order: int) -> str:
    return f"volume-{volume_order:03d}.xhtml"


def build_chapter_xhtml(template: str, title: str, contents: list[str]) -> str:
    body = "\n".join(f"    <p>{escape(para)}</p>" for para in contents)
    return render_text(template, {"CHAPTER_TITLE": escape(title), "CHAPTER_BODY": body})


def build_nav(
    volumes: list[dict],
    hrefs: list[list[str]],
    pad_width: int,
    vol_pad_width: int,
    volume_hrefs: list[str] | None = None,
) -> tuple[str, str]:
    toc_items: list[str] = []
    if len(volumes) > 1:
        for i, (volume, chapter_hrefs) in enumerate(zip(volumes, hrefs)):
            chapter_lis = "\n".join(
                f"        <li><a href=\"text/{escape(href)}\">{escape(numbered_title(chapter['order'], chapter['title'], pad_width))}</a></li>"
                for href, chapter in zip(chapter_hrefs, volume["chapters"])
            )
            vol_title = escape(volume_title(volume["order"], volume["title"], vol_pad_width))
            if volume_hrefs is not None:
                vol_href = f"text/{escape(volume_hrefs[i])}"
                volume_label = f"<a href=\"{vol_href}\">{vol_title}</a>"
            else:
                volume_label = vol_title
            toc_items.append(
                f"      <li>{volume_label}\n"
                f"        <ol>\n{chapter_lis}\n        </ol>\n"
                f"      </li>"
            )
    else:
        for href, chapter in zip(hrefs[0], volumes[0]["chapters"]):
            toc_items.append(
                f"      <li><a href=\"text/{escape(href)}\">{escape(numbered_title(chapter['order'], chapter['title'], pad_width))}</a></li>"
            )

    toc_list = "\n".join(toc_items)
    first_href = hrefs[0][0]
    landmarks = f"      <li><a epub:type=\"bodymatter\" href=\"text/{escape(first_href)}\">开始阅读</a></li>"
    return toc_list, landmarks


def build_opf(
    template: str,
    values: dict,
    manifest_entries: list[tuple[str, str]],
    spine_ids: list[str],
    has_cover: bool,
    show_index: bool,
) -> str:
    manifest_items = "\n".join(
        f'    <item id="{cid}" href="text/{href}" media-type="application/xhtml+xml"/>'
        for cid, href in manifest_entries
    )
    spine_items = "\n".join(f'    <itemref idref="{cid}"/>' for cid in spine_ids)

    rendered = render_text(
        template,
        {
            **values,
            "MANIFEST_ITEMS": manifest_items,
            "SPINE_ITEMS": spine_items,
            "NAV_ITEMREF": '    <itemref idref="nav"/>' if show_index else "",
            "COVER_ITEM": (
                f'    <item id="cover-image" href="images/{values["COVER_FILE"]}" media-type="{values["COVER_MEDIA_TYPE"]}" properties="cover-image"/>'
                if has_cover
                else ""
            ),
        },
    )
    return rendered


def build_cover(template: str, values: dict, has_cover: bool) -> str:
    cover_block = (
        f'    <img src="images/{values["COVER_FILE"]}" alt="{values["BOOK_TITLE"]}"/>'
        if has_cover
        else f'    <p class="book-title">{values["BOOK_TITLE"]}</p>'
    )
    return render_text(template, {**values, "COVER_BLOCK": cover_block})


def build_book(book_name: str) -> None:
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

    cover_info = find_cover(book_name)
    if cover_info is not None:
        cover_file, cover_media_type, cover_path = cover_info
        has_cover = True
        shutil.copy(cover_path, build_dir / "EPUB" / "images" / cover_file)
    else:
        cover_file = ""
        cover_media_type = ""
        has_cover = False

    values = {
        "BOOK_UUID": str(uuid.uuid4()),
        "BOOK_MODIFIED": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "BOOK_TITLE": escape(data["title"]),
        "BOOK_AUTHOR": escape(data["author"]),
        "BOOK_DESCRIPTION": "&#10;".join(escape(line) for line in data["description"]),
        "BOOK_DESCRIPTION_BLOCK": (
            f'    <p class="book-description">'
            + "".join(f'<span class="desc-line">{escape(line)}</span>' for line in data["description"])
            + "</p>"
        ),
        "BOOK_SUBJECTS": "\n".join(f"    <dc:subject>{escape(tag)}</dc:subject>" for tag in data["tags"]),
        "COVER_FILE": cover_file,
        "COVER_MEDIA_TYPE": cover_media_type,
    }

    volumes = data["volumes"]
    multi_volume = len(volumes) > 1
    max_order = max((ch["order"] for v in volumes for ch in v["chapters"]), default=0)
    pad_width = len(str(max_order))
    vol_max = max((v["order"] for v in volumes), default=0)
    vol_pad_width = len(str(vol_max))

    chapter_template = (TEMPLATE_DIR / "EPUB" / "text" / "chapter-template.xhtml").read_text(encoding="utf-8")
    volume_template = (TEMPLATE_DIR / "EPUB" / "text" / "volume-template.xhtml").read_text(encoding="utf-8")

    chapter_hrefs: list[list[str]] = []
    flat_chapter_hrefs: list[str] = []
    volume_hrefs: list[str] = []
    manifest_entries: list[tuple[str, str]] = []
    spine_ids: list[str] = []

    for volume in volumes:
        if multi_volume:
            vhref = volume_file_name(volume["order"])
            vid = f"vol{volume['order']:03d}"
            volume_hrefs.append(vhref)
            vtitle = volume_title(volume["order"], volume["title"], vol_pad_width)
            vxhtml = render_text(volume_template, {"VOLUME_TITLE": escape(vtitle)})
            (build_dir / "EPUB" / "text" / vhref).write_text(vxhtml, encoding="utf-8")
            manifest_entries.append((vid, vhref))
            spine_ids.append(vid)
        volume_hrefs_group: list[str] = []
        for chapter in volume["chapters"]:
            href = chapter_file_name(volume["order"], chapter["order"], multi_volume)
            cid = f"ch{volume['order']:03d}c{chapter['order']:04d}" if multi_volume else f"ch{chapter['order']:04d}"
            volume_hrefs_group.append(href)
            flat_chapter_hrefs.append(href)
            title = numbered_title(chapter["order"], chapter["title"], pad_width)
            xhtml = build_chapter_xhtml(chapter_template, title, chapter["contents"])
            (build_dir / "EPUB" / "text" / href).write_text(xhtml, encoding="utf-8")
            manifest_entries.append((cid, href))
            spine_ids.append(cid)
        chapter_hrefs.append(volume_hrefs_group)

    nav_template = (TEMPLATE_DIR / "EPUB" / "nav.xhtml").read_text(encoding="utf-8")
    toc_list, landmarks = build_nav(
        volumes, chapter_hrefs, pad_width, vol_pad_width, volume_hrefs if multi_volume else None
    )
    landmark_items = '      <li><a epub:type="cover" href="cover.xhtml">封面</a></li>'
    if SHOW_INDEX:
        landmark_items += '\n      <li><a epub:type="toc" href="nav.xhtml#toc">目录</a></li>'
    landmark_items += f"\n{landmarks}"
    nav_html = render_text(
        nav_template,
        {
            "CHAPTER_TOC_LIST": toc_list,
            "LANDMARKS_LIST": landmark_items,
        },
    )
    (build_dir / "EPUB" / "nav.xhtml").write_text(nav_html, encoding="utf-8")

    cover_template = (TEMPLATE_DIR / "EPUB" / "cover.xhtml").read_text(encoding="utf-8")
    cover_html = build_cover(cover_template, values, has_cover)
    (build_dir / "EPUB" / "cover.xhtml").write_text(cover_html, encoding="utf-8")

    titlepage_template = (TEMPLATE_DIR / "EPUB" / "titlepage.xhtml").read_text(encoding="utf-8")
    titlepage_html = render_text(titlepage_template, values)
    (build_dir / "EPUB" / "titlepage.xhtml").write_text(titlepage_html, encoding="utf-8")

    opf_template = (TEMPLATE_DIR / "EPUB" / "content.opf").read_text(encoding="utf-8")
    opf = build_opf(opf_template, values, manifest_entries, spine_ids, has_cover, SHOW_INDEX)
    (build_dir / "EPUB" / "content.opf").write_text(opf, encoding="utf-8")

    total = len(flat_chapter_hrefs)
    cover_note = f" 封面={cover_file}" if has_cover else " 封面=缺失(文本封面)"
    print(f"[OK] {book_name}: {len(volumes)} 卷 {total} 章 -> {build_dir}{cover_note}")


def main():
    for book_name in BOOKS:
        build_book(book_name)


if __name__ == "__main__":
    main()