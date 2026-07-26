@echo off
setlocal

set "APP_DIR=C:\Users\M\Pictures\IA_ImagesManager"

if exist "%APP_DIR%\.venv\Scripts\pythonw.exe" (
    start "IA Images Manager" /D "%APP_DIR%" "%APP_DIR%\.venv\Scripts\pythonw.exe" -m aplicacion.principal
    exit /b 0
)

where pyw.exe >nul 2>&1
if not errorlevel 1 (
    start "IA Images Manager" /D "%APP_DIR%" pyw.exe -m aplicacion.principal
    exit /b 0
)

where pythonw.exe >nul 2>&1
if not errorlevel 1 (
    start "IA Images Manager" /D "%APP_DIR%" pythonw.exe -m aplicacion.principal
    exit /b 0
)

echo No se encontro Python para ejecutar IA Images Manager.
echo Revisa que exista: "%APP_DIR%\.venv\Scripts\pythonw.exe"
pause
exit /b 1
