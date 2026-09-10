#!/bin/bash
set -euo pipefail
apt-get update
apt-get install -y live-build ca-certificates
mkdir -p /build
cd /build
lb config --distribution bookworm --architectures amd64 --binary-images iso-hybrid --debian-installer false --archive-areas main --bootappend-live "boot=live components username=technician"
mkdir -p config/package-lists config/includes.chroot/usr/share/master-it-toolkit config/includes.chroot/etc/skel/Desktop
printf '%s\n' live-task-xfce firefox-esr python3 python3-cryptography rsync gparted smartmontools testdisk > config/package-lists/toolkit.list.chroot
cp -a /workspace/MASTER-IT-TOOLKIT/. config/includes.chroot/usr/share/master-it-toolkit/
cat > config/includes.chroot/etc/skel/Desktop/master-it-toolkit.desktop <<'EOF'
[Desktop Entry]
Type=Application
Name=Master IT Toolkit
Exec=sh -c 'test -d "$HOME/Master-IT-Toolkit" || cp -a /usr/share/master-it-toolkit "$HOME/Master-IT-Toolkit"; cd "$HOME/Master-IT-Toolkit"; python3 launcher.py --no-startup-scan'
Terminal=true
Icon=utilities-terminal
EOF
chmod +x config/includes.chroot/etc/skel/Desktop/master-it-toolkit.desktop
lb build
cp live-image-amd64.hybrid.iso /output/master-it-toolkit-experimental-amd64.iso
cd /output
sha256sum master-it-toolkit-experimental-amd64.iso > SHA256SUMS
