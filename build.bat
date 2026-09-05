@echo off
setlocal
cd /d "%~dp0"

set "PYTHON="
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
  set "PYTHON=%LocalAppData%\Programs\Python\Python312\python.exe"
) else (
  where py >nul 2>nul
  if not errorlevel 1 set "PYTHON=py"
)

if not defined PYTHON (
  echo Nie znaleziono Pythona.
  echo Zainstaluj Python 3.12 z https://www.python.org/downloads/windows/
  echo Podczas instalacji zaznacz "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" "%PYTHON%" -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name "NF-Dyzury" app.py

if errorlevel 1 (
  echo Budowanie nie powiodlo sie.
  pause
  exit /b 1
)

echo.
echo Gotowe: %CD%\dist\NF-Dyzury.exe
pause
