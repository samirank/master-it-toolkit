Master IT Toolkit now supports one SSD with shared data across Windows x64, Linux x64 and Apple Silicon Macs.

- **Fresh SSD:** download `standalone-all-platforms.zip`, extract it once, and use `Start-Windows.exe`, `Start-Linux.sh` or `Start-macOS.command`.
- **Existing toolkit:** update its shared source first, then extract the required `runtime-<platform>.zip` beside the `MASTER-IT-TOOLKIT` folder. These smaller archives add only that platform's runtime and launcher. Do not overlay a complete fresh toolkit package onto your existing workspace.
- **Master computers:** create/unlock Private vault, enter your passphrase again, and choose **Make this a master computer**. Registered OS accounts unlock at startup using their native credential store. Other computers require the vault passphrase or recovery key. Shared notes remain encrypted on the SSD after vault setup.
- Each platform prepares its bundled browser on first launch, entirely offline. The Mac browser expands into a temporary host session, cleaned after the last managed browser window closes. Interrupted sessions are checked for cleanup on the next launch. Linux retains its browser on the SSD. Long Mac bundle paths never travel back to Windows.
- `SHA256SUMS.txt` contains checksums for the release packages.

No Python installation is required for standalone packages. Linux still needs a compatible desktop and Chromium system libraries, plus permission to execute files on the SSD mount. Windows tools cannot run natively on other operating systems. Intel Mac, Linux ARM and native Windows ARM builds are not included.

OS keychain approval may be required. Linux master unlock needs Secret Service; unavailable credential stores fall back to the vault passphrase. Keep the recovery key separate from the SSD. The vault protects SQLite workspace data, not exported reports, downloaded programs or browser profiles. Removing a master affects the current vault copy; older copies/backups retain their previous grants.

Windows signing is present only when configured by the publisher. This release does not bypass SmartScreen or macOS security checks. Keep the launcher running while using local actions, and restart it after source updates.

[Setup and limitations](https://github.com/samirank/master-it-toolkit#start-here)
