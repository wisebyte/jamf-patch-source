#!/usr/bin/env python3
"""Fetch vendor version feeds listed in sources.json and merge new versions into definitions/<id>.json.
Only versions present in the vendor feed are ever added; existing entries are never removed.
Idempotent: a definition file is rewritten only when a new version appears (lastModified/currentVersion bump).
Creates the definition if it does not exist. Usage: check_versions.py [id ...]
"""
import datetime as dt, email.utils, json, pathlib, sys, urllib.request, xml.etree.ElementTree as ET
ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFS = ROOT / "definitions"
UA = {"User-Agent": "wisebyte-patch-source/1.0 (+https://github.com/wisebyte/jamf-patch-source)"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()

def iso(t): return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
def os_norm(v):
    if not v: return None
    p = str(v).split(".")
    while len(p) > 2 and p[-1] == "0": p.pop()
    return ".".join(p)
def vkey(v): return [int(x) if x.isdigit() else 0 for x in v.split(".")]

def f_renewedvision(s):
    out = {}
    for o in s["osVersions"]:
        url = f"https://api.renewedvision.com/v1/pro/upgrade?platform=macos&osVersion={o}&appVersion=0&buildNumber=0&includeNotes=0"
        for u in json.loads(get(url))["upgrades"]:
            if u.get("isBeta") or u.get("channel") != "production" or not u.get("version"): continue
            out[u["version"]] = (iso(dt.datetime.fromtimestamp(u["releaseDate"], dt.timezone.utc)), os_norm(u.get("minOSVersion")))
    return out

def f_logos_atom(s):
    ns = {"a": "http://www.w3.org/2005/Atom", "l": "http://services.logos.com/update/v1/"}
    out = {}
    for e in ET.fromstring(get(s["url"])).findall("a:entry", ns):
        v = e.find("l:version", ns).text.strip()
        out[v] = (iso(dt.datetime.fromisoformat(e.find("a:updated", ns).text.replace("Z", "+00:00"))),
                  os_norm((e.findtext("l:minimum-os-version", None, ns) or "").strip()))
    return out

def f_sparkle(s):
    sp = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"
    out = {}
    for url in s["urls"]:
        for it in ET.fromstring(get(url)).iter("item"):
            enc = it.find("enclosure")
            v = it.findtext(sp + "shortVersionString") or (enc is not None and enc.get(sp + "shortVersionString"))
            if not v: continue
            d = it.findtext("pubDate")
            date = iso(email.utils.parsedate_to_datetime(d)) if d else None
            mos = it.findtext(sp + "minimumSystemVersion")
            if v not in out: out[v.strip()] = (date, os_norm(mos))
    return out

FETCH = {"renewedvision": f_renewedvision, "logos_atom": f_logos_atom, "sparkle": f_sparkle}

def crit(name, value): return {"name": name, "operator": "is", "value": value, "type": "recon", "and": True}

def patch(cfg, v, date, mos):
    p = {"version": v, "releaseDate": date or iso(dt.datetime.now(dt.timezone.utc)), "standalone": True,
         "minimumOperatingSystem": mos or "10.13", "reboot": False,
         "killApps": [{"bundleId": cfg["bundleId"], "appName": cfg["appName"]}],
         "components": [{"name": cfg["name"], "version": v, "criteria": [
             crit("Application Bundle ID", cfg["bundleId"]), crit("Application Version", v)]}],
         "capabilities": [{"name": "Operating System Version", "operator": "greater than or equal",
                           "value": mos or "10.13", "type": "recon"}],
         "dependencies": []}
    return p

def run(tid, cfg):
    f = DEFS / f"{tid}.json"
    d = json.loads(f.read_text()) if f.exists() else {
        "id": tid, "name": cfg["name"], "publisher": cfg["publisher"], "appName": cfg["appName"],
        "bundleId": cfg["bundleId"], "currentVersion": "", "lastModified": "",
        "requirements": [crit("Application Bundle ID", cfg["bundleId"])], "patches": [], "extensionAttributes": []}
    feed = FETCH[cfg["source"]["type"]](cfg["source"])
    if not feed: raise RuntimeError("feed returned no versions")
    have = {p["version"] for p in d["patches"]}
    new = [v for v in feed if v not in have]
    if not new: return 0
    d["patches"] += [patch(cfg, v, *feed[v]) for v in new]
    d["patches"].sort(key=lambda p: vkey(p["version"]), reverse=True)
    d["currentVersion"] = d["patches"][0]["version"]
    d["lastModified"] = iso(dt.datetime.now(dt.timezone.utc))
    f.write_text(json.dumps(d, indent=2) + "\n")
    return len(new)

def main():
    srcs = json.loads((ROOT / "sources.json").read_text())
    ids = sys.argv[1:] or list(srcs)
    failed = 0
    for tid in ids:
        try: print(f"{tid}: +{run(tid, srcs[tid])} versions")
        except Exception as e: failed += 1; print(f"{tid}: ERROR {e}", file=sys.stderr)
    sys.exit(1 if failed == len(ids) else 0)  # one flaky vendor shouldn't block the others

if __name__ == "__main__": main()
