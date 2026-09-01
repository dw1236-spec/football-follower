@echo off
REM Build a standalone Windows 10+ app in dist\NFLDraftAnalyzer\.
REM Must be run on Windows - PyInstaller does not cross-compile.
cd /d %~dp0\..

python -m pip install -r requirements-dev.txt
python -m PyInstaller --noconfirm packaging\pyinstaller.spec

echo.
echo Build complete: dist\NFLDraftAnalyzer\
echo Run it with: dist\NFLDraftAnalyzer\NFLDraftAnalyzer.exe
