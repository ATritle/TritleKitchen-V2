# Tritle Kitchen Recipe Creator

A PyQt6 desktop utility for adding recipes to the Tritle Kitchen V2 (`tritlekitchen-js`) project.

## What it does

- Recipe title
- Optional subtitle/source
- Category and sub-category
- Recipe photo with preview
- Ingredients table: amount, unit, ingredient, note
- Ordered directions
- Live JSON preview
- Validation and duplicate checking
- Adds the recipe to the correct `data/*.json` file
- Adds the image to `assets/recipes/`
- Keeps sub-categories and recipes alphabetized
- Uses the existing V2 recipe fields: `name`, `url`, `ingredients`, `directions`, and optional `subtitle`
- Converts unsupported common image formats to JPG automatically

## Local testing

The easiest way to test on Windows is to double-click `run.bat`.

It creates a local `.venv`, installs the requirements, and launches the app. Nothing is installed globally.

Or from PowerShell:

```powershell
cd tools\recipe_creator
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe recipe_creator.py
```

The app automatically looks upward for a Tritle Kitchen V2 project containing `index.html`, `data/`, and `assets/recipes/`. You can also choose the project manually with the **Project** button.

## GitHub layout

This tool is designed to live inside the V2 repository at:

```text
tools/
  recipe_creator/
    recipe_creator.py
    requirements.txt
    run.bat
    build.bat
    README.md
    assets/
      tritlekitchenlogo.png
      tritlekitchenlogo.ico
```

The tool is not part of the GitHub Pages site; it is a local development utility stored in the same repository so another PC can clone the repository and use it.

## Building the EXE later

`build.bat` is included for the eventual Windows build. It uses PyInstaller to create a windowed Windows application in `dist/`. We are intentionally testing the normal Python version first so the recipe-writing workflow can be verified before packaging.
