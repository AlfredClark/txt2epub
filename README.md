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
│   ├── env.py                   # 全局配置（书名、路径、清理规则、编号格式）
│   ├── 00_check_txt.py          # 1. 校验源 TXT 格式
│   ├── 01_split_txt_to_json.py  # 2. TXT → JSON
│   ├── 02_clean_json.py         # 3. 清理广告 / 作者注
│   ├── 03_generate_struct.py    # 4. 生成 EPUB 目录结构
│   └── 04_build_epub.py         # 5. 打包 .epub 并 epubcheck 校验
├── sources/                     # 源 TXT 与同名封面图（如《书名》.txt / .jpg）
├── temps/                       # 中间 JSON（脚本自动生成，已忽略）
├── outputs/                     # 生成的 EPUB 目录结构与 .epub 产物（已忽略）
├── templates/EPUB33/            # EPUB3 模板
│   ├── mimetype
│   ├── META-INF/container.xml
│   └── EPUB/
│       ├── content.opf          # 包描述（元数据 + manifest + spine）
│       ├── cover.xhtml          # 封面页
│       ├── titlepage.xhtml      # 扉页
│       ├── nav.xhtml            # 目录
│       ├── styles/base.css      # 样式
│       └── text/
│           ├── chapter-template.xhtml  # 章节页模板
│           └── volume-template.xhtml   # 分卷页模板
└── pyproject.toml
```

## 源文件格式

TXT 需满足以下结构（`00` 步会逐项校验）：

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
- **封面**：在 `sources/` 中放置与书名同名的图片（如 `书名.jpg`），脚本会自动找到并嵌入

## 使用流程

按顺序执行 00 → 04：

```bash
# 1. 校验源 TXT 格式（属性齐全、简介/正文非空、章节/卷编号连续）
uv run python scrcpts/00_check_txt.py

# 2. 按 env.BOOKS 逐书解析，生成 temps/书名.json
uv run python scrcpts/01_split_txt_to_json.py

# 3. 清理广告与作者注（按 env 中的规则，原位覆写）
uv run python scrcpts/02_clean_json.py

# 4. 基于 EPUB33 模板生成 outputs/书名/ 目录结构
uv run python scrcpts/03_generate_struct.py

# 5. 打包为 outputs/书名.epub 并调用 epubcheck 校验
uv run python scrcpts/04_build_epub.py
```

各步说明：

| 步骤 | 脚本 | 输入 → 输出 | 说明 |
| --- | --- | --- | --- |
| 00 | `00_check_txt.py` | `sources/` → 校验报告 | 检查属性齐全、简介/正文非空、书名一致性、章节/卷编号是否连续（分卷按卷分别校验）；任一错误该书 FAIL，全部通过 exit 0 |
| 01 | `01_split_txt_to_json.py` | `sources/*.txt` → `temps/*.json` | 解析元数据、简介与章节/分卷结构，章节与卷按编号排序 |
| 02 | `02_clean_json.py` | `temps/*.json` → `temps/*.json` | 按 `env` 清理规则删除整行广告、剥离行内 PS 注记，输出删除/剥离明细 |
| 03 | `03_generate_struct.py` | `temps/*.json` → `outputs/*/` | 渲染封面、扉页、目录、分卷页、章节页，注入 manifest / spine |
| 04 | `04_build_epub.py` | `outputs/*/` → `outputs/*.epub` | mimetype 置首且不压缩，其余 DEFLATE；epubcheck 有 ERROR 则 FAIL |

## 配置说明（`scrcpts/env.py`）

- `BOOKS`：书名清单，脚本依此在 `sources/` 查找同名 `.txt`
- 路径常量：`SOURCE_DIR` / `OUTPUT_DIR`(temps) / `BUILD_DIR`(outputs) / `TEMPLATE_DIR`(EPUB33)
- `DROP_LINE_PATTERNS` / `STRIP_PATTERNS`：广告清理规则（正则），`DROP` 整行删除、`STRIP` 剥离行内子串
- 编号格式（章节 / 卷独立配置）：
  - `arabic`：阿拉伯数字（1、2、3…）
  - `arabic_padded`：阿拉伯数字自动补零（宽度 = 该书最大编号位数，如 `0001`）
  - `chinese_lower`：小写中文（一、二、三…）
  - `chinese_upper`：大写中文（壹、贰、叁…）
- `CHAPTER_TITLE_TEMPLATE` / `VOLUME_TITLE_TEMPLATE`：标题前缀模板，`{number}` 为格式化编号、`{title}` 为原标题

## 中间 JSON 结构（`temps/书名.json`）

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

## 许可证

本项目使用 [GPL-3.0](LICENSE) 许可证。

## 注意事项

- 源小说文本与封面通常受版权保护，建议不要纳入版本控制（可在 `.gitignore` 中排除 `sources/`）
- 分卷小说的章节编号每卷重新开始，`00` 步会按卷校验完整性
- 第 04 步依赖 epubcheck（Java）；未安装时打包仍会完成，但该校书会被标记为失败
