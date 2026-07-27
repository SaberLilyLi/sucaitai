import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Input,
  InputNumber,
  Message,
  Modal,
  Select,
  Tag,
  Typography,
} from "@arco-design/web-react";
import {
  IconDown,
  IconRobot,
  IconSearch,
  IconUp,
} from "@arco-design/web-react/icon";
import {
  parseSearchIntent,
  searchTaobao,
  fetchProductDetailMedia,
  exportToTencentDocs,
  exportProductMedia,
  saveToLibrary,
  type IntentTag,
  type SearchFilters,
  type SearchPlatform,
} from "../api/client";
import { ProductTable } from "../components/ProductTable";
import { hasFetchedMedia, type Product } from "../types/product";

const LOCATION_OPTIONS = [
  "广东",
  "浙江",
  "江苏",
  "上海",
  "北京",
  "福建",
  "山东",
  "河南",
  "湖北",
  "湖南",
  "四川",
  "安徽",
  "河北",
  "天津",
  "重庆",
  "江西",
  "辽宁",
  "云南",
  "广西",
  "陕西",
].map((v) => ({ label: v, value: v }));

const SHIP_TIME_OPTIONS = [
  { label: "24小时内发货", value: "24小时内发货" },
  { label: "48小时内发货", value: "48小时内发货" },
  { label: "当天发货", value: "当天发货" },
  { label: "次日达", value: "次日达" },
  { label: "隔日达", value: "隔日达" },
  { label: "极速发货", value: "极速发货" },
];

type Props = {
  products: Product[];
  setProducts: (items: Product[] | ((prev: Product[]) => Product[])) => void;
  selected: Set<string>;
  setSelected: (next: Set<string>) => void;
  libraryIds: Set<string>;
  setLibraryIds: (next: Set<string>) => void;
  platform: SearchPlatform;
};

type SearchParams = {
  keyword: string;
  locations?: string[];
  shipTime?: string;
  priceMin?: number;
  priceMax?: number;
};

