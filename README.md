# Static Jamf Pro External Patch Source (GitHub Pages)

1. Add/edit title definitions in `definitions/<TitleId>.json` (Jamf patch definition schema).
2. `python3 scripts/build.py` -> `_site/` (`software`, `software/<ids>`, `patch/<id>`).
3. Test locally: `python3 scripts/serve_local.py 8000`, then `curl localhost:8000/software`.
4. Push to GitHub `main`; in repo Settings > Pages set Source = "GitHub Actions". The workflow publishes `_site/`.

## Jamf Pro setup
Settings > Computer Management > Patch Management > + New external source:
- Server: `<user>.github.io/<repo>` (no `https://`; a path prefix is allowed — Jamf's API example uses `host_name` `patch.url.com/v1`, and community PatchServer uses `<host>/jamf/v1`)
- Port: `443`, Use SSL: on. Then click Test.

## Caveats
- **`/software` vs `software/`:** a path can't be both file and directory, so the index is `software.html`; GitHub Pages serves `/software` from it with 200 (no redirect), but as `text/html`.
- **Content-Type:** GitHub Pages serves extensionless files as `application/octet-stream` and cannot set custom headers. Jamf parses the body; verify with the Test button + adding a title. If it rejects it, deploy the same `_site/` to Cloudflare Pages (free, honors the generated `_headers` file -> `application/json`).
- **`/software/<a>,<b>`:** Jamf requests the comma-separated list of subscribed titles. Static hosting can't parse it, so the build pre-generates every combination in sorted-id order (up to 12 titles). If Jamf asks in another order you'll get 404 for that call (watch `serve_local.py` logs to see the exact order your Jamf sends). Past 12 titles only single-id files are generated.
- Pages URLs are case-sensitive; ids must not contain `,` or `/`.

## Wisebyte Catalog titles & version checker
- `sources.json`: per-title vendor feed config (bundle ID verified from vendor Info.plist/PackageInfo).
- `scripts/check_versions.py`: fetches feeds, adds any new versions (never invents or removes), bumps `currentVersion`/`lastModified`. Idempotent.
- `.github/workflows/check-versions.yml`: runs every 6 h + manual dispatch, commits to `main` (Cloudflare Pages redeploys on push).
- Note: commits pushed with the default `GITHUB_TOKEN` do not trigger other workflows, but Cloudflare Pages' Git integration still deploys them.
- `/software/{a,b,...}` combos are pre-generated only while there are <= 12 titles (2^n files). Beyond that only single ids + the full list are built; arbitrary combos will move to a Cloudflare Worker.
- Titles were filtered against Jamf's Patch Management Software Titles list and App Installers list; don't add titles Jamf already patches.
