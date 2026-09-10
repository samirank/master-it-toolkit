window.TOOLKIT_WORKFLOWS = {
  "newpc": {
    "name": "New Windows PC Setup",
    "steps": [
      {
        "text": "Confirm ownership, scope and backup preferences"
      },
      {
        "text": "Record model, serial and Windows edition"
      },
      {
        "text": "Create a restore point or recoverable baseline backup"
      },
      {
        "text": "Run Windows Update and restart; recheck"
      },
      {
        "text": "Review BIOS/firmware model, release notes and stable power"
      },
      {
        "text": "Install OEM chipset, network and GPU drivers"
      },
      {
        "text": "Remove unwanted OEM trialware with owner approval",
        "tool": "bcu"
      },
      {
        "text": "Review supported privacy, advertising and telemetry settings"
      },
      {
        "text": "Review Copilot, Recall, Click to Do and app AI preferences"
      },
      {
        "text": "Confirm OneDrive known-folder backup and account preferences"
      },
      {
        "text": "Check BitLocker status and owner-held recovery-key access"
      },
      {
        "text": "Install browser, office suite, PDF reader, 7-Zip and media player"
      },
      {
        "text": "Install required Visual C++ / .NET runtimes"
      },
      {
        "text": "Test audio, webcam, networking, sleep and peripheral devices"
      },
      {
        "text": "Record versions, changes and owner handover"
      }
    ]
  },
  "malware": {
    "name": "Malware Cleanup",
    "steps": [
      {
        "text": "Confirm authorization and incident-response requirements"
      },
      {
        "text": "Isolate active compromise when appropriate"
      },
      {
        "text": "Preserve evidence and necessary data before modifying"
      },
      {
        "text": "Prepare a trusted environment and fresh scanner definitions"
      },
      {
        "text": "Scan and review findings; avoid restoring infected executables",
        "tool": "safetyscanner"
      },
      {
        "text": "Review startup persistence, services, tasks and browser extensions",
        "tool": "autoruns"
      },
      {
        "text": "Update Windows, browsers and software"
      },
      {
        "text": "Rotate compromised credentials from a clean device"
      },
      {
        "text": "Reinstall trusted media if cleanup confidence is insufficient"
      },
      {
        "text": "Document findings and verify protection is enabled"
      }
    ]
  },
  "boot": {
    "name": "PC Won't Boot",
    "steps": [
      {
        "text": "Record error, recent changes and firmware boot mode"
      },
      {
        "text": "Check power, cables and firmware disk detection"
      },
      {
        "text": "Confirm BitLocker key availability with owner"
      },
      {
        "text": "Check drive health before filesystem or boot repair",
        "tool": "cdi"
      },
      {
        "text": "Back up / image important data"
      },
      {
        "text": "Use Windows RE Startup Repair"
      },
      {
        "text": "Identify Windows and EFI partitions before manual repair"
      },
      {
        "text": "Review BCD and WinRE configuration without blanket changes"
      },
      {
        "text": "Test repeated cold boots"
      },
      {
        "text": "Record cause and successful recovery steps"
      }
    ]
  },
  "failing": {
    "name": "Failing Disk",
    "steps": [
      {
        "text": "Stop unnecessary use and writes"
      },
      {
        "text": "Discuss professional recovery for physical damage or irreplaceable files"
      },
      {
        "text": "Record drive serial, capacity and minimal health observations"
      },
      {
        "text": "Prepare a healthy destination large enough for image and recovery output"
      },
      {
        "text": "Image first with a resumable mapfile, if appropriate"
      },
      {
        "text": "Preserve source and original image"
      },
      {
        "text": "Recover from a working image copy"
      },
      {
        "text": "Save recovered files to separate healthy storage"
      },
      {
        "text": "Verify critical files with owner"
      },
      {
        "text": "Replace failed media and document outcome"
      }
    ]
  },
  "gaming": {
    "name": "Gaming PC Troubleshooting",
    "steps": [
      {
        "text": "Record game, symptom and reproducible workload"
      },
      {
        "text": "Review Reliability Monitor and crash timestamps"
      },
      {
        "text": "Return CPU/GPU/RAM tuning to defaults for baseline"
      },
      {
        "text": "Check temperatures, cooling and power connectors",
        "tool": "hwinfo"
      },
      {
        "text": "Check RAM and storage health",
        "tool": "cdi"
      },
      {
        "text": "Stage and install model-matched GPU drivers"
      },
      {
        "text": "Verify required runtimes and game files"
      },
      {
        "text": "Test one subsystem at a time while monitoring temperatures"
      },
      {
        "text": "Preserve Xbox/anti-cheat dependencies required by games"
      },
      {
        "text": "Repeat original workload and record result"
      }
    ]
  },
  "network": {
    "name": "Network Troubleshooting",
    "steps": [
      {
        "text": "Check cable, link LEDs, airplane mode and adapter state"
      },
      {
        "text": "Confirm driver hardware ID and link speed"
      },
      {
        "text": "Record IP, mask, gateway, DNS and DHCP status"
      },
      {
        "text": "Test the gateway and another LAN device"
      },
      {
        "text": "Compare known external IP and DNS lookup results"
      },
      {
        "text": "Check duplicate IP against DHCP leases / neighbor table"
      },
      {
        "text": "Test required TCP port and proxy/VPN configuration",
        "tool": "tcpview"
      },
      {
        "text": "Compare known-good Ethernet cable and Wi-Fi location"
      },
      {
        "text": "Run authorized throughput or packet capture tests if needed"
      },
      {
        "text": "Document changes and restore temporary test settings"
      }
    ]
  },
  "return": {
    "name": "Before Returning Customer PC",
    "steps": [
      {
        "text": "Verify the original issue is resolved using the original workload"
      },
      {
        "text": "Check updates, Defender, firewall and restore configuration"
      },
      {
        "text": "Verify user data, applications, printing and peripherals"
      },
      {
        "text": "Confirm BitLocker recovery key is held by the owner"
      },
      {
        "text": "Remove temporary remote access and technician accounts if created"
      },
      {
        "text": "Remove customer copies from toolkit according to agreed retention"
      },
      {
        "text": "Remove test files and close customer sessions"
      },
      {
        "text": "Export service notes without credentials"
      },
      {
        "text": "Document changes, licenses and remaining issues"
      },
      {
        "text": "Obtain owner acceptance and disconnect toolkit safely"
      }
    ]
  },
  "migration": {
    "name": "Data Migration",
    "steps": [
      {
        "text": "Identify source, destination and owner-approved data scope"
      },
      {
        "text": "Check source health, encryption and cloud-only placeholders",
        "tool": "cdi"
      },
      {
        "text": "Create an independent backup before migration"
      },
      {
        "text": "Download necessary synced files and verify availability"
      },
      {
        "text": "Preview copy paths; avoid mirror/delete modes"
      },
      {
        "text": "Prefer Robocopy on Windows or rsync on Linux/macOS for scriptable copying. Review the official instructions, preview source/destination paths, keep originals, avoid move/delete/mirror options, and retain the copy log. This is a manual checkpoint until a reviewed copy job is configured; FastCopy is an optional GUI alternative."
      },
      {
        "text": "Compare counts, sizes and open critical sample files"
      },
      {
        "text": "Confirm Desktop, Documents, Pictures and application data"
      },
      {
        "text": "Do not transfer unknown persistence or compromised executables"
      },
      {
        "text": "Keep original until the owner approves the migration"
      }
    ]
  },
  "ssd": {
    "name": "SSD Upgrade",
    "steps": [
      {
        "text": "Confirm interface, form factor and capacity compatibility"
      },
      {
        "text": "Check source health and encryption",
        "tool": "cdi"
      },
      {
        "text": "Create verified backup and confirm recovery-key access"
      },
      {
        "text": "Record both disk serials before cloning"
      },
      {
        "text": "Use guided clone/image tool for healthy media"
      },
      {
        "text": "Do not interrupt copy; maintain stable power"
      },
      {
        "text": "Disconnect original before first boot of clone"
      },
      {
        "text": "Verify partitions, files, applications and boot behavior"
      },
      {
        "text": "Check SSD health and available space",
        "tool": "cdi"
      },
      {
        "text": "Retain original until verification and handover are complete"
      }
    ]
  },
  "reinstall": {
    "name": "Windows Reinstallation",
    "steps": [
      {
        "text": "Confirm owner authorization, Windows license and edition"
      },
      {
        "text": "Back up data and application/license records without passwords"
      },
      {
        "text": "Verify recovery keys and cloud sync completeness"
      },
      {
        "text": "Stage correct offline network, chipset and storage drivers"
      },
      {
        "text": "Create trusted Windows media and verify source"
      },
      {
        "text": "Review partition selection carefully; installation can erase data"
      },
      {
        "text": "Use supported account/OOBE choices agreed with owner"
      },
      {
        "text": "Install drivers, Windows updates and required runtimes"
      },
      {
        "text": "Restore verified data and install approved applications"
      },
      {
        "text": "Review privacy, AI, OneDrive and BitLocker preferences"
      },
      {
        "text": "Test hardware, apps, activation and recovery options"
      },
      {
        "text": "Document build and return the PC with owner acceptance"
      }
    ]
  },
  "profile-migration": {
    "name": "New PC / profile migration",
    "steps": [
      {
        "text": "Agree which user folders, browser bookmarks, mail archives and application settings to migrate. Record application licenses without credentials."
      },
      {
        "text": "Back up the source independently, unlock encrypted data with the owner and fully download cloud-only files."
      },
      {
        "text": "Check the source drive health before copying. Stop and use a recovery workflow if it is failing.",
        "tool": "cdi"
      },
      {
        "text": "Prefer Robocopy on Windows or rsync on Linux/macOS for scriptable copying. Review the official instructions, preview source/destination paths, keep originals, avoid move/delete/mirror options, and retain the copy log. This is a manual checkpoint until a reviewed copy job is configured; FastCopy is an optional GUI alternative."
      },
      {
        "text": "Review the copy log and verification failures. Compare file counts and sizes; open critical files on the destination."
      },
      {
        "text": "Install applications from trusted installers on the new PC. Import supported bookmarks, mail and settings; do not copy Windows or Program Files as an OS migration."
      },
      {
        "text": "Have the owner confirm access to files and applications. Keep the original and backup until acceptance."
      }
    ]
  }
};
for (const id of ["migration","profile-migration"]) window.TOOLKIT_CHECKLISTS[id] = {name:window.TOOLKIT_WORKFLOWS[id].name,items:window.TOOLKIT_WORKFLOWS[id].steps.map(s=>s.text)};