export function ProductListPage({
  products,
  setProducts,
  selected,
  setSelected,
  libraryIds,
  setLibraryIds,
  platform,
}: Props) {
  const [keyword, setKeyword] = useState("");
  const [locations, setLocations] = useState<string[]>([]);
  const [shipTime, setShipTime] = useState<string | undefined>();
  const [priceMin, setPriceMin] = useState<number | undefined>();
  const [priceMax, setPriceMax] = useState<number | undefined>();
  const [filter, setFilter] = useState("");
  const [aiText, setAiText] = useState("");
  const [aiTags, setAiTags] = useState<IntentTag[]>([]);
  const [aiOpen, setAiOpen] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [fetchingIds, setFetchingIds] = useState<Set<string>>(() => new Set());
  const [exporting, setExporting] = useState(false);
  const [exportingMedia, setExportingMedia] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | null>(null);
  const [projectDraft, setProjectDraft] = useState("");
  const [tagsDraft, setTagsDraft] = useState("");
  const [noteDraft, setNoteDraft] = useState("");
  const [savingLibrary, setSavingLibrary] = useState(false);
  const [compareVisible, setCompareVisible] = useState(false);
  const navigate = useNavigate();

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return products;
    return products.filter(
      (p) =>
        p.title.toLowerCase().includes(q) ||
        p.url.toLowerCase().includes(q) ||
        (p.location || "").toLowerCase().includes(q) ||
        (p.ship_time || "").toLowerCase().includes(q),
    );
  }, [products, filter]);

  const selectedKeys = useMemo(() => [...selected], [selected]);

  const openSaveDialog = (id: string) => {
    const p = products.find((x) => x.id === id);
    if (!p) return;
    setEditingProduct(p);
    setProjectDraft(p.project || "");
    setTagsDraft((p.tags || []).join(", "));
    setNoteDraft(p.note || "");
  };

  const onSave = async () => {
    if (!editingProduct) return;
    const tags = [...new Set(tagsDraft.split(/[,，、]/).map((x) => x.trim()).filter(Boolean))];
    setSavingLibrary(true);
    try {
      const res = await saveToLibrary({
        ...editingProduct,
        project: projectDraft.trim() || undefined,
        tags,
        note: noteDraft.trim() || undefined,
      });
      setLibraryIds(new Set(res.libraryIds || []));
      setProducts((prev) => prev.map((p) => (p.id === res.product.id ? { ...p, ...res.product } : p)));
      setEditingProduct(null);
      Message.success("已保存到本地素材库");
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSavingLibrary(false);
    }
  };

  const onExportToTencentDocs = async () => {
    if (!selectedKeys.length) return;
    setExporting(true);
    try {
      const result = await exportToTencentDocs(selectedKeys);
      Message.success(result.message || "已同步到腾讯文档，可在腾讯文档列表中查看。");
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "同步到腾讯文档失败");
    } finally {
      setExporting(false);
    }
  };

  const onExportMedia = async () => {
    if (!selectedKeys.length) return;
    setExportingMedia(true);
    try {
      const result = await exportProductMedia(selectedKeys);
      Message.success(`已下载素材包：${result.products || selectedKeys.length} 个商品`);
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "素材打包失败");
    } finally {
      setExportingMedia(false);
    }
  };

  const compareProducts = useMemo(
    () => products.filter((p) => selected.has(p.id)),
    [products, selected],
  );

  const onFetchMedia = async (id: string) => {
    const p = products.find((x) => x.id === id);
    if (!p?.url) {
      Message.error("缺少商品链接");
      return;
    }
    if (hasFetchedMedia(p)) {
      Message.info("该商品素材已拉取");
      return;
    }
    setFetchingIds((prev) => new Set(prev).add(id));
    Message.info("正在拉取素材，请稍候…");
    try {
      const res = await fetchProductDetailMedia(p.id, p.url, p, platform);
      setProducts((prev) =>
        prev.map((x) => {
          if (x.id !== res.product.id && x.id !== id) return x;
          const next = res.product;
          return {
            ...x,
            ...next,
            title: next.title?.trim() ? next.title : x.title,
            price: next.price?.trim() ? next.price : x.price,
            location: next.location?.trim() ? next.location : x.location,
            url: next.url || x.url,
          };
        }),
      );
      const savedTotal =
        (res.saved_main || 0) +
        (res.saved_sku || 0) +
        (res.saved_detail || 0) +
        (res.saved_video || 0);
      if (savedTotal === 0) {
        Message.warning(
          "未拉到可用素材。天猫商品可能暂不可用（服务商修复中），请换淘宝商品或稍后再试。",
        );
      } else {
        Message.success(res.message || "素材拉取完成");
      }
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "拉取失败，请稍后再试");
    } finally {
      setFetchingIds((prev) => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
    }
  };

  const runSearch = async (params: SearchParams) => {
    const kw = params.keyword.trim();
    if (!kw) {
      Message.warning("请输入淘宝搜索关键词");
      return;
    }
    const locs = (params.locations || []).map((x) => x.trim()).filter(Boolean);
    const ship = params.shipTime?.trim() || undefined;
    const pMin = params.priceMin;
    const pMax = params.priceMax;
    if (
      pMin != null &&
      pMax != null &&
      !Number.isNaN(pMin) &&
      !Number.isNaN(pMax) &&
      pMin > pMax
    ) {
      Message.warning("价格下限不能大于上限");
      return;
    }

    setSearching(true);
    setProducts([]);
    setSelected(new Set());
    const bits = [
      locs.length ? `发货地 ${locs.join("/")}` : "",
      ship ? `发货 ${ship}` : "",
      pMin != null || pMax != null ? `价格 ${pMin ?? "不限"}-${pMax ?? "不限"}` : "",
    ].filter(Boolean);
    Message.info(
      `正在淘宝搜索「${kw}」${bits.length ? `（${bits.join("，")}）` : ""}，目标约 100 条…`,
    );
    try {
      const filters: SearchFilters = {
        locations: locs,
        ship_time: ship,
        price_min: pMin,
        price_max: pMax,
      };
      const res = await searchTaobao(kw, 100, filters, platform);
      setProducts(res.items || []);
      setSelected(new Set());
      setLibraryIds(new Set(res.libraryIds || []));
      setFilter("");
      Message.success(res.message || `搜索完成，共 ${res.count} 个商品`);
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "搜索失败");
    } finally {
      setSearching(false);
    }
  };

  const onSearchTaobao = () =>
    void runSearch({
      keyword,
      locations,
      shipTime,
      priceMin,
      priceMax,
    });

  const onAiParseAndSearch = async () => {
    const text = aiText.trim();
    if (!text) {
      Message.warning("请先输入一段选品描述");
      return;
    }
    setParsing(true);
    try {
      const intent = await parseSearchIntent(text);
      setAiTags(intent.tags || []);
      setKeyword(intent.keyword || "");
      const locs =
        intent.locations?.filter(Boolean) ||
        (intent.location
          ? intent.location.split(/[,，、/\s]+/).filter(Boolean)
          : []);
      setLocations(locs);
      setShipTime(intent.ship_time || undefined);
      setPriceMin(
        intent.price_min != null && !Number.isNaN(intent.price_min)
          ? intent.price_min
          : undefined,
      );
      setPriceMax(
        intent.price_max != null && !Number.isNaN(intent.price_max)
          ? intent.price_max
          : undefined,
      );
      Message.success(intent.message || "识别完成");
      await runSearch({
        keyword: intent.keyword,
        locations: locs,
        shipTime: intent.ship_time || undefined,
        priceMin:
          intent.price_min != null && !Number.isNaN(intent.price_min)
            ? intent.price_min
            : undefined,
        priceMax:
          intent.price_max != null && !Number.isNaN(intent.price_max)
            ? intent.price_max
            : undefined,
      });
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "识别失败");
    } finally {
      setParsing(false);
    }
  };

  const resetFilters = () => {
    setKeyword("");
    setLocations([]);
    setShipTime(undefined);
    setPriceMin(undefined);
    setPriceMax(undefined);
  };

  const tagColor = (type: string) => {
    if (type === "keyword") return "arcoblue";
    if (type === "location") return "green";
    if (type === "ship_time") return "orangered";
    if (type === "price") return "gold";
    return "gray";
  };

  const hasSelection = selected.size > 0;

  return (
    <main className="view view-list">
      <section className="search-card">
        <div className="search-main">
          <Input
            size="large"
            prefix={<IconSearch />}
            allowClear
            placeholder="输入商品关键词，如：夏季清凉女装"
            value={keyword}
            disabled={searching || parsing}
            onChange={setKeyword}
            onPressEnter={onSearchTaobao}
          />
          <Button
            type="primary"
            size="large"
            className="search-submit"
            loading={searching}
            disabled={parsing}
            onClick={onSearchTaobao}
          >
            搜索商品
          </Button>
        </div>
        <div className="search-filters">
          <label className="filter-item">
            <span>发货地</span>
            <Select
              allowClear
              allowCreate
              showSearch
              mode="multiple"
              maxTagCount={2}
              disabled={searching || parsing}
              style={{ width: 230 }}
              placeholder="不限（可多选）"
              options={LOCATION_OPTIONS}
              value={locations}
              onChange={(v) => setLocations(Array.isArray(v) ? v : [])}
            />
          </label>
          <label className="filter-item">
            <span>发货时效</span>
            <Select
              allowClear
              disabled={searching || parsing}
              style={{ width: 160 }}
              placeholder="不限"
              options={SHIP_TIME_OPTIONS}
              value={shipTime}
              onChange={(v) => setShipTime(v || undefined)}
            />
          </label>
          <label className="filter-item">
            <span>价格区间</span>
            <div className="price-range">
              <InputNumber
                hideControl
                disabled={searching || parsing}
                style={{ width: 96 }}
                placeholder="最低价"
                min={0}
                value={priceMin}
                onChange={(v) => setPriceMin(typeof v === "number" ? v : undefined)}
              />
              <span>—</span>
              <InputNumber
                hideControl
                disabled={searching || parsing}
                style={{ width: 96 }}
                placeholder="最高价"
                min={0}
                value={priceMax}
                onChange={(v) => setPriceMax(typeof v === "number" ? v : undefined)}
              />
            </div>
          </label>
          <Button
            type="text"
            className="filter-reset"
            disabled={searching || parsing}
            onClick={resetFilters}
          >
            重置
          </Button>
        </div>
      </section>

      <section className={`ai-panel${aiOpen ? " is-open" : ""}`}>
        <button
          type="button"
          className="ai-panel-head"
          aria-expanded={aiOpen}
          onClick={() => setAiOpen((v) => !v)}
        >
          <span className="ai-panel-icon" aria-hidden>
            <IconRobot />
          </span>
          <span className="ai-panel-title">智能选品助手</span>
          <span className="ai-panel-sub">
            用一句话描述选品需求，AI 自动识别关键词与筛选条件
          </span>
          {!aiOpen && aiTags.length > 0 ? (
            <span className="ai-panel-tags">
              {aiTags.map((t) => (
                <Tag key={t.label} color={tagColor(t.type)} size="small">
                  {t.label}
                </Tag>
              ))}
            </span>
          ) : null}
          {aiOpen ? <IconUp /> : <IconDown />}
        </button>
        {aiOpen ? (
          <div className="ai-panel-body">
            <Input.TextArea
              value={aiText}
              disabled={searching || parsing}
              autoSize={{ minRows: 2, maxRows: 4 }}
              placeholder="例如：帮我找夏季清凉碎花裙，从浙江发货，次日达，价格 80 到 200"
              onChange={setAiText}
            />
            {aiTags.length > 0 ? (
              <div className="ai-panel-tags">
                {aiTags.map((t) => (
                  <Tag key={t.label} color={tagColor(t.type)} size="small">
                    {t.label}
                  </Tag>
                ))}
              </div>
            ) : null}
            <div className="ai-panel-actions">
              <Button
                type="primary"
                loading={parsing || searching}
                onClick={() => void onAiParseAndSearch()}
              >
                识别并搜索
              </Button>
              <Button
                type="text"
                disabled={parsing || searching || !aiText}
                onClick={() => {
                  setAiText("");
                  setAiTags([]);
                }}
              >
                清空
              </Button>
            </div>
          </div>
        ) : null}
      </section>

      <section className={`batch-bar${hasSelection ? " is-active" : ""}`}>
        <span className="batch-count">
          已选 <b>{selected.size}</b> 项
        </span>
        <div className="batch-actions">
          <Button
            disabled={selected.size < 2 || selected.size > 4}
            onClick={() => setCompareVisible(true)}
          >
            商品对比
          </Button>
          <Button
            loading={exportingMedia}
            disabled={!hasSelection || exportingMedia}
            onClick={() => void onExportMedia()}
          >
            打包下载素材
          </Button>
          <Button
            type="primary"
            loading={exporting}
            disabled={!hasSelection || searching || parsing || exporting}
            onClick={() => void onExportToTencentDocs()}
          >
            导出腾讯文档
          </Button>
        </div>
        <span className="batch-hint">
          {hasSelection
            ? "商品对比支持 2–4 个商品"
            : "勾选表格中的商品后，可进行对比、素材打包与导出"}
        </span>
      </section>

      <section className="table-card">
        <div className="table-card-head">
          <div className="t-title">
            商品结果
            <span className="t-count">{filtered.length}</span>
            {filter && filtered.length !== products.length ? (
              <span className="t-sub">从 {products.length} 条中筛选</span>
            ) : null}
          </div>
          <Input
            allowClear
            style={{ width: 220 }}
            placeholder="筛选当前列表…"
            value={filter}
            onChange={setFilter}
          />
        </div>
        <ProductTable
          products={filtered}
          selectedKeys={selectedKeys}
          libraryIds={libraryIds}
          fetchingIds={fetchingIds}
          onSelectionChange={(keys) => setSelected(new Set(keys))}
          onFetchMedia={(id) => void onFetchMedia(id)}
          onSave={openSaveDialog}
          onView={(id) => navigate(`/detail/${id}`)}
        />
      </section>

      <Modal
        visible={Boolean(editingProduct)}
        title="归档到素材库"
        okText="保存"
        cancelText="取消"
        confirmLoading={savingLibrary}
        onCancel={() => setEditingProduct(null)}
        onOk={() => void onSave()}
      >
        <div className="library-edit-form">
          <Typography.Text type="secondary">
            {editingProduct?.title || "商品"}
          </Typography.Text>
          <label>
            项目
            <Input value={projectDraft} placeholder="例如：2026 夏季女装" onChange={setProjectDraft} />
          </label>
          <label>
            标签
            <Input value={tagsDraft} placeholder="用逗号分隔，例如：连衣裙, 待测, 浙江" onChange={setTagsDraft} />
          </label>
          <label>
            备注
            <Input.TextArea value={noteDraft} autoSize={{ minRows: 3, maxRows: 6 }} placeholder="记录选品理由、风险或后续动作" onChange={setNoteDraft} />
          </label>
        </div>
      </Modal>

      <Modal
        visible={compareVisible}
        title="商品对比"
        footer={null}
        style={{ width: "min(1100px, calc(100vw - 32px))" }}
        onCancel={() => setCompareVisible(false)}
      >
        <Typography.Paragraph type="secondary">
          最多同时比较 4 个商品，可从表格勾选后打开。
        </Typography.Paragraph>
        <div className="compare-table-wrap">
          <table className="compare-table">
            <tbody>
              <tr>
                <th>商品</th>
                {compareProducts.map((p) => <td key={p.id}><img src={p.cover} alt="" /><strong>{p.title || "（无标题）"}</strong></td>)}
              </tr>
              <tr><th>价格</th>{compareProducts.map((p) => <td key={p.id}>{p.price || "—"}</td>)}</tr>
              <tr><th>销量</th>{compareProducts.map((p) => <td key={p.id}>{p.total_sales || "—"}</td>)}</tr>
              <tr><th>发货地</th>{compareProducts.map((p) => <td key={p.id}>{p.location || "—"}</td>)}</tr>
              <tr><th>发货时效</th>{compareProducts.map((p) => <td key={p.id}>{p.ship_time || "—"}</td>)}</tr>
              <tr><th>素材</th>{compareProducts.map((p) => <td key={p.id}>主图 {p.images?.main?.length || 0} · SKU {p.images?.sku?.length || 0} · 详情 {p.images?.detail?.length || 0} · 视频 {p.images?.video?.length || 0}</td>)}</tr>
              <tr><th>归档</th>{compareProducts.map((p) => <td key={p.id}>{p.project || "未归档"}{p.tags?.length ? ` · ${p.tags.join("、")}` : ""}{p.note ? <p>{p.note}</p> : null}</td>)}</tr>
            </tbody>
          </table>
        </div>
      </Modal>
    </main>
  );
}
