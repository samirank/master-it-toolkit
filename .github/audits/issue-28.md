# Download, detection and workflow reliability audit

Audit completed 2026-09-11 for issue #28. This is a sampled Windows audit, not certification of every publisher, installer or operating system.

## Acceptance evidence

| Requirement | Evidence and result |
| --- | --- |
| Current failed sources | Repository catalog refreshes 34630388167 and 34630511843 succeeded. A fresh feed read at audit completion reported zero source errors. This is point-in-time health. |
| Direct / GitHub / SourceForge transfers | Complete official HWiNFO ZIP, 7-Zip installer, CrystalDiskInfo ZIP and Blender installer transfers succeeded. Blender's full installer matched the WinGet SHA256. Earlier Clonezilla and WinUtil checks were endpoint probes, not complete transfers. |
| Managed publisher transfers | Real managed Chromium downloaded the official GitHub 7-Zip MSI into an isolated toolkit destination and invoked the production inventory scanner. The scanner detected a downloaded installer. Eight browser-host tests passed, including real browser attachment navigation, destination routing and ad-blocking behavior. |
| Portable detection / organization | HWiNFO and CrystalDiskInfo archives produced detected runnable files; 7-Zip MSI remained an installer, not a portable executable. Three fresh CrystalDiskInfo extractions passed. Seven organization tests and nine portable-tool tests passed in the preceding audit pass. |
| Installer / update decisions | Four installer tests passed, including the actual PowerShell control script with mocked installer launch, signature and restore-point functions. Modified hashes and unlisted paths were rejected. Browser checks verified signed/unsigned review gates, no Download button for an existing current package, and Update for a newer package. Same-filename release tests preserve the old file and verify the new receipt. No third-party installer or repair tool was run on the host. |
| Cancellation / interrupted recovery | Nine download tests cover incomplete HTTP responses, partial cleanup/retry, and scanning a completed file before stopping a queue. Five workflow tests include abrupt process exit followed by checkpoint resume with inputs/notes preserved. Nineteen launcher tests passed with one platform-specific skip; seven migration tests passed with two platform-specific skips; two persistence tests passed. These cover updater preservation/recovery and interrupted copy behavior with fixtures, not physical power loss. |
| User-visible behavior | `validate-download-retry.cjs`, `validate-live-downloads.cjs`, `validate-workflow-jobs.cjs`, `validate-launcher.cjs`, `validate-catalog-ui.cjs`, and `validate-workflows.cjs` passed. Missing-list removal completed in under one second in the controlled completion-event check. Three HTTP transfer-manager tests passed. |
| Focused follow-ups | #29 retains the unreproduced initial CrystalDiskInfo extraction error. #30 retains the HWiNFO browser no-download observation. Physical macOS/Linux testing remains #26. |

## Fixes delivered during the audit

- HWiNFO: discover the stable portable package from the official publisher page rather than the dead WinGet mirror.
- Backup cancellation: set the active server's cancellation event, preserving the job lock and Origin validation.
- Downloads: reject incomplete responses even when only HTTP Content-Length supplies the expected length; remove partial files.
- Bulk stop: organize completed packages and send the inventory completion callback before stopping.
- Blender: use the official mirror entry point, record the selected mirror for each offered architecture and retain WinGet SHA256 verification. Probe with desktop-equivalent GET headers; range probes concealed real download redirects.
- Managed browser: wait briefly for the download event when direct-attachment navigation rejects before Playwright delivers that event. Genuine navigation failures still surface when no download starts. A real GitHub attachment previously failed with “Download is starting”; it now completes and scans.

## Limits and reproducibility

The live publisher checks used disposable local destinations. Packages were never executed. Test copies were removed after verification. The automated browser suite uses harmless local HTTP payloads; the separately recorded 7-Zip managed-browser check used an actual publisher package and real scanner. Installer/restore-point side effects were simulated deliberately, per the issue's prohibition against installing or repairing the host merely to test it.

The original CrystalDiskInfo exception was not retained, so its cause cannot be inferred from a later successful retry. HWiNFO's managed-browser URL did not initiate a download during a bounded pre-fix check; its direct downloader worked. These are documented uncertainties, not claims of repaired behavior. Publisher changes after this audit are handled by the existing scheduled source-health workflow.

Run Python suites from the repository root. Browser-host integration checks require the bundled Playwright/Chromium environment; UI `.cjs` checks require Playwright and the configured Edge executable. Platform-specific skips must remain visible in reports. Test fixture inputs contain no vault secrets or personal records.
