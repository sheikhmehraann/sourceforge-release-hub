# 🚀 SourceForge Release Hub & Cloud Management Engine

An automated release, folder organization, and cloud file-transfer suite for **SourceForge File Release System (FRS)** using **GitHub Actions cloud servers** and a Python CLI.

Designed for high-speed delivery of Android custom ROMs, flashable packages, partition dumps, OTA images, recovery builds, and software binaries directly to SourceForge mirrors.

---

## 🌟 Key Highlights

- ☁️ **GitHub Actions Cloud Server Uploads**: Delegate large multi-gigabyte file transfers (from Gofile, Google Drive, direct links) to GitHub's high-speed datacenter runners to push directly to SourceForge.
- 📁 **Clean & Logical Folder Hierarchies**: Pre-structured into `Devices/<Brand-Model>/` (Flashable-ROMs, Recovery-Images, Stock-Images), `Custom-Kernels/`, `OTA-Payloads/`, and `Tools-and-Utilities/`.
- ⚡ **Worldwide Fast CDN Auto-Routing**: When someone downloads from your GitHub, they are automatically routed to the nearest high-speed global SourceForge mirror (Fastly, Akamai, 40+ Datacenters worldwide).
- 🔄 **Automated Project Mirroring**: Mirror and re-organize entire release trees from other repositories or direct links with 1 click using GitHub Actions.
- 📊 **Download Analytics & Public File Browser**: Query public RSS feeds for file lists, sizes, MD5 hashes, and download statistics without entering passwords.
- 🔐 **Zero-Friction Secrets Setup**: One command (`python sf_tool.py setup-secrets`) automatically configures GitHub repository secrets (`SF_USERNAME`, `SF_PROJECT`, `SF_SSH_KEY`) using the GitHub CLI (`gh`).

---

## 🏗️ Architecture & Download Flow

```
                                 ┌──────────────────────────────────────────────┐
                                 │      GitHub Cloud Datacenter Server          │
                                 │ (Downloads file @ multi-gigabit speeds)      │
                                 └───────────────┬──────────────────────────────┘
                                                 │
                 ┌───────────────────────────────┴──────────────────────────────┐
                 │                                                              │
                 ▼                                                              ▼
┌───────────────────────────────────┐                          ┌───────────────────────────────────┐
│     SourceForge FRS Storage       │                          │      GitHub Release Page          │
│ (mehraann19/Devices/X6871/...)    │                          │  (Auto-created with CDN buttons)  │
└─────────────────┬─────────────────┘                          └─────────────────┬─────────────────┘
                  │                                                              │
                  └───────────────────────────────┬──────────────────────────────┘
                                                  │
                                                  ▼
                        ┌──────────────────────────────────────────────────┐
                        │      SourceForge Global Fast CDN Mirrors         │
                        │ (Fastly / Akamai / 40+ Datacenters Worldwide)    │
                        │ Auto-routes user to nearest max-bandwidth mirror │
                        └──────────────────────────────────────────────────┘
```

---

## 📂 Logical Directory Hierarchy (`/home/frs/project/mehraann19/`)

```
/home/frs/project/mehraann19/
├── Devices/
│   ├── Infinix-GT-20-Pro-X6871/
│   │   ├── Flashable-ROMs/            # Recovery-flashable A/B ZIPs & full ROMs
│   │   ├── Recovery-Images/           # OrangeFox & TWRP Custom Recoveries
│   │   ├── Stock-Images/              # Stock boot, init_boot, vendor_boot
│   │   └── Official-Firmware/         # Factory fastboot stock ROM archives
│   ├── Infinix-Hot-50-Pro-X6886/
│   ├── Infinix-Zero-40-5G-X6880/
│   └── Infinix-Note-40-Pro-X6850/
├── Custom-ROMs/                       # Universal recovery-flashable packages
├── Custom-Recoveries/                 # OrangeFox / TWRP / PBRP builds
├── Custom-Kernels/
│   ├── Linux-5.10/                    # 5.10 AnyKernel3 trees
│   ├── Linux-6.1/                     # 6.1 AnyKernel3 trees
│   └── Linux-6.6/                     # 6.6 AnyKernel3 trees
├── Stock-Firmware/                    # Boot images & factory unbrick firmware
├── OTA-Payloads/                      # Extracted raw partition dumps & zstd images
├── Porting-Files/                     # Vendor64 libraries & sepolicy patches
└── Tools-and-Utilities/               # Flashable makers & AVB patchers
```

---

## 🛠️ CLI Usage & Quick Start

### 1. Dual Cloud Publish (URL ➔ SourceForge ➔ GitHub Release with CDN)
Download any remote URL on GitHub's fast servers, upload to SourceForge, and create an official GitHub Release:
```bash
python sf_tool.py publish "https://example.com/ROM.zip" --category FLASHABLE --device X6871 --title "Infinix GT 20 Pro Flashable ROM"
```

### 2. Auto-Mirror Projects in Cloud (GitHub Actions)
Trigger GitHub Actions to mirror files from any source project into your clean logical folders:
```bash
gh workflow run cloud_mirror_project.yml --repo sheikhmehraann/sourceforge-release-hub -f source_project=rama982 -f device_filter=X6871 -f max_files=5
```

### 3. Browse SourceForge Folders & Files
Browse files using public RSS feed (no login required):
```bash
python sf_tool.py list --public
```

---

## 📄 License
MIT License. Created by [Mehraan](https://github.com/sheikhmehraann).
