import { Button, Image, Link, Space, Table, Typography } from "@arco-design/web-react";
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
      width: 80,
      render: (_, p) =>
        p.cover ? (
          <Image
            src={p.cover}
            width={48}
            height={48}
            style={{ objectFit: "cover", borderRadius: 2 }}
            preview={false}
          />
        ) : (
          <Typography.Text type="secondary">无图</Typography.Text>
        ),
    },
    {
      title: "标题",
      dataIndex: "title",
      ellipsis: true,
      render: (title: string) => (
        <Typography.Text style={{ fontWeight: 500 }}>{title || "（无标题）"}</Typography.Text>
      ),
    },
    {
      title: "链接",
      dataIndex: "url",
      width: 220,
      bodyCellStyle: { whiteSpace: "normal", wordBreak: "break-all" },
      render: (url: string) =>
        url ? (
          <Link
            className="link-cell"
            href={url}
            target="_blank"
            hoverable={false}
          >
            {url}
          </Link>
        ) : (
          "—"
        ),
    },
    {
      title: "价格",
      dataIndex: "price",
      width: 90,
      render: (v: string) => v || "—",
    },
    {
      title: "发货地",
      dataIndex: "location",
      width: 100,
      render: (v: string) => v || "—",
    },
    {
      title: "发货时间",
      dataIndex: "ship_time",
      width: 120,
      render: (v: string | undefined) => v || "—",
    },
    {
      title: "操作",
      width: 220,
      fixed: "right",
      render: (_, p) => {
        const fetched = hasFetchedMedia(p);
        const fetching = fetchingIds.has(p.id);
        const saved = libraryIds.has(p.id);
        return (
          <Space size="mini">
            <Button
              size="mini"
              type="primary"
              disabled={fetched || fetching}
              loading={fetching}
              onClick={() => onFetchMedia(p.id)}
            >
              {fetched ? "已拉取" : "拉取该素材"}
            </Button>
            {fetched ? (
              <Button size="mini" type="outline" onClick={() => onView(p.id)}>
                查看
              </Button>
            ) : null}
            <Button
              size="mini"
              type="secondary"
              disabled={saved}
              onClick={() => onSave(p.id)}
            >
              {saved ? "已保存" : "保存"}
            </Button>
          </Space>
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
      scroll={{ x: 1100 }}
      border={{ wrapper: true, cell: true }}
      rowSelection={{
        type: "checkbox",
        selectedRowKeys: selectedKeys,
        onChange: (keys) => onSelectionChange(keys as string[]),
      }}
      noDataElement="暂无商品。请先搜索淘宝。"
    />
  );
}
