import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from sync_palette import check


class PaletteChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for name in ("assets/report-tokens.json", "assets/html/palette.css",
                     "assets/html/countdown.css", "references/visual-system.md", "agents/openai.yaml"):
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_current_defaults_agree(self):
        self.assertEqual(check(ROOT), [])

    def test_detects_unmapped_control_color(self):
        with (self.root / "assets/html/countdown.css").open("a") as stream:
            stream.write(".button{color:#FF00FF}")
        self.assertTrue(any("outside defaults" in error for error in check(self.root)))

    def test_valid_color_in_wrong_role_is_detected(self):
        with (self.root / "assets/html/countdown.css").open("a") as stream:
            stream.write(".button{color:var(--tc-primary,#53585F)}")
        self.assertTrue(any("fallback differs" in error for error in check(self.root)))

    def test_stale_generated_palette_is_detected(self):
        path = self.root / "assets/html/palette.css"
        path.write_text(path.read_text().replace("#0052D9", "#0152D9"))
        self.assertTrue(any("palette.css differs" in error for error in check(self.root)))

    def test_checker_is_read_only(self):
        paths = [p for p in self.root.rglob("*") if p.is_file()]
        before = {p: p.read_bytes() for p in paths}
        check(self.root)
        self.assertEqual(before, {p: p.read_bytes() for p in paths})


if __name__ == "__main__":
    unittest.main()
