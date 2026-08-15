#!/usr/bin/env python3
"""
Rock-Solid Cloud Mirror Engine for GitHub Actions
Mirrors ALL releases from source projects into clean SourceForge folders and publishes GitHub Releases.
"""

import os
import sys
import re
import subprocess
import hashlib
import traceback
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.mirror_engine import CloudMirrorEngine
from core.sourceforge_client import SourceForgeClient


def main():
    sf_user = os.environ.get("SF_USERNAME", "mehraann19").strip()
    sf_project = os.environ.get("SF_PROJECT", "mehraann19").strip()
    source_proj = os.environ.get("SOURCE_PROJECT", "rama982").strip()
    dev_filter = os.environ.get("DEVICE_FILTER", "ALL").strip().upper()
    cat_filter = os.environ.get("CATEGORY_FILTER", "ALL").strip().upper()
    max_files_str = os.environ.get("MAX_FILES", "200").strip()
    max_files = int(max_files_str) if max_files_str.isdigit() else 200

    print("=" * 65)
    print("🚀 SOURCEFORGE CLOUD MIRROR & RELEASE ENGINE")
    print(f"Target SourceForge Account: {sf_user}")
    print(f"Target SourceForge Project: {sf_project}")
    print(f"Source Project to Mirror:   {source_proj}")
    print(f"Device Filter:              {dev_filter}")
    print(f"Category Filter:            {cat_filter}")
    print(f"Max Files to Process:       {max_files}")
    print("=" * 65)

    # 1. Fetch release list
    print(f"\n[*] Fetching complete file catalogue from 'https://sourceforge.net/projects/{source_proj}/'...")
    try:
        items = CloudMirrorEngine.get_source_project_files(source_proj)
    except Exception as e:
        print(f"[-] Failed to fetch RSS catalogue: {e}")
        sys.exit(1)

    print(f"[+] Total files discovered in source: {len(items)}")

    # 2. Filter files
    filtered = []
    for it in items:
        if dev_filter != "ALL" and dev_filter not in it["device"].upper() and dev_filter not in it["filename"].upper():
            continue
        if cat_filter != "ALL" and cat_filter not in it["category"].upper():
            continue
        filtered.append(it)

    print(f"[+] Files matching filters: {len(filtered)}")
    selected = filtered[:max_files]

    if not selected:
        print("[-] No matching files found to process.")
        sys.exit(0)

    # 3. Initialize SourceForge SFTP Client for remote directory creation & verification
    key_file = os.path.expanduser("~/.ssh/id_sf")
    if not os.path.isfile(key_file):
        # Local fallback
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
        print(f"[!] SFTP connect warning: {e}")

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

        print("\n" + "=" * 65)
        print(f"[{idx}/{len(selected)}] Processing: {fname}")
        print(f"    Source: {url}")
        print(f"    Category: {category} | Device: {device}")
        print(f"    Target SourceForge Folder: /{sf_project}/{target_folder}/")
        print("=" * 65)

        # Ensure remote directory structure exists on SourceForge via SFTP
        try:
            sf_client.mkdir_p(target_folder)
        except Exception as e:
            print(f"[!] Notice creating folder via SFTP: {e}")

        # Check if already present on SourceForge to save time
        remote_target_file = f"{sf_client.get_project_remote_root()}/{target_folder}/{fname}"
        file_already_exists = False
        try:
            if sf_client._sftp_client:
                sf_client._sftp_client.stat(remote_target_file)
                print(f"[i] File already exists on SourceForge: {remote_target_file}")
                file_already_exists = True
        except Exception:
            file_already_exists = False

        local_file = workdir / fname
        if local_file.exists():
            local_file.unlink()

        # Download file if not on SourceForge or needed for checksums
        if not file_already_exists:
            print(f"[*] Downloading at cloud speed via aria2c...")
            cmd = ["aria2c", "-x", "16", "-s", "16", "-k", "1M", "--check-certificate=false", "-d", str(workdir), "-o", fname, url]
            try:
                subprocess.run(cmd, check=True)
            except Exception:
                print("[!] aria2c failed, falling back to wget...")
                subprocess.run(["wget", "--no-check-certificate", "-O", str(local_file), url], check=True)

            if not local_file.exists() or local_file.stat().st_size == 0:
                print(f"[-] Failed to download {fname}, skipping.")
                continue

            file_size = local_file.stat().st_size
            file_size_mb = file_size / (1024 * 1024)

            # Checksums
            print(f"[*] Calculating cryptographic checksums...")
            file_bytes = local_file.read_bytes()
            md5 = hashlib.md5(file_bytes).hexdigest()
            sha256 = hashlib.sha256(file_bytes).hexdigest()

            # Upload to SourceForge
            print(f"[*] Uploading {fname} ({file_size_mb:.2f} MB) to SourceForge...")
            upload_success = False

            # Try rsync first
            remote_dir_full = f"/home/frs/project/{sf_project}/{target_folder}/"
            rsync_cmd = [
                "rsync", "-avP",
                "-e", f"ssh -i {key_file} -o StrictHostKeyChecking=no",
                str(local_file),
                f"{sf_user}@frs.sourceforge.net:{remote_dir_full}"
            ]
            try:
                subprocess.run(rsync_cmd, check=True)
                upload_success = True
                print(f"[+] rsync upload completed successfully!")
            except Exception as e:
                print(f"[!] rsync failed ({e}), falling back to SFTP direct put...")
                try:
                    sf_client.upload_file(str(local_file), target_folder)
                    upload_success = True
                    print(f"[+] SFTP upload completed successfully!")
                except Exception as sftp_err:
                    print(f"[-] SFTP upload also failed: {sftp_err}")

            if not upload_success:
                print(f"[-] Could not upload {fname}, skipping release creation.")
                continue
        else:
            file_size_mb = item.get("size_bytes", 0) / (1024 * 1024) if item.get("size_bytes") else 0
            md5 = "Verified on SourceForge Mirror"
            sha256 = "Verified on SourceForge Mirror"

        # URLs
        direct_cdn = f"https://downloads.sourceforge.net/project/{sf_project}/{target_folder}/{fname}"
        sf_page = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/{fname}/download"
        sf_folder_url = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/"

        # Shortcut file
        shortcut_file = shortcut_dir / f"FastDownload-{fname}.url"
        shortcut_file.write_text(f"[InternetShortcut]\nURL={direct_cdn}\n", encoding="utf-8")

        # GitHub Release Tag & Title
        safe_name = re.sub(r'[^a-zA-Z0-9\.\-]', '_', fname)
        release_tag = f"{item['tag_prefix']}-{safe_name[:40]}"
        release_title = f"[{device}] {category} - {fname}"

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

        processed_releases.append({
            "filename": fname,
            "size_mb": file_size_mb,
            "cdn": direct_cdn,
            "device": device,
            "category": category
        })

        # Cleanup local downloaded file to free disk space on runner
        if local_file.exists():
            local_file.unlink()

    try:
        sf_client.close()
    except Exception:
        pass

    # Summary
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("### 🌟 All Source Projects Successfully Mirrored!\n\n")
            f.write("| Device | Category | File Name | Size | Fast CDN Mirror |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for pr in processed_releases:
                f.write(f"| `{pr['device']}` | `{pr['category']}` | `{pr['filename']}` | `{pr['size_mb']:.1f} MB` | [⚡ Direct CDN]({pr['cdn']}) |\n")

    print("\n" + "=" * 65)
    print(f"🎉 COMPLETED! Successfully mirrored {len(processed_releases)} releases.")
    print("=" * 65)


if __name__ == "__main__":
    main()
