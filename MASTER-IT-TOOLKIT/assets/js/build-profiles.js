window.TOOLKIT_BUILDS = {
  "build-personal": {
    "name": "Personal PC",
    "platform": "Windows",
    "description": "Choose default apps and privacy preferences; verify browser, documents, media and backup restore.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Firefox Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "firefox",
        "action": "install"
      },
      {
        "text": "Set up 7-Zip. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "7zip",
        "action": "install"
      },
      {
        "text": "Set up LibreOffice Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "libreoffice",
        "action": "install"
      },
      {
        "text": "Set up VLC Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vlc",
        "action": "install"
      },
      {
        "text": "Set up KeePassXC. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "keepassxc",
        "action": "install"
      },
      {
        "text": "Set up FreeFileSync. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "freefilesync",
        "action": "install"
      },
      {
        "text": "Choose default apps and privacy preferences; verify browser, documents, media and backup restore."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-office": {
    "name": "Office PC",
    "platform": "Windows",
    "description": "Configure approved work accounts, printer/scanner and document templates; test printing and a sample attachment. Follow employer device policies.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up ONLYOFFICE Desktop Editors. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "onlyoffice",
        "action": "install"
      },
      {
        "text": "Set up Mozilla Thunderbird. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "thunderbird",
        "action": "install"
      },
      {
        "text": "Set up NAPS2. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "naps2",
        "action": "install"
      },
      {
        "text": "Set up PDF Arranger. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "pdfarranger",
        "action": "install"
      },
      {
        "text": "Set up KeePassXC. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "keepassxc",
        "action": "install"
      },
      {
        "text": "Configure approved work accounts, printer/scanner and document templates; test printing and a sample attachment. Follow employer device policies."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-gaming": {
    "name": "Gaming PC",
    "platform": "Windows",
    "description": "Install the correct OEM GPU driver; check display refresh rate, controller input, game saves and a representative game. Do not apply automatic overclocks.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Steam. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "steam",
        "action": "install"
      },
      {
        "text": "Set up HWiNFO. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "hwinfo",
        "action": "install"
      },
      {
        "text": "Set up CPU-Z. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "cpuz",
        "action": "install"
      },
      {
        "text": "Set up GPU-Z. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "gpuz",
        "action": "install"
      },
      {
        "text": "Set up OBS Studio. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "obs",
        "action": "install"
      },
      {
        "text": "Install the correct OEM GPU driver; check display refresh rate, controller input, game saves and a representative game. Do not apply automatic overclocks."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-printing": {
    "name": "3D Printing PC",
    "platform": "Windows",
    "description": "Select the exact printer, nozzle and filament profile; preview toolpaths and run a supervised calibration print. Firmware flashing is a separate task.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up FreeFileSync. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "freefilesync",
        "action": "install"
      },
      {
        "text": "Set up 7-Zip. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "7zip",
        "action": "install"
      },
      {
        "text": "Install FreeCAD and verify a simple model export.",
        "url": "https://www.freecad.org/downloads",
        "tool": "freecad",
        "action": "install"
      },
      {
        "text": "Install PrusaSlicer for the selected platform.",
        "url": "https://help.prusa3d.com/downloads/prusaslicer",
        "tool": "prusaslicer",
        "action": "install"
      },
      {
        "text": "Select the exact printer, nozzle and filament profile; preview toolpaths and run a supervised calibration print. Firmware flashing is a separate task."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-electronics": {
    "name": "Electronics Workbench PC",
    "platform": "Windows",
    "description": "Install board-specific USB drivers; verify serial ports, board voltage and a simple test circuit before connecting equipment.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Visual Studio Code (VS Code / portable). Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vscode",
        "action": "install"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "install"
      },
      {
        "text": "Set up PuTTY. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "putty",
        "action": "install"
      },
      {
        "text": "Set up USB Device Tree Viewer. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "usbtree",
        "action": "install"
      },
      {
        "text": "Install KiCad; create a project and check symbols, footprints and design rules.",
        "url": "https://www.kicad.org/download/",
        "tool": "kicad",
        "action": "install"
      },
      {
        "text": "Install Arduino IDE; select the correct board and test compilation before uploading.",
        "url": "https://www.arduino.cc/en/software",
        "tool": "arduino-ide",
        "action": "install"
      },
      {
        "text": "Install board-specific USB drivers; verify serial ports, board voltage and a simple test circuit before connecting equipment."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-developer": {
    "name": "Developer PC · no AI",
    "platform": "Windows",
    "description": "Install the full language SDK required by the project (the catalog Python package is embeddable). Configure Git identity, SSH keys and a project environment; run a small build and tests.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up GitHub Desktop. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "github-desktop",
        "action": "install"
      },
      {
        "text": "Set up GitHub CLI (gh). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "gh",
        "action": "manual"
      },
      {
        "text": "Set up Node.js LTS (includes npm). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "nodejs",
        "action": "install"
      },
      {
        "text": "Set up uv (Python environment manager). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "uv",
        "action": "manual"
      },
      {
        "text": "Set up Podman Desktop. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "podman-desktop",
        "action": "install"
      },
      {
        "text": "Set up DBeaver Community. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "dbeaver",
        "action": "install"
      },
      {
        "text": "Set up Windows Terminal. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "windows-terminal",
        "action": "manual"
      },
      {
        "text": "Set up Visual Studio Code (VS Code / portable). Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vscode",
        "action": "install"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "install"
      },
      {
        "text": "Set up PowerShell 7. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "powershell",
        "action": "install"
      },
      {
        "text": "Set up SQLite tools. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sqlite",
        "action": "install"
      },
      {
        "text": "Set up curl. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "curl",
        "action": "install"
      },
      {
        "text": "Set up jq. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "jq",
        "action": "install"
      },
      {
        "text": "Install the full language SDK required by the project (the catalog Python package is embeddable). Configure Git identity, SSH keys and a project environment; run a small build and tests."
      },
      {
        "text": "Choose Podman or Docker Desktop for the project, not both by default. If Docker Desktop is required, review its license and virtualization requirements before installing.",
        "url": "https://docs.docker.com/desktop/"
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-developer-ai": {
    "name": "Developer PC · local AI",
    "platform": "Windows",
    "description": "Check RAM, GPU compatibility and model disk budget. Choose model licenses and privacy settings; keep model services bound locally and verify a small inference before editor integration.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up GitHub Desktop. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "github-desktop",
        "action": "install"
      },
      {
        "text": "Set up GitHub CLI (gh). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "gh",
        "action": "manual"
      },
      {
        "text": "Set up Node.js LTS (includes npm). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "nodejs",
        "action": "install"
      },
      {
        "text": "Set up uv (Python environment manager). Verify its version in a new terminal and follow the official project instructions.",
        "tool": "uv",
        "action": "manual"
      },
      {
        "text": "Set up Podman Desktop. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "podman-desktop",
        "action": "install"
      },
      {
        "text": "Set up DBeaver Community. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "dbeaver",
        "action": "install"
      },
      {
        "text": "Set up Windows Terminal. Verify its version in a new terminal and follow the official project instructions.",
        "tool": "windows-terminal",
        "action": "manual"
      },
      {
        "text": "Set up Visual Studio Code (VS Code / portable). Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vscode",
        "action": "install"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "install"
      },
      {
        "text": "Set up PowerShell 7. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "powershell",
        "action": "install"
      },
      {
        "text": "Set up SQLite tools. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sqlite",
        "action": "install"
      },
      {
        "text": "Set up curl. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "curl",
        "action": "install"
      },
      {
        "text": "Set up jq. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "jq",
        "action": "install"
      },
      {
        "text": "Install Ollama from its official instructions; choose models explicitly.",
        "url": "https://docs.ollama.com/quickstart",
        "tool": "ollama",
        "action": "install"
      },
      {
        "text": "Check RAM, GPU compatibility and model disk budget. Choose model licenses and privacy settings; keep model services bound locally and verify a small inference before editor integration."
      },
      {
        "text": "Choose Podman or Docker Desktop for the project, not both by default. If Docker Desktop is required, review its license and virtualization requirements before installing.",
        "url": "https://docs.docker.com/desktop/"
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-custom": {
    "name": "Custom PC · starter",
    "platform": "Windows",
    "description": "Clone this profile, choose applications and add the owner’s acceptance checks.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Firefox Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "firefox",
        "action": "install"
      },
      {
        "text": "Set up 7-Zip. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "7zip",
        "action": "install"
      },
      {
        "text": "Set up KeePassXC. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "keepassxc",
        "action": "install"
      },
      {
        "text": "Clone this profile, choose applications and add the owner’s acceptance checks."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-support": {
    "name": "Tech Support PC",
    "platform": "Windows",
    "description": "Set up remote access with owner consent, strong access controls and a tested removal path. Verify access on a test device; document handover.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up RustDesk. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "rustdesk",
        "action": "install"
      },
      {
        "text": "Set up Tailscale. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "tailscale",
        "action": "install"
      },
      {
        "text": "Set up Sysinternals Suite. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sysinternals",
        "action": "install"
      },
      {
        "text": "Set up Wireshark. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "wireshark",
        "action": "install"
      },
      {
        "text": "Set up PuTTY. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "putty",
        "action": "install"
      },
      {
        "text": "Set up WinSCP. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "winscp",
        "action": "install"
      },
      {
        "text": "Set up Bulk Crap Uninstaller. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "bcu",
        "action": "install"
      },
      {
        "text": "Set up remote access with owner consent, strong access controls and a tested removal path. Verify access on a test device; document handover."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-field": {
    "name": "Field Technician PC",
    "platform": "Windows",
    "description": "Prepare offline drivers for the models you service. Test diagnostics without modifying customer data and verify backup destination capacity.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Sysinternals Suite. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sysinternals",
        "action": "install"
      },
      {
        "text": "Set up CrystalDiskInfo. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "cdi",
        "action": "install"
      },
      {
        "text": "Set up HWiNFO. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "hwinfo",
        "action": "install"
      },
      {
        "text": "Set up USBDeview. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "usbdeview",
        "action": "install"
      },
      {
        "text": "Set up WifiInfoView. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "wifiinfoview",
        "action": "install"
      },
      {
        "text": "Set up FreeFileSync. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "freefilesync",
        "action": "install"
      },
      {
        "text": "Prepare offline drivers for the models you service. Test diagnostics without modifying customer data and verify backup destination capacity."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-linux": {
    "name": "Custom Linux PC",
    "platform": "Linux",
    "description": "Choose a supported distribution. Verify Wi-Fi, audio, graphics and suspend; use its trusted package manager for native apps. Review encryption, firewall and backups.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Firefox Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "firefox",
        "action": "manual"
      },
      {
        "text": "Set up LibreOffice Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "libreoffice",
        "action": "manual"
      },
      {
        "text": "Set up KeePassXC. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "keepassxc",
        "action": "manual"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "manual"
      },
      {
        "text": "Set up Visual Studio Code (VS Code / portable). Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vscode",
        "action": "manual"
      },
      {
        "text": "Choose a supported distribution. Verify Wi-Fi, audio, graphics and suspend; use its trusted package manager for native apps. Review encryption, firewall and backups."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-design": {
    "name": "Design PC",
    "platform": "Windows",
    "description": "Install required fonts from licensed sources, configure a color-managed display and test export to client formats.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up GIMP. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "gimp",
        "action": "install"
      },
      {
        "text": "Set up FreeFileSync. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "freefilesync",
        "action": "install"
      },
      {
        "text": "Install Inkscape for vector design.",
        "url": "https://inkscape.org/download/",
        "tool": "inkscape",
        "action": "install"
      },
      {
        "text": "Install Blender if 3D modeling is needed; test a sample render.",
        "url": "https://www.blender.org/download/",
        "tool": "blender",
        "action": "install"
      },
      {
        "text": "Install required fonts from licensed sources, configure a color-managed display and test export to client formats."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-video": {
    "name": "Video Editing PC",
    "platform": "Windows",
    "description": "Choose one primary editor; configure scratch/cache paths, proxy settings and project backups. Test playback and export using representative footage.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Kdenlive. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "kdenlive",
        "action": "install"
      },
      {
        "text": "Set up Shotcut. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "shotcut",
        "action": "install"
      },
      {
        "text": "Set up HandBrake. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "handbrake",
        "action": "install"
      },
      {
        "text": "Set up MediaInfo. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "mediainfo",
        "action": "install"
      },
      {
        "text": "Set up Audacity. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "audacity",
        "action": "install"
      },
      {
        "text": "Set up OBS Studio. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "obs",
        "action": "install"
      },
      {
        "text": "Choose one primary editor; configure scratch/cache paths, proxy settings and project backups. Test playback and export using representative footage."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-study": {
    "name": "Study PC",
    "platform": "Windows",
    "description": "Configure course folders, offline materials, accessibility and backup. Verify assignments export correctly before enabling optional sync.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up LibreOffice Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "libreoffice",
        "action": "install"
      },
      {
        "text": "Set up Joplin. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "joplin",
        "action": "install"
      },
      {
        "text": "Set up SumatraPDF. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sumatra",
        "action": "install"
      },
      {
        "text": "Set up Firefox Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "firefox",
        "action": "install"
      },
      {
        "text": "Set up KeePassXC. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "keepassxc",
        "action": "install"
      },
      {
        "text": "Configure course folders, offline materials, accessibility and backup. Verify assignments export correctly before enabling optional sync."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-streaming": {
    "name": "Streaming & Podcast PC",
    "platform": "Windows",
    "description": "Configure microphone, scene collection and recording paths. Test a local recording and private stream; check audio levels and dropped frames.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up OBS Studio. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "obs",
        "action": "install"
      },
      {
        "text": "Set up Audacity. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "audacity",
        "action": "install"
      },
      {
        "text": "Set up VLC Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vlc",
        "action": "install"
      },
      {
        "text": "Configure microphone, scene collection and recording paths. Test a local recording and private stream; check audio levels and dropped frames."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-home-lab": {
    "name": "Home Lab Admin PC",
    "platform": "Linux",
    "description": "Separate lab and production networks; configure least-privilege credentials, SSH host verification and a restore-tested config backup.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up OpenSSH client. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "ssh",
        "action": "manual"
      },
      {
        "text": "Set up Remmina. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "remmina",
        "action": "manual"
      },
      {
        "text": "Set up Tailscale. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "tailscale",
        "action": "manual"
      },
      {
        "text": "Set up Wireshark. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "wireshark",
        "action": "manual"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "manual"
      },
      {
        "text": "Separate lab and production networks; configure least-privilege credentials, SSH host verification and a restore-tested config backup."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-accessible": {
    "name": "Accessible Family PC",
    "platform": "Windows",
    "description": "Configure screen scaling, narration, captions, input devices and simple shortcuts with the user. Test real daily tasks and recovery contacts.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Firefox Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "firefox",
        "action": "install"
      },
      {
        "text": "Set up LibreOffice Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "libreoffice",
        "action": "install"
      },
      {
        "text": "Set up VLC Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vlc",
        "action": "install"
      },
      {
        "text": "Configure screen scaling, narration, captions, input devices and simple shortcuts with the user. Test real daily tasks and recovery contacts."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  },
  "build-research": {
    "name": "Research & Data PC",
    "platform": "Linux",
    "description": "Install project-specific language tools in isolated environments; document dataset licenses and reproduce a small analysis from a clean environment.",
    "steps": [
      {
        "text": "Confirm the owner’s requirements, hardware, operating system and available storage. Export the existing app list and verify a recoverable backup before changes."
      },
      {
        "text": "Apply supported OS updates and restart. Review OEM drivers, disk encryption recovery access and a recovery checkpoint. Prefer a standard daily-use account."
      },
      {
        "text": "Set up Joplin. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "joplin",
        "action": "manual"
      },
      {
        "text": "Set up Git Portable. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "git",
        "action": "manual"
      },
      {
        "text": "Set up SQLite tools. Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "sqlite",
        "action": "manual"
      },
      {
        "text": "Set up Visual Studio Code (VS Code / portable). Check whether it is already installed and use its documented native package or portable edition.",
        "tool": "vscode",
        "action": "manual"
      },
      {
        "text": "Install project-specific language tools in isolated environments; document dataset licenses and reproduce a small analysis from a clean environment."
      },
      {
        "text": "Restart if required. Verify apps and devices, test restoring a sample file, record installed versions and recovery steps, and export the completed workflow record."
      }
    ]
  }
};
