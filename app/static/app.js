const $ = (s) => document.querySelector(s);

const LABELS = {
  company: "公司",
  contact: "联系人",
  country: "国家/地区",
  product: "产品",
  quantity: "数量",
  target_price: "目标价",
  delivery: "交期",
  incoterm: "贸易条款",
  urgency: "紧急度",
  intent: "意图",
  confidence: "置信度",
  summary: "摘要",
};

const URGENCY_TEXT = { high: "高", medium: "中", low: "低" };

let currentId = null;

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

async function loadStats() {
  try {
    const s = await fetch("/api/stats").then((r) => r.json());
    $("#s-total").textContent = s.total;
    $("#s-drafted").textContent = s.drafted;
    $("#s-high").textContent = s.high_priority;
  } catch (e) {}
}

async function loadSamples() {
  try {
    const list = await fetch("/api/samples").then((r) => r.json());
    const box = $("#samples");
    box.innerHTML = "";
    list.forEach((s) => {
      const b = document.createElement("button");
      b.className = "chip";
      b.textContent = s.name;
      b.onclick = () => {
        $("#raw").value = s.text;
        $("#source").value = s.source;
        $("#raw").focus();
      };
      box.appendChild(b);
    });
  } catch (e) {}
}

async function loadList() {
  const items = await fetch("/api/inquiries").then((r) => r.json());
  const box = $("#list");
  box.innerHTML = "";
  if (!items.length) {
    box.innerHTML = '<div class="empty">还没有询盘。点上方样例或粘贴内容开始。</div>';
    return;
  }
  items.forEach((it) => {
    const div = document.createElement("div");
    div.className = "item" + (it.id === currentId ? " active" : "");
    div.dataset.id = it.id;
    const title = it.company || it.summary || "未命名询盘";
    const meta = [it.product, it.quantity, it.intent].filter(Boolean).join(" · ");
    div.innerHTML = `
      <div class="line1">
        <span class="title">${esc(title)}</span>
        <span class="tag ${esc(it.urgency)}">${URGENCY_TEXT[it.urgency] || "中"}</span>
      </div>
      <div class="meta">#${it.id} · ${esc(it.created_at)} ${meta ? "· " + esc(meta) : ""}</div>
    `;
    div.onclick = () => selectItem(it.id);
    box.appendChild(div);
  });
}

function fieldHtml(k, v) {
  const empty = v == null || v === "";
  return `<div class="field">
    <div class="k">${esc(LABELS[k] || k)}</div>
    <div class="v ${empty ? "none" : ""}">${empty ? "未识别" : esc(v)}</div>
  </div>`;
}

function renderDetail(item) {
  const box = $("#detail");
  const missing = (item.missing_info || [])
    .map((m) => `<span>${esc(m)}</span>`)
    .join("");
  const conf = Math.round((item.confidence || 0) * 100);
  const engineText = item.engine === "llm" ? "大模型解析" : "规则解析";

  box.innerHTML = `
    <div class="section-title" style="margin-top:0">
      询盘 #${item.id}
      <span class="badge">${esc(engineText)}</span>
      <span class="tag ${esc(item.urgency)}">${URGENCY_TEXT[item.urgency] || "中"}优先</span>
    </div>
    <div class="fields">
      ${fieldHtml("company", item.company)}
      ${fieldHtml("contact", item.contact)}
      ${fieldHtml("country", item.country)}
      ${fieldHtml("product", item.product)}
      ${fieldHtml("quantity", item.quantity)}
      ${fieldHtml("target_price", item.target_price)}
      ${fieldHtml("delivery", item.delivery)}
      ${fieldHtml("incoterm", item.incoterm)}
      ${fieldHtml("intent", item.intent)}
      ${fieldHtml("confidence", conf + "%")}
    </div>
    <div class="section-title">一句话摘要</div>
    <div style="font-size:13.5px;line-height:1.6">${esc(item.summary) || '<span style="color:#b6bdca">无</span>'}</div>
    <div class="section-title">缺失信息</div>
    <div class="missing">${missing || '<span style="background:#d1fae5;color:#059669;border-color:#a7f3d0">信息较完整</span>'}</div>
    <div class="section-title">回复草稿</div>
    ${item.draft
      ? `<pre class="draft" id="draft-text">${esc(item.draft)}</pre>
         <div class="actions">
           <button class="primary-btn" id="btn-copy">复制回复</button>
           <button id="btn-redraft">重新生成</button>
         </div>`
      : `<div class="empty" style="text-align:left;padding:6px 0">还没有草稿。点下方按钮生成一封可直接改用的回复。</div>
         <div class="actions"><button class="primary-btn" id="btn-draft">生成回复草稿</button></div>`}
    <div class="section-title">原文</div>
    <pre class="draft" style="max-height:200px;overflow:auto">${esc(item.raw_text)}</pre>
  `;

  const draftBtn = $("#btn-draft");
  if (draftBtn) draftBtn.onclick = () => doDraft(item.id);
  const redraftBtn = $("#btn-redraft");
  if (redraftBtn) redraftBtn.onclick = () => doDraft(item.id);
  const copyBtn = $("#btn-copy");
  if (copyBtn) copyBtn.onclick = () => copyDraft();
}

async function selectItem(id) {
  currentId = id;
  document.querySelectorAll(".item").forEach((el) => {
    el.classList.toggle("active", Number(el.dataset.id) === id);
  });
  const item = await fetch(`/api/inquiries/${id}`).then((r) => r.json());
  renderDetail(item);
}

async function doDraft(id) {
  const btn = $("#btn-draft") || $("#btn-redraft");
  if (btn) { btn.disabled = true; btn.textContent = "生成中…"; }
  try {
    const item = await fetch(`/api/inquiries/${id}/draft`, { method: "POST" }).then((r) => r.json());
    renderDetail(item);
    loadStats();
    loadList();
  } catch (e) {
    alert("生成失败：" + e.message);
  }
}

function copyDraft() {
  const el = $("#draft-text");
  if (!el) return;
  navigator.clipboard.writeText(el.textContent).then(
    () => { const b = $("#btn-copy"); if (b) { b.textContent = "已复制"; setTimeout(() => (b.textContent = "复制回复"), 1500); } },
    () => alert("复制失败，请手动选中复制")
  );
}

$("#btn-extract").onclick = async () => {
  const text = $("#raw").value.trim();
  if (!text) { alert("请先粘贴询盘内容"); return; }
  const btn = $("#btn-extract");
  btn.disabled = true;
  const old = btn.textContent;
  btn.textContent = "解析中…";
  try {
    const res = await fetch("/api/inquiries", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, source: $("#source").value }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "解析失败" }));
      throw new Error(err.detail || "解析失败");
    }
    const item = await res.json();
    $("#raw").value = "";
    await Promise.all([loadList(), loadStats()]);
    await selectItem(item.id);
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
};

(async function init() {
  loadSamples();
  loadList();
  loadStats();
  try {
    const h = await fetch("/api/health").then((r) => r.json());
    if (!h.llm) {
      $("#hint").textContent = "当前未配置大模型 Key，正在使用内置规则解析（可直接体验）。";
    } else {
      $("#hint").textContent = "已接入大模型，解析与草拟质量更高。";
    }
  } catch (e) {}
})();
