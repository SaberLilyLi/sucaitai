import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button, Input, Message, Modal, Space, Tag, Typography } from "@arco-design/web-react";
import { fetchLibrary, saveToLibrary } from "../api/client";
import type { Product } from "../types/product";

type Props = {
  setProducts: (items: Product[] | ((prev: Product[]) => Product[])) => void;
  onLibraryItemsChange: (items: Product[]) => void;
};

export function LibraryPage({ setProducts, onLibraryItemsChange }: Props) {
  const [items, setItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [editing, setEditing] = useState<Product | null>(null);
  const [project, setProject] = useState("");
  const [tags, setTags] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const result = await fetchLibrary();
      setItems(result.items || []);
      onLibraryItemsChange(result.items || []);
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "读取本地库失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const shown = useMemo(() => {
    const q = filter.trim().toLowerCase();
    if (!q) return items;
    return items.filter((item) =>
      [item.title, item.project, item.note, ...(item.tags || [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q),
    );
  }, [filter, items]);

  const openEdit = (item: Product) => {
    setEditing(item);
    setProject(item.project || "");
    setTags((item.tags || []).join(", "));
    setNote(item.note || "");
  };

  const save = async () => {
    if (!editing) return;
    setSaving(true);
    try {
      const result = await saveToLibrary({
        ...editing,
        project: project.trim() || undefined,
        tags: [...new Set(tags.split(/[,，、]/).map((x) => x.trim()).filter(Boolean))],
        note: note.trim() || undefined,
      });
      setItems(result.items || []);
      onLibraryItemsChange(result.items || []);
      setEditing(null);
      Message.success("归档信息已更新");
    } catch (e) {
      Message.error(e instanceof Error ? e.message : "保存失败");
    } finally {
      setSaving(false);
    }
  };

  const openDetail = (item: Product) => {
    setProducts((prev) => {
      const exists = prev.some((p) => p.id === item.id);
      return exists ? prev.map((p) => (p.id === item.id ? { ...p, ...item } : p)) : [item, ...prev];
    });
    navigate(`/detail/${item.id}`);
  };

  return (
    <main className="view view-library">
      <section className="toolbar">
        <div className="toolbar-left">
          <Typography.Title heading={4} style={{ margin: 0 }}>本地素材库</Typography.Title>
          <Typography.Text type="secondary">已归档商品的项目、标签、备注和已拉取素材。</Typography.Text>
        </div>
        <Space wrap>
          <Input allowClear value={filter} style={{ width: 240 }} placeholder="搜索标题、项目、标签或备注…" onChange={setFilter} />
          <Button loading={loading} onClick={() => void load()}>刷新</Button>
        </Space>
      </section>

      {loading ? <p className="empty-hint">正在读取本地素材库…</p> : null}
      {!loading && !shown.length ? <p className="empty-hint">本地库暂无商品。请先在商品列表中点击“归档”。</p> : null}
      <section className="library-grid">
        {shown.map((item) => (
          <article className="library-card" key={item.id}>
            <div className="library-cover" style={item.cover ? { backgroundImage: `url("${item.cover}")` } : undefined} />
            <div className="library-card-body">
              <Typography.Text bold ellipsis={{ showTooltip: true }}>{item.title || "（无标题）"}</Typography.Text>
              <Typography.Text type="secondary">{item.price || "—"} · {item.location || "未知发货地"}</Typography.Text>
              {item.project ? <Tag color="arcoblue">{item.project}</Tag> : null}
              {item.tags?.length ? <div className="library-tags">{item.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}</div> : null}
              {item.note ? <Typography.Paragraph className="library-note" ellipsis={{ rows: 2, expandable: true }}>{item.note}</Typography.Paragraph> : null}
              <Space size="mini">
                <Button size="mini" type="primary" onClick={() => openDetail(item)}>查看素材</Button>
                <Button size="mini" onClick={() => openEdit(item)}>编辑归档</Button>
              </Space>
            </div>
          </article>
        ))}
      </section>

      <Modal visible={Boolean(editing)} title="编辑归档" okText="保存" confirmLoading={saving} onCancel={() => setEditing(null)} onOk={() => void save()}>
        <div className="library-edit-form">
          <label>项目<Input value={project} onChange={setProject} placeholder="例如：2026 夏季女装" /></label>
          <label>标签<Input value={tags} onChange={setTags} placeholder="用逗号分隔" /></label>
          <label>备注<Input.TextArea value={note} onChange={setNote} autoSize={{ minRows: 3, maxRows: 6 }} /></label>
        </div>
      </Modal>
    </main>
  );
}
