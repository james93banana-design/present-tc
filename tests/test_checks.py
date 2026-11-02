import hashlib
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from check_delivery import inspect, resolve_target
from validate_repo import validate
from check_public import candidates, check_public

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def html(body="<p>Demo</p>", head=""):
    return '<!doctype html><html><head><meta charset="utf-8"><title>Demo</title>' + head + '</head><body>' + body + '</body></html>'


def pptx_parts():
    # Minimal XML fixtures exercise the checker; they are not production PPTX output.
    return {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "_rels/.rels": '<Relationships xmlns="' + REL + '"><Relationship Id="rId1" Type="' + R + '/officeDocument" Target="ppt/presentation.xml"/></Relationships>',
        "ppt/presentation.xml": '<p:presentation xmlns:p="' + P + '" xmlns:r="' + R + '"><p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst></p:presentation>',
        "ppt/_rels/presentation.xml.rels": '<Relationships xmlns="' + REL + '"><Relationship Id="rId1" Type="' + R + '/slide" Target="slides/slide1.xml"/></Relationships>',
        "ppt/slides/slide1.xml": '<p:sld xmlns:p="' + P + '" xmlns:a="' + A + '"><a:t>Synthetic demo</a:t></p:sld>',
    }


class DeliveryChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write_html(self, text):
        path = self.root / "demo.html"
        path.write_text(text, encoding="utf-8")
        return path

    def write_pptx(self, parts):
        path = self.root / "demo.pptx"
        with zipfile.ZipFile(path, "w") as package:
            for name, content in parts.items():
                package.writestr(name, content)
        return path

    def codes(self, path, level=None):
        return {item["code"] for item in inspect(path) if level is None or item["level"] == level}

    def test_self_contained_html(self):
        path = self.write_html(html('<a href="https://example.com">Source</a><img alt="demo" src="data:image/png;base64,AA==">'))
        self.assertEqual(self.codes(path, "error"), set())
        self.assertIn("visual-unchecked", self.codes(path))

    def test_relative_and_remote_resources(self):
        for src in ("image.png", "https://example.com/a.png", "//example.com/a.png", "file:///tmp/a.png"):
            with self.subTest(src=src):
                self.assertIn("offline-resource", self.codes(self.write_html(html('<img src="' + src + '">'))))

    def test_css_import_and_url(self):
        for css in ('@import "https://example.com/a.css";', 'p{background:url(image.png)}'):
            with self.subTest(css=css):
                self.assertIn("offline-resource", self.codes(self.write_html(html(head="<style>" + css + "</style>"))))

    def test_linked_stylesheet(self):
        path = self.write_html(html(head='<link rel="stylesheet" href="style.css">'))
        self.assertIn("offline-resource", self.codes(path))

    def test_malformed_data_uri(self):
        path = self.write_html(html('<img src="data:image/png;base64">'))
        self.assertIn("data-uri", self.codes(path))

    def test_script_and_srcset_warnings(self):
        path = self.write_html(html('<img srcset="a.png 1x"><script>fetch("/data")</script>'))
        self.assertTrue({"srcset", "dynamic-network"}.issubset(self.codes(path, "warning")))

    def test_invalid_html_structure(self):
        self.assertIn("html-structure", self.codes(self.write_html("<p>Fragment</p>")))

    def test_executable_link(self):
        path = self.write_html(html('<a href="javascript:alert(1)">Bad link</a>'))
        self.assertIn("unsafe-link", self.codes(path))

    def test_basic_package_fixture(self):
        path = self.write_pptx(pptx_parts())
        self.assertEqual(self.codes(path, "error"), set())
        self.assertIn("slide-count", self.codes(path))

    def test_missing_part_and_relationship(self):
        parts = pptx_parts()
        del parts["ppt/slides/slide1.xml"]
        self.assertIn("relationship-target", self.codes(self.write_pptx(parts)))
        self.assertIn("missing-part", self.codes(self.write_pptx({})))

    def test_invalid_slide_reference(self):
        parts = pptx_parts()
        parts["ppt/presentation.xml"] = parts["ppt/presentation.xml"].replace('r:id="rId1"', 'r:id="rId99"')
        self.assertIn("slide-reference", self.codes(self.write_pptx(parts)))

    def test_macro_and_embedded_objects(self):
        parts = pptx_parts()
        parts["ppt/vbaProject.bin"] = "not executable test data"
        parts["ppt/embeddings/demo.xlsx"] = "synthetic test data"
        path = self.write_pptx(parts)
        self.assertIn("macro", self.codes(path, "error"))
        self.assertIn("embedded-object", self.codes(path, "warning"))

    def test_external_relationship(self):
        parts = pptx_parts()
        parts["ppt/slides/_rels/slide1.xml.rels"] = '<Relationships xmlns="' + REL + '"><Relationship Id="rId2" TargetMode="External" Target="https://example.com"/></Relationships>'
        self.assertIn("external-relationship", self.codes(self.write_pptx(parts), "warning"))

    def test_author_value_not_printed(self):
        parts = pptx_parts()
        parts["docProps/core.xml"] = '<core><creator>PrivateAuthorValue</creator></core>'
        findings = inspect(self.write_pptx(parts))
        self.assertIn("author-metadata", {item["code"] for item in findings})
        self.assertNotIn("PrivateAuthorValue", str(findings))

    def test_hidden_slide_and_notes(self):
        parts = pptx_parts()
        parts["ppt/slides/slide1.xml"] = parts["ppt/slides/slide1.xml"].replace("<p:sld ", '<p:sld show="0" ')
        parts["ppt/notesSlides/notesSlide1.xml"] = "<notes/>"
        self.assertTrue({"hidden-slide", "notes-comments"}.issubset(self.codes(self.write_pptx(parts))))

    def test_bad_xml_and_dtd(self):
        parts = pptx_parts()
        parts["ppt/slides/slide1.xml"] = "<broken>"
        self.assertIn("xml-invalid", self.codes(self.write_pptx(parts)))
        parts["ppt/slides/slide1.xml"] = '<!DOCTYPE test [<!ENTITY x "text">]><test/>'
        self.assertIn("xml-declaration", self.codes(self.write_pptx(parts)))

    def test_corrupt_archive(self):
        path = self.root / "bad.pptx"
        path.write_text("not a zip", encoding="utf-8")
        self.assertIn("read-failed", self.codes(path))

    def test_size_limit(self):
        path = self.write_html(html())
        with patch("check_delivery.MAX_FILE_BYTES", 10):
            self.assertIn("size-limit", self.codes(path))

    def test_relationship_resolution(self):
        self.assertEqual(resolve_target("ppt/slides/_rels/slide1.xml.rels", "../media/image1.png"), "ppt/media/image1.png")
        self.assertEqual(resolve_target("_rels/.rels", "/ppt/presentation.xml"), "ppt/presentation.xml")

    def test_read_only(self):
        path = self.write_pptx(pptx_parts())
        before = hashlib.sha256(path.read_bytes()).digest()
        inspect(path)
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).digest())
        self.assertEqual(list(self.root.iterdir()), [path])

    def test_cli_exit_codes(self):
        path = self.write_html(html())
        command = [sys.executable, str(ROOT / "scripts/check_delivery.py"), str(path), "--json"]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        path.write_text("<p>Broken</p>", encoding="utf-8")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)


