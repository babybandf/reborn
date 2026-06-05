#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将重生(七年就是一辈子) 项目中的所有 Markdown 合并为一本 EPUB 电子书。
- 7 英寸墨水屏最佳显示优化
- 图片正确嵌入
- 自动生成章节级别的导航目录
"""

import os
import re
import sys
import base64
import urllib.parse
from pathlib import Path

import markdown as md
from ebooklib import epub

ROOT = Path(__file__).parent.resolve()
IMAGES_DIR = ROOT / "images"
COVER = ROOT / "cover.jpg"
OUTPUT = ROOT / "重生-七年就是一辈子.epub"

# 章节顺序：Preface -> A01..A33(A14-1 在 A14 之前) -> B02..B13 -> C01..C05
CHAPTER_ORDER = [
    "Preface.md",
    "A01.md", "A02.md", "A03.md", "A04.md", "A05.md",
    "A06.md", "A07.md", "A08.md", "A09.md", "A10.md",
    "A11.md", "A12.md", "A13.md", "A14-1.md", "A14.md",
    "A15.md", "A16.md", "A17.md", "A18.md", "A19.md",
    "A20.md", "A21.md", "A22.md", "A23.md", "A24.md",
    "A25.md", "A26.md", "A27.md", "A28.md", "A29.md",
    "A30.md", "A31.md", "A32.md", "A33.md",
    "B02.md", "B03.md", "B04.md", "B05.md", "B06.md",
    "B07.md", "B08.md", "B09.md", "B10.md", "B11.md",
    "B12.md", "B13.md",
    "C01.md", "C02.md", "C03.md", "C04.md", "C05.md",
]

# 为常见格式扩展补充 MIME
MIME_MAP = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".png": "image/png",  ".gif": "image/gif",
    ".svg": "image/svg+xml", ".webp": "image/webp",
}

# ---------- 7 英寸墨水屏优化的 CSS ----------
EINK_CSS = """
@namespace epub "http://www.idpf.org/2007/ops";

/* ===== 页面与版式：适配 7 英寸墨水屏 (1404x1872, 300ppi) ===== */
body {
    font-family: "Noto Serif CJK SC", "Source Han Serif SC", "Songti SC",
                 "STSong", "SimSun", "FangSong", serif;
    font-size: 1.05em;          /* 约 18~20px，配合默认行距 */
    line-height: 1.75;
    color: #000;
    background: #fff;
    margin: 0;
    padding: 0.6em 0.9em 0.8em 0.9em;
    text-align: justify;
    text-justify: inter-ideograph;
    word-wrap: break-word;
    -webkit-text-size-adjust: 100%;
    writing-mode: horizontal-tb;
}

