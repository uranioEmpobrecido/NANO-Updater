#!/usr/bin/env python3
"""Publishes the release firmware listed in releases.json into the site's product folders.

    python3 release.py              # every product in releases.json
    python3 release.py fum iso-f1   # only these

For each product: copies its .bin files from the release folder (releases.json "source") into
<slug>/firmware/, checks each against the product's settings in products.json (the reset vector
where that product's firmware has it, the size), and writes <slug>/firmware.json, signed as firmware.json.sig. A product with
several builds gets them as variants, and the page asks which one the device needs. Every build
carries its file's date; one with a "version" in releases.json is shown by that version, the rest
by their date. Then run build.py if the pages changed, commit and push.

The FX-DR2 is not here: its firmware comes from NANO-FX-DR (tools/web_updater/publish.sh).
"""
import hashlib, json, os, re, shutil, struct, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

# The Ed25519 key that signs each firmware.json. It lives outside every repository and is
# never published; only its public half is embedded in template.html. The page refuses any
# firmware whose signature does not verify, so a host compromise that can rewrite the .bin
# and its firmware.json still cannot make a browser flash it.
KEY = Path(os.environ.get("NANO_SIGNING_KEY", "~/.nano/firmware-signing/nano-firmware-ed25519.pem")).expanduser()

def sign(path):
    """Writes <path>.sig: an Ed25519 signature over the file's exact bytes."""
    if not KEY.exists():
        sys.exit(f"no signing key at {KEY}.\n"
                 f"Set NANO_SIGNING_KEY, or restore it from your backup. Do not publish unsigned\n"
                 f"firmware: the pages refuse it, so it would only look broken to every user.")
    try:
        sig = subprocess.run(["openssl", "pkeyutl", "-sign", "-inkey", str(KEY), "-rawin", "-in", str(path)],
                             capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        sys.exit(f"could not sign {path.name}: {e}")
    if len(sig) != 64:
        sys.exit(f"the signature for {path.name} is {len(sig)} bytes, not the 64 Ed25519 produces")
    (path.parent / (path.name + ".sig")).write_bytes(sig)

def check(data, p, name):
    if p.get("maxSize") and len(data) > p["maxSize"]:
        sys.exit(f"{name}: {len(data)} B is more than the {p['maxSize']} B it may be")
    reset = struct.unpack_from("<I", data, 4)[0]
    ranges = [(int(a, 16), int(b, 16)) for a, b in p.get("resetVector", [])]
    if not (reset & 1 and any(a <= reset < b for a, b in ranges)):
        sys.exit(f"{name}: reset vector 0x{reset:08x} is not where {p['name']} firmware has it")

def slug_file(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s)

def main():
    rel = json.loads((HERE / "releases.json").read_text())
    cat = json.loads((HERE / "products.json").read_text())
    src = Path(rel["source"]).expanduser()
    wanted = sys.argv[1:] or list(rel["products"])
    for slug in wanted:
        p = cat["products"][slug]
        out = HERE / slug
        if (out / "firmware").exists():
            shutil.rmtree(out / "firmware")
        (out / "firmware").mkdir(parents=True)
        variants = []
        for v in rel["products"][slug]:
            path = src / v["file"]
            data = path.read_bytes()
            check(data, p, v["file"])
            date = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
            name = f"firmware/{slug_file(path.name)}"
            (out / name).write_bytes(data)
            build = {"id": v.get("id", ""), "name": v.get("name", p["name"])}
            if v.get("version"):
                build["version"] = v["version"]
            build.update({"date": date, "file": name, "size": len(data), "sha256": hashlib.sha256(data).hexdigest()})
            variants.append(build)
        meta = {"product": p["name"], "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if len(variants) == 1:
            v = variants[0]
            meta.update({k: v[k] for k in ("version", "date", "file", "size", "sha256") if k in v})
        else:
            meta["variants"] = variants
        (out / "firmware.json").write_text(json.dumps(meta, indent=2) + "\n")
        sign(out / "firmware.json")
        print(f"{slug}: " + ", ".join(f"{v['name']} {v.get('version', v['date'])} ({v['size']} B)" for v in variants))

if __name__ == "__main__":
    main()
