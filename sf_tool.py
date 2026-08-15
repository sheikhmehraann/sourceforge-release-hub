#!/usr/bin/env python3
"""
SourceForge Release Hub - Unified CLI
Manage SourceForge files, folders, cloud transfers, and GitHub automation.
"""

import os
import sys
import argparse
from pathlib import Path

# Load .env if present
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / "config" / ".env")
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass

from core.sourceforge_client import SourceForgeClient
from core.folder_manager import FolderManager
from core.api_helper import SourceForgeAPI
from core.github_runner import GitHubRunner


def get_client(args) -> SourceForgeClient:
    project = getattr(args, "project", None) or os.getenv("SF_PROJECT")
    username = getattr(args, "username", None) or os.getenv("SF_USERNAME")
    key_path = getattr(args, "key", None) or os.getenv("SF_KEY_PATH")
    password = os.getenv("SF_PASSWORD")
    api_key = os.getenv("SF_API_KEY")

    if not project:
        print("[!] Warning: SF_PROJECT is not set. Use --project or set in config/.env")

    return SourceForgeClient(
        project_name=project,
        username=username,
        password=password,
        key_path=key_path,
        api_key=api_key
    )


def cmd_list(args):
    """List remote directory files & folders."""
    client = get_client(args)
    subpath = args.folder or ""
    print(f"[*] Browsing SourceForge project: '{client.project_name}', path: '/{subpath}'")

    if args.public or not client.username:
        print("[i] Using public RSS feed...")
        files = SourceForgeClient.get_public_project_files(client.project_name, subpath)
        if not files:
            print("[-] No published files found via RSS.")
            return
        print(f"\nFound {len(files)} file(s):")
        for f in files:
            size_mb = f["size"] / (1024 * 1024) if f["size"] else 0
            print(f"  • {f['title']} ({size_mb:.2f} MB)")
            print(f"    Link: {f['download_url']}")
            print(f"    Date: {f['pub_date']}")
    else:
        with client:
            items = client.list_dir(subpath)
            if not items:
                print(f"[-] Directory is empty or does not exist: /{subpath}")
                return
            print(f"\nDirectory Contents of '/{subpath}':")
            for item in items:
                icon = "📁 [DIR] " if item["is_dir"] else "📄 [FILE]"
                size_str = f"({item['size'] / (1024*1024):.2f} MB)" if not item["is_dir"] else ""
                print(f"  {icon:8} {item['name']} {size_str}")


def cmd_mkdir(args):
    """Create directory on SourceForge."""
    client = get_client(args)
    fm = FolderManager(client)
    print(f"[*] Creating directory '{args.folder}' on project '{client.project_name}'...")
    fm.create_custom_folder(args.folder)


def cmd_preset(args):
    """Create directory tree using a preset template."""
    client = get_client(args)
    fm = FolderManager(client)
    vars_dict = {}
    if args.device:
        vars_dict["device"] = args.device
        vars_dict["device_codename"] = args.device
    if args.brand:
        vars_dict["brand"] = args.brand
    if args.model:
        vars_dict["model"] = args.model

    print(f"[*] Applying preset '{args.name}' with variables: {vars_dict}...")
    created = fm.create_structure(args.name, vars_dict)
    print(f"[+] Successfully created {len(created)} folders:")
    for c in created:
        print(f"  ✓ /{c}")


def cmd_upload(args):
    """Upload local file to SourceForge."""
    client = get_client(args)
    local_path = Path(args.file).resolve()
    if not local_path.exists():
        print(f"[-] Error: File '{args.file}' not found.")
        sys.exit(1)

    remote_folder = args.folder or ""
    with client:
        res = client.upload_file(str(local_path), remote_folder)
        print("\n=======================================================")
        print("✅ UPLOAD SUMMARY")
        print("=======================================================")
        print(f"File Name:      {res['filename']}")
        print(f"File Size:      {res['size'] / (1024*1024):.2f} MB")
        print(f"MD5 Checksum:   {res['md5']}")
        print(f"SHA256:         {res['sha256']}")
        print(f"Direct Mirror:  {res['direct_mirror_url']}")
        print(f"Web Page:       {res['download_url']}")
        print("=======================================================")


def cmd_cloud_upload(args):
    """Trigger GitHub Actions cloud runner to download URL and push to SourceForge."""
    runner = GitHubRunner(repo_name=args.repo)
    success = runner.trigger_cloud_upload(
        file_url=args.url,
        folder_path=args.folder,
        project_name=args.project,
        release_notes=args.notes or ""
    )
    if not success:
        sys.exit(1)


def cmd_cloud_status(args):
    """Check status of GitHub Actions cloud jobs."""
    runner = GitHubRunner(repo_name=args.repo)
    print(f"[*] Fetching latest cloud workflow runs for {runner.repo_name}...")
    runner.list_runs(limit=args.limit)


