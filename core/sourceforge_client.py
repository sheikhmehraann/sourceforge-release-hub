#!/usr/bin/env python3
"""
SourceForge Client Module
Provides SFTP, SSH, rsync, and HTTP/RSS integration with SourceForge FRS (File Release System).
"""

import os
import sys
import stat
import time
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Optional, Callable, Any

try:
    import requests
except ImportError:
    requests = None

try:
    import paramiko
except ImportError:
    paramiko = None


class SourceForgeClient:
    """Client for interacting with SourceForge File Release System (frs.sourceforge.net)."""

    HOST = "frs.sourceforge.net"
    PORT = 22
    BASE_REMOTE_PATH = "/home/frs/project"

    def __init__(
        self,
        project_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        key_path: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        self.project_name = project_name or os.getenv("SF_PROJECT", "")
        self.username = username or os.getenv("SF_USERNAME", "")
        self.password = password or os.getenv("SF_PASSWORD", None)
        self.key_path = key_path or os.getenv("SF_KEY_PATH", None)
        self.api_key = api_key or os.getenv("SF_API_KEY", None)

        self._ssh_client = None
        self._sftp_client = None

    def get_project_remote_root(self) -> str:
        """Returns the full remote path root for this project on SourceForge."""
        if not self.project_name:
            raise ValueError("SourceForge project name is required.")
        return f"{self.BASE_REMOTE_PATH}/{self.project_name}"

    def connect(self):
        """Establishes an SSH & SFTP connection to frs.sourceforge.net."""
        if not paramiko:
            raise ImportError(
                "Paramiko library is required for SFTP. Install via: pip install paramiko"
            )

        if not self.username:
            raise ValueError("SourceForge username is required.")

        print(f"[*] Connecting to {self.username}@{self.HOST}:{self.PORT}...")
        self._ssh_client = paramiko.SSHClient()
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        pkey = None
        if self.key_path:
            expanded_key = os.path.expanduser(self.key_path)
            if os.path.isfile(expanded_key):
                try:
                    pkey = paramiko.Ed25519Key.from_private_key_file(expanded_key)
                except Exception:
                    try:
                        pkey = paramiko.RSAKey.from_private_key_file(expanded_key)
                    except Exception:
                        try:
                            pkey = paramiko.ECDSAKey.from_private_key_file(expanded_key)
                        except Exception:
                            pkey = None

        connect_kwargs: Dict[str, Any] = {
            "hostname": self.HOST,
            "port": self.PORT,
            "username": self.username,
            "timeout": 30,
            "banner_timeout": 60,
        }

        if pkey:
            connect_kwargs["pkey"] = pkey
        elif self.password:
            connect_kwargs["password"] = self.password
        else:
            # Check default SSH keys in ~/.ssh
            default_keys = [
                os.path.expanduser("~/.ssh/id_ed25519"),
                os.path.expanduser("~/.ssh/id_rsa"),
            ]
            for dk in default_keys:
                if os.path.isfile(dk):
                    try:
                        pkey = paramiko.Ed25519Key.from_private_key_file(dk)
                        connect_kwargs["pkey"] = pkey
                        break
                    except Exception:
                        try:
                            pkey = paramiko.RSAKey.from_private_key_file(dk)
                            connect_kwargs["pkey"] = pkey
                            break
                        except Exception:
                            continue

        self._ssh_client.connect(**connect_kwargs)
        self._sftp_client = self._ssh_client.open_sftp()
        print(f"[+] Successfully connected to SourceForge SFTP as {self.username}!")
        return self._sftp_client

    def close(self):
        """Closes active SFTP and SSH sessions."""
        if self._sftp_client:
            try:
                self._sftp_client.close()
            except Exception:
                pass
            self._sftp_client = None

        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception:
                pass
            self._ssh_client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def resolve_remote_path(self, subpath: str = "") -> str:
        """Resolves subpath relative to project root."""
        root = self.get_project_remote_root()
        subpath = subpath.strip("/\\").replace("\\", "/")
        if not subpath:
            return root
        return f"{root}/{subpath}"

    def mkdir_p(self, remote_dir: str):
        """Recursively creates directory path on SourceForge via SFTP."""
        if not self._sftp_client:
            self.connect()

        full_path = self.resolve_remote_path(remote_dir) if not remote_dir.startswith("/home/frs") else remote_dir
        parts = [p for p in full_path.split("/") if p]
        
        current = ""
        for part in parts:
            current += "/" + part
            try:
                self._sftp_client.stat(current)
            except IOError:
                try:
                    print(f"[*] Creating remote directory: {current}")
                    self._sftp_client.mkdir(current)
                except IOError as e:
                    # Ignore if another thread or process just created it
                    pass

    def list_dir(self, remote_subpath: str = "") -> List[Dict[str, Any]]:
        """Lists files and folders inside a remote SourceForge project path via SFTP."""
        if not self._sftp_client:
            self.connect()

        target = self.resolve_remote_path(remote_subpath)
        items = []
        try:
            for attr in self._sftp_client.listdir_attr(target):
                is_dir = stat.S_ISDIR(attr.st_mode)
                items.append({
                    "name": attr.filename,
                    "is_dir": is_dir,
                    "size": attr.st_size if not is_dir else 0,
                    "mtime": attr.st_mtime,
                    "path": f"{remote_subpath.strip('/')}/{attr.filename}".strip("/"),
                })
        except IOError as e:
            print(f"[-] Remote path not found or error listing {target}: {e}")
        return items

    def upload_file(
        self,
        local_path: str,
        remote_folder: str = "",
        callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Any]:
        """Uploads a local file to SourceForge."""
        if not self._sftp_client:
            self.connect()

        local_file = Path(local_path).resolve()
        if not local_file.is_file():
            raise FileNotFoundError(f"Local file '{local_path}' does not exist.")

        # Ensure target folder exists
        self.mkdir_p(remote_folder)

        remote_target_folder = self.resolve_remote_path(remote_folder)
        remote_target_file = f"{remote_target_folder}/{local_file.name}"
        file_size = local_file.stat().st_size

        print(f"[*] Uploading '{local_file.name}' ({file_size / (1024*1024):.2f} MB) -> {remote_target_file}...")

        # Calculate hashes
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        with open(local_file, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                md5_hash.update(chunk)
                sha256_hash.update(chunk)

        start_time = time.time()

        def default_callback(transferred: int, total: int):
            elapsed = time.time() - start_time
            speed = (transferred / (1024 * 1024)) / elapsed if elapsed > 0 else 0
            percent = (transferred / total * 100) if total > 0 else 0
            sys.stdout.write(
                f"\r    Uploading: {percent:6.1f}% [{transferred / (1024*1024):.1f}/{total / (1024*1024):.1f} MB] @ {speed:.2f} MB/s"
            )
            sys.stdout.flush()

        cb = callback or default_callback
        self._sftp_client.put(str(local_file), remote_target_file, callback=cb)
        print("\n[+] File upload complete!")

        # Direct download link
        relative_path = f"{remote_folder.strip('/')}/{local_file.name}".strip("/")
        download_url = f"https://sourceforge.net/projects/{self.project_name}/files/{relative_path}/download"
        direct_mirror = f"https://downloads.sourceforge.net/project/{self.project_name}/{relative_path}"

        return {
            "filename": local_file.name,
            "size": file_size,
            "md5": md5_hash.hexdigest(),
            "sha256": sha256_hash.hexdigest(),
            "remote_path": remote_target_file,
            "download_url": download_url,
            "direct_mirror_url": direct_mirror
        }

    def delete_file(self, remote_subpath: str):
        """Deletes a file on SourceForge."""
        if not self._sftp_client:
            self.connect()

        target = self.resolve_remote_path(remote_subpath)
        print(f"[*] Deleting remote file: {target}")
        self._sftp_client.remove(target)
        print("[+] File deleted.")

    def delete_dir(self, remote_subpath: str):
        """Recursively removes a directory on SourceForge."""
        if not self._sftp_client:
            self.connect()

        target = self.resolve_remote_path(remote_subpath)

        def _recursive_rmdir(path: str):
            for attr in self._sftp_client.listdir_attr(path):
                sub = f"{path}/{attr.filename}"
                if stat.S_ISDIR(attr.st_mode):
                    _recursive_rmdir(sub)
                else:
                    self._sftp_client.remove(sub)
            self._sftp_client.rmdir(path)

        print(f"[*] Deleting remote directory: {target}")
        _recursive_rmdir(target)
        print("[+] Directory deleted.")

    @staticmethod
    def get_public_project_files(project_name: str, subpath: str = "") -> List[Dict[str, Any]]:
        """
        Publicly queries SourceForge RSS feed without requiring login/SSH.
        Returns all published files, sizes, MD5s, pubdates, and download URLs.
        """
        if not requests:
            raise ImportError("requests library required: pip install requests")

        url = f"https://sourceforge.net/projects/{project_name}/rss"
        if subpath:
            clean_sub = subpath.strip("/\\")
            url += f"?path=/{clean_sub}"

        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code != 200:
            print(f"[-] Could not fetch RSS for project '{project_name}' (HTTP {resp.status_code})")
            return []

        files = []
        try:
            root = ET.fromstring(resp.content)
            channel = root.find("channel")
            if channel is None:
                return []

            for item in channel.findall("item"):
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                pub_date = item.findtext("pubDate", "")
                desc = item.findtext("description", "")
                
                # Check media or enclosure
                enclosure = item.find("enclosure")
                size = int(enclosure.attrib.get("length", 0)) if enclosure is not None else 0

                files.append({
                    "title": title,
                    "download_url": link,
                    "pub_date": pub_date,
                    "description": desc,
                    "size": size,
                })
        except Exception as e:
            print(f"[-] Failed to parse RSS feed: {e}")

        return files
