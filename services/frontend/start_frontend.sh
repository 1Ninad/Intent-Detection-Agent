#!/bin/bash
# Start script for Next.js frontend

echo "Starting Next.js Frontend..."
echo "================================"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if .env.local exists
if [ ! -f ".env.local" ]; then
    echo "Warning: .env.local not found. Creating from .env.example..."
    cp .env.example .env.local
fi

echo ""
echo "Frontend will be available at: http://localhost:3000"
echo "Make sure the orchestrator backend is running on http://localhost:8004"
echo ""

# Start the development server
npm run dev
