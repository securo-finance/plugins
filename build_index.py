#!/usr/bin/env python3
"""Build the Securo plugin index: static files a Securo instance reads.

Two modes, one output:

    build_index.py github --out site       # every repository with the `securo-plugin` topic
    build_index.py local PATH... --out site  # plugin folders on disk, to test your own

The output is `site/v1/index.json` plus a copy of each plugin's manifest and
README, each named in the index with its sha256. Serve `site/` with any static
file server and point `PLUGINS_INDEX_URL` at `.../v1/index.json`.

Only the standard library is used, so authors can run this as is (Python 3.11+).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOPIC = "securo-plugin"
MANIFEST_FILE = "securo-plugin.json"
MAX_MANIFEST_BYTES = 2 << 20
MAX_README_BYTES = 256 << 10
README_NAMES = ("README.md", "readme.md", "Readme.md")

# The same patterns Securo checks; Securo validates the whole manifest again
# before anything is installed, so these only keep obviously broken entries out.
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,38}/[a-z0-9][a-z0-9-]{0,63}$")
VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
REPOSITORY_PATTERN = re.compile(r"^https://github\.com/[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")
CODE_FIELDS = ("runtime", "network", "api_scopes")


class Invalid(Exception):
    """A plugin that can't be listed, and why."""


def now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _text(value, field: str) -> dict[str, str]:
    if isinstance(value, str):
        return {"en": value}
    if not isinstance(value, dict) or not isinstance(value.get("en"), str):
        raise Invalid(f"{field} needs text or a locale map with `en`")
    return value


def _locales(manifest: dict) -> list[str]:
    """Every locale the plugin's text is written in."""
    found: set[str] = set()

    def walk(value) -> None:
        if isinstance(value, dict):
            if "en" in value and all(isinstance(k, str) and LOCALE_PATTERN.match(k) for k in value):
                found.update(value)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk({"name": manifest.get("name"), "description": manifest.get("description"), **manifest.get("contributes", {})})
    return sorted(found)


def check_manifest(body: bytes, *, plugin_id: str | None = None, repository: str | None = None) -> dict:
    """The manifest as JSON, if it's one this index can list."""
    if len(body) > MAX_MANIFEST_BYTES:
        raise Invalid(f"{MANIFEST_FILE} is larger than {MAX_MANIFEST_BYTES} bytes")
    try:
        manifest = json.loads(body)
    except ValueError as exc:
        raise Invalid(f"{MANIFEST_FILE} isn't JSON") from exc
    if not isinstance(manifest, dict):
        raise Invalid(f"{MANIFEST_FILE} isn't an object")
    code = [field for field in CODE_FIELDS if field in manifest]
    if code:
        raise Invalid(f"plugins with code aren't supported yet ({', '.join(code)})")
    for field, pattern in (("id", ID_PATTERN), ("version", VERSION_PATTERN),
                           ("min_securo_version", VERSION_PATTERN), ("repository", REPOSITORY_PATTERN)):
        if not isinstance(manifest.get(field), str) or not pattern.match(manifest[field]):
            raise Invalid(f"`{field}` is missing or malformed")
    if not isinstance(manifest.get("license"), str) or not 2 <= len(manifest["license"]) <= 64:
        raise Invalid("`license` is missing")
    _text(manifest.get("name"), "name")
    _text(manifest.get("description"), "description")
    contributes = manifest.get("contributes")
    if not isinstance(contributes, dict) or not all(isinstance(v, list) for v in contributes.values()):
        raise Invalid("`contributes` must map each kind to a list")
    if not any(contributes.values()):
        raise Invalid("contributes nothing")
    if plugin_id is not None and manifest["id"] != plugin_id:
        raise Invalid(f"`id` is {manifest['id']}, expected {plugin_id}")
    if repository is not None and manifest["repository"].lower() != repository.lower():
        raise Invalid(f"`repository` is {manifest['repository']}, expected {repository}")
    return manifest


