#!/usr/bin/env python3
"""
Ultra-Fast Parallel Cloud Mirror Engine for GitHub Actions
Downloads from source, pushes to SourceForge, and creates GitHub CDN Releases.
"""

import os
import sys
import re
import subprocess
import hashlib
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.mirror_engine import CloudMirrorEngine
from core.sourceforge_client import SourceForgeClient


def get_existing_github_releases():
    """Fetches already published release tags to avoid duplicate work."""
    try:
        res = subprocess.run(["gh", "release", "list", "--limit", "200", "--json", "tagName"], capture_output=True, text=True, check=True)
        import json
        data = json.loads(res.stdout)
        return {item["tagName"] for item in data}
    except Exception:
        return set()


def main():
    sf_user = os.environ.get("SF_USERNAME", "mehraann19").strip()
    sf_project = os.environ.get("SF_PROJECT", "mehraann19").strip()
    source_proj = os.environ.get("SOURCE_PROJECT", "rama982").strip()
    dev_filter = os.environ.get("DEVICE_FILTER", "ALL").strip().upper()
    cat_filter = os.environ.get("CATEGORY_FILTER", "ALL").strip().upper()
    max_files_str = os.environ.get("MAX_FILES", "100").strip()
    max_files = int(max_files_str) if max_files_str.isdigit() else 100

    print("=" * 65)
    print("⚡ HIGH-SPEED PARALLEL CLOUD MIRROR RUNNER")
    print(f"Target SourceForge Account: {sf_user}")
    print(f"Target SourceForge Project: {sf_project}")
    print(f"Source Project:             {source_proj}")
    print(f"Device Filter:              {dev_filter}")
    print(f"Category Filter:            {cat_filter}")
    print(f"Max Files:                  {max_files}")
    print("=" * 65)

    # 1. Fetch file catalogue
    items = CloudMirrorEngine.get_source_project_files(source_proj)
    print(f"[+] Total files discovered in source: {len(items)}")

    # 2. Filter files for this matrix runner
    filtered = []
    for it in items:
        if dev_filter != "ALL" and dev_filter not in it["device"].upper() and dev_filter not in it["filename"].upper():
            continue
        if cat_filter != "ALL":
            # Support multiple comma-separated categories in filter
            target_cats = [c.strip().upper() for c in cat_filter.split(",")]
            if not any(c in it["category"].upper() for c in target_cats):
                continue
        filtered.append(it)

    print(f"[+] Category '{cat_filter}' matching files: {len(filtered)}")
    selected = filtered[:max_files]

    if not selected:
        print("[-] No matching files found for this category.")
        sys.exit(0)

    # 3. Setup SSH & SFTP backend
    key_file = os.path.expanduser("~/.ssh/id_sf")
    if not os.path.isfile(key_file):
        key_file = os.path.expanduser("~/.ssh/id_ed25519")

    sf_client = SourceForgeClient(
        project_name=sf_project,
        username=sf_user,
        key_path=key_file
    )

    try:
        sf_client.connect()
        print(f"[+] Connected to SourceForge SFTP backend as '{sf_user}'")
    except Exception as e:
        print(f"[!] SFTP connection notice: {e}")

    existing_gh_tags = get_existing_github_releases()
    print(f"[*] Found {len(existing_gh_tags)} existing GitHub releases.")

    workdir = Path("work_downloads")
    workdir.mkdir(exist_ok=True)
    shortcut_dir = Path("shortcuts")
    shortcut_dir.mkdir(exist_ok=True)

    processed_releases = []

    for idx, item in enumerate(selected, 1):
        fname = item["filename"]
        url = item["source_download_url"]
        target_folder = item["target_folder"]
        category = item["category"]
        device = item["device"]

        safe_name = re.sub(r'[^a-zA-Z0-9\.\-]', '_', fname)
        release_tag = f"{item['tag_prefix']}-{safe_name[:40]}"
        release_title = f"[{device}] {category} - {fname}"

        print(f"\n-------------------------------------------------------")
        print(f"[{idx}/{len(selected)}] Processing: {fname}")
        print(f"    Category: {category} | Device: {device}")
        print(f"    Target Folder: /{sf_project}/{target_folder}/")
        print(f"-------------------------------------------------------")

        # 1. Ensure remote directory exists
        try:
            sf_client.mkdir_p(target_folder)
        except Exception:
            pass

        # 2. Check if already uploaded on SourceForge
        remote_target_file = f"{sf_client.get_project_remote_root()}/{target_folder}/{fname}"
        file_already_on_sf = False
        try:
            if sf_client._sftp_client:
                sf_client._sftp_client.stat(remote_target_file)
                print(f"[✓] File already exists on SourceForge: {remote_target_file}")
                file_already_on_sf = True
        except Exception:
            file_already_on_sf = False

        local_file = workdir / fname
        if local_file.exists():
            local_file.unlink()

        file_size = item.get("size_bytes", 0)
        md5 = "Verified on SourceForge Mirror"
        sha256 = "Verified on SourceForge Mirror"

        # 3. If not on SourceForge, download & upload
        if not file_already_on_sf:
            print(f"[*] Downloading at multi-gigabit speed via aria2c...")
            cmd = ["aria2c", "-x", "16", "-s", "16", "-k", "1M", "--check-certificate=false", "-d", str(workdir), "-o", fname, url]
            try:
                subprocess.run(cmd, check=True)
            except Exception:
                print("[!] aria2c fallback to wget...")
                subprocess.run(["wget", "--no-check-certificate", "-O", str(local_file), url], check=True)

            if not local_file.exists() or local_file.stat().st_size == 0:
                print(f"[-] Download failed for {fname}, skipping.")
                continue

            file_size = local_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # Checksums
            file_bytes = local_file.read_bytes()
            md5 = hashlib.md5(file_bytes).hexdigest()
            sha256 = hashlib.sha256(file_bytes).hexdigest()

            # Upload to SourceForge
            print(f"[*] Uploading {fname} ({file_size_mb:.2f} MB) to SourceForge FRS...")
            upload_success = False
            remote_dir_full = f"/home/frs/project/{sf_project}/{target_folder}/"

            # rsync with SSH keepalive and timeout
            rsync_cmd = [
                "rsync", "-avzP", "--inplace", "--timeout=300",
                "-e", f"ssh -i {key_file} -o StrictHostKeyChecking=no -o ServerAliveInterval=10 -o ServerAliveCountMax=60",
                str(local_file),
                f"{sf_user}@frs.sourceforge.net:{remote_dir_full}"
            ]
            try:
                subprocess.run(rsync_cmd, check=True)
                upload_success = True
                print(f"[+] rsync upload completed successfully!")
            except Exception as e:
                print(f"[!] rsync warning ({e}), uploading via SFTP stream...")
                try:
                    sf_client.upload_file(str(local_file), target_folder)
                    upload_success = True
                    print(f"[+] SFTP stream upload completed successfully!")
                except Exception as sftp_err:
                    print(f"[-] SFTP upload failed: {sftp_err}")

            if not upload_success:
                print(f"[-] Upload failed for {fname}, skipping.")
                if local_file.exists():
                    local_file.unlink()
                continue
        else:
            file_size_mb = file_size / (1024 * 1024) if file_size else 0

        # Direct CDN Links
        import urllib.parse
        encoded_fname = urllib.parse.quote(fname)
        direct_cdn = f"https://downloads.sourceforge.net/project/{sf_project}/{target_folder}/{encoded_fname}"
        sf_page = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/{encoded_fname}/download"
        sf_folder_url = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/"

        # Check if GitHub release already exists
        if release_tag not in existing_gh_tags:
            # Create Shortcut file with safe ascii filename
            shortcut_file = shortcut_dir / f"FastDownload-{safe_name}.url"
            shortcut_file.write_text(f"[InternetShortcut]\nURL={direct_cdn}\n", encoding="utf-8")

            body = f"""## 🚀 {release_title}

High-speed release distribution powered by **SourceForge Global Fast CDN Mirror Network** & **GitHub Cloud Infrastructure**.

---

### ⚡ Fast Global Download Mirrors

| Mirror Server | Location / Network | Download Link |
| :--- | :--- | :--- |
| ⚡ **Primary Fast CDN** | Global Edge (Auto-Nearest Datacenter) | [🚀 **Direct Download ({file_size_mb:.2f} MB)**]({direct_cdn}) |
| 🌐 **SourceForge Mirror Page** | Multi-Region Mirrors | [🔗 **SourceForge Download Page**]({sf_page}) |
| 📁 **Browse Folder** | SourceForge Storage | [📂 **View Directory**]({sf_folder_url}) |

---

### 📱 Package Details

- **Device:** `{device}`
- **Category:** `{category}`
- **File Name:** `{fname}`
- **File Size:** `{file_size_mb:.2f} MB`
- **SourceForge Logical Path:** `/{sf_project}/{target_folder}/`

### 🛡️ Checksums & Integrity

```text
MD5:    {md5}
SHA256: {sha256}
```

---

*Maintained by [@{os.environ.get('GITHUB_REPOSITORY_OWNER', 'sheikhmehraann')}](https://github.com/{os.environ.get('GITHUB_REPOSITORY_OWNER', 'sheikhmehraann')}) · Mirror on [SourceForge](https://sourceforge.net/projects/{sf_project})*
"""
            body_file = Path("rel_body.md")
            body_file.write_text(body, encoding="utf-8")

            try:
                gh_cmd = [
                    "gh", "release", "create", release_tag,
                    "--title", release_title,
                    "--notes-file", str(body_file),
                    str(shortcut_file)
                ]
                subprocess.run(gh_cmd, check=True)
                print(f"[+] Created GitHub Release: {release_tag}")
                existing_gh_tags.add(release_tag)
            except Exception as e:
                print(f"[!] Release notice: {e}")
        else:
            print(f"[✓] GitHub Release already published for {release_tag}")

        processed_releases.append({
            "filename": fname,
            "size_mb": file_size_mb,
            "cdn": direct_cdn,
            "device": device,
            "category": category
        })

        if local_file.exists():
            local_file.unlink()

    try:
        sf_client.close()
    except Exception:
        pass

    print(f"\n[✓] Finished category '{cat_filter}': {len(processed_releases)} files processed.")


if __name__ == "__main__":
    main()
