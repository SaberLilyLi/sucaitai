import { Button, Dropdown, Menu, Table } from "@arco-design/web-react";
import { IconLaunch, IconMore } from "@arco-design/web-react/icon";
import type { ColumnProps } from "@arco-design/web-react/es/Table";
import { hasFetchedMedia, type Product } from "../types/product";

type Props = {
  products: Product[];
  selectedKeys: string[];
  libraryIds: Set<string>;
  fetchingIds: Set<string>;
  onSelectionChange: (keys: string[]) => void;
  onFetchMedia: (id: string) => void;
  onSave: (id: string) => void;
  onView: (id: string) => void;
};

const MEDIA_LABELS = [
  ["main", "主图"],
  ["sku", "SKU"],
  ["detail", "详情"],
  ["video", "视频"],
] as const;

function formatSales(v: unknown): string | null {
  if (v == null || v === "") return null;
  if (typeof v === "string" && Number.isNaN(Number(v))) return v;
  const n = Number(v);
  if (Number.isNaN(n)) return null;
  if (n >= 10000) return `${(n / 10000).toFixed(1).replace(/\.0$/, "")}万`;
  return String(n);
}

/** 价格统一展示为「¥ 数字」，无数据时返回 null 由调用方降级 */
function formatPrice(v: string): { yen: boolean; text: string } | null {
  const t = (v || "").trim();
  if (!t) return null;
  const bare = t.replace(/^[¥￥]\s*/, "");
  return { yen: true, text: bare };
}

export function ProductTable({
  products,
  selectedKeys,
  libraryIds,
  fetchingIds,
  onSelectionChange,
  onFetchMedia,
  onSave,
  onView,
}: Props) {
  const columns: ColumnProps<Product>[] = [
    {
      title: "主图",
      dataIndex: "cover",
      width: 88,
      render: (_, p) =>
        p.cover ? (
          <span className="thumb-64">
            <img src={p.cover} alt="" loading="lazy" />
          </span>
        ) : (
          <span className="thumb-64">无图</span>
        ),
    },
    {
      title: "标题",
      dataIndex: "title",
      render: (title: string, p) => {
        const is1688 = p.platform === "1688";
        const archived = libraryIds.has(p.id) || Boolean(p.project);
        return (
          <div className="cell-title">
            <span className="t2">{title || "（无标题）"}</span>
            <div className="cell-meta">
              <span className={`badge badge-platform${is1688 ? " is-1688" : ""}`}>
                {is1688 ? "1688" : "淘宝"}
              </span>
              {archived ? <span className="badge badge-archived">已归档</span> : null}
              {p.url ? (
                <a
                  className="open-link"
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  title={p.url}
                >
                  <IconLaunch />
                  打开商品
                </a>
              ) : null}
            </div>
          </div>
        );
      },
    },
    {
      title: "价格",
      dataIndex: "price",
      width: 104,
      render: (v: string) => {
        const price = formatPrice(v);
        if (!price) return <span className="cell-dash">—</span>;
        return (
          <span className="cell-price">
            <span className="yen">¥</span>
            {price.text}
          </span>
        );
      },
    },
    {
      title: "销量",
      dataIndex: "total_sales",
      width: 92,
      render: (v: unknown) => {
        const text = formatSales(v);
        return text ? (
          <span className="cell-sales">{text}</span>
        ) : (
          <span className="cell-sales is-empty">暂无</span>
        );
      },
    },
    {
      title: "素材完整度",
      dataIndex: "images",
      width: 188,
      render: (_, p) => {
        const counts: Record<string, number> = {
          main: p.images?.main?.length || 0,
          sku: p.images?.sku?.length || 0,
          detail: p.images?.detail?.length || 0,
          video: p.images?.video?.length || 0,
        };
        const total = counts.main + counts.sku + counts.detail + counts.video;
        if (total === 0) return <span className="media-empty">未拉取</span>;
        return (
          <div className="media-badges">
            {MEDIA_LABELS.map(([key, label]) => (
              <span
                key={key}
                className={`media-badge${counts[key] ? "" : " is-zero"}`}
              >
                {label}
                <b>{counts[key]}</b>
              </span>
            ))}
          </div>
        );
      },
    },
    {
      title: "发货地",
      dataIndex: "location",
      width: 92,
      render: (v: string) => v || <span className="cell-dash">—</span>,
    },
    {
      title: "发货时效",
      dataIndex: "ship_time",
      width: 116,
      render: (v: string | undefined) =>
        v ? <span className="pill-ship">{v}</span> : <span className="cell-dash">—</span>,
    },
    {
      title: "归档",
      width: 168,
      render: (_, p) => {
        const tags = p.tags || [];
        const saved = libraryIds.has(p.id);
        if (!saved && !p.project && !tags.length) {
          return <span className="archive-empty">未归档</span>;
        }
        return (
          <div className="cell-archive">
            <span className="proj" title={p.project || undefined}>
              {p.project || "未设项目"}
            </span>
            {tags.length ? (
              <span className="tags">
                {tags.slice(0, 2).map((tag) => (
                  <span key={tag} className="badge">
                    {tag}
                  </span>
                ))}
                {tags.length > 2 ? (
                  <span className="badge">+{tags.length - 2}</span>
                ) : null}
              </span>
            ) : null}
          </div>
        );
      },
    },
    {
      title: "操作",
      width: 152,
      fixed: "right",
      render: (_, p) => {
        const fetched = hasFetchedMedia(p);
        const fetching = fetchingIds.has(p.id);
        const saved = libraryIds.has(p.id);
        return (
          <div className="cell-actions">
            <Button
              size="small"
              type={fetched ? "secondary" : "primary"}
              disabled={fetched || fetching}
              loading={fetching}
              onClick={() => onFetchMedia(p.id)}
            >
              {fetched ? "已拉取" : "拉取素材"}
            </Button>
            <Dropdown
              trigger="click"
              position="br"
              droplist={
                <Menu
                  onClickMenuItem={(key) => {
                    if (key === "view") onView(p.id);
                    if (key === "save") onSave(p.id);
                  }}
                >
                  <Menu.Item key="view" disabled={!fetched}>
                    查看详情
                  </Menu.Item>
                  <Menu.Item key="save">{saved ? "编辑归档" : "归档"}</Menu.Item>
                </Menu>
              }
            >
              <Button
                size="small"
                type="secondary"
                icon={<IconMore />}
                aria-label="更多操作"
              />
            </Dropdown>
          </div>
        );
      },
    },
  ];

  return (
    <Table
      rowKey="id"
      columns={columns}
      data={products}
      pagination={{ pageSize: 20, showTotal: true }}
      scroll={{ x: 1330 }}
      border={{ wrapper: false, cell: false }}
      rowSelection={{
        type: "checkbox",
        selectedRowKeys: selectedKeys,
        onChange: (keys) => onSelectionChange(keys as string[]),
      }}
      noDataElement={<div className="table-empty">暂无商品。请先搜索淘宝。</div>}
    />
  );
}
