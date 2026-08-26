@echo off
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0sshctl.ps1" %*
exit /b %ERRORLEVEL%
