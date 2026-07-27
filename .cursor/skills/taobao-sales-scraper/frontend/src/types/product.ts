export type ProductImage = {
  name: string;
  src: string;
};

export type Product = {
  id: string;
  title: string;
  url: string;
  price: string;
  location: string;
  /** 发货时间，如「次日达」「48小时内发货」 */
  ship_time?: string;
  total_sales?: number;
  cover: string;
  /** taobao | 1688 */
  platform?: "taobao" | "1688" | string;
  images: {
    main: ProductImage[];
    sku: ProductImage[];
    detail?: ProductImage[];
    video?: ProductImage[];
  };
};

export type LibraryItem = {
  id: string;
  title: string;
  url: string;
  price: string;
  location: string;
  ship_time?: string;
  cover: string;
  savedAt: string;
};

/** 是否已拉取过详情素材（本地 product_media，而非搜索封面） */
export function hasFetchedMedia(p: Product): boolean {
  const main = p.images?.main || [];
  const sku = p.images?.sku || [];
  const detail = p.images?.detail || [];
  const video = p.images?.video || [];
  const localMain = main.filter((x) => x.src?.includes("/product_media/"));
  return (
    localMain.length >= 1 ||
    sku.length >= 1 ||
    detail.length >= 1 ||
    video.length >= 1
  );
}
