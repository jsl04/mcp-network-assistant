#!/usr/bin/env bash
# -------------------------------------------------------------------
# install_mcp.sh  •  Provision Cisco Network‑Assistant MCP server
# -------------------------------------------------------------------
# * Ubuntu 22.04/24.04
# * FastMCP 2.10.6  (binds 127.0.0.1:8000 via streamable-http)
# * nginx reverse‑proxy on 0.0.0.0:4242
# -------------------------------------------------------------------
set -euo pipefail

##### 1. CONFIGURE THESE FOUR VARS ##################################
DNAC_IP="server ip"
DNAC_USER="username"
DNAC_PASS="password"
MCP_DIR="/opt/mcp"
#####################################################################

PYENV="$MCP_DIR/.venv"
SCRIPT="$MCP_DIR/simple_mcp.py"
SERVICE="/etc/systemd/system/mcp.service"

echo "==> Installing prerequisites"
sudo apt update -qq
sudo apt install -y python3.12-venv nginx curl jq

echo "==> Creating project directory $MCP_DIR"
sudo mkdir -p "$MCP_DIR"
sudo chown "$USER:$USER" "$MCP_DIR"

echo "==> Creating virtual‑env"
python3 -m venv "$PYENV"
"$PYENV/bin/pip" install --upgrade pip
"$PYENV/bin/pip" install 'fastmcp==2.10.6' 'dnacentersdk[async]' requests
python -m pip install dnacentersdk tabulate
python -m pip install "dnacentersdk" rich fastmcp uvicorn

echo "==> Writing simple_mcp.py"
cat >"$SCRIPT" <<'PY'
# (placeholder – paste or git clone your simple_mcp.py here)
PY
chmod +x "$SCRIPT"

echo "==> Creating systemd unit"
sudo tee "$SERVICE" >/dev/null <<EOF
[Unit]
Description=Cisco Network Assistant MCP
After=network.target

[Service]
WorkingDirectory=$MCP_DIR
ExecStart=$PYENV/bin/python $SCRIPT --dnac $DNAC_IP --username $DNAC_USER --password $DNAC_PASS
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mcp.service

echo "==> Configuring nginx proxy 4242 → 8000"
sudo tee /etc/nginx/sites-available/mcp.conf >/dev/null <<'NG'
server {
    listen 4242;
    location / {
        proxy_pass http://127.0.0.1:8000/;
        proxy_http_version 1.1;
    }
}
NG
sudo ln -sf /etc/nginx/sites-available/mcp.conf /etc/nginx/sites-enabled/mcp.conf
sudo nginx -t && sudo systemctl reload nginx

echo "==> Opening UFW port 4242 (if firewall is active)"
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 4242/tcp
fi

IP=$(hostname -I | awk '{print $1}')
echo
echo "✅  MCP server ready:"
echo "   Base URL → http://$IP:4242/mcp"
echo
echo "   Try:  curl http://$IP:4242/mcp/inventory | jq ."
echo
