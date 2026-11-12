import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_index  # noqa: E402

EXAMPLE = ROOT / "examples" / "streaming"
CODE_EXAMPLE = ROOT / "examples" / "hello-sync"


class LocalIndex(unittest.TestCase):
    def build(self, *folders: Path) -> tuple[subprocess.CompletedProcess, Path]:
        out = Path(tempfile.mkdtemp())
        result = subprocess.run(
            [sys.executable, str(ROOT / "build_index.py"), "local", *map(str, folders), "--out", str(out)],
            capture_output=True, text=True,
        )
        return result, out / "v1"

    def test_copies_are_named_by_their_checksum(self):
        result, v1 = self.build(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        [entry] = json.loads((v1 / "index.json").read_text())["plugins"]
        self.assertEqual(entry["id"], "your-name/streaming")
        self.assertEqual(entry["contributes"], {"categories": 1, "rules": 1})
        self.assertEqual(entry["locales"], ["en", "pt-BR"])
        for path, digest in ((entry["manifest"], entry["manifest_sha256"]), (entry["readme"], entry["readme_sha256"])):
            self.assertEqual(hashlib.sha256((v1 / path).read_bytes()).hexdigest(), digest)
        self.assertEqual((v1 / entry["manifest"]).read_bytes(), (EXAMPLE / "securo-plugin.json").read_bytes())

    def test_a_broken_plugin_fails_the_build(self):
        folder = Path(tempfile.mkdtemp())
        (folder / "securo-plugin.json").write_text(json.dumps({"id": "a/b", "runtime": "node"}))
        result, _ = self.build(folder)
        self.assertEqual(result.returncode, 1)
        self.assertIn("runtime", result.stderr)

    def test_a_plugin_with_code_ships_its_source(self):
        import io
        import tarfile

        result, v1 = self.build(CODE_EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        [entry] = json.loads((v1 / "index.json").read_text())["plugins"]
        self.assertEqual(entry["contributes"], {"integrations": 1})
        archive = (v1 / entry["archive"]).read_bytes()
        self.assertEqual(hashlib.sha256(archive).hexdigest(), entry["archive_sha256"])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            names = tar.getnames()
        self.assertIn("plugin/hello_sync/plugin.py", names)
        self.assertIn("plugin/securo-plugin.json", names)

    def test_data_plugins_ship_no_source(self):
        _, v1 = self.build(EXAMPLE)
        [entry] = json.loads((v1 / "index.json").read_text())["plugins"]
        self.assertNotIn("archive", entry)


class Manifest(unittest.TestCase):
    def manifest(self, **changes) -> bytes:
        data = json.loads((EXAMPLE / "securo-plugin.json").read_text()) | changes
        return json.dumps(data).encode()

    def test_must_be_the_repository_it_was_found_in(self):
        with self.assertRaisesRegex(build_index.Invalid, "expected someone/streaming"):
            build_index.check_manifest(self.manifest(), plugin_id="someone/streaming")
        with self.assertRaisesRegex(build_index.Invalid, "repository"):
            build_index.check_manifest(self.manifest(), repository="https://github.com/someone/streaming")

    def test_malformed_fields(self):
        for changes in ({"version": "1.0"}, {"contributes": {"rules": []}}, {"name": {"pt-BR": "x"}}):
            with self.subTest(changes), self.assertRaises(build_index.Invalid):
                build_index.check_manifest(self.manifest(**changes))


class Stars(unittest.TestCase):
    def test_gained_against_the_newest_count_a_week_old(self):
        today = datetime(2026, 11, 10, tzinfo=timezone.utc)
        day = lambda n: build_index.iso(today - timedelta(days=n))  # noqa: E731
        history = [[day(10), 5], [day(8), 7], [day(3), 20]]
        self.assertEqual(build_index.stars_gained(history, 30, today), 23)
        self.assertEqual(build_index.stars_gained([[day(2), 5]], 30, today), 0)


class Revoked(unittest.TestCase):
    def test_marks_the_entry(self):
        out = build_index.Output(Path(tempfile.mkdtemp()))
        body = (EXAMPLE / "securo-plugin.json").read_bytes()
        out.add(json.loads(body), body, None, commit="1" * 40, release="v1.0.0")
        index = json.loads(out.write({"your-name/streaming": "Matches far too much"}).read_text())
        self.assertTrue(index["plugins"][0]["revoked"])
        self.assertEqual(index["plugins"][0]["revoked_reason"], "Matches far too much")


if __name__ == "__main__":
    unittest.main()
