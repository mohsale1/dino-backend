#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Start the server
echo "🦕 Starting Dino E-Menu Backend API..."
echo "📍 Server will be available at: http://localhost:8080"
echo "📚 API Documentation: http://localhost:8080/docs"
echo "🏥 Health Check: http://localhost:8080/api/v1/health/health"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload