# Securo plugins

The index behind the plugin catalog in [Securo](https://github.com/securo-finance/securo).

A plugin is a public GitHub repository with a `securo-plugin.json` at its root. A data plugin brings categories, category groups and rules to a workspace; a theme plugin brings looks for the library. A plugin with code adds integrations with outside services, run by Securo in an isolated runner. Securo shows a preview of exactly what changes before anything is installed: for a plugin with code, the hosts it reaches and what it may read or change, each with your stated reason.

There's no review step: any repository with the `securo-plugin` topic, a release and a valid manifest is listed. Plugins aren't reviewed by the Securo team, so read the preview.

## Publish a plugin

1. Create a public repository and add `securo-plugin.json` at its root (start from [`examples/streaming`](examples/streaming)).
2. Add the `securo-plugin` topic to the repository.
3. Publish a GitHub release. The index pins your plugin to the commit of the latest release, never to a branch, so pushing to `main` changes nothing until you release.

The index is rebuilt every 6 hours. A new release appears as an update for workspaces that have the plugin installed.

## The manifest

```json
{
  "id": "your-name/streaming",
  "name": { "en": "Streaming", "pt-BR": "Streaming" },
  "description": "A Streaming category with rules for the common video and music services.",
  "version": "1.0.0",
  "repository": "https://github.com/your-name/streaming",
  "license": "MIT",
  "min_securo_version": "0.19.0",
  "contributes": {
    "category_groups": [],
    "categories": [{ "key": "streaming", "name": "Streaming", "group": "lifestyle", "icon": "tv" }],
    "rules": [
      {
        "key": "video-and-music",
        "name": "Streaming services",
        "conditions_op": "or",
        "conditions": [{ "field": "description", "op": "contains", "value": "NETFLIX" }],
        "actions": [{ "op": "set_category", "value": "streaming" }]
      }
    ]
  }
}
```

- `id` is `owner/repository` in lowercase and must match where the plugin lives, as must `repository`.
- `version` is `MAJOR.MINOR.PATCH`; bump it with every release.
- Any text can be a string or a map of locales with an `en` entry.
- `key` identifies an item across versions: keep it stable, since renaming a key replaces the item. A category's `group` and a rule's `set_category` name a key of this plugin or a built-in one (`food`, `groceries`, `transport`, `lifestyle`, ...).
- Rule conditions use `description`, `payee`, `notes`, `amount`, `type`, `date` or `status`; actions are `set_category`, `set_description`, `append_notes` and `ignore`.
- Plugins with code add `runtime`, `network` and `api_scopes` (below).

Securo validates the whole manifest again before installing, so the preview is the final word on whether it applies.

## Themes

A plugin can add themes to Securo's library: colors for its design tokens in light and dark, an optional corner radius (0 to 1 rem) and an optional font (`sans`, `mono` or `serif`, from the device's own fonts).

```json
"contributes": {
  "themes": [
    {
      "key": "matrix",
      "name": "Matrix",
      "radius": 0,
      "font": "mono",
      "dark": { "background": "#000000", "foreground": "#B6FFB9", "primary": "#00FF41", "primary-foreground": "#001A07" },
      "light": { "background": "#F3FFF4", "foreground": "#002B0A", "primary": "#007A1F", "primary-foreground": "#FFFFFF" }
    }
  ]
}
```

- Tokens: `background`, `foreground`, `card`, `primary`, `primary-foreground`, `muted`, `muted-foreground`, `border`, `chart-1` to `chart-12`, `chart-muted`, `chart-income`, `chart-expense`. Each value is a `#RRGGBB` color; anything else is refused.
- Text has to stay readable: `foreground` and `muted-foreground` on `background` and `card`, and `primary-foreground` on `primary`, need a contrast of 4.5:1 when both are set.
- No CSS, images or downloaded fonts: a theme is only colors, so nothing leaves the person's server.

## Plugins with code

Start from [`examples/hello-sync`](examples/hello-sync). On top of the fields above:

```json
{
  "runtime": { "entrypoint": "hello_sync.plugin:plugin", "lockfile": "requirements.txt" },
  "network": [{ "host": "api.example.com", "purpose": "Reads your payouts" }],
  "api_scopes": [{ "scope": "transactions:write", "purpose": "Adds your payouts as transactions" }],
  "contributes": {
    "integrations": [
      {
        "key": "account",
        "name": "Example",
        "auth": "credentials",
        "fields": [{ "key": "api_key", "label": "API key", "secret": true }],
        "sync_minutes": 60
      }
    ]
  }
}
```

- `runtime.entrypoint` is `module:attribute`. Securo calls `attribute.<method>(params, context)`: `sync` on the schedule, and `oauth_url` / `oauth_exchange` for integrations with `"auth": "oauth"`. The example's docstring describes `context` and what `sync` returns.
- `runtime.lockfile` is a requirements file with a hash for every package (`uv export --format requirements-txt`). Packages install as wheels only, for Python 3.14.
- `network` lists every host the code may reach. Anything else is refused, and so are private addresses. Without `network`, nothing leaves the server.
- `api_scopes` gives the code a token for Securo's API, limited to those scopes, for each connection. Leave it out if the plugin doesn't touch the workspace.
- Only the workspace owner can install a plugin with code. The index copies the source at the release commit; Securo installs only that copy, checked against its sha256.

## Test your plugin locally

You don't need to publish anything to try a plugin in your own Securo:

```bash
python3 build_index.py local path/to/your-plugin --out site
python3 -m http.server 8787 --bind 127.0.0.1 --directory site
```

Then start Securo with:

```bash
PLUGINS_ENABLED=true
PLUGINS_INDEX_URL=http://127.0.0.1:8787/v1/index.json
```

When Securo runs in Docker, use `http://host.docker.internal:8787/v1/index.json` instead. Rebuild the index after each change to the manifest; the catalog checks each copy against its sha256.

## The index format

`v1/index.json` lists every plugin with its pinned commit, the sha256 of the copied manifest, README and, for plugins with code, source archive, and what the catalog shows (name, description, counts per kind, locales, stars, dates). Securo fetches the index only when someone opens the catalog, reads manifests and READMEs only from the index's own host and refuses any copy whose sha256 doesn't match. No instance talks to GitHub, and nothing is counted: popularity is GitHub stars.

You can host a mirror or your own index anywhere that serves static files and point `PLUGINS_INDEX_URL` at it.

## Revoking a plugin

[`revoked.json`](revoked.json) is the one list kept by hand:

```json
[{ "id": "someone/plugin", "reason": "Recategorizes every transaction" }]
```

A revoked plugin can't be installed or updated; workspaces that have it can still remove it. To report a plugin, open an issue.

## License

[AGPL-3.0](LICENSE)
