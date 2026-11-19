import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import build_index  # noqa: E402

EXAMPLE = ROOT / "examples" / "streaming"
CODE_EXAMPLE = ROOT / "examples" / "hello-sync"


def build(*folders: Path) -> tuple[subprocess.CompletedProcess, Path]:
    out = Path(tempfile.mkdtemp())
    result = subprocess.run(
        [sys.executable, str(ROOT / "build_index.py"), "local", *map(str, folders), "--out", str(out)],
        capture_output=True, text=True,
    )
    return result, out / "v1"


class LocalIndex(unittest.TestCase):
    def build(self, *folders: Path) -> tuple[subprocess.CompletedProcess, Path]:
        return build(*folders)

    def test_copies_are_named_by_their_checksum(self):
        result, v1 = self.build(EXAMPLE)
        self.assertEqual(result.returncode, 0, result.stderr)
        [entry] = json.loads((v1 / "index.json").read_text())["plugins"]
        self.assertEqual(entry["id"], "your-name/streaming")
        self.assertEqual(entry["contributes"], {"categories": 1, "rules": 1})
        self.assertEqual(entry["locales"], ["en", "pt-BR"])
        self.assertEqual(entry["workspaces"], ["personal", "business"])
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


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 24


class Icons(unittest.TestCase):
    def plugin(self, icon: bytes | None, name: str = "icon.png") -> Path:
        folder = Path(tempfile.mkdtemp())
        (folder / "securo-plugin.json").write_bytes((EXAMPLE / "securo-plugin.json").read_bytes())
        if icon is not None:
            (folder / name).write_bytes(icon)
        return folder

    def build(self, folder: Path) -> tuple[subprocess.CompletedProcess, dict, Path]:
        result, v1 = build(folder)
        self.assertEqual(result.returncode, 0, result.stderr)
        [entry] = json.loads((v1 / "index.json").read_text())["plugins"]
        return result, entry, v1

    def test_the_icon_at_the_root_is_copied_under_its_checksum(self):
        for icon, name, extension in ((PNG, "icon.png", "png"), (WEBP, "icon.webp", "webp")):
            with self.subTest(name):
                _, entry, v1 = self.build(self.plugin(icon, name))
                digest = hashlib.sha256(icon).hexdigest()
                self.assertEqual(entry["icon"], f"icons/{digest}.{extension}")  # named by its checksum
                self.assertEqual((v1 / entry["icon"]).read_bytes(), icon)

    def test_a_plugin_without_an_icon_is_listed_without_one(self):
        result, entry, _ = self.build(self.plugin(None))
        self.assertNotIn("icon", entry)
        self.assertEqual(result.stderr, "")
        _, entry, _ = self.build(self.plugin(PNG, "logo.png"))  # only icon.png or icon.webp, at the root
        self.assertNotIn("icon", entry)

    def test_an_icon_that_breaks_a_rule_is_left_out_and_the_plugin_still_listed(self):
        for icon, reason in ((b"<svg/>", "not a PNG or WebP"), (b"GIF89a" + b"\x00" * 32, "not a PNG or WebP"),
                             (PNG + b"\x00" * build_index.MAX_ICON_BYTES, "larger than 64 KB")):
            with self.subTest(reason):
                result, entry, _ = self.build(self.plugin(icon))
                self.assertNotIn("icon", entry)
                self.assertIn(reason, result.stderr)

    def test_an_icon_that_is_a_link_is_left_out(self):
        outside = Path(tempfile.mkdtemp()) / "icon.png"
        outside.write_bytes(PNG)
        folder = self.plugin(None)
        (folder / "icon.png").symlink_to(outside)
        _, entry, _ = self.build(folder)
        self.assertNotIn("icon", entry)

    def test_the_manifest_is_left_as_it_is(self):
        folder = self.plugin(PNG)
        _, entry, v1 = self.build(folder)
        self.assertEqual((v1 / entry["manifest"]).read_bytes(), (EXAMPLE / "securo-plugin.json").read_bytes())


class FakeGitHub:
    """Answers `get` from a map of file name to bytes, or to the error fetching it raises."""

    def __init__(self, files: dict) -> None:
        self.files, self.asked = files, []

    def get(self, url: str, *, accept: str = "", limit: int | None = None) -> bytes:
        name = url.rsplit("/", 1)[-1]
        self.asked.append(name)
        found = self.files.get(name, 404)
        if isinstance(found, int):
            raise urllib.error.HTTPError(url, found, "error", None, None)  # type: ignore[arg-type]
        if limit and len(found) > limit:
            raise build_index.Invalid(f"{url} is larger than {limit} bytes")
        return found


class GitHubIcons(unittest.TestCase):
    def icon(self, files: dict) -> tuple[bytes | None, list[str], str]:
        gh, errors = FakeGitHub(files), io.StringIO()
        with contextlib.redirect_stderr(errors):
            found = build_index._github_icon(gh, "maria/casa", "1" * 40)  # type: ignore[arg-type]
        return found, gh.asked, errors.getvalue()

    def test_the_first_icon_the_repository_has_is_read_at_the_release_commit(self):
        self.assertEqual(self.icon({"icon.png": PNG, "icon.webp": WEBP}), (PNG, ["icon.png"], ""))
        self.assertEqual(self.icon({"icon.webp": WEBP}), (WEBP, ["icon.png", "icon.webp"], ""))

    def test_a_repository_without_an_icon_has_none_and_no_warning(self):
        self.assertEqual(self.icon({}), (None, ["icon.png", "icon.webp"], ""))

    def test_an_icon_that_is_too_large_or_cant_be_read_is_left_out_as_in_a_local_folder(self):
        for png, reason in ((PNG + b"\x00" * build_index.MAX_ICON_BYTES, "larger than"), (500, "500")):
            with self.subTest(reason):
                found, asked, errors = self.icon({"icon.png": png, "icon.webp": WEBP})
                self.assertIsNone(found)
                self.assertEqual(asked, ["icon.png"])  # the other name isn't a fallback
                self.assertIn(reason, errors)


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
        for changes in ({"version": "1.0"}, {"contributes": {"rules": []}}, {"name": {"pt-BR": "x"}},
                        {"workspaces": []}, {"workspaces": ["family"]}, {"workspaces": ["business", "business"]}):
            with self.subTest(changes), self.assertRaises(build_index.Invalid):
                build_index.check_manifest(self.manifest(**changes))


    def test_a_plugin_can_be_limited_to_one_workspace_type(self):
        self.assertEqual(build_index.check_manifest(self.manifest(workspaces=["business"]))["workspaces"], ["business"])


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
