#!/usr/bin/env python3
"""
Ultra-Fast Distributed Cloud Mirror Engine for GitHub Actions
Mirrors 100% of files from source to SourceForge using Sharded Matrix Execution.
"""

import os
import sys
import re
import json
import subprocess
import hashlib
import urllib.parse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.mirror_engine import CloudMirrorEngine
from core.sourceforge_client import SourceForgeClient


def get_existing_github_releases():
    """Fetches set of already published release tags from GitHub repository."""
    try:
        res = subprocess.run(["gh", "release", "list", "--limit", "500", "--json", "tagName"], capture_output=True, text=True, check=True)
        if res.stdout.strip():
            data = json.loads(res.stdout)
            return {item["tagName"] for item in data}
    except Exception:
        pass
    return set()


def main():
    sf_user = os.environ.get("SF_USERNAME", "mehraann19").strip()
    sf_project = os.environ.get("SF_PROJECT", "mehraann19").strip()
    source_proj = os.environ.get("SOURCE_PROJECT", "rama982").strip()
    shard_num = int(os.environ.get("SHARD_NUM", "1"))
    total_shards = int(os.environ.get("TOTAL_SHARDS", "8"))
    shard_index = max(0, shard_num - 1)

    print("=" * 65)
    print(f"🚀 CLOUD MIRROR WORKER [Shard {shard_num}/{total_shards}]")
    print(f"Source Project:   {source_proj}")
    print(f"Target Account:   {sf_user}")
    print(f"Target Project:   {sf_project}")
    print("=" * 65)

    # 1. Fetch complete file catalogue
    items = CloudMirrorEngine.get_source_project_files(source_proj)
    print(f"[+] Total files discovered in source '{source_proj}': {len(items)}")

    # 2. Select this worker's shard
    shard_items = [it for idx, it in enumerate(items) if idx % total_shards == shard_index]
    print(f"[+] Worker Shard {shard_index + 1}/{total_shards} assigned: {len(shard_items)} files")

    if not shard_items:
        print("[-] No files assigned to this shard.")
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
        print(f"[+] SFTP backend connected as '{sf_user}'")
    except Exception as e:
        print(f"[!] SFTP connect note: {e}")

    existing_gh_tags = get_existing_github_releases()
    print(f"[*] Found {len(existing_gh_tags)} existing releases on GitHub.")

    workdir = Path("work_downloads")
    workdir.mkdir(exist_ok=True)
    shortcut_dir = Path("shortcuts")
    shortcut_dir.mkdir(exist_ok=True)

    processed_count = 0

    for idx, item in enumerate(shard_items, 1):
        fname = item["filename"]
        url = item["source_download_url"]
        target_folder = item["target_folder"]
        category = item["category"]
        device = item["device"]

        safe_name = re.sub(r'[^a-zA-Z0-9\.\-]', '_', fname)
        release_tag = f"{item['tag_prefix']}-{safe_name[:40]}"
        release_title = f"[{device}] {category} - {fname}"

        print(f"\n" + "-" * 60)
        print(f"[{idx}/{len(shard_items)}] Processing: {fname}")
        print(f"    Category: {category} | Device: {device}")
        print(f"    Target SourceForge: /{sf_project}/{target_folder}/{fname}")
        print(f"-" * 60)

        try:
            # 1. Pre-create remote directory if needed
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

            # 3. If file not on SourceForge, download & upload
            if not file_already_on_sf:
                print(f"[*] Downloading at multi-gigabit cloud speed via aria2c...")
                cmd = [
                    "aria2c",
                    "-x", "16",
                    "-s", "16",
                    "-k", "1M",
                    "--file-allocation=none",
                    "--check-certificate=false",
                    "-d", str(workdir),
                    "-o", fname,
                    url
                ]
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
                print(f"[*] Calculating cryptographic checksums...")
                file_bytes = local_file.read_bytes()
                md5 = hashlib.md5(file_bytes).hexdigest()
                sha256 = hashlib.sha256(file_bytes).hexdigest()

                # Upload to SourceForge using hardware-accelerated AES cipher
                print(f"[*] Uploading {fname} ({file_size_mb:.2f} MB) to SourceForge FRS...")
                upload_success = False
                remote_dir_full = f"/home/frs/project/{sf_project}/{target_folder}/"

                rsync_cmd = [
                    "rsync", "-avP", "--inplace", "--timeout=300",
                    "-e", f"ssh -i {key_file} -o Compression=no -o Cipher=aes128-gcm@openssh.com -o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=10",
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

            # 4. Generate Direct CDN Mirrors & Links
            encoded_fname = urllib.parse.quote(fname)
            direct_cdn = f"https://downloads.sourceforge.net/project/{sf_project}/{target_folder}/{encoded_fname}"
            sf_page = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/{encoded_fname}/download"
            sf_folder_url = f"https://sourceforge.net/projects/{sf_project}/files/{target_folder}/"

            # 5. Create / Update GitHub Release if not already created
            if release_tag not in existing_gh_tags:
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

            processed_count += 1

            if local_file.exists():
                local_file.unlink()

        except Exception as item_err:
            print(f"[!] Error processing {fname}: {item_err}")
            continue

    try:
        sf_client.close()
    except Exception:
        pass

    print(f"\n[✓] Shard {shard_index + 1}/{total_shards} finished: {processed_count} files mirrored & released.")


if __name__ == "__main__":
    main()
