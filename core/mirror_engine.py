#!/usr/bin/env python3
"""
Automated Cloud Mirror Engine
Maps and mirrors release packages from public sources into clean, logical SourceForge hierarchies
and generates GitHub Releases with direct high-speed global CDN mirror links.
"""

import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import requests
except ImportError:
    requests = None


class CloudMirrorEngine:
    """Intelligently categorizes and maps firmware packages into logical directory structures."""

    DEVICE_MAP = {
        "X6871": "Infinix-GT-20-Pro-X6871",
        "X6886": "Infinix-Hot-50-Pro-X6886",
        "X6880": "Infinix-Zero-40-5G-X6880",
        "X6850": "Infinix-Note-40-Pro-X6850",
        "X6858": "Infinix-Note-40-Pro-Plus-X6858",
        "X6855": "Infinix-Note-40-5G-X6855",
        "X6851": "Infinix-Note-40-4G-X6851",
        "X6873": "Infinix-Zero-30-5G-X6873",
        "X6885": "Infinix-Hot-50-X6885",
        "X6853": "Infinix-Note-30-X6853",
        "X6720": "Infinix-GT-10-Pro-X6720",
        "LI6": "Tecno-Pova-6-Pro-LI6",
        "LI7": "Tecno-Camon-30-5G-LI7",
        "CL7": "Tecno-Camon-30-Pro-CL7",
    }

    @classmethod
    def resolve_device(cls, filename: str) -> str:
        """Extracts and maps device codename from filename."""
        upper = filename.upper()
        for code, full_name in cls.DEVICE_MAP.items():
            if code in upper:
                return full_name
        return "Universal-ARM64"

    @classmethod
    def map_file_to_logical_path(cls, filename: str, original_path: str = "") -> Dict[str, str]:
        """
        Maps any firmware/ROM file into clean, intuitive logical folders.
        """
        device = cls.resolve_device(filename)
        upper_name = filename.upper()
        upper_path = original_path.upper()

        # 1. Custom Recoveries (OrangeFox / TWRP / PBRP)
        if "ORANGEFOX" in upper_name or "TWRP" in upper_name or "RECOVERY" in upper_path:
            category = "Custom-Recoveries"
            tool_type = "OrangeFox" if "ORANGEFOX" in upper_name else "TWRP"
            target_folder = f"Devices/{device}/Recovery-Images"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "recovery"
            }

        # 2. Custom Kernels (AK3 / AnyKernel3)
        if "AK3" in upper_name or "KERNEL" in upper_path or "KERNEL" in upper_name:
            category = "Custom-Kernels"
            kver = "Linux-5.10"
            if "6.6" in filename or "6.6" in original_path:
                kver = "Linux-6.6"
            elif "6.1" in filename or "6.1" in original_path:
                kver = "Linux-6.1"
            elif "5.10" in filename or "5.10" in original_path:
                kver = "Linux-5.10"

            target_folder = f"Custom-Kernels/{kver}"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "kernel"
            }

        # 3. Flashable Recovery ROMs (A/B Dynamic Partition Packages)
        if "RECOVERY-AB" in upper_name or "FLASHABLE" in upper_path or "FLASHABLE" in upper_name:
            category = "Flashable-ROMs"
            target_folder = f"Devices/{device}/Flashable-ROMs"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "rom"
            }

        # 4. Stock Boot / Init_Boot Images
        if "BOOT" in upper_name or "STOCK-IMAGE" in upper_path:
            category = "Stock-Images"
            target_folder = f"Devices/{device}/Stock-Images"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "boot"
            }

        # 5. Extracted OTA Payloads / Raw Partitions
        if "IMAGES.TAR" in upper_name or "OTA-EXTRACT" in upper_path or ".ZST" in upper_name:
            category = "OTA-Payloads"
            target_folder = f"OTA-Payloads/Partition-Dumps/{device}"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "ota"
            }

        # 6. Official Fastboot Firmware
        if "OFFICIAL" in upper_name or "OFFICIAL-FW" in upper_path:
            category = "Stock-Firmware"
            target_folder = f"Devices/{device}/Official-Firmware"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "stock-fw"
            }

        # 7. Porting Ecosystem & Vendor Libraries
        if "VENDOR64" in upper_name or "PORT" in upper_path or "PORT-FILES" in upper_path:
            category = "Porting-Files"
            target_folder = f"Porting-Files/Vendor64/{device}"
            return {
                "category": category,
                "device": device,
                "target_folder": target_folder,
                "clean_path": f"{target_folder}/{filename}",
                "tag_prefix": "port"
            }

        # Default: Tools & Utilities
        target_folder = f"Tools-and-Utilities"
        return {
            "category": "Tools",
            "device": device,
            "target_folder": target_folder,
            "clean_path": f"{target_folder}/{filename}",
            "tag_prefix": "tool"
        }

    @staticmethod
    def get_source_project_files(project_name: str = "rama982") -> List[Dict[str, Any]]:
        """Parses public RSS feed for all available files."""
        if not requests:
            import urllib.request
            url = f"https://sourceforge.net/projects/{project_name}/rss"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read()
        else:
            url = f"https://sourceforge.net/projects/{project_name}/rss"
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            content = resp.content

        root = ET.fromstring(content)
        items = []
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            pub_date = item.findtext("pubDate", "")
            enclosure = item.find("enclosure")
            size = int(enclosure.attrib.get("length", 0)) if enclosure is not None else 0

            # Extract filename and relative path
            clean_rel = link.replace(f"https://sourceforge.net/projects/{project_name}/files/", "")
            filename = clean_rel.split("/")[-1].split("?")[0].split("&")[0]

            if not filename or filename.endswith("/"):
                continue

            mapped = CloudMirrorEngine.map_file_to_logical_path(filename, clean_rel)

            items.append({
                "filename": filename,
                "source_path": clean_rel,
                "source_download_url": link,
                "size_bytes": size,
                "pub_date": pub_date,
                "target_folder": mapped["target_folder"],
                "clean_path": mapped["clean_path"],
                "category": mapped["category"],
                "device": mapped["device"],
                "tag_prefix": mapped["tag_prefix"]
            })

        return items
