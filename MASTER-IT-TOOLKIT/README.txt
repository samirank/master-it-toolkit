MASTER IT TOOLKIT TOOLKIT — FIRST WORKING EDITION
September 2026 | Offline PC Rescue & Field Service Toolkit

STARTING AND DEPLOYING
Open index.html directly from disk. The dashboard uses local HTML, CSS and
classic JavaScript only: no server, fetch(), module loader, CDN, database,
browser extension, Node.js, Python or npm is needed to USE it.

Back up the SSD before preparing it. Install Ventoy from ventoy.net and verify
the destination drive carefully: initial installation repartitions/erases it.
Copy the CONTENTS of this folder to the Ventoy data partition root. Do not put
it on the small EFI partition. Boot images go under 00_BOOT. Ventoy handles
booting; index.html is a browser dashboard, not a bootloader or WinPE image.
Do not flash an ISO to the Ventoy data partition with Rufus/Etcher; copy the
ISO file there. Keep the dashboard and trusted tools backed up elsewhere.

Use Missing Downloads to populate P1 tools first. Links are official vendor,
project or explicitly identified portable-package publisher pages, not
guaranteed direct binary links. Choose the current architecture and edition.
Verify vendor checksums/signatures; a reachable page does not certify a binary.
Extract portable apps with their whole directory tree. Folder guidance files
describe expected filenames. Installer packages remain installers even when
their files are detected on this SSD. No software payloads are bundled here.

This package is intended for the specified 256 GB SSD but can be copied to a
500 GB, 1 TB or larger data partition without architecture changes. Set the
planned capacity in Settings. Retain at least 20-30 GB free. Driver libraries
can be much larger than estimates; stage the actual OEM models you service.
The normal 256 GB decimal capacity is about 238 GiB before partition overhead.
The category budget is an initial plan, not a recommendation to select every
upper range simultaneously. Store recovery images on separate healthy media.

DASHBOARD
- Search names, vendors, descriptions, categories, tags, OS, file patterns and
  commands. Symptoms also match task guides: PC won't boot, GPU crash,
  remove OneDrive, recover files, malware, no Wi-Fi and more.
- Press / to focus search. Esc closes a dialog or clears search.
- Use categories and Favorites, Installed only, Boot/Portable, priority, type,
  online-source and Needs update filters. Reset filters removes restrictions.
- Choose cards, list or compact layout. Dark/light and layout persist.
- Tool details contain licensing notes, safety, local paths, website,
  documentation, download and command actions. HIGH RISK actions require
  reading details before the copy-command button becomes available.
- OPEN LOCAL is available for a file recorded by inventory. Browser policy
  may download or display a binary rather than launch it. Use Copy Path and
  File Explorer instead. OPEN FOLDER is also browser-dependent. The dashboard
  does not bypass browser security or execute a binary automatically.
- Built-in Windows/Linux commands are marked HOST TOOL. They are not counted
  as installed SSD files. Availability varies by OS, edition, packages and
  elevation. Linux commands run in a Linux shell, not Windows Command Prompt.
- Installer/driver presence does not mean installed on this PC. Inventory is
  only an expected-file match, not authenticity, completeness or compatibility.

LOCAL STATE AND CUSTOMER DATA
Launcher mode stores favorites, checklists, notes, capacity and display settings
in 70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite alongside job history.
This data travels with the SSD. No account or sign-in is needed. Existing browser
values migrate when absent from SQLite. Hosted demo/direct HTML mode still uses
browser storage. Settings exports/imports a JSON workspace backup. Download
receipts and generated inventory remain compatibility JSON files.
Notes also export to TXT/JSON; checklists export with their item definitions.
Exports use browser Blob downloads. Choose a destination in your browser;
the dashboard cannot silently write notes back to the SSD.

Never record customer passwords, recovery codes, private authentication
secrets or BitLocker keys. This is not an encrypted customer database. Export
approved service records, reset checklist state between jobs, clear service
notes and follow the agreed data-retention policy. Inventory and diagnostic
reports may contain filenames or device identifiers. Do not commit customer
reports to version control. Scripts never configure unattended remote access.

