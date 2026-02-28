#!/bin/bash
# AI Interview System - PostgreSQL Database Stop Script

echo "========================================"
echo "  Stopping PostgreSQL Database"
echo "========================================"
echo ""

# Stop and remove container
docker-compose down

echo ""
echo "[SUCCESS] Database stopped"
echo ""
echo "To restart, run: ./scripts/start-db.sh"
