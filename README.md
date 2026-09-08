# The Tritle Kitchen v2

A modern, framework-free ES-module rebuild of The Tritle Kitchen for GitHub Pages.

## Features

- Recipe browsing by category and sub-category
- Recipe name search
- Ingredient search with AND matching for comma-separated terms
- Favorites with localStorage persistence
- SPA-style recipe pages
- Cook Mode / screen wake lock
- Weekly meal planner with drag-and-drop
- Week navigation and local persistence
- Consolidated grocery list
- Grocery item check-off and collapsible categories
- Calendar `.ics` export
- Recipe submission modal
- PWA manifest and service worker

## Data migration

Copy the existing repository's five category JSON files into `data/`:
`breakfast.json`, `desserts.json`, `dinner.json`, `drinks.json`, and `miscellaneous.json`.

Copy your current `tritlekitchenlogo.png` to `assets/tritlekitchenlogo.png`, favicon files to `assets/`, and recipe photos into `assets/recipes/` using the existing recipe filename slug (for example `french-toast-bake.jpg`).

The original `recipes/*.html` pages are not required by the new application, but the current source URLs are preserved in the imported JSON for reference.

## GitHub Pages

Create a new repository, copy this folder into it, commit to `main`, and enable GitHub Pages from the repository settings.