INVENTORY — WINDOWS POWERSHELL 5.1 / POWERSHELL 7
Open PowerShell in the toolkit root. Review script text before running:
  .\60_SCRIPTS\Inventory\Update-ToolkitInventory.ps1
Preview without writing:
  .\60_SCRIPTS\Inventory\Update-ToolkitInventory.ps1 -WhatIf

If execution policy blocks a reviewed downloaded file, inspect its signature,
origin and contents. Unblock that individual file through Properties when
appropriate. Do not weaken machine-wide policy. Follow workplace policy on
signed scripts; these locally authored scripts are not publisher-signed.

The script reads the central dataset, scans only configured folders, matches
expected filenames recursively, skips empty files and junctions/symlinks,
reads executable version resources without running them, records size and
last-modified time, and writes assets/js/local-inventory.js. It also refreshes
assets/toolkit-manifest.json for external maintenance. Read errors are saved,
not silently called healthy. Run inventory on the real SSD after copying.
The volume snapshot describes whatever volume contains the toolkit at scan
time; a development-PC run is not a measurement of the external SSD.

Reload index.html after running. Missing inventory or metadata files degrade
to unknown/unscanned state. A missing optional JS file may produce the
browser's normal resource-not-found message but does not stop the dashboard.
Stale inventory cannot detect files deleted since the scan. Archive-only
downloads are not considered installed portable apps until extracted.
Shared-suite entries may count the same package separately; storage totals
are measured by top-level folder rather than summed catalog size estimates.
SDIO executable presence does not establish offline driver-pack completeness.

ONLINE METADATA MAINTENANCE
  .\60_SCRIPTS\Inventory\Update-ToolkitMetadata.ps1
  .\60_SCRIPTS\Inventory\Update-ToolkitMetadata.ps1 -ToolId win11debloat
  .\60_SCRIPTS\Inventory\Update-ToolkitMetadata.ps1 -WhatIf

Checks official HTTPS pages and supported GitHub release APIs. It never
downloads/replaces installers, licensed software or boot media, executes
downloaded code, or flashes firmware. GitHub rate limits, missing releases,
blocked pages and redirects can require manual checks. Failures preserve a
previous known version and record the failed attempt. A page-only check does
not invent a version or advance its last-version-check date. Manual version
checks are flagged. Version strings with different formats require comparison
instead of automatically asserting an update. Fresh scanners have a separate
refresh warning; Safety Scanner expires 10 days after download.

OPTIONAL CONTROLLED DOWNLOADS
  .\60_SCRIPTS\Inventory\Download-MissingTools.ps1 -WhatIf
  .\60_SCRIPTS\Inventory\Download-MissingTools.ps1 -ToolId sysinternals

Only a small reviewed direct-download subset is enabled initially; the full
catalog remains available through Missing Downloads. The initial automated
entry is Microsoft's Sysinternals ZIP. The script displays URLs/destinations,
requires typing DOWNLOAD, supports ShouldProcess/-WhatIf, follows only
allowlisted HTTPS redirects, never runs/extracts packages, and skips existing
files unless -Replace is given. A vendor-published SHA256 must be configured
before a checksum-required entry is usable. When no vendor hash is recorded,
the script logs a computed hash WITHOUT claiming vendor verification. Review
Authenticode signatures after extraction. Successful downloads are logged in
60_SCRIPTS/Inventory/download-log.jsonl. Failures retain .partial files for
inspection and leave the existing destination untouched.

Do not add licensed binaries, vendor-account tokens or unreviewed mirrors to
the download manifest. Vendor account downloads for Revo/EaseUS and other paid
tools are manual. Read the separate source-review page for important caveats.

REPAIR AND DIAGNOSTIC SCRIPTS
Get-PCDiagnostics.ps1 requires an explicit new OutputPath, reads system and
adapter information, and does not change configuration. Get-NetworkDiagnostics
prints local addressing/adapter state without scanning or resetting anything.
Repair-WindowsFiles.ps1 checks the current component-store health by default;
-Repair offers elevated DISM RestoreHealth followed by SFC with confirmation.
It does not restart the PC automatically. Use the offline reference for WinRE
targets and disk/boot work; no automatic partition, BIOS or BCD repairs exist.