/* 标题 */
h1, h2, h3, h4, h5, h6 {
    font-family: "Noto Sans CJK SC", "Source Han Sans SC", "PingFang SC",
                 "Microsoft YaHei", sans-serif;
    color: #000;
    line-height: 1.35;
    margin: 1.4em 0 0.6em 0;
    page-break-after: avoid;
    break-after: avoid;
    font-weight: 700;
}
h1 { font-size: 1.6em; text-align: center; margin-top: 0.2em; padding-bottom: 0.4em; border-bottom: 2px solid #000; }
h2 { font-size: 1.3em; border-bottom: 1px solid #444; padding-bottom: 0.2em; }
h3 { font-size: 1.12em; }
h4 { font-size: 1.02em; }

/* 段落 */
p {
    margin: 0 0 0.55em 0;
    text-indent: 2em;           /* 中文段落首行缩进 2 字符 */
}
p.toc-no-indent, .toc-entry p { text-indent: 0; }

/* 引用块 */
blockquote {
    margin: 0.8em 0.5em;
    padding: 0.4em 0.9em;
    border-left: 3px solid #000;
    color: #000;
    background: #f3f3f3;
    font-size: 0.97em;
    page-break-inside: avoid;
}
blockquote p { text-indent: 2em; margin: 0.3em 0; }
blockquote blockquote { margin: 0.4em 0; }

/* 列表 */
ul, ol { margin: 0.5em 0 0.7em 1.6em; padding: 0; }
li { margin: 0.2em 0; line-height: 1.7; }

/* 行内代码 / 代码块 */
code {
    font-family: "Fira Mono", "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 0.92em;
    background: #eee;
    padding: 0 0.18em;
    border-radius: 2px;
    color: #000;
}
pre {
    font-family: "Fira Mono", "DejaVu Sans Mono", "Courier New", monospace;
    font-size: 0.9em;
    line-height: 1.5;
    background: #f3f3f3;
    border: 1px solid #999;
    padding: 0.7em 0.9em;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-all;
    page-break-inside: avoid;
}
pre code { background: transparent; padding: 0; }

/* 强调 */
strong, b { font-weight: 700; color: #000; }
em, i { font-style: italic; }

/* 链接 */
a, a:link, a:visited {
    color: #000;
    text-decoration: underline;
    word-break: break-all;
}

/* 水平线 */
hr {
    border: 0;
    border-top: 1px dashed #555;
    margin: 1.4em 30%;
    height: 0;
}

/* ===== 插图：墨水屏必须清晰且不超页 ===== */
figure, .figure {
    margin: 1em 0;
    text-align: center;
    page-break-inside: avoid;
    break-inside: avoid;
}
figure img, .figure img {
    display: block;
    margin: 0 auto;
    max-width: 100%;
    height: auto;
    /* 墨水屏下不强制灰度，部分电纸书会自行抖动灰阶；保留原色以防信息丢失 */
}
figcaption {
    font-size: 0.9em;
    color: #222;
    margin-top: 0.3em;
    text-align: center;
    text-indent: 0;
    line-height: 1.5;
}

/* 仅图片无标题的场景 */
p > img:only-child {
    display: block;
    margin: 1em auto;
    max-width: 100%;
    height: auto;
}

/* 段落里夹着图片的常规情况：让图片不顶满 */
img {
    max-width: 100%;
    height: auto;
}

/* ===== 目录样式 ===== */
h1.toc-title {
    text-align: center;
    border-bottom: 2px solid #000;
    margin-bottom: 1em;
}
ul.toc {
    list-style: none;
    padding-left: 0;
    margin: 0.3em 0;
}
ul.toc li {
    margin: 0.35em 0;
    line-height: 1.55;
    text-indent: 0;
}
ul.toc li a {
    display: block;
    text-decoration: none;
    color: #000;
    word-break: break-word;
}
ul.toc li .toc-num {
    display: inline-block;
    width: 2.6em;
    font-weight: 700;
}
ul.toc.toc-sub {
    margin: 0.1em 0 0.3em 1.4em;
    font-size: 0.95em;
}
ul.toc.toc-sub li {
    margin: 0.2em 0;
    line-height: 1.5;
}
ul.toc.toc-sub li a {
    text-decoration: none;
    border-bottom: 1px dashed #888;
}

/* 章节正文首段不缩进（与 H1 紧邻时） */
h1 + p, h2 + p, h3 + p { text-indent: 0; }

/* 避免孤行寡行 */
p, li, blockquote { orphans: 2; widows: 2; }

/* 表格 */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 0.8em 0;
    page-break-inside: avoid;
    font-size: 0.95em;
}
th, td {
    border: 1px solid #000;
    padding: 0.35em 0.6em;
    text-align: left;
    vertical-align: top;
}
th { background: #e6e6e6; font-weight: 700; }

/* 注释：墨水屏下角标略放大 */
sup, sub { font-size: 0.8em; line-height: 0; }
"""


# ---------- HTML 模板 ----------
HTML_HEAD = (
    '<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" '
    'xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN">\n'
    '<head>\n<meta charset="utf-8" />\n<title>{title}</title>\n'
    '<link rel="stylesheet" type="text/css" href="style/main.css" />\n'
    '</head>\n<body>\n'
)
HTML_TAIL = "\n</body>\n</html>\n"


# ---------- 工具函数 ----------
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chapter_title(md_text: str, fallback: str) -> str:
    """从首行 H1 抽取章节标题；找不到则用文件名。"""
    for line in md_text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return m.group(1).strip()
        break
    return fallback


def strip_first_h1(md_text: str) -> str:
    """移除首行 H1（避免与章节标题重复）。保留其余内容。"""
    lines = md_text.splitlines()
    out = []
    skipped = False
    for line in lines:
        if not skipped and line.strip().startswith("# "):
            skipped = True
            continue
        out.append(line)
    return "\n".join(out)


def extract_headings(md_text: str) -> list[tuple[int, str]]:
    """提取 markdown 中的 H2~H4 标题，返回 [(level, title), ...] 列表。"""
    headings = []
    for line in md_text.splitlines():
        m = re.match(r"^(#{2,4})\s+(.+?)\s*$", line)
        if m:
            level = len(m.group(1))
            title = m.group(2).strip()
            headings.append((level, title))
    return headings


def inject_heading_ids(html: str) -> tuple[str, list[tuple[int, str, str]]]:
    """在 HTML 的 <h2>/<h3>/<h4> 上注入 id，返回 (处理后的 HTML, [(level, title, anchor_id)])。"""
    counter = 0
    headings: list[tuple[int, str, str]] = []   # (level, plain_title, id)

    def repl(m: re.Match) -> str:
        nonlocal counter
        level = int(m.group(1))
        title_html = m.group(2)
        # 把 HTML 内常见标签/实体剥掉，得到纯文本
        plain = re.sub(r"<[^>]+>", "", title_html)
        plain = (plain.replace("&amp;", "&").replace("&lt;", "<")
                     .replace("&gt;", ">").replace("&quot;", '"')
                     .replace("&#39;", "'").replace("&nbsp;", " ")).strip()
        counter += 1
        sid = f"h-sec-{counter:03d}"
        headings.append((level, plain, sid))
        return f'<h{level} id="{sid}">{title_html}</h{level}>'

    new_html = re.sub(r"<h([234])>(.*?)</h\1>", repl, html, flags=re.DOTALL)
    return new_html, headings


# ---------- 图片处理 ----------
class ImageCollector:
    """收集每章出现的图片，写入 EPUB 的 image 目录并返回内部 URL。"""
    def __init__(self, book: epub.EpubBook):
        self.book = book
        self.cache: dict[str, str] = {}   # 原文件 -> 内部文件名
        self.counter = 0

    def resolve(self, src: str, chapter_dir: Path) -> str:
        """把 markdown 中的图片路径转成 epub 内部 href。"""
        if not src:
            return src
        # 去掉 URL 片段
        src_path = src.split("#", 1)[0]
        if not src_path:
            return src
        # 跳过外链
        if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", src_path):
            return src
        # 计算磁盘上的实际文件
        local = (chapter_dir / src_path).resolve()
        if not local.exists():
            # 退路：images/ 目录
            alt = (IMAGES_DIR / Path(src_path).name)
            if alt.exists():
                local = alt
            else:
                print(f"  [!] 图片缺失: {src_path}", file=sys.stderr)
                return src

        if str(local) in self.cache:
            return self.cache[str(local)]

        self.counter += 1
        ext = local.suffix.lower()
        mime = MIME_MAP.get(ext, "application/octet-stream")
        internal = f"images/img_{self.counter:03d}{ext}"
        with open(local, "rb") as f:
            data = f.read()
        item = epub.EpubItem(
            uid=f"img_{self.counter:03d}",
            file_name=internal,
            media_type=mime,
            content=data,
        )
        self.book.add_item(item)
        # epub href 相对于 chapter 的 xhtml
        self.cache[str(local)] = internal
        return internal


# ---------- Markdown -> HTML ----------
def md_to_html(md_text: str, image_collector: ImageCollector, chapter_dir: Path) -> str:
    # 将 ![](images/x.jpg) 这类相对路径转成绝对路径，方便 markdown 渲染
    def repl_img(m: re.Match) -> str:
        alt = m.group(1) or ""
        src = m.group(2)
        resolved = image_collector.resolve(src, chapter_dir)
        return f"![{alt}]({resolved})"

    processed = re.sub(r"!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)", repl_img, md_text)

    html_body = md.markdown(
        processed,
        extensions=[
            "fenced_code",
            "tables",
            "footnotes",
            "codehilite",
            "sane_lists",
            "nl2br",
        ],
        extension_configs={"codehilite": {"guess_lang": False}},
    )
    return html_body


# ---------- 生成 ----------
def build():
    book = epub.EpubBook()

    # 元数据
    book.set_identifier("reborn-7years-1")
    book.set_title("重生 —— 七年就是一辈子")
    book.set_language("zh-CN")
    book.add_author("李笑来")
    book.add_metadata("DC", "description",
                      "《新生 —— 七年就是一辈子》合集。七年就是一辈子，每个人都拥有获得重生的机会。")
    book.add_metadata("DC", "publisher", "GitHub 公开版本")
    book.add_metadata("DC", "rights", "版权归原作者所有；本 EPUB 仅供个人学习使用。")

    # 封面
    if COVER.exists():
        with open(COVER, "rb") as f:
            cover_data = f.read()
        book.set_cover("cover.jpg", cover_data, create_page=True)

    # 样式
    style_item = epub.EpubItem(
        uid="style_main",
        file_name="style/main.css",
        media_type="text/css",
        content=EINK_CSS.encode("utf-8"),
    )
    book.add_item(style_item)

    img_collector = ImageCollector(book)

    # 构建章节
    chapters = []
    chapter_index = []         # (display_title, item)  仅顶层
    chapter_subheadings = []   # 每章对应的 [(level, title, anchor_id)] 列表

    # 跨章链接映射：旧 .md 文件名 -> EPUB 内 .xhtml 文件名
    link_map: dict[str, str] = {}
    link_map["Preface.md"] = "chap_preface.xhtml"
    link_map["README.md"] = "chap_readme.xhtml"
    _chap_seq = 0
    for _fname in CHAPTER_ORDER:
        if _fname in ("Preface.md",):
            continue
        if not (ROOT / _fname).exists():
            continue
        _chap_seq += 1
        link_map[_fname] = f"chap_{_chap_seq:02d}.xhtml"

    def rewrite_md_links(md_text: str) -> str:
        """把 markdown 文本里的跨章链接与图片链接重写为 EPUB 内部 href。

        - [text](A01.md)            -> [text](chap_01.xhtml)
        - [text](A01.md#sec)        -> [text](chap_01.xhtml#sec)
        - [![](inner.png)](/img/foo.jpg) 这类带图片的链接会同时处理内层和外层

        实现：用占位符先提取全部 image 语法，再处理 link 语法，最后恢复。
        """
        img_collector_local = img_collector
        placeholders: list[str] = []

        def stash_img(m: re.Match) -> str:
            idx = len(placeholders)
            placeholders.append(m.group(0))
            return f"\x00IMG{idx}\x00"

        # 1) 提取全部 image 语法到占位符
        s = re.sub(r"!\[[^\]]*\]\([^)\s]+(?:\s+\"[^\"]*\")?\)", stash_img, md_text)

        # 2) 在剩下的 link 语法上做替换
        def repl(m: re.Match) -> str:
            text = m.group(1)
            target = m.group(2)
            fragment = m.group(3) or ""

            # 跳过外链
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target):
                return m.group(0)
            # 跳过纯 fragment
            if target.startswith("#"):
                return m.group(0)
            # 跨章 .md 链接
            if target.endswith(".md"):
                new_target = link_map.get(target)
                if new_target is not None:
                    return f"[{text}]({new_target}{fragment})"
                return m.group(0)
            # 以 / 开头的图片相对根路径：尝试解析
            if target.startswith("/") and target.lower().endswith(
                (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg")
            ):
                rel = target.lstrip("/")
                resolved = img_collector_local.resolve(rel, ROOT)
                return f"[{text}]({resolved}{fragment})"
            # 相对图片路径（无 / 开头）—— 用 images 目录解析
            if re.search(r"\.(jpg|jpeg|png|gif|webp|svg)$", target, re.IGNORECASE) \
                    and not target.startswith("/"):
                # 把形如 images/foo.jpg 直接解析；不在 images 下的不动
                if target.startswith("images/") or "/" not in target:
                    resolved = img_collector_local.resolve(target, ROOT)
                    return f"[{text}]({resolved}{fragment})"
            # 裸域名（例如 knewone.com）—— 自动补 http://
            if re.match(r"^[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)+(/.*)?$", target):
                return f"[{text}](http://{target}{fragment})"
            return m.group(0)

        s = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)(#[^)\s]*)?\)",
            repl,
            s,
        )

        # 3) 恢复 image 占位符
        def restore(m: re.Match) -> str:
            return placeholders[int(m.group(1))]

        s = re.sub(r"\x00IMG(\d+)\x00", restore, s)
        return s

    def add_chapter(display_title: str, file_name: str, raw_md: str,
                    anchor: str | None = None):
        """处理一篇章节：剥离首行 H1、改写跨章链接、转 HTML、注入子标题 id。"""
        body = strip_first_h1(raw_md)
        body = rewrite_md_links(body)        # 新增：把 [A01.md] 改成 [chap_01.xhtml]
        body_html = md_to_html(body, img_collector, ROOT)
        # 在最前面放章节级锚点
        prefix = f'<a id="{anchor}"></a>\n' if anchor else ""
        body_html = prefix + body_html
        # 给子标题注入 id，并收集目录条目
        body_html, sub_ids = inject_heading_ids(body_html)
        html = HTML_HEAD.format(title=html_escape(display_title)) + body_html + HTML_TAIL
        item = epub.EpubHtml(
            title=display_title, file_name=file_name, lang="zh-CN", content=html
        )
        item.add_link(href="style/main.css", rel="stylesheet", type="text/css")
        book.add_item(item)
        chapters.append(item)
        chapter_index.append((display_title, item))
        chapter_subheadings.append(sub_ids)
        return item

    # 1) 自序
    preface_path = ROOT / "Preface.md"
    if preface_path.exists():
        raw = read_text(preface_path)
        title = chapter_title(raw, "自序")
        add_chapter(title, "chap_preface.xhtml", raw, anchor="ch_00")

    # 2) 章节主体
    i = 0
    for fname in CHAPTER_ORDER:
        if fname in ("Preface.md",):
            continue
        p = ROOT / fname
        if not p.exists():
            print(f"  [!] 缺失章节: {fname}", file=sys.stderr)
            continue
        i += 1
        raw = read_text(p)
        title = chapter_title(raw, fname.replace(".md", ""))
        full_title = f"{i:02d}　{title}"
        file_name = f"chap_{i:02d}.xhtml"
        add_chapter(full_title, file_name, raw, anchor=f"ch_{i:02d}")

    # 3) 阅读说明（原 README.md）
    readme_path = ROOT / "README.md"
    if readme_path.exists():
        raw = read_text(readme_path)
        title = "阅读说明 / 关于本书"
        # README 第一行是 "# 前言" 之类，去掉
        body = re.sub(r"^#\s+.+?\n", "", raw, count=1)
        # 复用同样的处理链路：先去掉首行 H1，再走 md->html，再注入 id
        raw_clean = re.sub(r"^#\s+.+?\n", "", raw, count=1)
        add_chapter(title, "chap_readme.xhtml", raw_clean, anchor="ch_readme")

    # 4) 目录页（含层级书签）
    toc_entries = []          # book.toc: tuple 形式 (parent, [children])
    toc_items_html = []       # 可见目录页
    toc_items_html.append('<h1 class="toc-title">目　录</h1>')
    toc_items_html.append('<ul class="toc">')

    def build_sub_tree(file_name: str, subs: list[tuple[int, str, str]]):
        """把章节内的子标题按 H2/H3/H4 嵌套转换为 node 树。"""
        root = []
        stack = []  # (level, node)
        for level, title, sid in subs:
            node = {
                "level": level,
                "title": title,
                "href": f"{file_name}#{sid}",
                "children": [],
            }
            while stack and stack[-1][0] >= level:
                stack.pop()
            if stack:
                stack[-1][1]["children"].append(node)
            else:
                root.append(node)
            stack.append((level, node))
        return root

    def node_to_toc(node: dict):
        """node -> toc entry 形式。
        无子节点：返回 Link；
        有子节点：返回 (Section(node), [child entries]) 元组。"""
        link = epub.Link(node["href"], node["title"], node["title"])
        if not node["children"]:
            return link
        sec = epub.Section(node["title"], href=node["href"])
        children = [node_to_toc(c) for c in node["children"]]
        return (sec, children)

    idx = 0
    for (title, item), subs in zip(chapter_index, chapter_subheadings):
        idx += 1
        clean_title = re.sub(r"^\d+[\s　]+", "", title)
        sub_tree = build_sub_tree(item.file_name, subs)
        # 顶层 chapter: 用 Section + 子条目
        chapter_section = epub.Section(clean_title, href=item.file_name)
        chapter_children = [node_to_toc(n) for n in sub_tree]
        toc_entries.append((chapter_section, chapter_children))

        # HTML 可见目录
        toc_items_html.append(
            f'<li><a href="{item.file_name}">'
            f'<span class="toc-num">{idx:02d}</span>{html_escape(title)}'
            f'</a>'
        )
        if sub_tree:
            toc_items_html.append('<ul class="toc toc-sub">')
            def render_tree(nodes):
                for n in nodes:
                    indent = "　" * (n["level"] - 2)
                    toc_items_html.append(
                        f'<li><a href="{n["href"]}">'
                        f'{indent}{html_escape(n["title"])}</a>'
                    )
                    if n["children"]:
                        toc_items_html.append('<ul class="toc toc-sub">')
                        render_tree(n["children"])
                        toc_items_html.append('</ul>')
                    toc_items_html.append('</li>')
            render_tree(sub_tree)
            toc_items_html.append('</ul>')
        toc_items_html.append('</li>')

    toc_items_html.append("</ul>")
    toc_html = HTML_HEAD.format(title="目录") + "\n".join(toc_items_html) + HTML_TAIL
    toc_item = epub.EpubHtml(title="目录", file_name="toc.xhtml",
                             lang="zh-CN", content=toc_html)
    toc_item.add_link(href="style/main.css", rel="stylesheet", type="text/css")
    book.add_item(toc_item)

    # 章节在书中的顺序
    book.toc = toc_entries
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["cover", toc_item, "nav"] + chapters

    # 写入
    epub.write_epub(str(OUTPUT), book)
    print(f"\n✅ 已生成: {OUTPUT}")
    print(f"   章节数: {len(chapters)}, 图片数: {img_collector.counter}")
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"   文件大小: {size_mb:.2f} MB")


def html_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "&#39;"))


if __name__ == "__main__":
    build()
