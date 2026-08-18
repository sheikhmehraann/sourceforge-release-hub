# 🚀 SourceForge Release Hub & Cloud Management Engine

An automated release, folder organization, and cloud file-transfer suite for **SourceForge File Release System (FRS)** using **GitHub Actions distributed cloud runners** and a Python CLI.

Designed for high-speed delivery of Android custom ROMs, flashable packages, partition dumps, OTA payloads, recovery builds, custom kernels, and firmware binaries directly to SourceForge global mirrors.

---

## 🌟 Key Highlights

- ☁️ **Distributed 8-Worker Cloud Mirror Engine**: Uses GitHub Actions matrix runners to process hundreds of multi-gigabyte files simultaneously with zero local bandwidth consumption.
- 📁 **Clean & Logical Folder Hierarchies**: Automatically maps 355+ firmware packages into clean directories: `Devices/<Brand-Model>/` (`Flashable-ROMs`, `Ported-ROMs`, `Recovery-Images`, `Stock-Images`, `Official-Firmware`), `Custom-Kernels/`, `OTA-Payloads/`, `Porting-Files/`, and `Tools-and-Utilities/`.
- 🔍 **Deep Recursive Multi-Tree Spider**: Recursively traverses and indexes 100% of all files across nested subdirectories, bypassing SourceForge's standard 100-item RSS feed limit.
- ⚡ **Direct Fast CDN Auto-Routing**: Every GitHub Release generates direct AnyCast CDN links (`downloads.sourceforge.net`) with fast mirror routing.
- 🔐 **Zero-Friction Secrets Setup**: One command (`python sf_tool.py setup-secrets`) automatically configures GitHub repository secrets (`SF_USERNAME`, `SF_PROJECT`, `SF_SSH_KEY`) using the GitHub CLI (`gh`).

---

## 🏗️ Architecture & Download Flow

```
                                 ┌──────────────────────────────────────────────┐
                                 │     GitHub 8-Worker Cloud Runners            │
                                 │ (Downloads & verifies @ 1-10 Gbps speeds)    │
                                 └───────────────┬──────────────────────────────┘
                                                 │
                 ┌───────────────────────────────┴──────────────────────────────┐
                 │                                                              │
                 ▼                                                              ▼
┌───────────────────────────────────┐                          ┌───────────────────────────────────┐
│     SourceForge FRS Storage       │                          │      GitHub Release Page          │
│ (mehraann19/Devices/<Device>/...) │                          │  (Auto-created with CDN buttons)  │
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
│   ├── Infinix-Note-30-X6853/
│   │   ├── Flashable-ROMs/
│   │   ├── Ported-ROMs/               # Custom ported ROMs for Note 30
│   │   └── Recovery-Images/
│   ├── Infinix-Note-12-2023/
│   │   └── Ported-ROMs/
│   ├── Infinix-Note-40-Pro-Plus-X6858/
│   ├── Infinix-Note-40-Pro-X6850/
│   ├── Infinix-Note-40-5G-X6855/
│   ├── Infinix-Note-40-4G-X6851/
│   ├── Infinix-Zero-40-5G-X6880/
│   ├── Infinix-Zero-30-5G-X6873/
│   ├── Infinix-Hot-50-Pro-X6886/
│   ├── Infinix-Hot-50-X6885/
│   ├── Infinix-Hot-50i-X6881/
│   ├── Infinix-GT-10-Pro-X6720/
│   ├── Tecno-Pova-6-Pro-LI6/
│   ├── Tecno-Camon-30-Pro-CL7/
│   ├── Tecno-Camon-30-5G-LI7/
│   └── Lava-Agni-Universal/
├── Custom-Kernels/
│   ├── Linux-5.10/                    # Linux 5.10 AnyKernel3 builds
│   ├── Linux-6.1/                     # Linux 6.1 AnyKernel3 builds
│   └── Linux-6.6/                     # Linux 6.6 AnyKernel3 builds
├── OTA-Payloads/
│   └── Partition-Dumps/<Device>/      # Extracted raw partition dumps & zstd images
├── Porting-Files/
│   └── Vendor64/<Device>/             # Vendor64 port libraries & binaries
└── Tools-and-Utilities/               # Flashing scripts & utility packages
```

---

## ⚡ Maximum Download Speed Optimization Guide (30–100+ MB/s)

To achieve maximum Gigabit download speeds when downloading large firmware/ROM files from SourceForge:

### 1. Enable Parallel Downloading in Google Chrome
By default, Chrome uses a single TCP connection, which can be throttled by cross-continental latency. Enable Chrome's built-in multi-thread downloading:
1. Open Chrome and navigate to: `chrome://flags/#enable-parallel-downloading`
2. Change **Parallel downloading** from `Default` to **`Enabled`**.
3. Click **Relaunch**. Chrome will now download with multiple concurrent streams at **15–30+ MB/s**!

### 2. Multi-Connection Download Managers (IDM / Motrix / FDM / Aria2)
For **50–100+ MB/s (Full Fiber Speed)**, use a download manager with **16 parallel connections**:
- **Aria2 CLI**:
  ```bash
  aria2c -x 16 -s 16 -k 1M "https://downloads.sourceforge.net/project/mehraann19/Devices/Infinix-GT-20-Pro-X6871/Flashable-ROMs/X6871-15.1.2.180SP05-OP001PF001AZ-recovery-ab.zip"
  ```
- **Internet Download Manager (IDM)** / **Free Download Manager (FDM)** / **Motrix**: Paste the direct CDN download link from your GitHub Releases page to saturate 100% of your bandwidth.

---

## 🛠️ CLI Usage & Cloud Workflows

### 1. Run 8-Worker Cloud Mirror via GitHub Actions
Mirror 100% of files from any source project directly to `mehraann19`:
```bash
gh workflow run mirror_all_rama.yml --repo sheikhmehraann/sourceforge-release-hub -f source_project=rama982
```

### 2. Dual Cloud Publish (URL ➔ SourceForge ➔ GitHub Release)
```bash
python sf_tool.py publish "https://example.com/ROM.zip" --category FLASHABLE --device X6871 --title "Infinix GT 20 Pro Flashable ROM"
```

### 3. Public File & RSS Browser
Browse files using the public API (no login required):
```bash
python sf_tool.py list --public
```

---

## 📄 License
MIT License. Maintained by [Mehraan](https://github.com/sheikhmehraann).
