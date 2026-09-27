# 🌟 GIMI Mod Manager Pro (MFM)

An ultra-lightweight graphical user interface (GUI) tool written in Python/Tkinter, specifically designed to help GIMI (Genshin Impact Model Importer) users automate the management, categorization, and installation of Mods. 

Instead of manually extracting archives, dragging and dropping files, or dealing with broken mods due to nested directory structures, **GIMI Mod Manager Pro** handles everything with just a few clicks.

---

## ✨ Key Features

### 1. 🏷️ Folder Tagging System
* Automatically renames folders following a standard structure: `[Tag1] [Tag2] Character_Name`.
* Add, remove, or toggle (tick/untick) multiple tags at once via the right-side control panel.
* **Global Tag Manager:** A dedicated tool that allows you to completely wipe a specific tag across ALL folders in your root directory with a single click.

### 2. 🚀 Automated Mod Deployment (Auto-Deploy & Routing)
The most powerful tool that eliminates 100% of the hassle when downloading mods:
* **Smart Routing (Exact Match Regex):** Automatically reads the archive's name (`.zip`, `.rar`, `.7z`) and routes it to the correct character folder (e.g., a file containing `hutao` will be sent to the `Hu Tao` folder). Prevents false positives with substrings.
* **Safe Extraction:** Automatically creates a dedicated sub-folder for each Mod, preventing file clutter and overwrites. Includes data integrity verification (Size Check) before proceeding.
* **Smart Un-nesting (Rule 2 - Onion Peeling Algorithm):** Automatically detects mods trapped inside multiple layers of junk folders, pulling core resource files (`.ini`, `.dds`, `.ib`) out to match GIMI's strict folder structure. 100% safe for Merged Mods or Multi-variant Mods.
* **Auto-Cleanup:** Automatically deletes the original archive files upon successful deployment.

### 3. 📁 Batch Folder Creator
* Initialize a directory structure for dozens of characters in just 1 second.
* Supports copy/pasting character name lists, automatically filtering out forbidden Windows characters.

### 4. 🛠️ Convenient File Management & Optimized UI/UX
* **Context Menu (Right-click):** Quickly Delete, Rename, or Reveal in File Explorer directly from the list.
* **Mute Warnings:** Temporarily silence deletion/renaming confirmation prompts for 5 minutes, enabling high-speed folder cleanup.
* **Native Dark Mode:** Modern, eye-friendly dark interface (default), with an option to toggle to Light Mode in the settings.

---

## ⚙️ System Requirements & Installation

The application runs directly via Python and requires the following environment:
* **Python 3.8** or higher.
* **WinRAR** or **7-Zip** installed on your system (required for extracting `.rar` and `.7z` files).

### Installation Steps:
1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/nghia-devarch/GIMI_Mod_Manager_Pro.git
   cd GIMI_Mod_Manager_Pro
   ```
2. Install the required extraction dependency (`patool`):
   ```bash
   pip install patool
   ```
3. Run the application:
   ```bash
   python MFM.py
   ```
   *(Recommendation: You can use `pyinstaller --noconsole --onefile MFM.py` to compile the script into a single, standalone `.exe` file for convenience).*

---

## 📖 Quick Start Guide

1. Launch the software, click **📂 Choose Root Folder**, and select your GIMI Mods directory.
2. Your character list/folders will appear in the left column. Click any folder to start managing its Tags in the right panel.
3. To quickly extract newly downloaded mods:
   * Go to **Advanced Toolbox** in the top Menu Bar > Select **Open GIMI Mod Workspace**.
   * Switch to the **Auto-Route** tab.
   * Click **Select Archives** (supports multi-selection) and watch the software automatically categorize, extract, and optimize your mod structures.

---

## ⚠️ Note on Mod Structure (Rule 2)

The un-nesting algorithm (Rule 2) is designed with extreme caution:
* The system will only peel off a folder layer if the outermost layer contains **EXACTLY 1 sub-folder** and **ZERO other files** (excluding system junk files like `desktop.ini` or `thumbs.db`).
* If a folder contains 2 or more sub-folders (e.g., a Mod packed with multiple outfit variants), the system will recognize this as the Modder's intent and abort the un-nesting process to preserve your data.

---

Developed by **Nghĩa Trịnh Xuân** - Optimizing the Genshin Impact Modding Experience.
