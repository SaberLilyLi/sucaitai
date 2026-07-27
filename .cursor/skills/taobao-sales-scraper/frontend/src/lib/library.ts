import type { LibraryItem, Product } from "../types/product";

const IDS_KEY = "scrape_library_ids";
const LIB_KEY = "scrape_library";

export function loadLibraryIds(): Set<string> {
  try {
    const raw = JSON.parse(localStorage.getItem(IDS_KEY) || "[]") as string[];
    return new Set(raw);
  } catch {
    return new Set();
  }
}

export function loadLibrary(): LibraryItem[] {
  try {
    return JSON.parse(localStorage.getItem(LIB_KEY) || "[]") as LibraryItem[];
  } catch {
    return [];
  }
}

export function saveProductToLibrary(product: Product): LibraryItem[] {
  const ids = loadLibraryIds();
  const lib = loadLibrary();
  if (!ids.has(product.id)) {
    ids.add(product.id);
    lib.push({
      id: product.id,
      title: product.title,
      url: product.url,
      price: product.price,
      location: product.location,
      cover: product.cover,
      savedAt: new Date().toISOString(),
    });
    localStorage.setItem(IDS_KEY, JSON.stringify([...ids]));
    localStorage.setItem(LIB_KEY, JSON.stringify(lib, null, 2));
  }
  return lib;
}
