# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  env.py
@Time    :  2026-08-19 16:20:00
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Environment (comic)
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 漫画源结构（两种形式，封面均位于 <书名>/cover.<ext>）：
#   分章: sources/comic/<书名>/<数字章节>/<数字图片>...   （章号支持小数，如 1.5）
#   平铺: sources/comic/<书名>/<数字图片>...
COMIC_SOURCE_DIR = PROJECT_ROOT / "sources" / "comic"
OUTPUT_DIR = PROJECT_ROOT / "temps" / "comic"
BUILD_DIR = PROJECT_ROOT / "outputs" / "comic"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "EPUB33-COMIC"

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

# 漫画清单与元数据（演示样例，替换为实际漫画信息
# name: 书名，对应 sources/comic/name/ 目录
# author / tags / description: 元数据（为空时 00 步会 WARNING 提示）
# cover: 可选，书名目录内的封面文件名（如 "001.jpg"）；缺省自动探测 cover.*
COMICS = [
    {
        "name": "遠い君に、僕は届かない",
        "author": "二峰跨人",
        "tags": ["NTR", "调教", "凌辱", "无修正"],
        "description": ["遠い君に、僕は届かない"],
        "cover": "0000.png",
    },
]

# 卷编号格式: arabic / arabic_padded / chinese_lower / chinese_upper
VOLUME_NUMBER_FORMAT = "arabic"
# 卷标题前缀模板（{number}=格式化编号, {title}=卷名）
VOLUME_TITLE_TEMPLATE = "第{number}卷 {title}"

# 话编号格式: arabic / arabic_padded / chinese_lower / chinese_upper
CHAPTER_NUMBER_FORMAT = "arabic"
# 话标题前缀模板（{number}=格式化编号, {title}=原标题）
CHAPTER_TITLE_TEMPLATE = "第{number}话 {title}"

# 是否在书中显示目录页（False 时仅从 spine 移除目录页，仍保留 EPUB 标准 nav
# 目录文档，阅读器目录解析跳转不受影响）
SHOW_INDEX = False
