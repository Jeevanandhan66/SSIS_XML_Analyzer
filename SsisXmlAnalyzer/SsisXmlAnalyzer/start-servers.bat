@echo off
echo Starting SSIS XML Analyzer...
echo.

REM Start Python FastAPI server in the background
echo Starting Python FastAPI server on port 8000...
start "Python FastAPI Server" cmd /k python api_server.py

REM Wait a bit for Python server to start
timeout /t 3 /nobreak >nul

REM Start Node.js server
echo Starting Node.js development server...
echo.
echo Both servers are starting. Press Ctrl+C to stop both servers.
echo.

REM Set NODE_ENV and run npm dev
set NODE_ENV=development
npm run dev