MAINTAINING THE CATALOG
assets/js/tools-data.js is the central source: window.TOOLKIT_DATA = [JSON];
Keep the assigned array valid JSON (double-quoted keys/strings, no trailing
commas/functions). Do not insert executable expressions into the array.
The scripts parse it as JSON and never evaluate JavaScript.

Fields include stable id, description, developer, categories/tags, license
notes, platform/architecture, type, size estimate, relative folder and expected
filename patterns, priority, risk/caution, versions, source-check evidence,
offline/portable/bootable flags and freshDownloadRequired. Built-in records
also contain command text. Catalog sizes are rough estimates, not live totals.

After edits, run inventory or Export-ToolkitManifest.ps1. Keep per-tool folders
for broad wildcard patterns so unrelated executables cannot create matches.
Do not use traversal/absolute paths, reparse points or external file mappings.
Latest known versions must come from primary sources and carry a check date.
HTTP reachability is recorded separately from current release verification.

assets/js/guides-data.js contains task guides, checklists and reference index.
assets/css/app.css contains the visual system. assets/js/app.js is application
logic. assets/js/local-inventory.js and metadata.js are maintenance output.
assets/source-audit.json records build-time official URL checks.
The canonical application source is inside MASTER-IT-TOOLKIT/.
Root index.html opens the dashboard there. Keep the directory intact or copy
its contents to the SSD root; both layouts work. Local paths resolve to full
native addresses from the actual file URL. Hosted demos cannot access drives.

On Linux/macOS, from this directory run:
  python3 60_SCRIPTS/Inventory/update_toolkit_inventory.py
Use --what-if to preview. Python 3.9+ is optional inventory tooling only;
the dashboard never requires it. Versions remain unknown in this updater.

Repository automation and tests live in .github/. From a Git checkout, use
.github/scripts/build_distribution.py to package tracked source files. Do not
publish generated inventory, software payloads or customer records. The root
README.md documents the public repository, Pages deployment and contribution
workflow. Add future categories to categories.js and tool records without
changing the application architecture.

SAFETY AND LICENSING
SAFE means ordinary observation, not a guarantee that a tool is harmless.
CAUTION modifies settings or needs special handling. HIGH RISK covers disk
writes, firmware, boot configuration, aggressive removal and stress testing.
Read the relevant warning before copying commands. Keep backups and confirm
the target by identity. On failing drives, image first; recover elsewhere.
Authorized account recovery uses the owner's supported recovery paths.
BitLocker is not bypassable through this dashboard.

Free/personal/technician rights are distinct. Check the CURRENT edition EULA
before commercial use, redistribution or unattended deployment. Revo Portable
and EaseUS packages belong under 80_LICENSED_TOOLS. A trial or personal license
does not automatically permit client service work. PortableApps.com entries
are explicitly identified as that project's portable packages, not claimed
to be raw upstream vendor builds. No tool is warranted safe merely because a
source responds. Avoid lookalike domains; use the linked publisher sources.

Test boot media on representative BIOS/UEFI hardware before field deployment.
This build validates the dashboard and maintenance behavior; it cannot certify
boot compatibility, Secure Boot support or binaries that have not been added.

AUTOMATIC ZIP ORGANIZATION
Launcher scans extract recognized ZIP packages into Ready folders beside the original archive. Original downloads are preserved; unchanged archives are skipped. Partial extraction files from the current scan are cleaned up. EXE/MSI installers are never run. Non-ZIP and encrypted archives require manual extraction. Use --no-organize on the Python inventory script for inventory only; --what-if makes no changes.

Download manager and app window

The launcher opens a dedicated Edge/Chrome/Chromium app window without browser tabs when a supported browser is installed (otherwise it falls back to the default browser). This is a portable launcher with an app window, not an installed PWA: keep its local launcher running for scripts, downloads and SSD access. No browser installation or system settings are changed.

