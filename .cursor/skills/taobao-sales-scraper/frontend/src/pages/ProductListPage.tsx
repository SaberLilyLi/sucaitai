import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Button,
  Input,
  InputNumber,
  Message,
  Select,
  Space,
  Tag,
  Typography,
} from "@arco-design/web-react";
import {
  parseSearchIntent,
  searchTaobao,
  fetchProductDetailMedia,
  exportToTencentDocs,
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
  const [parsing, setParsing] = useState(false);
  const [searching, setSearching] = useState(false);
  const [fetchingIds, setFetchingIds] = useState<Set<string>>(() => new Set());
  const [exporting, setExporting] = useState(false);
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

  const onSave = async (id: string) => {
    const p = products.find((x) => x.id === id);
    if (!p) return;
    try {
      const res = await saveToLibrary(p);
      setLibraryIds(new Set(res.libraryIds || []));
      Message.success(`已保存到 library.json`);
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "保存失败");
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

  const tagColor = (type: string) => {
    if (type === "keyword") return "arcoblue";
    if (type === "location") return "green";
    if (type === "ship_time") return "orangered";
    if (type === "price") return "gold";
    return "gray";
  };

  return (
    <main className="view view-list">
      <section className="toolbar">
        <div className="toolbar-left">
          <Typography.Title heading={4} style={{ margin: 0 }}>
            商品列表
          </Typography.Title>
          <Typography.Text type="secondary">
            输入关键词与筛选条件实时搜索淘宝；也可在下方用自然语言让 AI 识别后搜索。
          </Typography.Text>
        </div>
        <div className="toolbar-actions">
          <Space wrap>
            <Input
              allowClear
              style={{ width: 220 }}
              placeholder="淘宝关键词，如：夏季清凉女装"
              value={keyword}
              disabled={searching || parsing}
              onChange={setKeyword}
              onPressEnter={onSearchTaobao}
            />
            <Select
              allowClear
              allowCreate
              showSearch
              mode="multiple"
              maxTagCount={2}
              disabled={searching || parsing}
              style={{ minWidth: 180, maxWidth: 280 }}
              placeholder="发货地（可多选）"
              options={LOCATION_OPTIONS}
              value={locations}
              onChange={(v) => setLocations(Array.isArray(v) ? v : [])}
            />
            <Select
              allowClear
              disabled={searching || parsing}
              style={{ width: 160 }}
              placeholder="发货时间"
              options={SHIP_TIME_OPTIONS}
              value={shipTime}
              onChange={(v) => setShipTime(v || undefined)}
            />
            <InputNumber
              hideControl
              disabled={searching || parsing}
              style={{ width: 100 }}
              placeholder="最低价"
              min={0}
              value={priceMin}
              onChange={(v) => setPriceMin(typeof v === "number" ? v : undefined)}
            />
            <Typography.Text type="secondary">—</Typography.Text>
            <InputNumber
              hideControl
              disabled={searching || parsing}
              style={{ width: 100 }}
              placeholder="最高价"
              min={0}
              value={priceMax}
              onChange={(v) => setPriceMax(typeof v === "number" ? v : undefined)}
            />
            <Button
              type="primary"
              loading={searching}
              disabled={parsing}
              onClick={onSearchTaobao}
            >
              淘宝搜索
            </Button>
            <Input
              allowClear
              style={{ width: 180 }}
              placeholder="筛选当前列表…"
              value={filter}
              onChange={setFilter}
            />
            <Button
              type="primary"
              status="success"
              loading={exporting}
              disabled={selected.size === 0 || searching || parsing || exporting}
              onClick={() => void onExportToTencentDocs()}
            >
              导出到腾讯文档（{selected.size}）
            </Button>
          </Space>
        </div>
      </section>

      <section className="ai-filter-panel">
        <div className="ai-filter-head">
          <Typography.Text bold>AI 帮你筛选</Typography.Text>
          <Typography.Text type="secondary">
            用一句话描述需求，智能识别标签后自动搜索
          </Typography.Text>
        </div>
        <Input.TextArea
          value={aiText}
          disabled={searching || parsing}
          autoSize={{ minRows: 2, maxRows: 4 }}
          placeholder="例如：帮我找夏季清凉碎花裙，从浙江发货，次日达，价格 80 到 200"
          onChange={setAiText}
        />
        {aiTags.length > 0 ? (
          <div className="ai-filter-tags">
            {aiTags.map((t) => (
              <Tag key={t.label} color={tagColor(t.type)} size="small">
                {t.label}
              </Tag>
            ))}
          </div>
        ) : null}
        <div className="ai-filter-actions">
          <Button
            type="primary"
            status="warning"
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
      </section>

      <ProductTable
        products={filtered}
        selectedKeys={selectedKeys}
        libraryIds={libraryIds}
        fetchingIds={fetchingIds}
        onSelectionChange={(keys) => setSelected(new Set(keys))}
        onFetchMedia={(id) => void onFetchMedia(id)}
        onSave={(id) => void onSave(id)}
        onView={(id) => navigate(`/detail/${id}`)}
      />
    </main>
  );
}
