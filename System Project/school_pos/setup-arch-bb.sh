#!/bin/bash
set -e

echo "=== Bug Bounty Toolchain Installer for Arch Linux ==="

sudo pacman -Sy --noconfirm \
    base-devel \
    git \
    curl \
    wget \
    jq \
    nmap \
    python \
    python-pip \
    ruby \
    cargo \
    rustc \
    go \
    chromium \
    enum4linux \
    ldns \
    dnsenum \
    onesixtyone \
    snmp \
    community/rage \
    community/john \
    community/hashcat \
    community/sqlmap 2>/dev/null || true

echo "[+] Installing Go tools..."

export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

install_go_tool() {
    local tool=$1
    local repo=$2
    if ! command -v $tool &>/dev/null; then
        echo "    Installing $tool..."
        go install -v $repo@latest 2>/dev/null
    else
        echo "    $tool already installed"
    fi
}

install_go_tool subfinder github.com/projectdiscovery/subfinder/v2/cmd/subfinder
install_go_tool nuclei github.com/projectdiscovery/nuclei/v2/cmd/nuclei
install_go_tool nuclei-templates github.com/projectdiscovery/nuclei-templates
install_go_tool httpx github.com/projectdiscovery/httpx/cmd/httpx
install_go_tool naabu github.com/projectdiscovery/naabu/v2/cmd/naabu
install_go_tool fff github.com/fffonion/xeff 2>/dev/null || go install -v github.com/fffonion/xeff@latest 2>/dev/null || true
install_go_tool puredns github.com/d3mondev/puredns/v2
install_go_tool shuffledns github.com/projectdiscovery/shuffledns/cmd/shuffledns
install_go_tool assetfinder github.com/tomnomnom/assetfinder
install_go_tool amass github.com/owasp-amass/amass/v3/...
install_go_tool gf github.com/tomnomnom/gf
install_go_tool qsreplace github.com/tomnomnom/qsreplace
install_go_tool dalfox github.com/hahwul/dalfox/v2
install_go_tool gospider github.com/jaeles-project/gospider
install_go_tool sqlmapdev sqlmap 2>/dev/null || pip3 install sqlmap
install_go_tool findomain github.com/findomain/findomain
install_go_tool certspotter github.com/CISOfy/ldeep 2>/dev/null || go install -v github.com/CISOfy/ldeep/cmd/ldeep@latest 2>/dev/null || true
install_go_tool gitleaks github.com/gitleaks/gitleaks/v8
install_go_tool secretfinder github.com/m4ll0k/SecretFinder
install_go_tool interlace github.com/codingo/Interlace
install_go_tool massdns github.com/blechschmidt/massdns

echo "[+] Setting up Nuclei templates..."
mkdir -p ~/.nuclei-templates
if [ ! -d ~/.nuclei-templates/.git ]; then
    git clone --depth 1 https://github.com/projectdiscovery/nuclei-templates.git ~/.nuclei-templates 2>/dev/null || true
else
    cd ~/.nuclei-templates && git pull 2>/dev/null || true
fi

echo "[+] Installing Python tools..."
pip3 install --user \
    requests \
    beautifulsoup4 \
    lxml \
    playwright \
    httpx \
    colorama \
    tldextract \
    python-dateutil \
    mechanize \
    scapy 2>/dev/null || true

playwright install chromium 2>/dev/null || true

echo "[+] Installing gf patterns..."
mkdir -p ~/.gf
git clone https://github.com/1ndianl33t/Gf-Patterns ~/.gf 2>/dev/null || true
echo 'export PATH=$PATH:$GOPATH/bin:~/.local/bin' >> ~/.bashrc

echo "[+] Installing BugBountyHunter tools..."
mkdir -p ~/bb-tools/{recon,scans,payloads,reports,targets}

echo ""
echo "=== Installation Complete ==="
echo "Run: source ~/.bashrc"
echo "Verify: subfinder -version && nuclei -version && httpx -version"
