# !/usr/bin/python
# -*- coding: utf-8 -*-
"""
@File    :  env.py
@Time    :  2026-08-19 10:48:26
@Author  :  Alfred Clark
@Contact :  alfredclark@163.com
@Desc    :  Environment
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 源结构: sources/novel/<书名>/正文.txt + 封面.<ext>
SOURCE_DIR = PROJECT_ROOT / "sources" / "novel"
TXT_FILE_NAME = "正文.txt"
COVER_FILE_STEM = "封面"

OUTPUT_DIR = PROJECT_ROOT / "temps" / "novel"
BUILD_DIR = PROJECT_ROOT / "outputs" / "novel"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "EPUB33-NOVEL"

COVER_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
COVER_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}

# 书名清单：脚本依此在 sources/novel/<书名>/ 查找 正文.txt 与 封面.<ext>
# 演示样例（替换为实际书名，例如：
#   BOOKS = ["绝世武神", "异世邪君"])
BOOKS = [
    "阿里布达年代记",
]

# 广告/作者注清理规则（02_clean_json.py 使用）
DROP_LINE_PATTERNS = [
    r"^\s*[（(]\s*[pP][sS]\s*[:：].*",  # （PS：...） 独占一行 → 整行删除
    r"^\s*[pP][sS]\s*[:：].*",  # PS：... 无括号变体 → 整行删除
    r"^\s*(?:https?://|www\.)\S+.*$",  # 以网址开头的行（http/https/www.）→ 整行删除
    r".*www\.[a-zA-Z0-9-]+\.(?:com|net|cn|org|cc|me|top|xyz|vip|site|club|info|biz|online|fun|live|icu|red|app|io|co)\b.*",
    # 行内含 www 域名 → 整行删除
    r".*https?://\S+.*$",  # 行内含 http(s):// → 整行删除
]
STRIP_PATTERNS = [
    r"[（(]\s*[pP][sS]\s*[:：].*?[）)]",  # 行内（PS：...）→ 剥离子串，保留正文
]

# 卷编号格式: arabic / arabic_padded / chinese_lower / chinese_upper
VOLUME_NUMBER_FORMAT = "chinese_lower"
# 卷标题前缀模板（{number}=格式化编号, {title}=卷名）
VOLUME_TITLE_TEMPLATE = "第{number}卷 {title}"

# 章节编号格式: arabic / arabic_padded / chinese_lower / chinese_upper
CHAPTER_NUMBER_FORMAT = "arabic_padded"
# 章节标题前缀模板（{number}=格式化编号, {title}=原标题）
CHAPTER_TITLE_TEMPLATE = "第{number}章 {title}"

# 章节序号缺失/错误时，自动按文档顺序重新编号（不使用源文件的错误编号）
RENUMBER_CHAPTERS = True

# 分卷是否重新章节计数（True：每卷章节从第 1 章重新开始；False：全书章节连续编号）
# 仅在 RENUMBER_CHAPTERS=True 时生效（False 时保持源编号）
VOLUME_RESTART_CHAPTERS = True

# 是否在书中显示目录页（False 时仅从 spine 移除目录页，仍保留 EPUB 标准 nav
# 目录文档，阅读器目录解析跳转不受影响）
SHOW_INDEX = False
