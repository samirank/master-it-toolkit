# Master IT Toolkit

A portable IT service dashboard for finding tools, preparing PCs, running reviewed workflows and keeping temporary job records offline.

**[Live demo](https://samirank.github.io/master-it-toolkit/)** · **[Standalone downloads](https://github.com/samirank/master-it-toolkit/releases)** · **[Source ZIP](https://samirank.github.io/master-it-toolkit/MASTER-IT-TOOLKIT.zip)**



## Start here

1. Download `standalone-all-platforms.zip` from Releases for one SSD shared between Windows x64, Linux x64 and macOS Apple Silicon. Smaller single-platform packages are also available.
2. Extract the complete package onto your SSD. Keep the root launcher beside `MASTER-IT-TOOLKIT/`.
3. Open `Start-Windows.exe`, `Start-Linux.sh` or `Start-macOS.command` for the connected computer. The launcher supplies Python and a dedicated browser window.
4. Select tools and download their supported platform packages. Vendor-managed sources open in the toolkit's download window.
5. Scan the SSD, review each tool's quick start, and prepare required software before going offline.

The standalone browser is Chromium with bundled uBlock Origin Lite. Individual vendor sites can require temporarily disabling filtering. Downloads handled by the toolkit go to the displayed tool folder instead of the host's default Downloads folder. The launcher must remain running for local operations. Reopening the launcher for the same toolkit folder brings its existing window forward instead of starting a second session. Vault setup accepts at least six characters, including a six-digit PIN; longer passphrases provide stronger protection.

The **source ZIP** is a separate option: open its HTML for static browsing, or use Python 3.11+ with `cryptography` and `keyring` and run `python launcher.py` inside the toolkit folder. A current standalone runtime is required for vault encryption; a source update does not add missing Python dependencies to an older executable. Playwright and its Chromium runtime enable the managed browser when running from source.

The hosted demo and direct HTML mode cannot install software, execute scripts, scan drives or manage local downloads. The interface is plain HTML, CSS and JavaScript; it does not use a design framework. Browser storage is used only in static/demo mode.

## One SSD, multiple platforms

The all-platforms bundle contains three root launchers and one shared `MASTER-IT-TOOLKIT/` folder. Platform-specific browsers and native Linux/macOS executables live under `runtimes/windows-x64/`, `runtimes/linux-x64/` and `runtimes/macos-arm64/`. Each browser stays in an internal `browser.zip` until its own platform first launches. That first launch verifies its checksum and prepares it offline, with progress in the launcher terminal. The Mac browser is extracted into an owned temporary session under the signed-in Mac account’s `~/Library/Caches/Master-IT-Toolkit/browser-sessions/` folder, never onto the shared SSD. The session is removed after the last managed browser window closes, including launch failures; each new session prepares the browser again offline. The next launch retries cleanup of abandoned sessions whose launcher process no longer exists, preserving live or uncertain sessions. A forced shutdown can leave temporary files until another launch; immediate cleanup after power loss cannot be guaranteed. Linux keeps its browser runtime on the SSD and does not create this host cache. Browser profiles and toolkit downloads also stay on the SSD. Registering a master computer intentionally retains its unlock credential in that account’s OS credential store. OS-generated logs and caches are outside the toolkit’s cleanup control. Older releases may already have an expanded Mac `runtimes/macos-arm64/browser/` folder on the SSD; the new launcher does not use or automatically delete that legacy folder. The internal archive is retained for repair; it is not an update ZIP left in the SSD root. Full backups verify and retain these archives while omitting the rebuildable expanded browser caches, keeping restored SSDs portable across platforms. Root detection follows the executable location; changing drive letters or mount points does not require reinstallation. The source updater preserves these runtime folders and your local data.

To add a platform to an existing toolkit, first update its shared source, then extract only the matching `runtime-<platform>.zip` beside the toolkit folder. Runtime-only archives contain the launcher and that platform's runtime, never notes, inventory, shared source or other platforms. Do not overlay a complete fresh toolkit ZIP onto an existing workspace. `SHA256SUMS.txt` accompanies release assets. The all-platforms package is assembled only after native package inventory/browser tests pass, and conflicting shared files stop the build.

Use a filesystem that each target OS can read and write. Linux must allow execution on the SSD mount; extraction must preserve executable permissions. The Linux build needs a compatible desktop system and Chromium's system libraries; bundled runtimes do not replace OS dependencies. macOS security approval and Windows signing/reputation checks still apply. No drive formatting or security bypass is performed. Intel Macs, Linux ARM and native Windows ARM packages are not currently included. Windows tools/scripts remain Windows-specific; the shared dashboard does not make third-party executables cross-platform.

## Master computers and shared encrypted notes

Set up **Private vault** with a passphrase, save the recovery key outside the SSD, then open the vault again. Enter that passphrase (or select recovery key), give the computer a name, and choose **Make this a master computer**. Up to 20 OS accounts can be registered. You must authorize each registration locally; no computer is trusted merely because its serial number matches.

The SSD stores an encrypted grant. Its random unlock credential is stored separately in the current account's Windows Credential Manager (local-machine persistence), macOS Keychain, or Linux Secret Service. No plaintext file fallback is used. A Linux desktop needs an available Secret Service keyring. If the keyring is missing, locked or denies access, the vault stays locked and accepts its normal passphrase/recovery key. OS keychain permission prompts may still appear. This feature uses a vault passphrase and protected local credentials, not a WebAuthn/passkey account or cloud authentication.

On a master account the vault unlocks at launcher startup. On other computers it stays locked until you enter the passphrase or recovery key. Notes, favorites, settings, custom workflows and history remain shared and accessible after unlocking; they are not deleted on a computer change. Workflow history still distinguishes machines. The same physical computer booted into another OS or account needs separate registration. The vault locks after 15 minutes of inactivity; **Unlock on this master computer** uses the local credential without asking for the vault passphrase. **Lock now** does not immediately auto-unlock.

Remove masters from the vault dialog. Revocation applies to the current vault copy; disconnected copies and older backups retain their previous grants and cannot be remotely revoked. Anyone able to use your signed-in master OS account may unlock the toolkit. The vault encrypts the SQLite workspace, not downloaded programs, exported reports or browser profiles. Do not store sensitive long-term records here; move them to their permanent home.

## Find and prepare tools

The catalog contains 332 records, including software, built-in commands, supplied scripts, driver/firmware libraries and references. Third-party applications, operating-system images and commercial licenses are obtained separately from their publishers. Commercial/freeware editions remain clearly labeled; free and open-source choices are prioritized.

Use search, priority and file type, then expand **More filters** for category, platform, architecture, license, risk, offline support and download method. Availability distinguishes:

- Not downloaded to SSD / downloaded to SSD.
- Installed on this PC / not detected on this PC.
- Ready on SSD / needs extraction / needs attention.
- Missing on both the host and SSD.

**Select all matching** and the selection bar apply bulk actions. Selections survive filter changes: clear them first to restrict a new selection to the current results. The whole-catalog download queue has separately labeled filters.

Supported downloads use the repository's maintained catalog, resolve publisher assets and show transfer progress. GitHub Actions refreshes supported sources; upstream filename/version changes are handled by source resolvers. Hashes are checked when provided. License gates, sign-ins, unsupported sources and failed checks remain vendor-managed. “Automatic download available” describes saved metadata, not a guarantee the publisher is reachable now.

Finished downloads refresh inventory. Existing packages show management/status controls; updates require evidence of a newer version. Unknown versions remain unknown. Vendor-window transfers show their destination and results. Every tool has an offline quick start and official documentation link.

## Scanning and organization

The scanner indexes relevant toolkit folders and reuses file metadata. It distinguishes downloaded installers/archives from runnable portable files and detects supported host installations. Files in unrelated host folders are not assumed to belong to the toolkit.

Recognized ZIP, TAR, TAR.GZ/TGZ, TAR.BZ2, TAR.XZ, GZIP, BZIP2 and XZ packages are safely extracted into `Ready/<archive>-<fingerprint>/`. Unchanged archives are skipped, extraction limits and paths are checked, and temporary extraction files are cleaned. Original archives are retained. 7z, RAR, Zstandard and ambiguous packages currently require manual attention. Archive-local file links are materialized as regular files; escaping links and special entries are rejected. Installers are not executed by scanning.

From inside `MASTER-IT-TOOLKIT`:

```sh
python 60_SCRIPTS/Inventory/update_toolkit_inventory.py
# Inventory only, without extraction:
python 60_SCRIPTS/Inventory/update_toolkit_inventory.py --no-organize
# Optional full folder sizes:
python 60_SCRIPTS/Inventory/update_toolkit_inventory.py --full-storage
```

`--what-if` previews without writing. Inventory is evidence of file presence, not proof of authenticity, compatibility or a complete installation. Copied destination paths include the actual drive letter, UNC share or Unix mount path.

## Workflows, builds and installation

PC build profiles cover personal, office, gaming, developer, design, video, study, electronics, 3D printing and support use cases. Custom profiles are saved in SQLite. Specialist entries include FreeCAD, PrusaSlicer, KiCad, Arduino IDE, Blender and Inkscape.

Each workflow run receives a job ID, starting form, per-step notes and history. Forms are prefilled from the same profile's last run on the current machine. Machine matching uses available hardware/OS identifiers with fallbacks; it is not an authentication mechanism. Migration workflows require source and destination folders. Their copy checkpoint previews the file count, size and skipped entries before an explicit Copy action. Files go into a new job-specific folder, with SHA-256 verification and reuse of verified files when resuming. Originals and existing destination files are preserved. Close applications first: this is regular-file migration, not an operating-system snapshot, installed-app transfer or account/permission migration. Cloud placeholders and filesystem links are skipped.

Automatic preparation can download required packages, organize supported archives and optionally invoke tracked installation. Existing installations are skipped unless a newer package can be established. Unsupported sources, ambiguous installers and platform restrictions stop for attention. Checkpoint verification remains a technician decision.

Interrupted runs can be reviewed and resumed from saved checkpoints when their machine and workflow definition still match. A resumed run receives a new job ID linked to its predecessor. Completed work is not automatically replayed or declared successful.

Windows portable executables and supported PowerShell scripts use reviewed launch actions. Tracked Windows installs validate package signatures, request a recovery checkpoint and record installer outcomes. UAC and interactive installer prompts still apply. Restore points are not universal rollback; third-party changes, firmware and failed installations can require manual recovery. Linux/macOS have the dashboard, inventory and guided content; native install/portable execution parity is not complete.

## Private workspace and backups

Launcher settings, notes, favorites, checklists, custom builds, chat and job history use:

`70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite`

No account is required. **Private vault** encrypts this database using AES-256-GCM with a passphrase-derived wrapping key and a separate recovery key. SQLite operates in memory while unlocked; saved snapshots are encrypted and atomically replaced. The vault locks on restart and after 15 minutes of inactivity. Locked workspaces do not fall back to stale browser notes. Save the recovery key separately from the SSD.

**This does not encrypt every file on the SSD.** Existing diagnostic exports, inventory/receipt files, browser profiles, standalone reports and older plaintext backups remain separate. Encryption does not protect data from administrators or malware on the computer where it is unlocked. It does not securely erase old SSD blocks.

**Temporary workspace only:** do not keep sensitive or long-term records here. Never enter passwords, authentication secrets or recovery codes. Export required job records to approved permanent storage, verify the copy, then clear temporary records. Backups may retain older copies.

In **Toolkit backup**, choose an existing folder outside the toolkit: a NAS share, mounted drive or a cloud-sync folder. Two engines are available:

- Versioned ZIP: checksum-verified, but not encrypted.
- Restic: encrypted incremental snapshots, optional retention, snapshot listing and restore into an empty folder. Requires restic plus an unlocked vault.

Full backup includes downloaded tools, workspace, runtime and the adjacent launcher. Workspace backup includes assets, scripts and documentation/local data. Browser profiles, temporary files and update rollback folders are excluded. Keep-all is the default; a chosen restic retention limit removes older snapshots after successful backup/checks, per host/path group.

Automatic backups run while the launcher is open, the destination is accessible and the vault is unlocked when needed. They defer during other jobs and retry unavailable destinations. Cloud upload completion remains the sync client's responsibility. Configure destinations and credentials locally, never in source control or chat.

See [encrypted backup setup and SSD-loss recovery](MASTER-IT-TOOLKIT/70_DOCUMENTATION/Encrypted-Backup-Recovery.txt). Test a restore before relying on automatic backups.

## Offline assistant

Catalog guidance works offline without a model. For chat that travels with the SSD, open **Offline assistant > Portable AI on this SSD**, select the desired platforms and prepare it once while online. The pinned Qwen3 0.6B Q8 model is about 640 MB; small CPU runtimes support Windows x64, Linux x64 and macOS Apple Silicon. No host Ollama installation is needed. Select **Portable AI chat (SSD)** afterward.

Preparation verifies publisher hashes, shows progress and supports cancellation. Runtime/model files stay under `20_PORTABLE_APPS/AI/ToolkitAssistant`, survive updates and are included in full backups. Each answer starts an authenticated loopback server in offline mode and stops it afterward. Generated text cannot execute commands; actions still use reviewed toolkit buttons. Older CPUs/native-library versions may be unsupported.

Allow about 2 GB free RAM. The small model can make mistakes; catalog references and recent chat provide context, not proof of a diagnosis. Chat history is encrypted when the private vault is configured. Existing host Ollama remains an optional mode. See [portable AI setup](MASTER-IT-TOOLKIT/70_DOCUMENTATION/Portable-AI.txt).

## Updates and recovery

**Update toolkit from GitHub** fetches the committed distribution from `samirank/master-it-toolkit`, verifies distribution hashes and updates managed application files. Downloaded tools, inventory, local records and SQLite are preserved. Local edits to managed files stop the update instead of being overwritten.

Updates use flushed temporary files, atomic replacement and a rollback journal. If interrupted, the next launcher start restores the previous application files and asks for a restart. Recognized update ZIPs are cleaned up; keep `.toolkit-backups` until recovery is complete. The embedded Python/browser runtime requires a new standalone package when its dependencies change.

These protections improve interruption recovery but cannot guarantee survival of hardware failure, unsaved edits or filesystem corruption. Distribution hashes are not independent publisher signatures. Trusted Windows signing setup is prepared, but requires the owner's signing account/certificate: [signing instructions](MASTER-IT-TOOLKIT/70_DOCUMENTATION/Signing-Setup.txt). Do not disable SmartScreen to compensate for missing signing.

## Boot media

The toolkit works on an ordinary SSD. Ventoy is optional and independent; this project is not affiliated with it. Back up the drive before installing a boot manager. Put the toolkit on its data partition and rescue ISOs under `00_BOOT/`; verify boot images on representative hardware before service work.

A manually triggered experimental Debian live-ISO workflow is provided in `.github/workflows/live-iso.yml`. It is not a validated bootable release, and it does not flash drives automatically. Full operating-system migration and ISO boot/hardware testing remain unfinished.

## Development and publishing

Keep tool IDs stable and synchronize `assets/toolkit-manifest.json` with `assets/js/tools-data.js`. Download resolvers live in `assets/download-sources.json`; generated metadata remains separate from inventory. Do not commit downloaded executables, credentials, customer records or machine snapshots.

```sh
python -m pip install cryptography==48.0.1
python -m unittest discover -s .github/tests -p 'test_*.py'
node .github/tests/validate-paths.cjs
node .github/tests/validate-structure.cjs
# Stage new source files before building the tracked-source archive:
python .github/scripts/build_distribution.py
```

GitHub Actions runs cross-platform checks, Pages publishing, source resolution and standalone builds. Browser tests use Playwright during development. Pages settings should use GitHub Actions. Standalone signing is conditional and inactive until configured; source updates do not silently enable it.

## License

Copyright © 2026 Samiran Kakoty. See the [Master IT Toolkit Source-Available License](MASTER-IT-TOOLKIT/LICENSE.txt). Use, modification and redistribution are subject to its attribution, naming and other terms. This is source-available software, not an OSI-approved open-source release. Third-party tools retain their own licenses.

### First-run setup

The local launcher opens a four-step setup wizard for a fresh toolkit workspace: review the drive and free space, configure optional vault encryption, save an optional backup destination, then finish or start an inventory scan. Encryption requires saving the recovery key separately. No software installation, download or new automatic backup schedule is started by the wizard. Existing settings are preserved when skipped.

Choose **Set up later** to resume next time, or reopen **Setup wizard** in the header. Progress and completion are saved in the toolkit SQLite database and survive source updates. On Windows and Linux, a changed volume identifier prompts another review when available; drive-letter changes do not reset Windows setup. On macOS or filesystems without a readable stable identifier, completion follows the toolkit copy. Cloned volumes with identical identifiers cannot be distinguished. The hosted demo does not run local setup.
