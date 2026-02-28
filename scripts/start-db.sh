#!/bin/bash
# AI Interview System - PostgreSQL Database Startup Script

echo "========================================"
echo "  Starting PostgreSQL Database"
echo "========================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "[ERROR] Docker is not running"
    exit 1
fi

# Start database container
echo "[INFO] Starting container..."
docker-compose up -d

echo ""
echo "[INFO] Waiting for database to be ready..."
sleep 3

# Check container status
if docker ps | grep -q "interview-postgres"; then
    echo ""
    echo "========================================"
    echo "  PostgreSQL Database Started Successfully!"
    echo "========================================"
    echo ""
    echo "Connection Info:"
    echo "  Host: localhost"
    echo "  Port: 5432"
    echo "  Database: interview_db"
    echo "  Username: postgres"
    echo "  Password: postgres"
    echo ""
    echo "Common Commands:"
    echo "  View logs: docker-compose logs postgres"
    echo "  Stop database: docker-compose down"
    echo "  Restart: docker-compose restart"
else
    echo ""
    echo "[ERROR] Database failed to start"
    echo "Check logs: docker-compose logs postgres"
    exit 1
fi
