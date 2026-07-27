import { Layout as ArcoLayout, Radio, Typography } from "@arco-design/web-react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";
import type { SearchPlatform } from "../api/client";

type LayoutProps = {
  children: ReactNode;
  total: number;
  selected: number;
  fetchedCount: number;
  libraryCount: number;
  platform: SearchPlatform;
  onPlatformChange: (next: SearchPlatform) => void;
};

export function Layout({
  children,
  total,
  selected,
  fetchedCount,
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
        <div className="topbar-stats">
          <div className="stat">
            <span className="stat-num">{total}</span>
            <span className="stat-label">当前结果</span>
          </div>
          <div className="stat">
            <span className="stat-num">{selected}</span>
            <span className="stat-label">已勾选</span>
          </div>
          <div className="stat">
            <span className="stat-num">{fetchedCount}</span>
            <span className="stat-label">已拉取素材</span>
          </div>
          <Link to="/library" className="stat stat-link" title="打开本地素材库">
            <span className="stat-num">{libraryCount}</span>
            <span className="stat-label">本地库 · 已归档</span>
          </Link>
        </div>
      </ArcoLayout.Header>
      <ArcoLayout.Content className="arco-content">{children}</ArcoLayout.Content>
    </ArcoLayout>
  );
}