Download dialogs display received/total bytes, a progress bar (indeterminate when the publisher omits the size), selected-file counts, saved paths and scan results. Downloaded tools have a Manage files button. Vendor links open a separate popup; save into the shown folder or use Import downloaded file to copy a package from another folder. While the manager is open, stable changes in the destination trigger a local scan and refresh the dashboard. Browser-managed transfers expose their detailed progress in the publisher window/browser download panel; the toolkit cannot read arbitrary third-party download events. Refresh files & scan is available if automatic detection does not apply. Imports preserve existing files and automatically scan/organize afterward. Closing a dialog does not cancel an active launcher transfer.

Background activity shows a persistent loader, current task and elapsed time during scans, downloads, bulk downloads, imports and updates. It remains visible with the launcher panel collapsed. Measured transfers show progress bars; other tasks use an indeterminate loader. Completion and errors remain visible until dismissed. For terminal-based scripts, the launcher stays busy until the terminal is closed. Reduced-motion preferences are respected.

Tracked application installation

Install on this PC opens a review, never starts an installer immediately. Through the Windows launcher, recognized EXE/MSI installers can run interactively after UAC, an installer/hash check, a before-program snapshot, and creation/verification of a new System Restore checkpoint. Unsigned packages without explicit official-source confirmation, invalid signatures, unavailable System Protection, restore-point frequency limits, or changed files stop the operation before installation. No policy settings or restore-point limits are bypassed. Choose the correct architecture and review installer choices. Firmware, drivers and boot media require their own procedures; portable tools usually need no install. Linux/macOS use their platform installer or package manager.

Install records are stored per computer in 70_DOCUMENTATION/Service-Notes/Install-History and preserved by toolkit updates. They include program lists, installer hash/publisher, return code and checkpoint identity; MSI installs also have a verbose log. These local records are excluded from published packages. A successful process exit is labeled review required, not proof of installation. Programs and Features and System Restore buttons open native interfaces for deliberate recovery. A restore point is not a disk image or a guaranteed complete rollback; keep a verified backup for changes that must be fully reversible.

Revo Uninstaller Pro is suggested for its own traced-install workflow. BCUninstaller is a free/open-source uninstall manager. Neither is installed automatically, and toolkit installs do not claim Revo tracing. For monitored installation, follow Revo's Install Program or installer context-menu workflow after preparing your recovery plan.

Sources: https://www.revouninstaller.com/online-manual/uninstaller/ ; https://www.bcuninstaller.com/ ; https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/checkpoint-computer?view=powershell-5.1 ; https://learn.microsoft.com/en-us/windows/win32/msi/rollback-installation

Unsigned installers require an explicit official-source confirmation in the review dialog. The approved hash and unsigned status are recorded; broken or invalid signatures remain blocked. This is a conscious exception, not publisher authentication.

Smart host and SSD inventory

The launcher starts a background scan automatically (use --no-startup-scan to opt out). Scans separately report registered applications on this computer, ready SSD files, downloaded installers, archives needing extraction, and interrupted files needing review. Host identity is checked so moving the SSD to another computer does not reuse that computer's installed-program status. Install review also checks the host directly. An installed host app does not replace a downloaded SSD package; the Downloaded only filter still refers to SSD files. Use Availability for Installed on this PC, Not detected on this PC, Ready on SSD, Needs extraction, Needs attention, and Missing on PC and SSD. A newer recognized SSD package gets an Update on this PC action.

Windows detection reads current-user and machine uninstall registry entries in 32/64-bit views without launching applications or invoking Win32_Product. Linux reads dpkg/rpm package databases; macOS reads application bundle metadata in standard Applications folders. Detection is conservative: exact normalized names and curated aliases/package IDs are used. Store-only apps, unsupported package managers, unregistered portable apps and uncommon installation locations can be missed; Not detected is not proof of absence. The detail view shows the evidence, version and coverage.

Recognized ZIP archives are extracted once. Other archive formats are identified for manual extraction. Installer executables are not confused with portable executables. Partially downloaded files and toolkit extraction staging folders older than 24 hours are listed for cleanup review, including their paths. Original downloads and installation/recovery records are preserved; review candidates are not automatically deleted.

PORTABLE LAUNCHES AND REVIEWED WORKFLOWS
On Windows, use Run portable to open a scanned portable EXE from its catalog
folder. Multiple matches require selecting the intended executable. Download
portable editions and scan/extract them first; an EXE installer is not portable.
Linux/macOS: run native applications manually; the guided content still works.

