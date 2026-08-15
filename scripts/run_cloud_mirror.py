#!/usr/bin/env python3
"""
Cloud Mirror Runner Script for GitHub Actions
"""

import os
import sys
import re
import subprocess
import hashlib
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.mirror_engine import CloudMirrorEngine


def main():
    sf_user = os.environ.get("SF_USERNAME", "mehraann19")
    sf_project = os.environ.get("SF_PROJECT", "mehraann19")
    source_proj = os.environ.get("SOURCE_PROJECT", "rama982")
    dev_filter = os.environ.get("DEVICE_FILTER", "ALL").upper()
    cat_filter = os.environ.get("CATEGORY_FILTER", "ALL").upper()
    max_files = int(os.environ.get("MAX_FILES", "5"))

    print(f"[*] Fetching release catalogue from SourceForge source: '{source_proj}'...")
    items = CloudMirrorEngine.get_source_project_files(source_proj)
    print(f"[*] Total files discovered: {len(items)}")

    # Apply filters
    filtered = []
    for it in items:
        if dev_filter != "ALL" and dev_filter not in it["device"].upper() and dev_filter not in it["filename"].upper():
            continue
        if cat_filter != "ALL" and cat_filter not in it["category"].upper():
            continue
        filtered.append(it)

    print(f"[*] Filtered matching files: {len(filtered)}")
    selected = filtered[:max_files]

    if not selected:
        print("[-] No files matched the selected filter.")
        sys.exit(0)

    print(f"[*] Processing {len(selected)} file(s) on GitHub high-speed runners...")

    processed_releases = []

    for idx, item in enumerate(selected, 1):
        fname = item["filename"]
        url = item["source_download_url"]
        target_folder = item["target_folder"]
        category = item["category"]
        device = item["device"]

        print(f"\n=======================================================")
        print(f"[{idx}/{len(selected)}] Downloading: {fname}")
        print(f"    Target Logical Path: /{sf_project}/{target_folder}/{fname}")
        print(f"=======================================================")

        # Download using aria2c multi-connection
        workdir = Path("work_downloads")
        workdir.mkdir(exist_ok=True)
        local_file = workdir / fname

        if local_file.exists():
            local_file.unlink()

        cmd = ["aria2c", "-x", "16", "-s", "16", "-k", "1M", "--check-certificate=false", "-d", str(workdir), "-o", fname, url]
        try:
            subprocess.run(cmd, check=True)
        except Exception:
            # Fallback
            subprocess.run(["wget", "--no-check-certificate", "-O", str(local_file), url], check=True)

        if not local_file.exists() or local_file.stat().st_size == 0:
            print(f"[-] Failed to download {fname}, skipping.")
            continue

        file_size = local_file.stat().st_size
        file_size_mb = file_size / (1024 * 1024)

        # Calculate Hashes
        md5 = hashlib.md5(local_file.read_bytes()).hexdigest()
        sha256 = hashlib.sha256(local_file.read_bytes()).hexdigest()

        # Create remote dir on SourceForge
        remote_dir = f"/home/frs/project/{sf_project}/{target_folder}"
        print(f"[*] Ensuring remote directory: {remote_dir}")
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
        print(f"[+] Successfully mirrored {fname} to SourceForge!")

        # Clean URL paths
        direct_cdn = f"https://downloads.sourceforge.net/project/{sf_project}/{target_folder}/{fname}"
        sf_page = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/{fname}/download"

        # Create Windows .url shortcut
        shortcut_dir = Path("shortcuts")
        shortcut_dir.mkdir(exist_ok=True)
        shortcut_file = shortcut_dir / f"FastDownload-{fname}.url"
        shortcut_file.write_text(f"[InternetShortcut]\nURL={direct_cdn}\n", encoding="utf-8")

        # Release Tag
        safe_name = re.sub(r'[^a-zA-Z0-9\.\-]', '_', fname)
        release_tag = f"{item['tag_prefix']}-{safe_name[:40]}"
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
            print(f"[!] GitHub Release creation notice: {e}")

        processed_releases.append({
            "filename": fname,
            "size_mb": file_size_mb,
            "cdn": direct_cdn,
            "device": device,
            "category": category
        })

        # Cleanup local downloaded file
        if local_file.exists():
            local_file.unlink()

    # Output Step Summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("### 🌟 Automated Cloud Mirror & Publish Completed!\n\n")
            f.write("| Device | Category | File Name | Size | Fast CDN Mirror |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for pr in processed_releases:
                f.write(f"| `{pr['device']}` | `{pr['category']}` | `{pr['filename']}` | `{pr['size_mb']:.1f} MB` | [⚡ Direct CDN]({pr['cdn']}) |\n")


if __name__ == "__main__":
    main()
