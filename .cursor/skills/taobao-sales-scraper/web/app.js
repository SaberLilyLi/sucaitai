/* 素材台 — 前端交互（当前用 mock / 本地图；后续换 API 即可） */
(() => {
  const state = {
    products: Array.isArray(window.MOCK_PRODUCTS) ? window.MOCK_PRODUCTS : [],
    selected: new Set(),
    libraryIds: new Set(JSON.parse(localStorage.getItem("scrape_library_ids") || "[]")),
    currentId: null,
    query: "",
  };

  const $ = (id) => document.getElementById(id);

  function toast(msg, ok = true) {
    const el = $("toast");
    el.hidden = false;
    el.textContent = msg;
    el.classList.toggle("is-ok", ok);
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 2200);
  }

  function persistLibrary() {
    localStorage.setItem("scrape_library_ids", JSON.stringify([...state.libraryIds]));
  }

  function updateStats() {
    $("statTotal").textContent = String(state.products.length);
    $("statSelected").textContent = String(state.selected.size);
    $("statLibrary").textContent = String(state.libraryIds.size);
    $("btnBatchDownload").disabled = state.selected.size === 0;
  }

  function filteredProducts() {
    const q = state.query.trim().toLowerCase();
    if (!q) return state.products;
    return state.products.filter(
      (p) =>
        (p.title || "").toLowerCase().includes(q) ||
        (p.url || "").toLowerCase().includes(q)
    );
  }

  function renderList() {
    const tbody = $("productTbody");
    const rows = filteredProducts();
    $("listEmpty").hidden = rows.length > 0;
    tbody.innerHTML = "";

    rows.forEach((p) => {
      const tr = document.createElement("tr");
      if (state.selected.has(p.id)) tr.classList.add("is-selected");

      const checkTd = document.createElement("td");
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = state.selected.has(p.id);
      cb.setAttribute("aria-label", `选择 ${p.title}`);
      cb.addEventListener("change", () => {
        if (cb.checked) state.selected.add(p.id);
        else state.selected.delete(p.id);
        tr.classList.toggle("is-selected", cb.checked);
        syncCheckAll();
        updateStats();
      });
      checkTd.appendChild(cb);

      const thumbTd = document.createElement("td");
      if (p.cover) {
        const img = document.createElement("img");
        img.className = "thumb";
        img.src = p.cover;
        img.alt = "";
        img.loading = "lazy";
        thumbTd.appendChild(img);
      } else {
        const ph = document.createElement("div");
        ph.className = "thumb placeholder";
        ph.textContent = "无图";
        thumbTd.appendChild(ph);
      }

      const titleTd = document.createElement("td");
      titleTd.className = "title-cell";
      titleTd.textContent = p.title || "（无标题）";

      const linkTd = document.createElement("td");
      linkTd.className = "link-cell";
      const a = document.createElement("a");
      a.href = p.url || "#";
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = p.url || "—";
      a.title = p.url || "";
      linkTd.appendChild(a);

      const priceTd = document.createElement("td");
      priceTd.className = "price-cell";
      priceTd.textContent = p.price || "—";

      const actTd = document.createElement("td");
      const acts = document.createElement("div");
      acts.className = "row-actions";

      const btnDetail = document.createElement("button");
      btnDetail.type = "button";
      btnDetail.className = "btn btn-sm";
      btnDetail.textContent = "详情";
      btnDetail.addEventListener("click", () => openDetail(p.id));

      const btnSave = document.createElement("button");
      btnSave.type = "button";
      btnSave.className = "btn btn-sm btn-ghost";
      btnSave.textContent = state.libraryIds.has(p.id) ? "已保存" : "保存";
      btnSave.disabled = state.libraryIds.has(p.id);
      btnSave.addEventListener("click", () => saveProduct(p.id));

      acts.append(btnDetail, btnSave);
      actTd.appendChild(acts);

      tr.append(checkTd, thumbTd, titleTd, linkTd, priceTd, actTd);
      tbody.appendChild(tr);
    });

    syncCheckAll();
    updateStats();
  }

  function syncCheckAll() {
    const rows = filteredProducts();
    const all =
      rows.length > 0 && rows.every((p) => state.selected.has(p.id));
    $("checkAll").checked = all;
    $("checkAll").indeterminate =
      !all && rows.some((p) => state.selected.has(p.id));
  }

  function showList() {
    $("viewList").hidden = false;
    $("viewDetail").hidden = true;
    state.currentId = null;
    history.replaceState(null, "", "#/");
    renderList();
  }

  function openDetail(id) {
    const p = state.products.find((x) => x.id === id);
    if (!p) return;
    state.currentId = id;
    $("viewList").hidden = true;
    $("viewDetail").hidden = false;
    history.replaceState(null, "", `#/detail/${id}`);

    $("detailTitle").textContent = p.title || "—";
    $("detailPrice").textContent = p.price || "—";
    $("detailLocation").textContent = p.location || "—";
    const link = $("detailLink");
    link.href = p.url || "#";
    link.textContent = p.url || "无链接";

    const cover = $("detailCover");
    if (p.cover) {
      cover.style.backgroundImage = `url("${p.cover}")`;
    } else {
      cover.style.backgroundImage = "";
    }

    const main = (p.images && p.images.main) || [];
    const sku = (p.images && p.images.sku) || [];
    $("mainCount").textContent = `${main.length} 张`;
    $("skuCount").textContent = `${sku.length} 张`;
    renderGallery($("galleryMain"), main, p);
    renderGallery($("gallerySku"), sku, p);

    $("btnSave").textContent = state.libraryIds.has(id) ? "已在本地库" : "保存到本地库";
    $("btnSave").disabled = state.libraryIds.has(id);
  }

  function renderGallery(container, list, product) {
    container.innerHTML = "";
    if (!list.length) {
      const empty = document.createElement("p");
      empty.className = "gallery-empty";
      empty.textContent = "暂无该类图片（可先跑分类下载脚本）";
      container.appendChild(empty);
      return;
    }
    list.forEach((img, i) => {
      const card = document.createElement("article");
      card.className = "shot-card";
      card.style.animationDelay = `${i * 40}ms`;

      const photo = document.createElement("img");
      photo.src = img.src;
      photo.alt = img.name || "";
      photo.loading = "lazy";

      const meta = document.createElement("div");
      meta.className = "shot-meta";
      const name = document.createElement("span");
      name.className = "shot-name";
      name.textContent = img.name || `图_${i + 1}`;
      const dl = document.createElement("button");
      dl.type = "button";
      dl.className = "btn btn-sm";
      dl.textContent = "下载";
      dl.addEventListener("click", () => downloadOne(img, product));
      meta.append(name, dl);

      card.append(photo, meta);
      container.appendChild(card);
    });
  }

  function saveProduct(id) {
    const p = state.products.find((x) => x.id === id);
    if (!p) return;
    state.libraryIds.add(id);
    // 前端阶段：模拟写入 library.json（存 localStorage）；后端接上后改为 POST /api/library
    const lib = JSON.parse(localStorage.getItem("scrape_library") || "[]");
    if (!lib.some((x) => x.id === id)) {
      lib.push({
        id: p.id,
        title: p.title,
        url: p.url,
        price: p.price,
        location: p.location,
        cover: p.cover,
        savedAt: new Date().toISOString(),
      });
      localStorage.setItem("scrape_library", JSON.stringify(lib, null, 2));
    }
    persistLibrary();
    toast(`已保存到本地库：${(p.title || "").slice(0, 18)}…`);
    if (state.currentId === id) openDetail(id);
    else renderList();
    updateStats();
  }

  function downloadOne(img, product) {
    // 静态预览：用 a[download] 触发；跨域 CDN 可能只打开新页，后端接上后走 /api/download
    const a = document.createElement("a");
    a.href = img.src;
    a.download = img.name || "image.jpg";
    a.target = "_blank";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast(`开始下载：${img.name || "图片"}（${(product.title || "").slice(0, 12)}）`);
  }

  function batchDownload() {
    const ids = [...state.selected];
    if (!ids.length) return;
    // 前端阶段仅提示；后端将打 zip
    toast(`已勾选 ${ids.length} 个商品，批量打包下载将在后端接入后生效`);
  }

  // —— events ——
  $("checkAll").addEventListener("change", () => {
    const rows = filteredProducts();
    if ($("checkAll").checked) rows.forEach((p) => state.selected.add(p.id));
    else rows.forEach((p) => state.selected.delete(p.id));
    renderList();
  });

  $("searchInput").addEventListener("input", (e) => {
    state.query = e.target.value || "";
    renderList();
  });

  $("btnBatchDownload").addEventListener("click", batchDownload);
  $("btnImportHint").addEventListener("click", () => {
    renderList();
    toast("已刷新列表（当前为爬虫 mock 数据）");
  });
  $("btnBack").addEventListener("click", showList);
  $("btnSave").addEventListener("click", () => {
    if (state.currentId) saveProduct(state.currentId);
  });
  $("btnDownloadAll").addEventListener("click", () => {
    const p = state.products.find((x) => x.id === state.currentId);
    if (!p) return;
    const all = [...(p.images?.main || []), ...(p.images?.sku || [])];
    if (!all.length) {
      toast("该商品暂无本地图片", false);
      return;
    }
    all.forEach((img, i) => {
      setTimeout(() => downloadOne(img, p), i * 200);
    });
  });

  // hash route
  function routeFromHash() {
    const m = location.hash.match(/^#\/detail\/([^/]+)/);
    if (m) openDetail(decodeURIComponent(m[1]));
    else showList();
  }
  window.addEventListener("hashchange", routeFromHash);

  routeFromHash();
})();