Start workflow from a checklist or task guide. Manual mode waits for a launch;
automatic mode opens a supported step's available tool. Both pause for your
verification before continuing. Review tool prompts, findings and child windows;
a zero exit code is not proof of repair, a clean system or a successful migration.
Stop prevents future launches, without terminating applications already running.
Closing the panel leaves the workflow active; use Workflow status to reopen it.
Stop a workflow before downloading missing tools or running other toolkit jobs.
Export its record before restarting or starting another workflow. Skips remain
unverified. This session record does not change saved manual checklist boxes.

Migration: select owner-approved data folders, back up independently, download
cloud placeholders, choose a healthy destination and configure a reviewed Robocopy/rsync copy.
Review its copy log, compare counts/sizes and open critical files. Keep originals
until owner acceptance. Reinstall apps and use supported settings/profile imports;
do not treat copying Windows or Program Files as bootable operating-system migration.
Administrator tools need explicit native elevation. No silent elevation occurs.
Bootable ISO support is planned for a future update, not provided here.


SOFTWARE SELECTION POLICY
Prefer suitable free and open-source software, then no-cost tools included with
the operating system or available as freeware. Keep freemium, personal-only,
trial and paid products as alternatives for a specific required capability.
Commercial-use and redistribution terms still apply; free does not mean open source.

The default catalog and task recommendations now use this order. The Automation-friendly
sort favors documented batch/command-line support within each licensing tier.
A BATCH / CLI AVAILABLE badge describes the vendor capability, not a promise
that the toolkit can already operate every feature unattended. Prefer explicit
inputs, logs, documented return codes, preview and recovery options over GUI clicking.
BCUninstaller is the first uninstall-manager suggestion; Revo Pro tracing is optional.

Migration preference: Robocopy on Windows and rsync on Linux/macOS, with reviewed
paths, a preview, logs and independent verification. FastCopy remains an optional
GUI alternative. The copy step is currently a manual checkpoint: this release
does not introduce a configured, unattended Robocopy/rsync copy adapter. No files
are copied until the technician explicitly configures and starts the chosen tool.


COMPACT REPORTS AND BUNDLED BROWSER
The launcher controls start collapsed. Status and popup notifications show a short
summary; expand Full report or open Logs / Job history to read complete output.
Local SQLite history retains the latest 500 jobs (the dialog shows 100), under
70_DOCUMENTATION/Service-Notes/Activity/activity.sqlite. It is excluded from
releases, static serving and toolkit updates. Back up private service notes separately.
Existing installation records remain available through installation history.

New standalone packages include their own browser engine and driver. Publisher
windows use isolated temporary profiles and route downloaded software into the
selected catalog folder, followed by a scan/organization callback. Existing filenames
are preserved; unsupported files and transfers attempted during another active job
are rejected and logged. Downloads are staged in 90_TEMP/browser-sessions, never
in the user's normal Downloads folder, and are never automatically executed.
Closing a publisher window can cancel its transfers. Some vendors may refuse
embedded/automated browsers; use a direct publisher package or explicit file import.

Dashboard browser data persists in the private Service-Notes/BrowserProfile folder.
When moving from your old browser, export its workspace backup and import it into
the bundled app if you need its notes/favorites. Publisher cookies are temporary.
Dashboard report exports go to Service-Notes/Exports. Browser software has its own
third-party notices in runtime-licenses, including the bundled browser credits.

Upgrade the COMPLETE standalone package to obtain new browser/runtime versions;
the source-only GitHub updater does not replace the browser or launcher EXE.
Keep the executable beside MASTER-IT-TOOLKIT. Existing source-only installations
can still use direct downloads/import, but managed publisher windows require the
new runtime. Source developers: install playwright==1.62.0 in a virtual environment,
set PLAYWRIGHT_BROWSERS_PATH to the toolkit runtime-browser folder, then run
python -m playwright install chromium --no-shell (Linux also needs system browser dependencies).

