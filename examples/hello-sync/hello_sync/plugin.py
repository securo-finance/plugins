"""A plugin with code, as small as it gets.

Securo calls `plugin.<method>(params, context)` in its own process, with only
the standard library and the packages in requirements.txt available:

- `context.secrets`: the connection's secret fields, and tokens from signing in
- `context.config`: its other fields
- `context.securo`: `api_url`, `workspace_id` and, if the manifest asks for
  `api_scopes`, a `token` for Securo's API limited to them

`sync` gets the `state` it returned last time and returns the next one. Return
`secrets` to replace stored ones (a refreshed token, say). Raise an exception
named `NeedsAuth` when the person has to sign in or fix a key again.
"""
from datetime import datetime, timezone


class NeedsAuth(Exception):
    pass


class HelloSync:
    def sync(self, params, context):
        if context.secrets.get("token") == "wrong":
            raise NeedsAuth("the secret was refused")
        runs = params["state"].get("runs", 0) + 1
        greeting = context.config.get("greeting") or "Hello"
        return {
            "state": {
                "runs": runs,
                "message": f"{greeting}, run {runs}",
                "at": datetime.now(timezone.utc).isoformat(),
            }
        }


plugin = HelloSync()
