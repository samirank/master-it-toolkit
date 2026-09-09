NEIGHBOR CIRCUIT TOOLKIT — FIRST WORKING EDITION
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
Favorites, checklists, notes, capacity and display settings use localStorage.
Under file:// this storage is browser/profile/file-URL dependent. It does NOT
travel automatically with the drive or survive a drive-letter change in all
browsers. Private browsing or policy may disable it. A visible warning appears
if storage is unavailable. Settings exports/imports a JSON workspace backup.
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
The canonical application source is inside NEIGHBOR-CIRCUIT-TOOLKIT/.
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