SQLite is a history database, not an authentication or encryption boundary.
The existing random local session URL and same-origin request protection remain;
this version adds no technician accounts or password vault. It does not encrypt
files on the SSD. The bundled desktop window is not a browser-installed PWA.


AD BLOCKING AND DOWNLOAD COMPLETION
Publisher windows include unmodified uBlock Origin Lite 2026.907.2003 with its
bundled default filters. The Downloads dialog has a Block ads on publisher site
checkbox. After changing it, reload the publisher page. Exceptions last for the
launcher session. The offline dashboard does not load this extension.
Source and license: https://github.com/uBlockOrigin/uBOL-home/releases/tag/2026.907.2003
The original GPL-3.0 license is included at runtime-extensions/ubol/LICENSE.txt.
These third-party files are not governed by the toolkit's custom branding license.

Catalogued PowerShell downloads such as WinUtil are supported as files, never
automatically executed. WinUtil's direct release PS1 is offered in Downloads;
its inventory also recognizes browser-added filename suffixes. Unrelated PS1
files are not accepted into arbitrary application folders.

Transfers queue behind active jobs instead of being cancelled immediately.
Identical destination files are reused; different same-name files are preserved
and require review. Successful transfers delete their owned staging file after
saving and scanning. Failed/queued transfers clean up their own temporary files.
The toolkit does not delete unrelated downloads, installed applications, or the
final offline package/ZIP in the destination folder. Browser profiles are cleaned
when publisher windows close. Use Open destination folder inside the toolkit's
Downloads dialog; the browser's own Show in folder may point to expired staging.

Completion events refresh the dashboard immediately after the inventory is written;
periodic polling remains a reconnect fallback. Missing-download entries disappear
once recognized. Download reports preserve line breaks and show completion milestones.
once recognized. Download reports preserve line breaks and show completion milestones.

## Repository-managed downloads

In **Missing downloads**, select a platform and architecture, then click **Download
all supported missing tools**. This scans existing files, processes one suitable
package per tool, retries transient network failures, and scans/refreshes after
each tool. Free/open-source tools go first. Windows x64 may use x86 packages when
the publisher has no x64 build. Boot ISOs are included. **All platforms** and **All
architectures** opt into additional builds. Downloads never execute installers.
**Stop queue after current file** retains completed packages. Repeating the queue
skips recorded files; partial transfers restart. Logs and the private
`70_DOCUMENTATION/Service-Notes/download-queue.json` report failures and exclusions.

The desktop resolves package identities through our repository's `download-catalog`
branch, not hardcoded publisher filenames. A bundled snapshot and local cache work
when catalog refresh is unavailable; downloading still requires network access.
**Updates → Download latest supported packages** fetches the current catalog's
packages. Older packages are preserved when checksums or version markers change.
Receipts let inventory recognize renamed packages. SHA256 is checked when the
publisher or Microsoft package manifest provides it; packages without a published
SHA256 are explicitly reported as unverified against a publisher checksum.

The **Refresh download catalog** GitHub Actions workflow runs at 05:23 and 17:23
UTC, and supports **Run workflow**. `assets/download-sources.json` maps stable tool
IDs to GitHub repositories, SourceForge stable feeds, Sysinternals archives, or
Microsoft's WinGet manifests. The workflow discovers versions/filenames, follows
repository transfers, checks recommended endpoints with one-byte requests, and
records HTTPS CDN redirects. It publishes metadata only—no third-party binaries.
It opens a GitHub issue assigned to the repository owner when releases/links
change or a source newly fails; unchanged checks do not send another notification.
GitHub email delivery follows your GitHub notification settings. The dashboard
also checks the small catalog at startup and shows a link to update notifications.

Stable repository-owned download links use:
`https://samirank.github.io/master-it-toolkit/MASTER-IT-TOOLKIT/70_DOCUMENTATION/download.html?tool=clonezilla&platform=Boot%20ISO&architecture=x64`
The Pages redirect resolves the current link from the catalog and sends the browser
to the publisher. Desktop downloads use the same catalog but save through the
launcher into the SSD. GitHub Pages does not proxy installer bytes.