class Output:
    """Writes `v1/` and collects its entries."""

    def __init__(self, root: Path):
        self.v1 = root / "v1"
        (self.v1 / "manifests").mkdir(parents=True, exist_ok=True)
        (self.v1 / "readmes").mkdir(parents=True, exist_ok=True)
        self.entries: list[dict] = []

    def add(self, manifest: dict, manifest_body: bytes, readme: bytes | None, *, commit: str, release: str,
            stars: int = 0, stars_7d: int = 0, topics: list[str] | None = None,
            added_at: datetime | None = None, updated_at: datetime | None = None) -> dict:
        stem = f"{manifest['id'].replace('/', '--')}--{commit}"
        (self.v1 / "manifests" / f"{stem}.json").write_bytes(manifest_body)
        entry = {
            "id": manifest["id"],
            "repository": manifest["repository"],
            "release": release,
            "commit": commit,
            "manifest": f"manifests/{stem}.json",
            "manifest_sha256": sha256(manifest_body),
            "name": manifest["name"],
            "description": manifest["description"],
            "version": manifest["version"],
            "license": manifest["license"],
            "min_securo_version": manifest["min_securo_version"],
            "contributes": {kind: len(items) for kind, items in manifest["contributes"].items()},
            "locales": _locales(manifest),
            "topics": topics or [],
            "stars": stars,
            "stars_7d": stars_7d,
            "added_at": iso(added_at) if added_at else None,
            "updated_at": iso(updated_at) if updated_at else None,
        }
        if readme is not None and len(readme) <= MAX_README_BYTES:
            (self.v1 / "readmes" / f"{stem}.md").write_bytes(readme)
            entry |= {"readme": f"readmes/{stem}.md", "readme_sha256": sha256(readme)}
        self.entries.append(entry)
        return entry

    def write(self, revoked: dict[str, str], extra: dict | None = None) -> Path:
        for entry in self.entries:
            if entry["id"] in revoked:
                entry |= {"revoked": True, "revoked_reason": revoked[entry["id"]] or None}
        self.entries.sort(key=lambda e: e["id"])
        path = self.v1 / "index.json"
        # No timestamp: an index that didn't change is byte for byte the same, so publishing it is a no-op.
        path.write_text(json.dumps({"plugins": self.entries, **(extra or {})}, indent=2, ensure_ascii=False) + "\n")
        return path


def load_revoked(path: Path) -> dict[str, str]:
    """`revoked.json`: the one list kept by hand. id -> reason."""
    if not path.exists():
        return {}
    return {item["id"]: item.get("reason", "") for item in json.loads(path.read_text())}


# --- local ------------------------------------------------------------------

