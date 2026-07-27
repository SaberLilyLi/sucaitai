import type { Product } from "../types/product";

export type ProductsResponse = {
  count: number;
  items: Product[];
  libraryIds?: string[];
  keyword?: string;
  message?: string;
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json() as Promise<T>;
}

export function fetchProducts() {
  return request<ProductsResponse>("/api/products");
}

export type SearchFilters = {
  location?: string;
  locations?: string[];
  ship_time?: string;
  price_min?: number | null;
  price_max?: number | null;
};

export type IntentTag = {
  type: string;
  label: string;
};

export type ParseIntentResponse = {
  keyword: string;
  location?: string | null;
  locations?: string[];
  ship_time?: string | null;
  price_min?: number | null;
  price_max?: number | null;
  tags: IntentTag[];
  message: string;
};

export function parseSearchIntent(text: string) {
  return request<ParseIntentResponse>("/api/parse-intent", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export type SearchPlatform = "taobao" | "1688";

export function searchTaobao(
  keyword: string,
  limit = 100,
  filters: SearchFilters = {},
  platform: SearchPlatform = "taobao",
) {
  const locations = (filters.locations || [])
    .map((x) => x.trim())
    .filter(Boolean);
  const single = filters.location?.trim();
  const body: Record<string, unknown> = {
    keyword,
    limit,
    platform,
    locations: locations.length
      ? locations
      : single
        ? single.split(/[,，、/\s]+/).filter(Boolean)
        : [],
    ship_time: filters.ship_time?.trim() || null,
    price_min:
      filters.price_min != null && !Number.isNaN(filters.price_min)
        ? filters.price_min
        : null,
    price_max:
      filters.price_max != null && !Number.isNaN(filters.price_max)
        ? filters.price_max
        : null,
  };
  return request<ProductsResponse>("/api/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function saveToLibrary(product: Product) {
  return request<{ count: number; items: Product[]; product: Product; libraryIds: string[] }>(
    "/api/library",
    {
      method: "POST",
      body: JSON.stringify({ product }),
    },
  );
}

export async function exportProductMedia(ids: string[]) {
  const res = await fetch("/api/products/export-media", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const filename = decodeURIComponent(
    disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1] ||
      disposition.match(/filename=\"?([^\";]+)\"?/i)?.[1] ||
      "素材台-批量素材.zip",
  );
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
  return { filename, products: Number(res.headers.get("X-Exported-Products") || 0) };
}

export function fetchLibrary() {
  return request<{ count: number; items: Product[] }>("/api/library");
}

export function exportToTencentDocs(ids: string[]) {
  return request<{
    ok: boolean;
    message: string;
    file: { id: string; title: string; url: string; rows: number };
  }>("/api/tencent-docs/export", {
    method: "POST",
    body: JSON.stringify({ ids }),
  });
}

export function fetchProductDetailMedia(
  id: string,
  url: string,
  product?: Product,
  platform?: SearchPlatform,
) {
  const plat =
    platform ||
    (product?.platform === "1688" ? "1688" : undefined) ||
    (url.includes("1688.com") ? "1688" : "taobao");
  return request<{
    product: Product;
    saved_main: number;
    saved_sku: number;
    saved_detail: number;
    saved_video: number;
    message: string;
  }>("/api/products/fetch-detail", {
    method: "POST",
    body: JSON.stringify({
      id,
      url,
      product: product || undefined,
      platform: plat,
    }),
  });
}