Coverage is explicit in the catalog: `ready`, `manual`, `error`, or `not-applicable`.
Licensed editions, sign-in/CAPTCHA flows, hardware-specific firmware/drivers,
built-in commands and unsupported publishers cannot all be universal one-click
downloads. Failed sources retain their last good metadata for diagnosis but are
not advertised as current automatic downloads. A vendor changing its API entirely
can require a resolver update; the monitor reports this instead of guessing a URL.

PC BUILDS
Open PC builds to review 18 software setup profiles, download their packages,
and start a guided workflow. Clone any profile or create your own; names,
platform, apps, ordered instructions and links are stored in local SQLite.
Installer steps need explicit review and use tracked Windows recovery checks.
Linux/macOS native installations and specialist vendor setup links are manual.
Automatic mode opens eligible portable tools; it never silently installs,
erases disks or changes firmware. Export definitions and saved run reports
from PC builds. Active runs do not automatically resume after a restart.
Optional Python helper: python 60_SCRIPTS/Setup/build_pc.py --list
Download example: python 60_SCRIPTS/Setup/build_pc.py --profile build-gaming --download
Guided example: python 60_SCRIPTS/Setup/build_pc.py --profile build-gaming

TOOLKIT BACKUP
Open Toolkit backup to save a verified workspace or full-toolkit ZIP into an
existing NAS, mounted drive or cloud-synced folder. Save destination stores
preferences in SQLite. Full backups include downloaded tools and the launcher;
workspace backups include SQLite notes, workflows, metadata and dashboard files.
Browser profiles, temporary files and old updater backups are excluded.
Archives are not encrypted. Use private storage, or Restic/Kopia/Duplicati for
encrypted backups. Confirm cloud upload in your sync client separately.
Verify the backup, close the launcher and extract to a separate location to
restore. Restore workspace backups onto a fresh toolkit package. Test recovery
before replacing the original SSD. This is not a boot-sector/partition image.

## WordPress development

The WordPress Development category includes Local (LocalWP), WordPress Studio, DDEV, WP-CLI and Composer. Each entry includes official documentation, setup steps and a dedicated download folder. These tools are also available in the custom PC-build editor.

Choose Local or Studio for desktop site management, or DDEV for a container-based environment. DDEV requires a supported Docker provider; Composer and standalone WP-CLI require PHP. Local and DDEV already provide a site-specific WP-CLI environment. Prepare runtimes, container images and project dependencies before going offline. Back up both site files and the database before imports or synchronization; projects stored outside the toolkit are not automatically included in toolkit backups.

## Offline toolkit assistant

Open **Offline assistant** in the desktop launcher. The built-in catalog guide searches tools, how-tos, bundled workflows and custom SQLite builds without any model or internet connection. Chat history stays in the toolkit activity SQLite database (last 40 messages). Clear saved chat removes those records; existing backups may still contain earlier history. The database is not encrypted. Avoid entering passwords or customer secrets.

