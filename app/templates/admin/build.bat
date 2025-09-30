@echo off
REM Hospital Admin Panel Build Script for Windows

echo 🏥 Building Hospital Admin Panel...

REM Navigate to admin directory
cd /d "%~dp0"

REM Install dependencies if node_modules doesn't exist
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
)

REM Build the project
echo 🔨 Building project...
npm run build

REM Check if build was successful
if %errorlevel% equ 0 (
    echo ✅ Build completed successfully!
    echo 📁 Build files are in .\dist\ directory
    echo 🚀 You can now deploy the contents of .\dist\ to your web server
) else (
    echo ❌ Build failed!
    exit /b 1
)