class RepositoryChecks(unittest.TestCase):
    def test_public_export_contains_complete_bundle(self):
        errors, count = check_public(ROOT)
        self.assertEqual(errors, [])
        self.assertGreater(count, 10)

    def test_personal_notes_are_rejected(self):
        with patch("check_public.candidates", return_value=["AI-progress.txt"]):
            errors, _ = check_public(ROOT)
        self.assertIn("Unexpected public file: AI-progress.txt", errors)

    def test_bundle_binaries_are_not_gitignored(self):
        names = set(candidates(ROOT))
        self.assertIn("assets/present-tc/assets/present-tc asset.pptx", names)
        self.assertIn("assets/present-tc/assets/fonts/Tencent-W3.woff2", names)
        self.assertIn("assets/present-tc/assets/fonts/Tencent-W7.woff2", names)
        self.assertEqual(sum(name.startswith("assets/present-tc/thumbs/") and name.endswith(".jpg") for name in names), 213)

    def test_missing_preview_fails_validation(self):
        real_is_file = Path.is_file
        with patch.object(Path, "is_file", lambda p: False if p.name == "001.jpg" else real_is_file(p)):
            errors, _ = validate(ROOT)
        self.assertTrue(any("001.jpg" in error for error in errors))

    def test_repository_valid(self):
        errors, count = validate(ROOT)
        self.assertEqual(errors, [])
        self.assertGreater(count, 10)

    def test_release_requires_license(self):
        with tempfile.TemporaryDirectory() as temp:
            errors, _ = validate(Path(temp), release=True)
            self.assertTrue(any("LICENSE" in message for message in errors))


if __name__ == "__main__":
    unittest.main()
