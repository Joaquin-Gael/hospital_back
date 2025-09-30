#!/bin/bash

# Hospital Admin Panel Setup and Development Script
echo "🏥 Hospital Admin Panel - Development Environment"
echo "=================================================="

# Navigate to admin directory
cd "$(dirname "$0")"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install dependencies!"
        exit 1
    fi
    echo "✅ Dependencies installed successfully!"
fi

# Start development server
echo ""
echo "🚀 Starting development server..."
echo "⭐ Features included:"
echo "   • AI Assistant Chat Interface"
echo "   • Hospital Dashboard with metrics"
echo "   • Modern black & white design"
echo "   • Radix UI components"
echo "   • Responsive layout"
echo ""
echo "🌐 Server will be available at: http://localhost:5173"
echo "📝 Press Ctrl+C to stop the server"
echo ""

npm run dev