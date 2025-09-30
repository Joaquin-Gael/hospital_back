#!/bin/bash

# Hospital Admin Panel Build Script
echo "🏥 Building Hospital Admin Panel..."

# Navigate to admin directory
cd "$(dirname "$0")"

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Build the project
echo "🔨 Building project..."
npm run build

# Check if build was successful
if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo "📁 Build files are in ./dist/ directory"
    echo "🚀 You can now deploy the contents of ./dist/ to your web server"
else
    echo "❌ Build failed!"
    exit 1
fi