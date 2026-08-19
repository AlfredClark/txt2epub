# txt2epub

纯文本 TXT 小说一键转换为带目录与封面的 EPUB。通过 5 个流水线脚本完成「校验 → 解析 → 清洗 → 生成 → 打包校验」，全程可控、可配置。

## 功能特性

- 自动解析头部元数据（书名 / 作者 / 标签 / 简介）与正文章节结构
- 支持分卷小说：每卷生成独立卷头页，目录按卷分组，卷内章节重新编号
- 章节 / 卷编号格式可配置：阿拉伯数字、阿拉伯数字（自动补零）、小写中文、大写中文
- 自动清理广告与作者注：PS 注记、网址广告等，规则集中配置、可扩展
- 自动匹配并嵌入同名封面图，支持 png / jpg / jpeg / webp / gif / bmp
- 基于 EPUB3 模板生成标准封面、扉页、目录（nav）、阅读顺序（spine），并通过 epubcheck 校验

## 环境要求

- Python 3.12+
- 依赖：[cn2an](https://pypi.org/project/cn2an/)
- epubcheck（第 04 步校验用，需 Java 运行时）

## 安装

```bash
uv pip install cn2an --python .venv/bin/python
```

## 目录结构

```
txt2epub/
├── scrcpts/                     # 流水线脚本与配置
│   ├── novel/                   # 小说转换脚本
│   │   ├── env.py               # 全局配置（书名、路径、清理规则、编号格式）
│   │   ├── 00_check_txt.py      # 1. 校验源 TXT 格式
│   │   ├── 01_split_txt_to_json.py  # 2. TXT → JSON
│   │   ├── 02_clean_json.py     # 3. 清理广告 / 作者注
│   │   ├── 03_generate_struct.py    # 4. 生成 EPUB 目录结构
│   │   └── 04_build_epub.py     # 5. 打包 .epub 并 epubcheck 校验
│   └── comic/                   # 漫画转换脚本（流水线规划中）
│       └── env.py               # 漫画清单与元数据、路径、编号格式配置
├── sources/
│   ├── novel/                   # 小说源目录：<书名>/正文.txt + 封面.<图片后缀>
│   └── comic/                   # 漫画源（书名/第X卷（可选）/第X话/图片…）
├── temps/
│   └── novel/                   # 小说中间 JSON（脚本自动生成，已忽略）
├── outputs/
│   └── novel/                   # 小说生成的 EPUB 目录结构与 .epub 产物（已忽略）
├── templates/
│   ├── EPUB33-NOVEL/            # EPUB3 小说模板
│   │   ├── mimetype
│   │   ├── META-INF/container.xml
│   │   └── EPUB/
│   │       ├── content.opf      # 包描述（元数据 + manifest + spine）
│   │       ├── cover.xhtml      # 封面页
│   │       ├── titlepage.xhtml  # 扉页
│   │       ├── nav.xhtml        # 目录
│   │       ├── styles/base.css  # 样式
│   │       └── text/
│   │           ├── chapter-template.xhtml  # 章节页模板
│   │           └── volume-template.xhtml   # 分卷页模板
│   └── EPUB33-COMIC/            # EPUB3 漫画模板（无扉页、无章节标题页）
│       ├── mimetype
│       ├── META-INF/container.xml
│       └── EPUB/
│           ├── content.opf      # 包描述（纯视觉访问模式 + LTR 阅读方向）
│           ├── cover.xhtml      # 封面页
│           ├── nav.xhtml        # 目录（仅列章节，链接到各章第一页）
│           ├── styles/base.css  # 样式（单图满页不裁剪）
│           └── text/
│               └── page-template.xhtml  # 单图页模板
└── pyproject.toml
```

## 源文件格式

每本书一个目录：`sources/novel/<书名>/`，内含 `正文.txt` 与封面图 `封面.<ext>`。`正文.txt` 需满足以下结构（`00` 步会逐项校验）：

```
书名：书名
作者：作者名
标签：标签一/标签二

简介：
简介内容……

正文：

第一章 章节标题
正文段落……
```

- **属性行**：`书名：`、`作者：`、`标签：`（标签可用 `/` 分隔多个）
- **区段**：`简介：`、`正文：`
- **章节标题**：`第X章 标题`，X 支持中文数字（一、二…）、阿拉伯数字（1、0001 等）
- **分卷标题**（可选）：`第X卷 卷名`，卷内章节编号从第 1 章重新开始
- **封面**：在 `sources/novel/<书名>/` 中放置 `封面.<ext>`（支持 png / jpg / jpeg / webp / gif / bmp），脚本会自动找到并嵌入

## 使用流程

按顺序执行 00 → 04：

```bash
# 1. 校验源 TXT 格式（属性齐全、简介/正文非空、章节/卷编号连续）
uv run python scrcpts/novel/00_check_txt.py

# 2. 按 env.BOOKS 逐书解析，生成 temps/novel/书名.json
uv run python scrcpts/novel/01_split_txt_to_json.py

# 3. 清理广告与作者注（按 env 中的规则，原位覆写）
uv run python scrcpts/novel/02_clean_json.py

# 4. 基于 EPUB33-NOVEL 模板生成 outputs/novel/书名/ 目录结构
uv run python scrcpts/novel/03_generate_struct.py

# 5. 打包为 outputs/novel/书名.epub 并调用 epubcheck 校验
uv run python scrcpts/novel/04_build_epub.py
```

各步说明：

| 步骤 | 脚本 | 输入 → 输出 | 说明 |
| --- | --- | --- | --- |
| 00 | `novel/00_check_txt.py` | `sources/novel/` → 校验报告 | 检查属性齐全、简介/正文非空、书名一致性、章节/卷编号是否连续（分卷按卷分别校验）；任一错误该书 FAIL，全部通过 exit 0 |
| 01 | `novel/01_split_txt_to_json.py` | `sources/novel/*/正文.txt` → `temps/novel/*.json` | 解析元数据、简介与章节/分卷结构，章节与卷按编号排序 |
| 02 | `novel/02_clean_json.py` | `temps/novel/*.json` → `temps/novel/*.json` | 按 `env` 清理规则删除整行广告、剥离行内 PS 注记，输出删除/剥离明细 |
| 03 | `novel/03_generate_struct.py` | `temps/novel/*.json` → `outputs/novel/*/` | 渲染封面、扉页、目录、分卷页、章节页，注入 manifest / spine |
| 04 | `novel/04_build_epub.py` | `outputs/novel/*/` → `outputs/novel/*.epub` | mimetype 置首且不压缩，其余 DEFLATE；epubcheck 有 ERROR 则 FAIL |

## 配置说明（`scrcpts/novel/env.py`）

- `BOOKS`：书名清单，脚本依此在 `sources/novel/<书名>/` 查找 `正文.txt`
- 路径常量：`SOURCE_DIR`(sources/novel) / `TXT_FILE_NAME`(正文.txt) / `COVER_FILE_STEM`(封面) / `OUTPUT_DIR`(temps/novel) / `BUILD_DIR`(outputs/novel) / `TEMPLATE_DIR`(EPUB33-NOVEL)
- `DROP_LINE_PATTERNS` / `STRIP_PATTERNS`：广告清理规则（正则），`DROP` 整行删除、`STRIP` 剥离行内子串
- 编号格式（章节 / 卷独立配置）：
  - `arabic`：阿拉伯数字（1、2、3…）
  - `arabic_padded`：阿拉伯数字自动补零（宽度 = 该书最大编号位数，如 `0001`）
  - `chinese_lower`：小写中文（一、二、三…）
  - `chinese_upper`：大写中文（壹、贰、叁…）
- `CHAPTER_TITLE_TEMPLATE` / `VOLUME_TITLE_TEMPLATE`：标题前缀模板，`{number}` 为格式化编号、`{title}` 为原标题
- `RENUMBER_CHAPTERS`：章节序号缺失/错误时自动按文档顺序重新编号（不使用源文件的错误编号）。按需开启（关闭时保持源编号）
- `VOLUME_RESTART_CHAPTERS`：分卷是否重新章节计数（`True` 每卷从第 1 章重新开始；`False` 全书连续编号）。仅在 `RENUMBER_CHAPTERS=True` 时生效。默认 `False`
- `SHOW_INDEX`：是否在书中显示目录页。默认 `True`（封面、扉页后显示完整目录）；设为 `False` 可从阅读顺序（spine）中移除目录页，避免长目录影响翻页体验，但仍保留 EPUB 标准 nav 目录文档，阅读器目录解析跳转不受影响

## 中间 JSON 结构（`temps/novel/书名.json`）

```json
{
  "title": "书名",
  "author": "作者",
  "tags": ["标签一", "标签二"],
  "description": ["简介行1", "简介行2"],
  "volumes": [
    {
      "order": 1,
      "title": "卷名",
      "chapters": [
        { "order": 1, "title": "章节标题", "contents": ["段落1", "段落2"] }
      ]
    }
  ]
}
```

- 无分卷的小说：`volumes` 仅含一个隐含卷（`order=0`，`title=书名`）
- 字段说明：`order` 编号、`title` 标题（不含「第X章/卷」前缀）、`contents` 按行分割的段落数组（已去除空行与首尾空白）

## 漫画（规划中）

漫画转换流水线脚本尚未实现，当前已完成目录与模板准备：

- **脚本目录**：`scrcpts/comic/`
  - `env.py`：漫画清单与元数据、路径、编号格式配置
  - `00_check_comic.py`：校验源目录结构（平铺 / 分章）、封面、章号 / 页码连续性
  - `01_comic_to_json.py`：扫描源目录 → `temps/comic/书名.json`，写入封面、章节与调整后的全局连续页码
  - `02_generate_comic.py`：基于 JSON 与 `EPUB33-COMIC` 模板生成 `outputs/comic/书名/` 结构（封面、单图页，manifest 含全部图片；章节目录直接链接到各章第一页）
  - `03_build_epub.py`：打包 `outputs/comic/书名.epub` 并 epubcheck 校验
- **模板**：`templates/EPUB33-COMIC/`，与小说模板同构但**无扉页、无章节标题页**（封面后直接进入正文），差异点：
  - `content.opf` 声明纯视觉访问模式（`accessModeSufficient=visual`），spine 指定 `page-progression-direction="ltr"`；spine 顺序为封面 →（可选目录页）→ 正文
  - `page-template.xhtml` 为单图页模板：每张图片渲染为独立 XHTML 页，spine 逐页翻图
  - `base.css` 单图页 `img { max-width:100%; max-height:100%; object-fit:contain }`，自适应视口不裁剪画面
  - `nav.xhtml` 目录仅列章节，链接指向各章第一页（图片页不展开）
  - 目录页默认不显示（`env.SHOW_INDEX = False`，仅从 spine 移除，仍保留 EPUB 标准 nav 供阅读器解析）
- **源目录布局**：

  ```
  sources/comic/书名/
    ├── cover.jpg                 # 封面（可选，env.cover 优先指定，缺省自动探测 cover.*）
    ├── 001.jpg                   # 平铺结构：图片直接位于书名目录下
    ├── 002.jpg
    │
    │                            # 或分章结构：数字章节目录（支持小数，如 1.5）
    ├── 1/
    │   ├── 002.jpg
    │   └── 003.jpg
    └── 1.5/
        └── 004.jpg
  ```

- **漫画 JSON 结构**（`temps/comic/书名.json`，序号已调整）：

  ```json
  {
    "title": "书名",
    "author": "作者",
    "tags": ["标签"],
    "description": ["简介"],
    "cover": "cover.jpg",
    "structure": "flat",
    "chapters": [
      {
        "order": 1,
        "source": "1.5",
        "pages": [
          { "order": 1, "file": "002.jpg" }
        ]
      }
    ]
  }
  ```

  - `structure`：`flat` 平铺 / `chaptered` 分章
  - `chapters[].order`：章号按原始值（含小数）排序后的调整序号（用于章节排序）；`source` 为原始章目录名（如 `1.5`），**用作目录标签**（平铺为 `null`）
  - `pages[].order`：全书全局连续 `1..N`；`file` 为原始图片文件名（02 步据此定位源图）

- **元数据配置**：在 `scrcpts/comic/env.py` 的 `COMICS` 列表中逐书输入书名 / 作者 / 标签 / 简介与封面文件名；标题模板默认「第{number}话」，编号格式与小说一致可配置

## 许可证

本项目使用 [GPL-3.0](LICENSE) 许可证。

## 注意事项

- 源小说文本与封面通常受版权保护，建议不要纳入版本控制（可在 `.gitignore` 中排除 `sources/`）
- 分卷小说的章节编号每卷重新开始，`00` 步会按卷校验完整性
- 第 04 步依赖 epubcheck（Java）；未安装时打包仍会完成，但该校书会被标记为失败
