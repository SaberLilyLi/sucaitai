import { Layout as ArcoLayout, Radio, Space, Typography } from "@arco-design/web-react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import type { SearchPlatform } from "../api/client";

type LayoutProps = {
  children: ReactNode;
  total: number;
  selected: number;
  libraryCount: number;
  platform: SearchPlatform;
  onPlatformChange: (next: SearchPlatform) => void;
};

export function Layout({
  children,
  total,
  selected,
  libraryCount,
  platform,
  onPlatformChange,
}: LayoutProps) {
  const platformLabel = platform === "1688" ? "1688 阿里巴巴" : "淘宝/天猫";

  return (
    <ArcoLayout className="app-shell-arco">
      <ArcoLayout.Header className="arco-topbar">
        <div className="topbar-left">
          <Link to="/" className="brand">
            <span className="brand-mark" aria-hidden />
            <div>
              <Typography.Title heading={5} style={{ margin: 0 }}>
                素材台
              </Typography.Title>
              <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                万邦 API · {platformLabel} 实时搜索
              </Typography.Text>
            </div>
          </Link>
          <Radio.Group
            type="button"
            name="platform"
            value={platform}
            onChange={(v) => onPlatformChange(v as SearchPlatform)}
            className="platform-switch"
          >
            <Radio value="taobao">淘宝</Radio>
            <Radio value="1688">1688</Radio>
          </Radio.Group>
        </div>
        <Space size="large" className="topbar-meta">
          <Typography.Text>
            已导入 <Typography.Text bold>{total}</Typography.Text>
          </Typography.Text>
          <Typography.Text>
            已勾选 <Typography.Text bold>{selected}</Typography.Text>
          </Typography.Text>
          <Typography.Text>
            本地库 <Typography.Text bold>{libraryCount}</Typography.Text>
          </Typography.Text>
        </Space>
      </ArcoLayout.Header>
      <ArcoLayout.Content className="arco-content">{children}</ArcoLayout.Content>
    </ArcoLayout>
  );
}
