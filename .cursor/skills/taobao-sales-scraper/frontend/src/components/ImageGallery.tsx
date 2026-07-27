import type { Product, ProductImage } from "../types/product";

type Props = {
  title: string;
  images: ProductImage[];
  product: Product;
  kind?: "image" | "video";
  onDownload: (img: ProductImage, product: Product) => void;
};

export function ImageGallery({
  title,
  images,
  product,
  kind = "image",
  onDownload,
}: Props) {
  return (
    <section className="gallery-block">
      <div className="gallery-head">
        <h2>{title}</h2>
        <span className="count-pill">
          {images.length} {kind === "video" ? "个" : "张"}
        </span>
      </div>
      {images.length === 0 ? (
        <p className="gallery-empty">
          暂无该类{kind === "video" ? "视频" : "图片"}，请点上方「重新拉取详情素材」
        </p>
      ) : (
        <div className="gallery-grid">
          {images.map((img, i) => (
            <article
              key={`${img.src}-${i}`}
              className={`shot-card${kind === "video" ? " shot-card-video" : ""}`}
              style={{ animationDelay: `${i * 40}ms` }}
            >
              {kind === "video" ? (
                <video src={img.src} controls preload="metadata" />
              ) : (
                <img src={img.src} alt={img.name} loading="lazy" />
              )}
              <div className="shot-meta">
                <span className="shot-name">{img.name}</span>
                <button
                  type="button"
                  className="btn btn-sm"
                  onClick={() => onDownload(img, product)}
                >
                  下载
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
