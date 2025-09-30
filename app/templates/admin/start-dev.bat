@echo off
REM Hospital Admin Panel Setup and Development Script

echo 🏥 Hospital Admin Panel - Development Environment
echo ==================================================

REM Navigate to admin directory
cd /d "%~dp0"

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
    if %errorlevel% neq 0 (
        echo ❌ Failed to install dependencies!
        exit /b 1
    )
    echo ✅ Dependencies installed successfully!
)

REM Start development server
echo.
echo 🚀 Starting development server...
echo ⭐ Features included:
echo    • AI Assistant Chat Interface
echo    • Hospital Dashboard with metrics
echo    • Modern black ^& white design
echo    • Radix UI components
echo    • Responsive layout
echo.
echo 🌐 Server will be available at: http://localhost:5173
echo 📝 Press Ctrl+C to stop the server
echo.

npm run dev