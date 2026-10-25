# KitAi Workspace Instructions & Continuous Obsidian Synchronization

## 1. Project Identity
- **Name:** KitAi (formerly NovaStudy / StudyBrain)
- **Tech Stack:** FastAPI, Groq Inference (`qwen/qwen3.8-27b`), Microsoft Edge-TTS, ChromaDB, SQLite, Tailwind CSS, Lucide Icons.

## 2. Mandatory Obsidian Documentation Sync
Whenever any changes, improvements, refactors, or bug fixes are made in this repository:
1. **Update the Obsidian Vault Hub:**
   Directory: `C:\Users\HP\Documents\Obsidian Vault\KitAi - Autonomous AI Study Agent\`
   - `00 - KitAi Project Overview.md`
   - `01 - System Architecture & Pipeline.md`
   - `02 - Core Agent Loop & Self-Learning Engine.md`
   - `03 - Frontend UI & Design System.md`
   - `04 - Multimodal & Vision Capabilities.md`
   - `05 - API Specifications & Endpoints.md`
   - `06 - Setup, Execution & Testing Guide.md`
   - `07 - Project Evolution & Changelog.md`
2. **Log Every Change:**
   Always append details to `07 - Project Evolution & Changelog.md` with:
   - What changed
   - Root cause / rationale
   - Verification status
3. **Automated Verification:**
   Run `.\scripts\sync_to_obsidian.ps1` to ensure timestamps and telemetry are synced.
