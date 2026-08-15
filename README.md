# 🚀 SourceForge Release Hub & Cloud Management Engine

An automated release, folder organization, and cloud file-transfer suite for **SourceForge File Release System (FRS)** using **GitHub Actions cloud servers** and a Python CLI.

Designed for high-speed delivery of Android custom ROMs, flashable packages, partition dumps, OTA images, recovery builds, and software binaries directly to SourceForge mirrors.

---

## 🌟 Key Highlights

- ☁️ **GitHub Actions Cloud Server Uploads**: Delegate large multi-gigabyte file transfers (from Gofile, Google Drive, direct links) to GitHub's high-speed datacenter runners to push directly to SourceForge.
- 📁 **Automated Folder Hierarchies**: Create complex nested folder trees (e.g. `X6871/ROMs`, `X6871/Recovery`, `Tools/Windows`) locally or from the cloud in seconds.
- 🔄 **GitHub Releases Mirroring**: Automatically mirrors new GitHub releases and binary artifacts to your SourceForge release folders.
- 📊 **Download Analytics & Public File Browser**: Query public RSS feeds for file lists, sizes, MD5 hashes, and download statistics without entering passwords.
- 🔐 **Zero-Friction Secrets Setup**: One command (`python sf_tool.py setup-secrets`) automatically configures GitHub repository secrets (`SF_USERNAME`, `SF_PROJECT`, `SF_SSH_KEY`) using the GitHub CLI (`gh`).

---

## 🏗️ Architecture

```
                                 ┌─────────────────────────────────┐
                                 │   GitHub Actions Cloud Server   │
                                 │  (High-Bandwidth Cloud Runner)  │
                                 └───────────────┬─────────────────┘
                                                 │
                   Direct URL (Gofile, GD, Web) │ (Aria2 / Multi-Thread Fast Pipe)
                                                 ▼
┌──────────────────┐    Dispatch Task    ┌───────────────┐   rsync / SFTP (SSH)   ┌───────────────────────────┐
│ Local CLI / User │ ──────────────────> │ GitHub Runner │ ─────────────────────> │ SourceForge FRS Storage   │
│   (sf_tool.py)   │                     │  Filesystem   │                        │ (frs.sourceforge.net)     │
└────────┬─────────┘                     └───────────────┘                        └─────────────┬─────────────┘
         │                                                                                      │
         │ Direct Local Upload (SFTP)                                                          │ Direct Mirror Links
         └──────────────────────────────────────────────────────────────────────────────────────▼
                                                                                   Worldwide Fast CDN Mirrors
```

---

## 📦 Installation & Setup

### 1. Install Requirements
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Copy the example configuration:
```bash
cp config/.env.example config/.env
```
Edit `config/.env` with your project credentials:
```env
SF_USERNAME=your_sourceforge_username
SF_PROJECT=your_sourceforge_project_name
SF_KEY_PATH=C:/Users/Admin/.ssh/id_ed25519
```

### 3. Push Secrets to GitHub Actions (One-Click)
Run the automated secrets configuration tool to sync with GitHub:
```bash
python sf_tool.py setup-secrets
```

---

## 🛠️ CLI Usage Guide

### 1. Cloud Upload (GitHub Servers)
Download a remote file (e.g. from Gofile or direct link) and upload it directly to SourceForge using GitHub Actions servers:
```bash
python sf_tool.py cloud-upload "https://example.com/ROM-v1.0.zip" "X6871/ROMs"
```

Check live status of cloud transfers:
```bash
python sf_tool.py cloud-status
```

---

### 2. Browse SourceForge Folders & Files
Browse files using public RSS feed (no login required):
```bash
python sf_tool.py list --public
```

Browse remote project directories via SFTP:
```bash
python sf_tool.py list "X6871/ROMs"
```

---

### 3. Create Remote Folders & Trees

Create a single directory:
```bash
python sf_tool.py mkdir "X6871/Recovery"
```

Create an entire device folder tree using presets:
```bash
python sf_tool.py preset android_device --device X6871
```
*(Creates `X6871/ROMs`, `X6871/Recovery`, `X6871/Firmware`, `X6871/Vendor_Boot`, `X6871/Kernel`, `X6871/Tools` automatically!)*

---

### 4. Upload Local Files
Upload local files directly to SourceForge with progress speed and checksums:
```bash
python sf_tool.py upload "./output/ROM.zip" "X6871/ROMs"
```

---

### 5. View Download Analytics
View total project downloads, top countries, and OS distribution:
```bash
python sf_tool.py stats --days 30
```

---

## ⚡ GitHub Actions Workflows

| Workflow | File | Description |
| :--- | :--- | :--- |
| **Cloud Uploader** | `.github/workflows/sourceforge_upload.yml` | Downloads any file URL on GitHub servers and uploads directly to SourceForge via rsync/SFTP. |
| **Release Mirror** | `.github/workflows/release_mirror.yml` | Automatically mirrors GitHub release tags and binaries to SourceForge release folders. |
| **Folder Organizer** | `.github/workflows/sourceforge_organize.yml` | Remotely creates folder structures, presets, and READMEs on SourceForge. |
| **CI Validation** | `.github/workflows/ci.yml` | Validates Python syntax and CLI help menus. |

---

## 🔗 Direct Download URL Format

Direct CDN mirror URLs generated for your users:
```
https://downloads.sourceforge.net/project/<SF_PROJECT>/<FOLDER_PATH>/<FILENAME>
```
Standard web download landing page:
```
https://sourceforge.net/projects/<SF_PROJECT>/files/<FOLDER_PATH>/<FILENAME>/download
```

---

## 📄 License
MIT License. Created by [Mehraan](https://github.com/sheikhmehraann).
