#!/usr/bin/env python3
"""
Folder Manager Module
Automates remote folder creation, hierarchical organization, and folder README generators.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from .sourceforge_client import SourceForgeClient


class FolderManager:
    """Manages SourceForge project folder structures and layouts."""

    DEFAULT_PRESETS = {
        "logical_hub": [
            "Devices/Infinix-GT-20-Pro-X6871/Flashable-ROMs",
            "Devices/Infinix-GT-20-Pro-X6871/Recovery-Images",
            "Devices/Infinix-GT-20-Pro-X6871/Stock-Images",
            "Devices/Infinix-GT-20-Pro-X6871/Official-Firmware",
            "Devices/Infinix-Hot-50-Pro-X6886/Flashable-ROMs",
            "Devices/Infinix-Zero-40-5G-X6880/Flashable-ROMs",
            "Devices/Infinix-Note-40-Pro-X6850/Flashable-ROMs",
            "Custom-ROMs",
            "Custom-Recoveries/OrangeFox",
            "Custom-Recoveries/TWRP",
            "Custom-Kernels/Linux-5.10",
            "Custom-Kernels/Linux-6.1",
            "Custom-Kernels/Linux-6.6",
            "Stock-Firmware/Boot-Images",
            "Stock-Firmware/Factory-Fastboot",
            "OTA-Payloads/Partition-Dumps",
            "Porting-Files/Vendor64",
            "Tools-and-Utilities/Flashable-Engine",
            "Tools-and-Utilities/AVB-Patcher"
        ],
        "transsion_firmware": [
            "FLASHABLE",
            "RECOVERY/{device}",
            "RECOVERY/{device}/XOS15",
            "KERNEL",
            "KERNEL/5.10",
            "KERNEL/6.1",
            "KERNEL/6.6",
            "STOCK-IMAGE/{device}",
            "STOCK-IMAGE/{device}/BOOT",
            "STOCK-IMAGE/BOOT-TRANSSION",
            "OTA-EXTRACT",
            "OTA-EXTRACT/pri_board",
            "PORT",
            "PORT-FILES",
            "OFFICIAL-FW",
            "TOOLS"
        ],
        "android_device": [
            "{device}/ROMs",
            "{device}/Recovery",
            "{device}/Firmware",
            "{device}/Vendor_Boot",
            "{device}/Kernel",
            "{device}/Tools"
        ],
        "software_hub": [
            "Releases/Windows",
            "Releases/Linux",
            "Releases/Android",
            "Releases/macOS",
            "Beta_Builds",
            "Changelogs"
        ],
        "firmware_dump": [
            "{brand}/{model}/Stock_ROM",
            "{brand}/{model}/Flashable_ZIPs",
            "{brand}/{model}/Partitions",
            "{brand}/{model}/OTA"
        ]
    }

    def __init__(self, client: SourceForgeClient, config_path: Optional[str] = None):
        self.client = client
        self.presets = dict(self.DEFAULT_PRESETS)
        if config_path and Path(config_path).is_file():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    if "folder_presets" in cfg:
                        self.presets.update(cfg["folder_presets"])
            except Exception as e:
                print(f"[!] Warning reading presets config: {e}")

    def create_structure(self, preset_name: str, variables: Dict[str, str]) -> List[str]:
        """Creates a predefined directory structure on SourceForge."""
        if preset_name not in self.presets:
            raise ValueError(f"Preset '{preset_name}' not found. Available: {list(self.presets.keys())}")

        template_paths = self.presets[preset_name]
        created_paths = []

        with self.client:
            for template in template_paths:
                rendered = template
                for var_name, var_value in variables.items():
                    rendered = rendered.replace(f"{{{var_name}}}", var_value)
                
                print(f"[*] Ensuring remote folder: {rendered}")
                self.client.mkdir_p(rendered)
                created_paths.append(rendered)

        return created_paths

    def create_custom_folder(self, folder_path: str):
        """Creates a custom remote directory path."""
        with self.client:
            self.client.mkdir_p(folder_path)
            print(f"[+] Folder '{folder_path}' created on SourceForge!")

    def set_folder_readme(self, folder_path: str, title: str, description: str, maintainer: str = "") -> str:
        """
        Creates a README.md file in the folder so SourceForge displays the notes.
        """
        readme_content = f"""# {title}

{description}

---
- **Maintained by:** {maintainer or self.client.username or "Mehraan"}
- **Auto-generated via:** [SourceForge Release Hub](https://github.com/{self.client.username or 'sheikhmehraann'}/sourceforge-release-hub)
"""
        temp_file = Path("temp_folder_readme.md")
        try:
            temp_file.write_text(readme_content, encoding="utf-8")
            with self.client:
                res = self.client.upload_file(str(temp_file), folder_path)
                return res.get("remote_path", "")
        finally:
            if temp_file.exists():
                temp_file.unlink()
