import { useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { fetchLibrary, fetchProducts, type SearchPlatform } from "./api/client";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./context/ToastContext";
import { ProductDetailPage } from "./pages/ProductDetailPage";
import { ProductListPage } from "./pages/ProductListPage";
import { LibraryPage } from "./pages/LibraryPage";
import { hasFetchedMedia, type Product } from "./types/product";

export default function App() {
  // 搜索结果仅前端会话态：刷新即空，需重新搜索
  const [products, setProducts] = useState<Product[]>([]);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [libraryIds, setLibraryIds] = useState<Set<string>>(() => new Set());
  const [platform, setPlatform] = useState<SearchPlatform>("taobao");
  const [booting, setBooting] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [library, productsResponse] = await Promise.all([
          fetchLibrary(),
          fetchProducts(),
        ]);
        if (cancelled) return;
        setLibraryIds(
          new Set((library.items || []).map((x) => x.id).filter(Boolean)),
        );
        setProducts(productsResponse.items || []);
      } catch {
        // 后端未启动时保持空列表
      } finally {
        if (!cancelled) setBooting(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedCount = useMemo(() => selected.size, [selected]);
  const fetchedCount = useMemo(
    () => products.filter(hasFetchedMedia).length,
    [products],
  );

  const onPlatformChange = (next: SearchPlatform) => {
    if (next === platform) return;
    setPlatform(next);
    setProducts([]);
    setSelected(new Set());
  };

  return (
    <ToastProvider>
      <Layout
        total={products.length}
        selected={selectedCount}
        fetchedCount={fetchedCount}
        libraryCount={libraryIds.size}
        platform={platform}
        onPlatformChange={onPlatformChange}
      >
        {booting ? (
          <p className="empty-hint">正在加载…</p>
        ) : (
          <Routes>
            <Route
              path="/"
              element={
                <ProductListPage
                  products={products}
                  setProducts={setProducts}
                  selected={selected}
                  setSelected={setSelected}
                  libraryIds={libraryIds}
                  setLibraryIds={setLibraryIds}
                  platform={platform}
                />
              }
            />
            <Route
              path="/detail/:id"
              element={
                <ProductDetailPage
                  products={products}
                  setProducts={setProducts}
                  libraryIds={libraryIds}
                  setLibraryIds={setLibraryIds}
                  platform={platform}
                />
              }
            />
            <Route
              path="/library"
              element={
                <LibraryPage
                  setProducts={setProducts}
                  onLibraryItemsChange={(items) =>
                    setLibraryIds(new Set(items.map((item) => item.id).filter(Boolean)))
                  }
                />
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        )}
      </Layout>
    </ToastProvider>
  );
}
