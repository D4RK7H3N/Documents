#!/bin/bash
# Firewall setup script for School POS Backend
# Run with: sudo bash firewall_setup.sh

echo "Setting up firewall rules for School POS..."

# Allow port 8000 (Gunicorn)
sudo ufw allow 8000/tcp

# Allow SSH if not already allowed
sudo ufw allow 22/tcp

# Enable ufw if not enabled
sudo ufw --force enable

# Reload to apply rules
sudo ufw reload

echo "Firewall rules applied:"
sudo ufw status verbose
