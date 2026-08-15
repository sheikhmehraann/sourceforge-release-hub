#!/usr/bin/env python3
"""
GitHub Runner & Cloud Dispatcher Module
Triggers GitHub Actions cloud servers to perform fast file transfers directly to SourceForge.
"""

import os
import shutil
import subprocess
from typing import Dict, Any, Optional


class GitHubRunner:
    """Dispatches and manages GitHub Actions cloud upload tasks."""

    def __init__(self, repo_name: Optional[str] = None):
        self.repo_name = repo_name or os.getenv("GITHUB_REPOSITORY", "sheikhmehraann/sourceforge-release-hub")

    @staticmethod
    def is_gh_installed() -> bool:
        """Checks if GitHub CLI (gh) is available on the system."""
        return shutil.which("gh") is not None

    def trigger_cloud_upload(
        self,
        file_url: str,
        folder_path: str,
        project_name: Optional[str] = None,
        release_notes: str = ""
    ) -> bool:
        """
        Dispatches the `sourceforge_upload.yml` workflow on GitHub Actions servers.
        The GitHub server downloads the file from URL and uploads directly to SourceForge!
        """
        if not self.is_gh_installed():
            print("[-] GitHub CLI (`gh`) is not installed or not in PATH.")
            return False

        cmd = [
            "gh", "workflow", "run", "sourceforge_upload.yml",
            "--repo", self.repo_name,
            "-f", f"file_url={file_url}",
            "-f", f"folder_path={folder_path}"
        ]

        if project_name:
            cmd.extend(["-f", f"project_name={project_name}"])
        if release_notes:
            cmd.extend(["-f", f"release_notes={release_notes}"])

        print(f"[*] Dispatching cloud job to GitHub Actions ({self.repo_name})...")
        print(f"    URL: {file_url}")
        print(f"    Target SourceForge Folder: {folder_path}")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("[+] Cloud job successfully dispatched to GitHub Actions servers!")
            print(res.stdout)
            print("[i] Run `python sf_tool.py cloud-status` to monitor live cloud progress.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to dispatch workflow: {e.stderr}")
            return False

    def trigger_cloud_publish(
        self,
        file_url: str,
        category: str = "FLASHABLE",
        device: str = "X6871",
        subfolder: str = "",
        release_tag: str = "",
        release_title: str = "",
        changelog: str = ""
    ) -> bool:
        """
        Dispatches the `cloud_publish.yml` workflow on GitHub Actions.
        Downloads file at multi-gigabit speeds, uploads to SourceForge, and creates a GitHub Release
        with direct fast CDN mirror links!
        """
        if not self.is_gh_installed():
            print("[-] GitHub CLI (`gh`) is not installed or not in PATH.")
            return False

        cmd = [
            "gh", "workflow", "run", "cloud_publish.yml",
            "--repo", self.repo_name,
            "-f", f"file_url={file_url}",
            "-f", f"category={category}",
            "-f", f"device={device}"
        ]

        if subfolder:
            cmd.extend(["-f", f"subfolder={subfolder}"])
        if release_tag:
            cmd.extend(["-f", f"release_tag={release_tag}"])
        if release_title:
            cmd.extend(["-f", f"release_title={release_title}"])
        if changelog:
            cmd.extend(["-f", f"changelog={changelog}"])

        print(f"[*] Dispatching Dual Cloud Publish to GitHub Actions ({self.repo_name})...")
        print(f"    Target Category: {category}")
        print(f"    Device: {device}")
        print(f"    Source URL: {file_url}")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("[+] Dual Cloud Publish workflow started on GitHub servers!")
            print(res.stdout)
            print("[i] The runner will upload to SourceForge and create a GitHub Release with fast CDN mirrors.")
            print("[i] Run `python sf_tool.py cloud-status` to monitor live progress.")
            return True
        except subprocess.CalledProcessError as e:
            print(f"[-] Failed to dispatch workflow: {e.stderr}")
            return False

    def list_runs(self, limit: int = 5):
        """Lists recent workflow runs for this repository."""
        if not self.is_gh_installed():
            return
        subprocess.run(["gh", "run", "list", "--repo", self.repo_name, "--limit", str(limit)])

    def setup_github_secrets(
        self,
        sf_username: str,
        sf_project: str,
        sf_key_path: Optional[str] = None,
        sf_password: Optional[str] = None,
        sf_api_key: Optional[str] = None
    ) -> bool:
        """
        Automatically pushes required SourceForge credentials to GitHub Repository Secrets.
        """
        if not self.is_gh_installed():
            print("[-] GitHub CLI (`gh`) is required to set secrets.")
            return False

        print(f"[*] Setting GitHub Repository Secrets for '{self.repo_name}'...")

        # 1. SF_USERNAME
        subprocess.run(
            ["gh", "secret", "set", "SF_USERNAME", "--repo", self.repo_name, "--body", sf_username],
            check=True
        )
        print("  [OK] SF_USERNAME set")

        # 2. SF_PROJECT
        subprocess.run(
            ["gh", "secret", "set", "SF_PROJECT", "--repo", self.repo_name, "--body", sf_project],
            check=True
        )
        print("  [OK] SF_PROJECT set")

        # 3. SF_SSH_KEY
        if sf_key_path and os.path.isfile(os.path.expanduser(sf_key_path)):
            with open(os.path.expanduser(sf_key_path), "r", encoding="utf-8") as f:
                key_content = f.read()
            subprocess.run(
                ["gh", "secret", "set", "SF_SSH_KEY", "--repo", self.repo_name, "--body", key_content],
                check=True
            )
            print("  [OK] SF_SSH_KEY set")

        # 4. SF_PASSWORD (optional)
        if sf_password:
            subprocess.run(
                ["gh", "secret", "set", "SF_PASSWORD", "--repo", self.repo_name, "--body", sf_password],
                check=True
            )
            print("  [OK] SF_PASSWORD set")

        # 5. SF_API_KEY (optional)
        if sf_api_key:
            subprocess.run(
                ["gh", "secret", "set", "SF_API_KEY", "--repo", self.repo_name, "--body", sf_api_key],
                check=True
            )
            print("  [OK] SF_API_KEY set")

        print("[+] All GitHub Secrets configured successfully!")
        return True
