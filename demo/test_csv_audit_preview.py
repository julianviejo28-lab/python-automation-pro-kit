import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from csv_audit_preview import inspect_csv, main


class CsvAuditPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_profiles_semicolon_file_without_modifying_it(self):
        path = self.root / "contacts.csv"
        content = "name;email;city\nAna;a@example.com;Quito\n; b@example.com;Lima\nAna;a@example.com;Quito\nbroken\n"
        path.write_text(content, encoding="utf-8")
        result = inspect_csv(path)
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["column_count"], 3)
        self.assertEqual(result["duplicate_rows"], 1)
        self.assertEqual(result["malformed_rows"], 1)
        self.assertEqual(result["missing_cells"][0]["count"], 1)
        self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_handles_utf8_bom_and_tab_delimiter(self):
        path = self.root / "bom.tsv"
        path.write_text("\ufeffid\tvalue\n1\tuno\n", encoding="utf-8")
        result = inspect_csv(path)
        self.assertEqual(result["columns"], ["id", "value"])
        self.assertEqual(result["rows"], 1)

    def test_empty_file_has_empty_report(self):
        path = self.root / "empty.csv"
        path.write_text("", encoding="utf-8")
        result = inspect_csv(path)
        self.assertEqual(result["rows"], 0)
        self.assertEqual(result["columns"], [])

    def test_json_cli_emits_machine_readable_report(self):
        path = self.root / "tiny.csv"
        path.write_text("a,b\n1,2\n", encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main([str(path), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["rows"], 1)

    def test_cli_reports_missing_file(self):
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            code = main([str(self.root / "missing.csv")])
        self.assertEqual(code, 2)
        self.assertIn("Error:", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
