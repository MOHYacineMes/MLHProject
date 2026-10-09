#!/usr/bin/env bash
# One-shot setup for an Ubuntu 24.04 Droplet (8 GB RAM / 4 vCPU recommended).
# Run as root:  bash setup_droplet.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/MOHYacineMes/MLHProject.git}"
APP_DIR=/opt/statement-analyzer
MODEL_NAME="${MODEL_NAME:-qwen2.5:3b}"

apt-get update
apt-get install -y python3-venv git curl

# Firewall: SSH and the app only. Ollama (11434) stays private on localhost.
ufw allow OpenSSH
ufw allow 7860/tcp
ufw --force enable

# Ollama installs itself as a systemd service listening on 127.0.0.1:11434.
curl -fsSL https://ollama.com/install.sh | sh
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/keepalive.conf <<'CONF'
[Service]
Environment="OLLAMA_KEEP_ALIVE=24h"
CONF
systemctl daemon-reload
systemctl restart ollama
ollama pull "$MODEL_NAME"

# App, running as an unprivileged user.
id -u analyzer >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin analyzer
if [ -d "$APP_DIR/.git" ]; then git -C "$APP_DIR" pull; else git clone "$REPO_URL" "$APP_DIR"; fi
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
chown -R analyzer:analyzer "$APP_DIR"

cp "$APP_DIR/deploy/analyzer.service" /etc/systemd/system/analyzer.service
systemctl daemon-reload
systemctl enable --now analyzer

# Warm up the model so the first visitor doesn't wait for it to load.
curl -s http://localhost:11434/api/generate -d "{\"model\": \"$MODEL_NAME\", \"prompt\": \"hi\", \"stream\": false}" >/dev/null

echo "Done. Open http://$(curl -s ifconfig.me):7860"