For natural-language AI chat, install [Ollama](https://ollama.com/download), enable its [local-only mode](https://docs.ollama.com/faq) with `OLLAMA_NO_CLOUD=1`, and start it on its default loopback address. In the assistant setup panel, click **Download local model** while online to prepare [Qwen3 0.6B](https://ollama.com/library/qwen3:0.6b). Then select **Local AI chat**. Once the runtime and model are present, chat works offline; no cloud endpoint or cloud fallback is used. The small model trades answer quality for a smaller footprint, and response speed depends on the computer.

The AI connects only to `127.0.0.1:11434`, bypasses proxy settings and rejects redirects. It receives your recent chat and matching catalog/workflow references, not a filesystem dump or your service notes. It cannot execute generated shell text. Tool and workflow buttons use existing toolkit launch/install/download reviews; diagnostic buttons require an explicit review click and then use existing job progress/logs. Confirm the current OS, errors and backups before following advice. An answer is not evidence that a command ran.

Ollama and model weights are **not bundled in the source ZIP or launcher**. By default they live on the host computer, so prepare each computer before going offline (or configure Ollama's documented model storage location). Toolkit workspace backups include the chat SQLite database, not external model storage. A missing or unavailable model falls back to catalog guidance. Model preparation can take several minutes; keep the launcher open until it reports completion.

## Finding tools with filters

Use **Availability → Not downloaded to SSD** to find packages absent from the saved inventory, independently of whether the application is installed on the host PC. **Downloaded to SSD**, host installation, ready-to-run, extraction and attention states are separate choices. Missing downloads includes every priority; choose P1/P2 when preparing only essentials.

Expand **More filters** to combine download method, category, operating system, architecture, license, risk and offline capability with the existing search, priority and file-type controls. **No automatic download available** includes vendor-managed sources, failed sources and entries without a matching automatic platform/architecture package. Unknown catalog status is separate. **Automatic download available** uses saved package metadata, not a fresh connectivity test. Platform/architecture filters also narrow the tool's advertised support.

Use **Select all matching** and **Download selected missing** to act on the filtered list. Existing selections remain selected when filters change; clear selection first if you want only the current matches. The whole-catalog download queue above the list retains its separately labeled queue filters. Reset filters clears the list criteria.

## Update, interruption and automatic-backup protection

Updates preserve downloaded tool packages, inventory, receipts, service notes, custom workflows and SQLite data. Local changes to managed application files stop an update instead of being overwritten. Toolkit file replacements now use flushed temporary files and atomic replacement, with a checksummed rollback journal committed before the first change. After an interrupted update, the next launcher start restores the previous files and asks you to restart once more to load that restored version. Recovery does not remove tools or personal data. Keep the `.toolkit-backups` folder until recovery is complete.

SQLite explicitly uses FULL synchronization and platform full-fsync support. Completed Windows managed downloads are flushed and renamed from partial files before being published. Backup ZIPs are verified and flushed before receiving their final filename. These measures improve crash recovery; they cannot guarantee survival of hardware failure, interrupted unsaved edits, a drive that ignores flush requests, or filesystem corruption. Interrupted third-party programs and partially completed installations still require their own recovery.

In **Toolkit backup**, choose an existing private destination outside the toolkit (NAS, mounted backup drive or cloud-synced folder), enable **Automatically back up when destination is available**, choose the interval and save. Enabling selects full backup for tools plus workspace; workspace-only is available if desired. The launcher checks once a minute while open, defers during toolkit jobs, and retries unavailable or failed destinations after five minutes. Last successful backup time is stored in SQLite and survives restarts. Versioned backups are retained; ensure destination capacity. A cloud-synced folder confirms only a local snapshot, not completion of the cloud upload. No cloud account is configured or data uploaded without your chosen destination. The launcher must be running; this is not an operating-system background service.

## Workflow preparation and machine job history

Every newly started checklist/workflow/build run has a unique job ID and a SQLite record from the start. **Workflow job history** shows the current machine by default, with an option for all machines. Matching prefers an available BIOS/hardware serial, then OS machine ID, then a hardware MAC or hostname fallback. MAC addresses and serials are shown as evidence; duplicates, virtualization, hardware replacement and randomized network addresses can affect matching. Records include starting details, per-step preparation/results and saved notes. An unfinished record remains visible as incomplete/interrupted after restart; it is not resumed or declared successful automatically.

The start form offers editable ticket, technician, issue, source/destination reference paths and notes, prefilled from the same profile's last run on this machine. Source/destination fields describe manual copy steps and are never interpolated into shell commands. Save checkpoint notes explicitly, or include them when continuing/skipping. Saved job records survive updates and are included in workspace/full backups.

In automatic mode, **Download missing tools and organize recognized archives** runs the repository download queue for each required tool and refreshes inventory. **Fetch latest supported packages** requests latest packages instead. Offline failures retain existing tools. Recognized ZIP extraction and organization use the scanner; original packages and customer files are not deleted. Cleanup requiring a choice remains manual.

Optionally enable tracked installation at the start. Only a single installer with a valid signature is eligible. Existing installations are skipped unless every detected host version can be compared numerically and the scanned package is proven newer, with updates enabled. Recovery-checkpoint creation, UAC and interactive installer prompts still apply. Ambiguous/unsigned packages, unsupported platforms, firmware/drivers and vendor-managed downloads stop for attention. Manual mode does not perform preparation automatically. Checkpoints still require technician verification; preparation is not a diagnosis or proof the requested repair worked.
