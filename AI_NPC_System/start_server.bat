@echo off
setlocal
cd /d "%~dp0"

REM Starts the TCP pipeline used by Unity or a local client.
echo Starting AI NPC TCP server...
python server.py
pause
