#!/bin/bash

echo "🚀 Starting Warm Transfer System..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Please copy .env.example to .env and fill in your API keys"
    exit 1
fi

echo "📋 Starting backend..."
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!

echo "🌐 Starting frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo "✅ System started!"
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
