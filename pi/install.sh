#!/usr/bin/env bash
# Rendu Pi installer.
# Run on a fresh Raspberry Pi OS (Bookworm or later) with internet access.
#
# Usage (run on the Pi directly or over SSH):
#   cd ~/rendu-pi
#   bash install.sh
#
# This script is idempotent. Safe to re-run if it fails partway.

set -euo pipefail

RENDU_USER="${SUDO_USER:-$USER}"
RENDU_HOME="/home/${RENDU_USER}/rendu-pi"
WHISPER_DIR="/home/${RENDU_USER}/whisper.cpp"
MODEL_PATH="/home/${RENDU_USER}/models/ggml-small.bin"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pi finds the Ally on the LAN as <ALLY_HOST>.local via mDNS.
# Override at runtime: ALLY_HOST=my-rig sudo bash install.sh
ALLY_HOST="${ALLY_HOST:-rendu-ally}"

echo "=== Rendu Pi installer ==="
echo "User:        ${RENDU_USER}"
echo "App:         ${RENDU_HOME}"
echo "Source:      ${SCRIPT_DIR}"
echo "Ally host:   ${ALLY_HOST}.local  (override with ALLY_HOST=...)"
echo

if [[ "${EUID}" -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    echo "This script needs sudo. Run with: sudo bash install.sh"
    exit 1
fi

run() { sudo -u "${RENDU_USER}" "$@"; }
sysrun() { sudo "$@"; }

echo "[1/8] Installing system packages..."
sysrun apt-get update
sysrun apt-get install -y \
    python3 python3-pip python3-venv \
    python3-pyqt5 python3-pyqt5.qtmultimedia \
    portaudio19-dev libasound2-dev \
    avahi-daemon avahi-utils \
    git build-essential cmake \
    xset unclutter \
    curl ca-certificates

echo "[2/8] Copying app to ${RENDU_HOME}..."
sysrun mkdir -p "${RENDU_HOME}"
sudo cp -r "${SCRIPT_DIR}/." "${RENDU_HOME}/"
sysrun chown -R "${RENDU_USER}:${RENDU_USER}" "${RENDU_HOME}"

echo "[3/8] Installing Python dependencies..."
run python3 -m pip install --user --upgrade pip
run python3 -m pip install --user -r "${RENDU_HOME}/requirements.txt"

echo "[4/8] Building whisper.cpp..."
if [[ ! -d "${WHISPER_DIR}" ]]; then
    run git clone https://github.com/ggerganov/whisper.cpp.git "${WHISPER_DIR}"
fi
run bash -c "cd ${WHISPER_DIR} && make -j\$(nproc)"
sysrun ln -sf "${WHISPER_DIR}/main" /usr/local/bin/whisper-cpp

echo "[5/8] Downloading Whisper small model (~466 MB)..."
run mkdir -p "$(dirname "${MODEL_PATH}")"
if [[ ! -s "${MODEL_PATH}" ]]; then
    run bash "${WHISPER_DIR}/models/download-ggml-model.sh" small
    run cp "${WHISPER_DIR}/models/ggml-small.bin" "${MODEL_PATH}"
fi

echo "[6/8] Configuring mDNS hostname (rendu-pi.local)..."
sysrun hostnamectl set-hostname rendu-pi || true
if ! grep -q "127.0.1.1.*rendu-pi" /etc/hosts; then
    sysrun sed -i 's/^127\.0\.1\.1.*/127.0.1.1\trendu-pi/' /etc/hosts
fi
sysrun systemctl enable --now avahi-daemon

echo "[7/8] Installing systemd service..."
sysrun cp "${RENDU_HOME}/rendu-pi.service" /etc/systemd/system/rendu-pi.service
sysrun sed -i "s|__USER__|${RENDU_USER}|g" /etc/systemd/system/rendu-pi.service
sysrun sed -i "s|__HOME__|${RENDU_HOME}|g" /etc/systemd/system/rendu-pi.service
sysrun sed -i "s|__ALLY_HOST__|${ALLY_HOST}|g" /etc/systemd/system/rendu-pi.service
sysrun systemctl daemon-reload
sysrun systemctl enable rendu-pi.service

echo "[8/8] Hiding mouse cursor on touchscreen (unclutter)..."
sysrun bash -c "cat > /etc/xdg/autostart/unclutter.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=unclutter
Exec=unclutter -idle 0
DESKTOP

echo
echo "=== Install complete ==="
echo "Reboot the Pi to start Rendu automatically:"
echo "    sudo reboot"
echo
echo "Useful commands:"
echo "  sudo systemctl status rendu-pi      # check service"
echo "  sudo journalctl -u rendu-pi -f      # follow logs"
echo "  sudo systemctl restart rendu-pi     # restart app"
