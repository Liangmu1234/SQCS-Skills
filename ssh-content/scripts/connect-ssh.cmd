@echo off
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "%~dp0connect-ssh.ps1" %*
exit /b %ERRORLEVEL%
