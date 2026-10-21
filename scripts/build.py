#!/usr/bin/env python3
"""Build a static Jamf Pro external patch source from definitions/*.json into _site/.
Layout (all extensionless, matching what Jamf requests):
  software.html            -> summary array of all titles (Pages serves it at /software)
  software/<id>            -> summary array for one title
  software/<a>,<b>,...     -> pre-generated combos (sorted ids) when title count <= MAX_COMBO_TITLES
  patch/<id>               -> full definition
"""
import itertools, json, pathlib, shutil, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "definitions", ROOT / "_site"
MAX_COMBO_TITLES = 12  # 2^12-1 = 4095 files; above this only single-id files are made
REQ = ["id", "name", "publisher", "currentVersion", "lastModified", "patches", "requirements"]

def summary(d):
    return {k: d[k] for k in ("id", "name", "publisher", "currentVersion", "lastModified")}

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2) + "\n")

defs = {}
for f in sorted(SRC.glob("*.json")):
    d = json.loads(f.read_text())
    missing = [k for k in REQ if k not in d]
    if missing: sys.exit(f"{f.name}: missing {missing}")
    if "," in d["id"] or "/" in d["id"]: sys.exit(f"{f.name}: id may not contain ',' or '/'")
    if d["id"] in defs: sys.exit(f"duplicate id {d['id']}")
    defs[d["id"]] = d

shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir()
ids = sorted(defs)
# /software must coexist with the software/ dir: GitHub Pages serves foo.html at /foo (200, no redirect)
write(OUT / "software.html", [summary(defs[i]) for i in ids])
for i in ids:
    write(OUT / "patch" / i, defs[i])
if len(ids) <= MAX_COMBO_TITLES:
    for n in range(1, len(ids) + 1):
        for combo in itertools.combinations(ids, n):
            write(OUT / "software" / ",".join(combo), [summary(defs[i]) for i in combo])
else:
    for i in ids: write(OUT / "software" / i, [summary(defs[i])])
(OUT / ".nojekyll").write_text("")
# Cloudflare Pages / Netlify honor this; GitHub Pages ignores it.
(OUT / "_headers").write_text("/software\n  Content-Type: application/json\n/software/*\n  Content-Type: application/json\n/patch/*\n  Content-Type: application/json\n")
(OUT / "index.html").write_text("<p>Jamf Pro external patch source. See <a href='software'>software</a>.</p>\n")
print(f"built {len(ids)} titles into {OUT}")
