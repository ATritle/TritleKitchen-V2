const sources = [
  ["Breakfast", "data/breakfast.json"],
  ["Desserts", "data/desserts.json"],
  ["Dinner", "data/dinner.json"],
  ["Drinks", "data/drinks.json"],
  ["Miscellaneous", "data/miscellaneous.json"],
];

const stripFavorite = (name) => name.replace(/^⭐\s*/, "");
const isFavorite = (name) => name.startsWith("⭐");

export async function loadRecipes() {
  const entries = await Promise.all(sources.map(async ([category, url]) => {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) throw new Error(`Unable to load ${url}`);
    const json = await response.json();
    return [category, json];
  }));

  const categories = {};
  const recipes = [];
  for (const [category, groups] of entries) {
    categories[category] = groups;
    for (const [subcategory, items] of Object.entries(groups)) {
      for (const recipe of items) {
        recipes.push({
          ...recipe,
          category,
          subcategory,
          favorite: isFavorite(recipe.name),
          displayName: stripFavorite(recipe.name),
          id: recipe.url,
        });
      }
    }
  }

  recipes.sort((a, b) => a.displayName.localeCompare(b.displayName));
  return { categories, recipes };
}
