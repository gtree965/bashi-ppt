"""Offline article export helpers for Markdown, DOCX, and ODT."""

from __future__ import annotations

import re
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile


EXPORT_MIMETYPES = {
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt": "application/vnd.oasis.opendocument.text",
}


def safe_export_filename(title: str, extension: str) -> str:
    """Return a Windows-safe download name while preserving Chinese text."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", (title or "").strip())
    clean = clean.rstrip(" .")[:100] or "备课文章"
    return f"{clean}.{extension}"


def _clean_xml_text(value: str) -> str:
    value = "".join(
        char
        for char in value
        if char in "\t\n\r" or ord(char) >= 0x20
    )
    return escape(value)


def _plain_text(value: str) -> str:
    """Remove lightweight Markdown markers for word-processor exports."""
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"(\*\*|__)(.*?)\1", r"\2", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", value)
    value = re.sub(r"(?<!_)_([^_]+)_(?!_)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    return value.strip()


def _article_blocks(article: str) -> list[tuple[str, str]]:
    """Convert plain/Markdown-like article text into simple semantic blocks."""
    blocks: list[tuple[str, str]] = []
    previous_blank = False
    for raw_line in article.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            if blocks and not previous_blank:
                blocks.append(("blank", ""))
            previous_blank = True
            continue

        previous_blank = False
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            blocks.append((f"heading{len(heading.group(1))}", _plain_text(heading.group(2))))
            continue

        bullet = re.match(r"^[-*+]\s+(.+)$", line)
        if bullet:
            blocks.append(("bullet", _plain_text(bullet.group(1))))
            continue

        blocks.append(("paragraph", _plain_text(line)))

    while blocks and blocks[-1][0] == "blank":
        blocks.pop()
    return blocks


def build_markdown(title: str, article: str) -> bytes:
    article = article.strip()
    heading = f"# {title.strip() or '备课文章'}"
    if article.startswith("# "):
        document = article
    else:
        document = f"{heading}\n\n{article}"
    return ("\ufeff" + document.rstrip() + "\n").encode("utf-8")


def _docx_paragraph(kind: str, text: str) -> str:
    if kind == "blank":
        return "<w:p/>"

    style_map = {
        "title": "Title",
        "heading1": "Heading1",
        "heading2": "Heading2",
        "heading3": "Heading3",
    }
    paragraph_style = style_map.get(kind)
    p_pr = f'<w:pPr><w:pStyle w:val="{paragraph_style}"/></w:pPr>' if paragraph_style else ""
    if kind == "bullet":
        text = f"• {text}"
    return (
        f"<w:p>{p_pr}<w:r><w:t xml:space=\"preserve\">"
        f"{_clean_xml_text(text)}</w:t></w:r></w:p>"
    )


def build_docx(title: str, article: str) -> bytes:
    body = [_docx_paragraph("title", title.strip() or "备课文章")]
    body.extend(_docx_paragraph(kind, text) for kind, text in _article_blocks(article))
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(body)
        + (
            "<w:sectPr>"
            '<w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
            'w:header="708" w:footer="708" w:gutter="0"/>'
            "</w:sectPr></w:body></w:document>"
        )
    )
    styles_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults><w:rPrDefault><w:rPr>
    <w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="Microsoft YaHei"/>
    <w:sz w:val="22"/><w:szCs w:val="22"/>
  </w:rPr></w:rPrDefault></w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/><w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="36"/><w:szCs w:val="36"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="30"/><w:szCs w:val="30"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="26"/><w:szCs w:val="26"/></w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading3">
    <w:name w:val="heading 3"/><w:basedOn w:val="Normal"/>
    <w:rPr><w:b/><w:sz w:val="24"/><w:szCs w:val="24"/></w:rPr>
  </w:style>
</w:styles>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/styles.xml", styles_xml)
        archive.writestr("word/_rels/document.xml.rels", document_rels)
    return output.getvalue()


def _odt_block(kind: str, text: str) -> str:
    if kind == "blank":
        return "<text:p/>"
    if kind.startswith("heading"):
        level = kind[-1]
        return f'<text:h text:outline-level="{level}">{_clean_xml_text(text)}</text:h>'
    if kind == "bullet":
        return f"<text:p>• {_clean_xml_text(text)}</text:p>"
    return f"<text:p>{_clean_xml_text(text)}</text:p>"


def build_odt(title: str, article: str) -> bytes:
    blocks = [f'<text:h text:outline-level="1">{_clean_xml_text(title.strip() or "备课文章")}</text:h>']
    blocks.extend(_odt_block(kind, text) for kind, text in _article_blocks(article))
    content_xml = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3">
 <office:automatic-styles/>
 <office:body><office:text>""" + "".join(blocks) + """</office:text></office:body>
</office:document-content>"""
    styles_xml = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
 xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
 xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"
 xmlns:fo="urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0"
 office:version="1.3">
 <office:styles>
  <style:default-style style:family="paragraph">
   <style:text-properties style:font-name="Arial" style:font-name-asian="Microsoft YaHei" fo:font-size="11pt"/>
  </style:default-style>
 </office:styles>
</office:document-styles>"""
    manifest_xml = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest
 xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"
 manifest:version="1.3">
 <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
 <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
 <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>"""

    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("mimetype", EXPORT_MIMETYPES["odt"], compress_type=ZIP_STORED)
        archive.writestr("content.xml", content_xml, compress_type=ZIP_DEFLATED)
        archive.writestr("styles.xml", styles_xml, compress_type=ZIP_DEFLATED)
        archive.writestr("META-INF/manifest.xml", manifest_xml, compress_type=ZIP_DEFLATED)
    return output.getvalue()


def build_article_export(title: str, article: str, export_format: str) -> tuple[bytes, str, str]:
    export_format = export_format.lower()
    builders = {
        "md": build_markdown,
        "docx": build_docx,
        "odt": build_odt,
    }
    if export_format not in builders:
        raise ValueError(f"Unsupported article export format: {export_format}")
    return (
        builders[export_format](title, article),
        safe_export_filename(title, export_format),
        EXPORT_MIMETYPES[export_format],
    )
