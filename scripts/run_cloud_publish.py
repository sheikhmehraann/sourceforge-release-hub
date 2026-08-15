#!/usr/bin/env python3
"""
Cloud Publish Script for GitHub Actions
Downloads single file URL at high speed, uploads to SourceForge, and creates GitHub Release.
"""

import os
import sys
import subprocess
import hashlib
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.mirror_engine import CloudMirrorEngine


def main():
    sf_user = os.environ.get("SF_USERNAME", "mehraann19")
    sf_project = os.environ.get("SF_PROJECT", "mehraann19")
    file_url = os.environ.get("FILE_URL", "").strip()
    category = os.environ.get("CATEGORY", "FLASHABLE").strip()
    device = os.environ.get("DEVICE", "X6871").strip()
    subfolder = os.environ.get("SUBFOLDER", "").strip()
    release_tag = os.environ.get("RELEASE_TAG", "").strip()
    release_title = os.environ.get("RELEASE_TITLE", "").strip()
    changelog = os.environ.get("CHANGELOG", "Initial high-speed release mirrored via SourceForge Release Hub.").strip()

    if not file_url:
        print("[-] Error: FILE_URL is empty.")
        sys.exit(1)

    print(f"[*] Starting high-speed cloud fetch for: {file_url}")

    workdir = Path("work_downloads")
    workdir.mkdir(exist_ok=True)

    # Multi-connection download
    cmd = ["aria2c", "-x", "16", "-s", "16", "-k", "1M", "--check-certificate=false", "-d", str(workdir), file_url]
    try:
        subprocess.run(cmd, check=True)
    except Exception:
        subprocess.run(["wget", "--no-check-certificate", "-P", str(workdir), file_url], check=True)

    files = sorted(workdir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("[-] Error: No files downloaded.")
        sys.exit(1)

    local_file = files[0]
    fname = local_file.name
    file_size = local_file.stat().st_size
    file_size_mb = file_size / (1024 * 1024)

    print(f"[+] Downloaded: {fname} ({file_size_mb:.2f} MB)")

    # Calculate Hashes
    md5 = hashlib.md5(local_file.read_bytes()).hexdigest()
    sha256 = hashlib.sha256(local_file.read_bytes()).hexdigest()

    # Determine logical path
    mapped = CloudMirrorEngine.map_file_to_logical_path(fname)
    if subfolder:
        target_folder = f"{mapped['target_folder']}/{subfolder}"
    else:
        target_folder = mapped["target_folder"]

    print(f"[*] Target Logical SourceForge Directory: /{sf_project}/{target_folder}/")

    # Create remote dir on SourceForge
    remote_dir = f"/home/frs/project/{sf_project}/{target_folder}"
    subprocess.run(["ssh", "-i", os.path.expanduser("~/.ssh/id_sf"), "-o", "StrictHostKeyChecking=no", f"{sf_user}@frs.sourceforge.net", f"mkdir -p '{remote_dir}'"], check=False)

    # RSYNC to SourceForge FRS
    print(f"[*] Uploading to SourceForge FRS mirror...")
    rsync_cmd = [
        "rsync", "-avP",
        "-e", f"ssh -i {os.path.expanduser('~/.ssh/id_sf')} -o StrictHostKeyChecking=no",
        str(local_file),
        f"{sf_user}@frs.sourceforge.net:{remote_dir}/"
    ]
    subprocess.run(rsync_cmd, check=True)
    print(f"[+] Successfully uploaded {fname} to SourceForge!")

    direct_cdn = f"https://downloads.sourceforge.net/project/{sf_project}/{target_folder}/{fname}"
    sf_page = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/{fname}/download"

    # Create Windows .url shortcut
    shortcut_dir = Path("shortcuts")
    shortcut_dir.mkdir(exist_ok=True)
    shortcut_file = shortcut_dir / f"FastDownload-{fname}.url"
    shortcut_file.write_text(f"[InternetShortcut]\nURL={direct_cdn}\n", encoding="utf-8")

    # Release Tag & Title
    if not release_tag:
        release_tag = f"{mapped['tag_prefix']}-{device}-{fname[:30]}"
    if not release_title:
        release_title = f"[{device}] {category} - {fname}"

    # Release Markdown Body
    body = f"""## 🚀 {release_title}

High-speed release distribution powered by **SourceForge Global Fast CDN Mirror Network** & **GitHub Cloud Infrastructure**.

---

### ⚡ Fast Global Download Mirrors

| Mirror Server | Location / Network | Download Link |
| :--- | :--- | :--- |
| ⚡ **Primary Fast CDN** | Global Edge (Auto-Nearest Datacenter) | [🚀 **Direct Download ({file_size_mb:.2f} MB)**]({direct_cdn}) |
| 🌐 **SourceForge Mirror Page** | Multi-Region Mirrors | [🔗 **SourceForge Download Page**]({sf_page}) |
| 📁 **Browse Folder** | SourceForge Storage | [📂 **View Directory**](https://sourceforge.net/projects/{sf_project}/files/{target_folder}/) |

---

### 📱 Package Details

- **Device:** `{device}`
- **Category:** `{category}`
- **File Name:** `{fname}`
- **File Size:** `{file_size_mb:.2f} MB` (`{file_size}` bytes)
- **SourceForge Logical Path:** `/{sf_project}/{target_folder}/`

### 🛡️ Checksums & Integrity

```text
MD5:    {md5}
SHA256: {sha256}
```

---

### 📝 Changelog & Notes

{changelog}

---

*Maintained by [@sheikhmehraann](https://github.com/sheikhmehraann) · Mirror on [SourceForge](https://sourceforge.net/projects/{sf_project})*
"""
    body_file = Path("rel_body.md")
    body_file.write_text(body, encoding="utf-8")

    # Create GitHub Release
    try:
        gh_cmd = [
            "gh", "release", "create", release_tag,
            "--title", release_title,
            "--notes-file", str(body_file),
            str(shortcut_file)
        ]
        subprocess.run(gh_cmd, check=True)
        print(f"[+] Created GitHub Release: {release_tag}")
    except Exception as e:
        print(f"[!] GitHub Release notice: {e}")

    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(f"### 🌟 Release Published & Mirrored!\n\n")
            f.write(f"- **File:** `{fname}` ({file_size_mb:.2f} MB)\n")
            f.write(f"- **Direct Fast CDN Mirror:** [{direct_cdn}]({direct_cdn})\n")
            f.write(f"- **GitHub Release:** `{release_tag}`\n")


if __name__ == "__main__":
    main()