def cmd_setup_secrets(args):
    """Interactive / CLI setup of GitHub Secrets."""
    runner = GitHubRunner(repo_name=args.repo)
    sf_user = args.username or input("Enter SourceForge Username: ").strip()
    sf_proj = args.project or input("Enter SourceForge Project UNIX name: ").strip()
    
    default_key = str(Path.home() / ".ssh" / "id_ed25519")
    sf_key = args.key or input(f"Enter Private SSH Key path [{default_key}]: ").strip() or default_key

    runner.setup_github_secrets(
        sf_username=sf_user,
        sf_project=sf_proj,
        sf_key_path=sf_key
    )


def cmd_stats(args):
    """Fetch download analytics."""
    client = get_client(args)
    api = SourceForgeAPI(project_name=client.project_name, api_key=client.api_key)
    print(f"[*] Fetching download statistics for '{client.project_name}' (past {args.days} days)...")
    stats = api.get_download_stats(days=args.days)
    if not stats:
        print("[-] Could not retrieve statistics.")
        return

    print("\n=======================================================")
    print(f"📊 DOWNLOAD ANALYTICS ({stats['start_date']} to {stats['end_date']})")
    print("=======================================================")
    print(f"Total Downloads: {stats['total_downloads']:,}")
    print("\nTop Countries:")
    for country, count in stats["top_countries"]:
        print(f"  • {country:15}: {count:,}")
    print("\nTop Operating Systems:")
    for os_name, count in stats["top_os"]:
        print(f"  • {os_name:15}: {count:,}")
    print("=======================================================")


def main():
    parser = argparse.ArgumentParser(
        description="SourceForge Release Hub & Cloud Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--project", "-p", help="SourceForge project UNIX name")
    parser.add_argument("--username", "-u", help="SourceForge username")
    parser.add_argument("--key", "-k", help="Path to SSH private key")
    
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # list
    p_list = subparsers.add_parser("list", help="List files and folders on SourceForge")
    p_list.add_argument("folder", nargs="?", default="", help="Subfolder path to browse")
    p_list.add_argument("--public", action="store_true", help="Use public RSS feed (no login needed)")

    # mkdir
    p_mkdir = subparsers.add_parser("mkdir", help="Create folder on SourceForge")
    p_mkdir.add_argument("folder", help="Remote folder path to create (e.g. X6871/ROMs)")

    # preset
    p_preset = subparsers.add_parser("preset", help="Create folder hierarchy from preset")
    p_preset.add_argument("name", choices=["transsion_firmware", "android_device", "software_hub", "firmware_dump"], help="Preset template name")
    p_preset.add_argument("--device", "-d", default="X6871", help="Device codename (default: X6871)")
    p_preset.add_argument("--brand", "-b", default="Infinix", help="Brand name (default: Infinix)")
    p_preset.add_argument("--model", "-m", default="GT20Pro", help="Model name (default: GT20Pro)")

    # upload
    p_upload = subparsers.add_parser("upload", help="Upload a local file to SourceForge")
    p_upload.add_argument("file", help="Local file path")
    p_upload.add_argument("folder", nargs="?", default="", help="Target remote folder")

    # cloud-upload
    p_cloud = subparsers.add_parser("cloud-upload", help="Delegate upload to GitHub Actions cloud runners")
    p_cloud.add_argument("url", help="Direct URL to download (Gofile, Google Drive, direct link)")
    p_cloud.add_argument("folder", help="Target SourceForge folder")
    p_cloud.add_argument("--notes", "-n", default="", help="Release notes / description")
    p_cloud.add_argument("--repo", default="sheikhmehraann/sourceforge-release-hub", help="GitHub repository name")

    # cloud-status
    p_status = subparsers.add_parser("cloud-status", help="Check GitHub Actions cloud jobs")
    p_status.add_argument("--repo", default="sheikhmehraann/sourceforge-release-hub", help="GitHub repo")
    p_status.add_argument("--limit", type=int, default=5, help="Number of runs to show")

    # setup-secrets
    p_secrets = subparsers.add_parser("setup-secrets", help="Push credentials to GitHub Secrets via gh CLI")
    p_secrets.add_argument("--repo", default="sheikhmehraann/sourceforge-release-hub", help="GitHub repo")

    # stats
    p_stats = subparsers.add_parser("stats", help="Show download analytics")
    p_stats.add_argument("--days", type=int, default=30, help="Days to analyze")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "mkdir": cmd_mkdir,
        "preset": cmd_preset,
        "upload": cmd_upload,
        "cloud-upload": cmd_cloud_upload,
        "cloud-status": cmd_cloud_status,
        "setup-secrets": cmd_setup_secrets,
        "stats": cmd_stats,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
