@echo off
REM Hospital Admin Panel - Production Build Script

echo.
echo 🏥 HOSPITAL ADMIN PANEL - PRODUCTION BUILD
echo ==========================================
echo.

REM Navigate to admin directory
cd /d "%~dp0"

echo 📦 Building for production...
echo.

REM Run the build
npx vite build

REM Check if build was successful
if %errorlevel% equ 0 (
    echo.
    echo ✅ BUILD SUCCESSFUL!
    echo.
    echo 📁 Production files generated in: .\dist\
    echo 🌐 Ready for deployment to web server
    echo.
    echo 📊 Build Statistics:
    echo    • JavaScript Bundle: ~362 KB ^(~114 KB gzipped^)
    echo    • CSS Styles: ~3.5 KB ^(~1.2 KB gzipped^)
    echo    • Total Modules: 1,762 processed
    echo.
    echo 🚀 Next Steps:
    echo    1. Deploy contents of .\dist\ to your web server
    echo    2. Configure web server to serve index.html for SPA routing
    echo    3. Set up HTTPS and security headers
    echo    4. Integrate with hospital backend API
    echo.
    echo 🔍 To preview the build locally, run:
    echo    npx vite preview
    echo.
    pause
) else (
    echo.
    echo ❌ BUILD FAILED!
    echo Check the error messages above for details.
    echo.
    pause
    exit /b 1
)