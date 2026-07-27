import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchProductDetailMedia, saveToLibrary, type SearchPlatform } from "../api/client";
import { ImageGallery } from "../components/ImageGallery";
import { useToast } from "../context/ToastContext";
import { hasFetchedMedia, type Product, type ProductImage } from "../types/product";

type Props = {
  products: Product[];
  setProducts: (items: Product[] | ((prev: Product[]) => Product[])) => void;
  libraryIds: Set<string>;
  setLibraryIds: (next: Set<string>) => void;
  platform: SearchPlatform;
};

function needsDetailFetch(p: Product) {
  const main = p.images?.main || [];
  const hasLocalMain = main.some((x) => x.src?.includes("/product_media/"));
  const hasDetail = (p.images?.detail || []).length > 0;
  // 有本地主图且已有详情图则不必自动再拉；视频可缺
  return !hasLocalMain || !hasDetail;
}

export function ProductDetailPage({
  products,
  setProducts,
  libraryIds,
  setLibraryIds,
  platform,
}: Props) {
  const { id } = useParams();
  const navigate = useNavigate();
  const { showToast } = useToast();
  const [fetching, setFetching] = useState(false);
  const [localProduct, setLocalProduct] = useState<Product | null>(null);
  const autoTried = useRef<string | null>(null);

  const base = products.find((p) => p.id === id);
  const product = localProduct?.id === id ? localProduct : base || null;

  const saved = product ? libraryIds.has(product.id) : false;
  const main = product?.images?.main || [];
  const sku = product?.images?.sku || [];
  const detail = product?.images?.detail || [];
  const video = product?.images?.video || [];
  const canFetch = useMemo(
    () => (product ? needsDetailFetch(product) : false),
    [product],
  );

  const onFetchDetail = async (silent = false) => {
    if (!product?.url) {
      showToast("缺少商品链接，无法拉取", false);
      return;
    }
    setFetching(true);
    if (!silent) showToast("正在拉取素材，请稍候…");
    try {
      const res = await fetchProductDetailMedia(
        product.id,
        product.url,
        product,
        platform,
      );
      const merged = {
        ...product,
        ...res.product,
        title: res.product.title?.trim() ? res.product.title : product.title,
        price: res.product.price?.trim() ? res.product.price : product.price,
        location: res.product.location?.trim()
          ? res.product.location
          : product.location,
        url: res.product.url || product.url,
        images: {
          main: res.product.images?.main || [],
          sku: res.product.images?.sku || [],
          detail: res.product.images?.detail || [],
          video: res.product.images?.video || [],
        },
      };
      setLocalProduct(merged);
      setProducts((prev) => prev.map((p) => (p.id === merged.id ? merged : p)));
      const total =
        (res.saved_main || 0) +
        (res.saved_sku || 0) +
        (res.saved_detail || 0) +
        (res.saved_video || 0);
      const msg =
        res.message ||
        `已拉取主图 ${res.saved_main} / SKU ${res.saved_sku} / 详情图 ${res.saved_detail} / 视频 ${res.saved_video}`;
      if (total === 0) {
        showToast(
          "未拉到可用素材。天猫商品可能暂不可用（服务商修复中），请换淘宝商品或稍后再试。",
          false,
        );
      } else {
        showToast(msg);
      }
    } catch (e) {
      showToast(e instanceof Error ? e.message : "详情拉取失败，请稍后再试", false);
    } finally {
      setFetching(false);
    }
  };

  useEffect(() => {
    if (!product || !canFetch || fetching) return;
    if (autoTried.current === product.id) return;
    autoTried.current = product.id;
    void onFetchDetail(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [product?.id]);

  if (!product) {
    return (
      <main className="view">
        <p className="empty-hint">未找到该商品。</p>
        <button type="button" className="btn btn-ghost" onClick={() => navigate("/")}>
          返回列表
        </button>
      </main>
    );
  }

  const downloadOne = (img: ProductImage) => {
    const a = document.createElement("a");
    a.href = img.src;
    a.download = img.name || "file";
    a.target = "_blank";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    showToast(`开始下载：${img.name || "文件"}`);
  };

  const downloadAll = () => {
    const all = [...main, ...sku, ...detail, ...video];
    if (!all.length) {
      showToast("该商品暂无素材，请先拉取详情素材", false);
      return;
    }
    all.forEach((img, i) => {
      window.setTimeout(() => downloadOne(img), i * 200);
    });
  };

  const onSave = async () => {
    try {
      const res = await saveToLibrary(product);
      setLibraryIds(new Set(res.libraryIds || []));
      showToast(`已保存到 library.json：${product.title.slice(0, 18)}…`);
    } catch (e) {
      showToast(e instanceof Error ? e.message : "保存失败", false);
    }
  };

  return (
    <main className="view view-detail">
      <section className="detail-nav">
        <Link to="/" className="btn btn-ghost">
          ← 返回列表
        </Link>
        <div className="detail-nav-actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={fetching}
            onClick={() => void onFetchDetail(false)}
          >
            {fetching ? "拉取中…" : "重新拉取详情素材"}
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={fetching}
            onClick={downloadAll}
          >
            下载本商品全部素材
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            disabled={saved || fetching}
            onClick={() => void onSave()}
          >
            {saved ? "已在本地库" : "保存到本地库"}
          </button>
        </div>
      </section>

      {fetching ? (
        <p className="empty-hint search-busy">正在通过万邦接口拉取素材…</p>
      ) : !hasFetchedMedia(product) ? (
        <p className="empty-hint search-busy">
          还没有本地详情素材。可点「重新拉取详情素材」。若刚搜完，进入本页会自动拉取一次。
        </p>
      ) : null}

      <section className="detail-hero">
        <div
          className="detail-cover"
          style={
            product.cover
              ? { backgroundImage: `url("${product.cover}")` }
              : undefined
          }
        />
        <div className="detail-summary">
          <p className="eyebrow">商品详情</p>
          <h1 className="detail-title">{product.title}</h1>
          <dl className="detail-facts">
            <div>
              <dt>价格</dt>
              <dd>{product.price || "—"}</dd>
            </div>
            <div>
              <dt>发货地</dt>
              <dd>{product.location || "—"}</dd>
            </div>
            <div className="fact-link">
              <dt>产品链接</dt>
              <dd>
                <a href={product.url} target="_blank" rel="noopener noreferrer">
                  {product.url || "无链接"}
                </a>
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <ImageGallery
        title="1比1主图"
        images={main}
        product={product}
        onDownload={(img) => downloadOne(img)}
      />
      <ImageGallery
        title="SKU图"
        images={sku}
        product={product}
        onDownload={(img) => downloadOne(img)}
      />
      <ImageGallery
        title="详情图"
        images={detail}
        product={product}
        onDownload={(img) => downloadOne(img)}
      />
      <ImageGallery
        title="视频"
        images={video}
        product={product}
        kind="video"
        onDownload={(img) => downloadOne(img)}
      />
    </main>
  );
}
