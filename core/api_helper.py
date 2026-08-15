#!/usr/bin/env python3
"""
SourceForge API Helper Module
Interacts with Allura REST APIs for metadata, default platform releases, and analytics.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None


class SourceForgeAPI:
    """Helper for SourceForge REST API and Download Analytics."""

    BASE_URL = "https://sourceforge.net"

    def __init__(self, project_name: str, api_key: Optional[str] = None):
        self.project_name = project_name
        self.api_key = api_key

    def get_project_info(self) -> Dict[str, Any]:
        """Fetches project overview from Allura API."""
        if not requests:
            raise ImportError("requests library required: pip install requests")

        url = f"{self.BASE_URL}/rest/p/{self.project_name}"
        params = {}
        if self.api_key:
            params["api_key"] = self.api_key

        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        print(f"[-] Error fetching project info (HTTP {resp.status_code})")
        return {}

    def get_download_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Fetches download statistics for the project over the past N days.
        SourceForge JSON stats endpoint: /projects/<project>/files/stats/json
        """
        if not requests:
            raise ImportError("requests library required: pip install requests")

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        url = f"{self.BASE_URL}/projects/{self.project_name}/files/stats/json"
        params = {
            "start_date": start_str,
            "end_date": end_str
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                total_downloads = data.get("total", 0)
                countries = data.get("countries", {})
                os_stats = data.get("oses", {})
                return {
                    "total_downloads": total_downloads,
                    "start_date": start_str,
                    "end_date": end_str,
                    "top_countries": sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5],
                    "top_os": sorted(os_stats.items(), key=lambda x: x[1], reverse=True)[:5],
                    "raw": data
                }
        except Exception as e:
            print(f"[-] Failed to get download stats: {e}")

        return {}

    def set_default_download(self, file_rel_path: str, platforms: list) -> bool:
        """
        Sets a file as default download for specific platforms (e.g. ['windows', 'linux', 'mac', 'android']).
        Note: Requires SourceForge Allura API key or web session.
        """
        if not self.api_key:
            print("[!] Setting default download via API requires SF_API_KEY.")
            return False

        url = f"{self.BASE_URL}/rest/p/{self.project_name}/files/{file_rel_path.strip('/')}"
        data = {
            "api_key": self.api_key,
            "default": ",".join(platforms)
        }
        try:
            resp = requests.post(url, data=data, timeout=15)
            return resp.status_code in (200, 201)
        except Exception as e:
            print(f"[-] API error setting default download: {e}")
            return False
