@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    py -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name "TritleKitchenRecipeCreator" --icon "assets\tritlekitchenlogo.ico" recipe_creator.py
pause
