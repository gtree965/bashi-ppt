import io
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from article_export import build_article_export, safe_export_filename


TITLE = "人工智能备课"
ARTICLE = """## 为什么学习人工智能

人工智能正在改变课堂。

- 理解基本概念
- 保持批判思考
"""


class TestArticleExportBuilders(unittest.TestCase):
    def test_markdown_export(self):
        content, filename, mimetype = build_article_export(TITLE, ARTICLE, "md")
        text = content.decode("utf-8-sig")
        self.assertTrue(text.startswith(f"# {TITLE}"))
        self.assertIn("## 为什么学习人工智能", text)
        self.assertEqual(filename, f"{TITLE}.md")
        self.assertIn("text/markdown", mimetype)

    def test_docx_is_valid_zip_with_readable_xml(self):
        content, filename, mimetype = build_article_export(TITLE, ARTICLE, "docx")
        with ZipFile(io.BytesIO(content)) as archive:
            self.assertIn("[Content_Types].xml", archive.namelist())
            self.assertIn("word/document.xml", archive.namelist())
            document = archive.read("word/document.xml")
            ET.fromstring(document)
            self.assertIn(TITLE.encode("utf-8"), document)
            self.assertIn("理解基本概念".encode("utf-8"), document)
        self.assertEqual(filename, f"{TITLE}.docx")
        self.assertIn("wordprocessingml", mimetype)

    def test_odt_has_uncompressed_mimetype_and_valid_content(self):
        content, filename, mimetype = build_article_export(TITLE, ARTICLE, "odt")
        with ZipFile(io.BytesIO(content)) as archive:
            self.assertEqual(archive.infolist()[0].filename, "mimetype")
            self.assertEqual(archive.infolist()[0].compress_type, ZIP_STORED)
            self.assertEqual(
                archive.read("mimetype").decode("ascii"),
                "application/vnd.oasis.opendocument.text",
            )
            document = archive.read("content.xml")
            ET.fromstring(document)
            self.assertIn(TITLE.encode("utf-8"), document)
            self.assertIn("保持批判思考".encode("utf-8"), document)
        self.assertEqual(filename, f"{TITLE}.odt")
        self.assertEqual(mimetype, "application/vnd.oasis.opendocument.text")

    def test_safe_filename(self):
        self.assertEqual(safe_export_filename('课程: AI/入门?', "docx"), "课程_ AI_入门_.docx")

    def test_unsupported_format(self):
        with self.assertRaises(ValueError):
            build_article_export(TITLE, ARTICLE, "pdf")


class TestArticleExportEndpoint(unittest.TestCase):
    def setUp(self):
        import app

        self.client = app.app.test_client()

    def test_docx_download(self):
        response = self.client.post(
            "/api/export-article",
            json={"title": TITLE, "article": ARTICLE, "format": "docx"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data.startswith(b"PK"))
        self.assertIn("attachment", response.headers.get("Content-Disposition", ""))

    def test_empty_article_rejected(self):
        response = self.client.post(
            "/api/export-article",
            json={"title": TITLE, "article": "", "format": "md"},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
