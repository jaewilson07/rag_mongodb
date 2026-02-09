#!/bin/bash
# Apply Docker Compose standardization changes
# This script backs up existing files and applies the updates

set -e

echo "Docker Compose Standardization - Applying Changes"
echo "=================================================="
echo ""

# Backup directory
BACKUP_DIR="temp/backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Creating backups in $BACKUP_DIR..."
cp docker-compose.yml "$BACKUP_DIR/"
cp docker-compose.vllm.yml "$BACKUP_DIR/"
cp docker-compose.vllm.48gb.yml "$BACKUP_DIR/"
echo "✓ Backups created"
echo ""

echo "Applying updates..."
cp temp/docker-compose.yml.updated docker-compose.yml
cp temp/docker-compose.vllm.yml.updated docker-compose.vllm.yml
cp temp/docker-compose.vllm.48gb.yml.updated docker-compose.vllm.48gb.yml
echo "✓ Compose files updated"
echo ""

echo "Documentation updates (manual review required):"
echo "1. AGENTS.md Docker Configuration section:"
echo "   See: temp/AGENTS.md.docker-section-update.md"
echo ""
echo "2. docs/design_patterns.md Compose section:"
echo "   See: temp/design_patterns.md.compose-section-update.md"
echo ""

echo "Next steps:"
echo "1. Review the documentation updates and apply manually"
echo "2. Stop existing containers: docker compose down"
echo "3. Test the new configuration: docker compose up -d"
echo "4. Verify services: docker ps"
echo "5. Check logs: docker logs <container-name>"
echo ""

echo "Rollback (if needed):"
echo "  cp $BACKUP_DIR/* ."
echo ""

read -p "Apply changes now? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Changes applied successfully!"
    echo "Review temp/IMPLEMENTATION_SUMMARY.md for details"
else
    echo "Changes prepared but not applied."
    echo "Files are in temp/*.updated - apply manually when ready"
fi