def _git_commit(folder: Path) -> str:
    """The folder's git commit, or a hash of its manifest when it isn't a repository."""
    try:
        out = subprocess.run(["git", "-C", str(folder), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        commit = out.stdout.strip()
        if re.fullmatch(r"[0-9a-f]{40}", commit):
            return commit
    except (OSError, subprocess.CalledProcessError):
        pass
    return hashlib.sha1((folder / MANIFEST_FILE).read_bytes()).hexdigest()


def build_local(folders: list[Path], out: Output) -> int:
    failed = 0
    for folder in folders:
        try:
            body = (folder / MANIFEST_FILE).read_bytes()
            manifest = check_manifest(body)
        except (OSError, Invalid) as exc:
            print(f"✗ {folder}: {exc}", file=sys.stderr)
            failed += 1
            continue
        readme = next((folder / n for n in README_NAMES if (folder / n).exists()), None)
        stamp = now()
        out.add(manifest, body, readme.read_bytes() if readme else None, commit=_git_commit(folder),
                release=f"v{manifest['version']}", added_at=stamp, updated_at=stamp)
        print(f"✓ {manifest['id']} {manifest['version']}")
    return failed


# --- github -----------------------------------------------------------------

class GitHub:
    def __init__(self, token: str | None):
        self.token = token

    def get(self, url: str, *, accept: str = "application/vnd.github+json", limit: int | None = None) -> bytes:
        if not url.startswith("https://"):
            url = "https://api.github.com" + url
        headers = {"Accept": accept, "User-Agent": "securo-plugin-indexer", "X-GitHub-Api-Version": "2022-11-28"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
            body = response.read((limit or 0) + 1 if limit else -1)
        if limit and len(body) > limit:
            raise Invalid(f"{url} is larger than {limit} bytes")
        return body

    def json(self, url: str):
        return json.loads(self.get(url))

    def repositories(self) -> list[dict]:
        found, page = [], 1
        while True:
            q = urllib.parse.quote(f"topic:{TOPIC} fork:false archived:false")
            data = self.json(f"/search/repositories?q={q}&per_page=100&page={page}")
            found += data["items"]
            if len(data["items"]) < 100 or len(found) >= 1000:  # search stops at 1000
                return found
            page += 1


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def stars_gained(history: list[list], stars: int, today: datetime) -> int:
    """Stars gained since the newest count at least 7 days old (0 until there is one)."""
    cutoff = today - timedelta(days=7)
    old = [count for day, count in history if _parse_time(day) <= cutoff]
    return max(stars - old[-1], 0) if old else 0


def build_github(gh: GitHub, out: Output, state: dict) -> tuple[int, dict]:
    """Lists every tagged repository at the commit of its latest release."""
    today, failed, seen = now(), 0, {}
    for repo in gh.repositories():
        full = repo["full_name"]
        try:
            try:
                release = gh.json(f"/repos/{full}/releases/latest")
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    raise Invalid("no release yet") from exc
                raise
            tag = release["tag_name"]
            commit = gh.json(f"/repos/{full}/commits/{urllib.parse.quote(tag, safe='')}")["sha"]
            body = gh.get(f"https://raw.githubusercontent.com/{full}/{commit}/{MANIFEST_FILE}", limit=MAX_MANIFEST_BYTES)
            manifest = check_manifest(body, plugin_id=full.lower(), repository=repo["html_url"])
            try:
                readme = gh.get(f"/repos/{full}/readme?ref={commit}", accept="application/vnd.github.raw")
            except (urllib.error.HTTPError, Invalid):
                readme = None
            known = state.get(manifest["id"], {})
            added_at = _parse_time(known.get("added_at")) or today
            history = [h for h in known.get("stars", []) if _parse_time(h[0]) > today - timedelta(days=30)]
            stars = repo["stargazers_count"]
            out.add(manifest, body, readme, commit=commit, release=tag, stars=stars,
                    stars_7d=stars_gained(history, stars, today),
                    topics=sorted(t for t in repo.get("topics", []) if t != TOPIC),
                    added_at=added_at, updated_at=_parse_time(release.get("published_at")) or today)
            # One count a day is enough for a weekly trend, and keeps the file from changing every run.
            history = [h for h in history if h[0][:10] != iso(today)[:10]] + [[iso(today), stars]]
            seen[manifest["id"]] = {"added_at": iso(added_at), "stars": history}
            print(f"✓ {manifest['id']} {manifest['version']} ({tag})")
        except (Invalid, urllib.error.URLError, KeyError, ValueError) as exc:
            print(f"✗ {full}: {exc}", file=sys.stderr)
            failed += 1
    return failed, seen


def load_state(source: str | None) -> dict:
    """What the last run remembered (first seen, star counts), read from the published site."""
    if not source:
        return {}
    try:
        if source.startswith("https://"):
            with urllib.request.urlopen(source, timeout=30) as response:
                return json.loads(response.read())
        return json.loads(Path(source).read_text())
    except (OSError, ValueError, urllib.error.URLError) as exc:
        print(f"! no previous state ({exc}), starting fresh", file=sys.stderr)
        return {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("github", "local"))
    parser.add_argument("paths", nargs="*", type=Path, help="plugin folders (local mode)")
    parser.add_argument("--out", type=Path, default=Path("site"))
    parser.add_argument("--revoked", type=Path, default=Path(__file__).with_name("revoked.json"))
    parser.add_argument("--state", help="the previous run's v1/state.json, as a URL or a path (github mode)")
    args = parser.parse_args()

    out = Output(args.out)
    if args.mode == "local":
        if not args.paths:
            parser.error("local mode needs at least one plugin folder")
        failed = build_local(args.paths, out)
        index = out.write(load_revoked(args.revoked))
    else:
        failed, state = build_github(GitHub(os.environ.get("GITHUB_TOKEN")), out, load_state(args.state))
        (out.v1 / "state.json").write_text(json.dumps(state, indent=1) + "\n")
        index = out.write(load_revoked(args.revoked))
    print(f"{len(out.entries)} plugin(s) in {index}, {failed} skipped")
    return 1 if args.mode == "local" and failed else 0


if __name__ == "__main__":
    sys.exit(main())
