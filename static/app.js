/* Crypto Portfolio Tracker — vanilla JS dashboard (no external libs) */
"use strict";

/* ================= i18n ================= */
const I18N = {
  en: {
    brand: "Crypto Portfolio Tracker",
    btnSources: "Sources", btnRefresh: "Refresh", btnLang: "中文",
    viewDateTitle: "View last snapshot of a day",
    fbCategory: "Category", fbAll: "All", fbBtc: "BTC", fbEvm: "EVM", fbSol: "Solana", fbCex: "CEX",
    fbWallet: "Wallet", fbChain: "Chain", fbWalletAll: "All wallets", fbChainAll: "All chains",
    assetTitle: "Total Assets (USD) · Wallet Share",
    totalAssets: "Total Assets",
    walletsTitle: "Wallets", btnManageWallets: "Manage Wallets",
    walletMgmtTitle: "Wallet Management",
    walletMgmtDesc: "Adding/removing wallets only affects future fetches; already stored historical snapshots are never touched.",
    wlNamePh: "Name (e.g. evm-new)", wlTypeEvm: "EVM (DeBank + Hyperliquid)", wlTypeBtc: "BTC", wlTypeSol: "Solana",
    wlAddrPh: "Address", btnAddWallet: "+ Add Wallet", delete: "Delete", builtin: "Built-in",
    trendTitle: "Portfolio Trend",
    chainTitle: "Chain Distribution (USD)",
    tokensTitle: "Token Details", searchPh: "Search token / name / wallet / address…",
    hideZero: "Hide USD≈0", btnBlacklist: "Blacklist",
    thSymbol: "Token", thName: "Name", thChain: "Chain", thWallet: "Wallet",
    thAmount: "Amount", thPrice: "Price (USD)", thUsd: "Balance (USD)", thOp: "Action",
    blTitle: "Token Blacklist",
    blDesc: "Blacklisted tokens are excluded from total assets, wallets, chain distribution and trends (including historical snapshots).\nRemove entries below to restore.",
    blSymbolPh: "Symbol (e.g. ETHG)", blTokenIdPh: "Contract/mint address (exact, optional)",
    blNamePh: "Name substring (optional)", blChainPh: "Chain (optional, e.g. eth / sol / hyperliquid)",
    btnAddBl: "+ Add Blacklist", remove: "Remove", config: "Built-in config", user: "User",
    blBtn: "Blacklist",
    srcTitle: "Data Source Configuration",
    srcDesc: "All APIs (URL + keys) are configured here: each source can have multiple providers, tried in order with automatic failover to the next working one (last successful provider is remembered). Save to apply without restart.\nYou can also edit portfolio_sources.json directly (hot-reload). Env vars DEBANK_API_KEY / BIRDEYE_API_KEY / COINGECKO_API_KEY / SOLANA_RPC have highest priority.",
    btnSaveSrc: "Save & Apply", btnExport: "Export Config", btnImport: "Import Config",
    footer: "Data sources: DeBank (EVM), Hyperliquid L1, blockchain.info/mempool (BTC), Solana RPC (SOL/SPL/staked), Binance/Bybit/Backpack (CEX), CoinGecko/DexScreener/OKX (prices). Refresh saves the last snapshot of the day and builds trend charts.",
    noData: "No data yet — click Refresh to fetch all wallets (first run ~30-60s)",
    noMatch: "No matching tokens",
    noSnapshot: "No snapshots yet, please click Refresh",
    noHistory: "No trend data yet — snapshots accumulate as you refresh",
    noValue: "All wallets are 0, nothing to show",
    emptyWallets: "No data",
    items: (n) => n + " items",
    snapDate: "snapshot",
    recorded: "recorded at",
    loadingFailed: "Load failed: ", refreshFailed: "Refresh failed: ",
    refreshStart: "Starting refresh…", refreshing: "Refreshing…",
    doneUpdating: "Done, updating view…", saving: "Saving…",
    savedOk: "Saved and applied (portfolio_sources.json). Click Refresh to fetch with the new config.",
    saveFailed: "Save failed: ", exportDone: "Configuration exported", importDone: "Configuration imported and applied",
    importFailed: "Import failed: ", exportFailed: "Export failed: ",
    confirmBl: (s, n) => 'Add "' + s + (n && n !== s ? " / " + n : "") + '" to blacklist?\nBlacklisted tokens are removed from totals, wallets, chain distribution and trends (incl. history).',
    blAddFail: "Blacklist add failed: ", blRemoveFail: "Remove failed: ",
    confirmDelWallet: "Delete wallet?\nOnly stops fetching this wallet; stored historical snapshots are NOT deleted.",
    walletAddFail: "Add failed: ", walletRemoveFail: "Remove failed: ",
    atLeastOne: "At least one of Symbol / contract / name required",
    walletFields: "Please fill in wallet name and address",
    emptyList: "No entries yet.",
    filteredNote: "(filtered)",
    tabDashboard: "Dashboard", tabSettings: "Settings",
    profilesTitle: "Profiles (named configs)",
    profilesDesc: "Each profile is an independent config: sources (APIs + keys), wallets, blacklist and its own snapshot history. The default profile is the public template (public wallets, empty keys); your private wallets/keys belong to a named profile of your choice.",
    pfNamePh: "Profile name",
    pfCreateTpl: "Create from public template", pfCopy: "Duplicate current",
    useProfile: "Use", activeProfile: "active", deleteProfile: "Delete",
    confirmDelProfile: "Delete this profile? Its snapshots and configs will be removed.",
    profileSwitchFail: "Switch failed: ", profileCreateFail: "Create failed: ", profileDeleteFail: "Delete failed: ",
    schedTitle: "Scheduled Daily Refresh",
    schedDesc: "Runs inside the Python server process (not the browser page) - closing the web page does not stop it. Fires at the exact local minute; the server must be running at that time. Saving a schedule resets today's once-per-day marker, so a future time fires the same day.",
    schedEnable: "Enable", btnSaveSched: "Save Schedule", schedSaved: "Schedule saved", schedLastRun: "Last auto-run: ",
    paidBadge: "PAID", lastOk: "last ok", never: "never",
    cexDefaultHint: "Enter read-only keys to enable; empty rows are skipped.",
    providersHint: "providers (paid first, free fallback)",
    getKey: "get API key",
    debankHint: "EVM source = DeBank. Fields: base_url = API endpoint (the paid pro provider needs the pro host); key = AccessKey for the paid provider, leave empty to use the free public API; chain_list_url = DeBank-specific endpoint that lists all supported chains (switch to a mirror if blocked); chains = optional comma-separated chain ids to fetch (e.g. eth,bsc,arb,base), empty = all.",
    urlPh: "API URL", chainListPh: "chain list API (DeBank-specific)", chainsPh: "optional: eth,bsc,arb,base (default: all)",
    profileActive: "Profile",
    apiKey: "API Key", enabled: "启用", rpcLabel: "RPC 节点", splPricesLabel: "SPL 价格",
    birdeyeLabel: "Birdeye", srcKeyPh: "key（可选）", cexKeyPh: "api key", cexSecretPh: "api secret",
    apiKey: "API Key", enabled: "enabled", rpcLabel: "RPC nodes", splPricesLabel: "SPL prices",
    birdeyeLabel: "Birdeye", srcKeyPh: "key (optional)", cexKeyPh: "api key", cexSecretPh: "api secret",
    profileSwitchTitle: "切换配置文件",
    pfSwitchHint: "右上角下拉框可随时切换 Profile。",
    profileSwitchTitle: "Switch profile",
    pfSwitchHint: "Switch profiles from the dropdown in the top-right corner.",

    staked: "staked", perpEquity: "Perp Equity",
    avg: "Share",
  },
  zh: {
    brand: "Crypto Portfolio Tracker",
    btnSources: "数据源", btnRefresh: "刷新数据", btnLang: "EN",
    viewDateTitle: "查看某一天的最后一次快照",
    fbCategory: "分类", fbAll: "全部", fbBtc: "BTC", fbEvm: "EVM", fbSol: "Solana", fbCex: "CEX",
    fbWallet: "钱包", fbChain: "网络", fbWalletAll: "全部钱包", fbChainAll: "全部网络",
    assetTitle: "总资产（USD）· 各钱包占比",
    totalAssets: "总资产",
    walletsTitle: "钱包", btnManageWallets: "⚙ 钱包管理",
    walletMgmtTitle: "钱包管理",
    walletMgmtDesc: "增加/删除钱包仅影响之后的抓取；已存储的历史快照数据不受影响。",
    wlNamePh: "名称（如 evm-new）", wlTypeEvm: "EVM（DeBank + Hyperliquid）", wlTypeBtc: "BTC", wlTypeSol: "Solana",
    wlAddrPh: "地址", btnAddWallet: "＋ 添加钱包", delete: "删除", builtin: "内置",
    trendTitle: "资产趋势",
    chainTitle: "网络分布（USD）",
    tokensTitle: "代币明细", searchPh: "搜索代币 / 名称 / 钱包 / 地址…",
    hideZero: "隐藏 USD≈0", btnBlacklist: "🛡 黑名单管理",
    thSymbol: "代币", thName: "名称", thChain: "网络", thWallet: "钱包",
    thAmount: "数量", thPrice: "单价（USD）", thUsd: "余额（USD）", thOp: "操作",
    blTitle: "代币黑名单",
    blDesc: "黑名单代币将从总资产、各钱包、网络分布、趋势图（含历史快照）中剔除。\n可在下方移除恢复。",
    blSymbolPh: "Symbol（如 ETHG）", blTokenIdPh: "合约/铸币地址（精确匹配，可选）",
    blNamePh: "名称子串（可选）", blChainPh: "网络（可选，如 eth / sol / hyperliquid）",
    btnAddBl: "＋ 添加黑名单", remove: "移除", config: "内置配置", user: "用户",
    blBtn: "拉黑",
    srcTitle: "数据源配置",
    srcDesc: "所有 API（URL + key）集中配置：每个 source 可配置多个 provider，抓取时按顺序尝试，失败自动切换下一个（记住最近成功者）。保存即生效，无需重启。\n也可直接编辑 portfolio_sources.json（热生效）。环境变量 DEBANK_API_KEY / BIRDEYE_API_KEY / COINGECKO_API_KEY / SOLANA_RPC 优先级最高。",
    btnSaveSrc: "💾 保存并生效", btnExport: "导出配置", btnImport: "导入配置",
    footer: "数据来源：DeBank（EVM）、Hyperliquid L1、blockchain.info/mempool（BTC）、Solana RPC（SOL/SPL/质押）、Binance/Bybit/Backpack（CEX）、CoinGecko/DexScreener/OKX（价格）。刷新即保存当天最后一次快照并形成趋势图。",
    noData: "暂无数据，请点击右上角「刷新数据」抓取全部钱包（首次约需 30~60 秒）",
    noMatch: "没有符合条件的代币",
    noSnapshot: "暂无快照，请先点击「刷新数据」",
    noHistory: "暂无趋势数据，刷新后生成",
    noValue: "所有钱包余额均为 0，暂无可展示占比",
    emptyWallets: "暂无数据",
    items: (n) => "共 " + n + " 项",
    snapDate: "快照",
    recorded: "记录于",
    loadingFailed: "加载失败：", refreshFailed: "刷新失败：",
    refreshStart: "开始刷新…", refreshing: "刷新中…",
    doneUpdating: "完成，正在更新视图…", saving: "保存中…",
    savedOk: "✅ 已保存并生效（portfolio_sources.json）。点「刷新数据」用新配置抓取。",
    saveFailed: "保存失败：", exportDone: "配置已导出", importDone: "配置已导入并生效",
    importFailed: "导入失败：", exportFailed: "导出失败：",
    confirmBl: (s, n) => '将「' + s + (n && n !== s ? " / " + n : "") + '」加入黑名单？\n黑名单代币将从总资产、各钱包、网络分布、趋势图中剔除（含历史快照）。',
    blAddFail: "拉黑失败：", blRemoveFail: "移除失败：",
    confirmDelWallet: "删除钱包？\n仅停止后续抓取该钱包，已存储的历史快照数据不会被删除。",
    walletAddFail: "添加失败：", walletRemoveFail: "删除失败：",
    atLeastOne: "至少填写 Symbol / 合约地址 / 名称 之一",
    walletFields: "请填写钱包名称和地址",
    emptyList: "暂无条目。",
    filteredNote: "（筛选后）",
    tabDashboard: "首页", tabSettings: "设置",
    profilesTitle: "配置文件（多 Profile）",
    profilesDesc: "每个 Profile 是独立配置：数据源（API+key）、钱包、黑名单和各自的快照历史。默认 Profile 是公开模板（公开钱包、空 key）；你的私人钱包和 key 属于独立命名的私有 Profile。",
    pfNamePh: "Profile 名称",
    pfCreateTpl: "从公开模板创建", pfCopy: "复制当前",
    useProfile: "使用", activeProfile: "当前", deleteProfile: "删除",
    confirmDelProfile: "删除该 Profile？其快照与配置将一并删除。",
    profileSwitchFail: "切换失败：", profileCreateFail: "创建失败：", profileDeleteFail: "删除失败：",
    schedTitle: "定时每日刷新",
    schedDesc: "定时器运行在 Python 服务进程内（与网页无关）——关闭网页不影响它。在设定分钟的整点触发；那一刻服务必须在运行。保存定时会重置当天的一次性标记：新时间若在今天之后，当天就会执行。",
    schedEnable: "启用", btnSaveSched: "保存定时", schedSaved: "定时已保存", schedLastRun: "上次自动执行：",
    paidBadge: "付费", lastOk: "上次成功", never: "从未",
    cexDefaultHint: "填入只读 key 即启用；空行自动跳过。",
    providersHint: "providers（付费优先，免费兜底）",
    getKey: "获取 API key",
    debankHint: "EVM 数据源 = DeBank。字段说明：base_url = API 地址（付费 pro 需要 pro 域名）；key = 付费源的 AccessKey，留空则走免费公开 API；chain_list_url = DeBank 特有的链列表接口（被墙/失效可换镜像）；chains = 可选，逗号分隔要抓取的链（如 eth,bsc,arb,base），留空抓全部。",
    urlPh: "API URL", chainListPh: "链列表接口（Debank 特有）", chainsPh: "可选：eth,bsc,arb,base（默认全部）",
    profileActive: "Profile",
    apiKey: "API Key", enabled: "启用", rpcLabel: "RPC 节点", splPricesLabel: "SPL 价格",
    birdeyeLabel: "Birdeye", srcKeyPh: "key（可选）", cexKeyPh: "api key", cexSecretPh: "api secret",
    apiKey: "API Key", enabled: "enabled", rpcLabel: "RPC nodes", splPricesLabel: "SPL prices",
    birdeyeLabel: "Birdeye", srcKeyPh: "key (optional)", cexKeyPh: "api key", cexSecretPh: "api secret",
    profileSwitchTitle: "切换配置文件",
    pfSwitchHint: "右上角下拉框可随时切换 Profile。",
    profileSwitchTitle: "Switch profile",
    pfSwitchHint: "Switch profiles from the dropdown in the top-right corner.",

    staked: "质押", perpEquity: "永续权益",
    avg: "占比",
  },
};
let theme = "dark";
try { theme = localStorage.getItem("pt_theme") || "dark"; } catch (e) { /* ignore */ }
document.documentElement.setAttribute("data-theme", theme);
const themeBtnIcon = () => theme === "light" ? "☀" : "☾";

let lang = "en";
try { lang = localStorage.getItem("pt_lang") || "en"; } catch (e) { /* ignore */ }

const APP_VERSION = "20260822b";
console.log("[dsh-crypto-portfolio] app v" + APP_VERSION);

const t = (key, ...args) => {
  const d = I18N[lang] || I18N.en;
  let v = d[key] !== undefined ? d[key] : (I18N.en[key] !== undefined ? I18N.en[key] : key);
  if (typeof v === "function") v = v(...args);
  return v;
};
function applyI18n() {
  const v = document.getElementById("versionTag");
  if (v) v.textContent = "v" + APP_VERSION;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
  document.title = t("brand");
  $("btnLang").textContent = lang === "zh" ? "EN" : "中文";
  const tb = document.getElementById("btnTheme");
  if (tb) tb.textContent = themeBtnIcon();
}

/* ---------------- helpers ---------------- */
const _inert = {
  addEventListener() {}, appendChild() {}, insertAdjacentHTML() {},
  querySelectorAll: () => [], setAttribute() {}, getContext: () => _inert,
  classList: { toggle() {}, add() {}, remove() {}, contains() { return false; } },
  style: {}, dataset: {}, options: [], files: [],
  value: "", textContent: "", innerHTML: "", title: "", href: "", download: "",
  click() {}, scrollIntoView() {}, focus() {}, remove() {},
};
const $ = (id) => document.getElementById(id) || _inert;
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
));

function fmtUsdFull(v) {
  if (v == null || isNaN(v)) return "--";
  return "$" + Number(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtUsd(v) {
  if (v == null || isNaN(v)) return "--";
  v = Number(v);
  if (v >= 1e9) return "$" + (v / 1e9).toFixed(2) + "B";
  if (v >= 1e6) return "$" + (v / 1e6).toFixed(2) + "M";
  if (v >= 1e3) return "$" + v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (v >= 1) return "$" + v.toFixed(2);
  if (v > 0) return "$" + v.toPrecision(3);
  return "$0.00";
}
function fmtAmount(v) {
  if (v == null || isNaN(v)) return "--";
  v = Number(v);
  if (v === 0) return "0";
  if (Math.abs(v) >= 1e6) return v.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (Math.abs(v) >= 1) return v.toLocaleString("en-US", { maximumFractionDigits: 4 });
  return v.toPrecision(4).replace(/\.?0+$/, "");
}
function fmtPct(v) {
  if (v == null || isNaN(v)) return "";
  return (v > 0 ? "+" : "") + v.toFixed(2) + "%";
}
function shortAddr(a, n = 10) {
  if (!a) return "";
  return a.length <= 2 * n ? a : a.slice(0, n) + "…" + a.slice(-6);
}

const PALETTE = ["#58a6ff", "#f0b95c", "#7ee787", "#d2a8ff", "#ff7b72", "#56d4dd",
                 "#ffa657", "#bc8cff", "#3fb950", "#e3b341", "#79c0ff", "#f85149"];
const TYPE_LABEL = { evm: "EVM", btc: "BTC", sol: "SOL", cex: "CEX" };

/* ---------------- state ---------------- */
const state = {
  wallets: [],          // config (with source/index)
  chains: {},           // id -> name
  view: null,           // current snapshot view (unfiltered)
  tokens: [],           // token rows for selected date (unfiltered)
  history: null,        // trend data (unfiltered)
  selectedDate: null,
  sortKey: "usd", sortDir: -1,
  filters: { category: "all", wallet: "", chain: "", search: "", hideZero: true },
  series: {},
  sourcesCfg: null,
  sourcesLastOk: {},
  activeProfile: "",
  dates: [],
};

/* ---------------- api ---------------- */
async function api(path) {
  const r = await fetch(path);
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).error || msg; } catch (e) { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}
async function postJSON(path, body) {
  const r = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    let msg = r.statusText;
    try { msg = (await r.json()).error || msg; } catch (e) { /* ignore */ }
    throw new Error(msg);
  }
  return r.json();
}

/* ---------------- init ---------------- */
function refreshLanguage() {
  applyI18n();
  fillDateSelect(state.dates || []);
  fillFilterSelects();
  // re-set dynamic date/updated texts
  if (state.view) {
    $("tokenDate").textContent = "(" + t("snapDate") + " " + state.selectedDate + ")";
    $("lastUpdated").textContent = t("snapDate") + " " + state.selectedDate + " · " + t("recorded") + " " +
      (state.view.created_at || "").replace("T", " ");
  }
  renderAll();
  if (!$("pageSettings").classList.contains("hidden")) renderSettings();
}

async function init() {
  bindEvents();
  applyI18n();
  try {
    const [cfg, history] = await Promise.all([api("/api/wallets"), api("/api/history?days=0")]);
    state.wallets = cfg.wallets;
    state.chains = cfg.chains || {};
    state.history = history;
    const dates = history.dates;
    state.dates = dates;
    fillDateSelect(dates);
    if (dates.length) {
      state.selectedDate = dates[dates.length - 1];
      $("dateSelect").value = state.selectedDate;
      await loadDate(state.selectedDate);
    } else {
      showEmpty();
    }
    renderChart();
    fillFilterSelects();
    renderBlacklist();
    renderWalletMgmt();
    renderProfiles();   // populate header profile dropdown
  } catch (e) {
    showError(t("loadingFailed") + e.message);
  }
}

function bindEvents() {
  $("btnRefresh").addEventListener("click", refresh);
  $("btnTheme").addEventListener("click", () => {
    theme = theme === "light" ? "dark" : "light";
    try { localStorage.setItem("pt_theme", theme); } catch (e) { /* ignore */ }
    document.documentElement.setAttribute("data-theme", theme);
    $("btnTheme").textContent = themeBtnIcon();
  });
  $("btnLang").addEventListener("click", () => {
    lang = lang === "zh" ? "en" : "zh";
    try { localStorage.setItem("pt_lang", lang); } catch (e) { /* ignore */ }
    refreshLanguage();
  });
  $("dateSelect").addEventListener("change", (e) => loadDate(e.target.value));
  // global filters
  $("filterCategory").addEventListener("change", (e) => {
    state.filters.category = e.target.value;
    if (state.filters.wallet && !walletInCategory(state.filters.wallet, state.filters.category)) {
      state.filters.wallet = "";
    }
    fillFilterSelects();
    renderAll();
  });
  $("filterWallet").addEventListener("change", (e) => { state.filters.wallet = e.target.value; renderAll(); });
  $("filterChain").addEventListener("change", (e) => { state.filters.chain = e.target.value; renderAll(); });
  // table locals
  $("search").addEventListener("input", (e) => { state.filters.search = e.target.value.trim().toLowerCase(); renderTable(); });
  $("hideZero").addEventListener("change", (e) => { state.filters.hideZero = e.target.checked; renderTable(); });
  document.querySelectorAll("#tokenTable th").forEach((th) => {
    th.addEventListener("click", () => {
      const k = th.dataset.key;
      if (state.sortKey === k) state.sortDir *= -1;
      else { state.sortKey = k; state.sortDir = -1; }
      document.querySelectorAll("#tokenTable th").forEach((x) => x.classList.remove("sorted"));
      th.classList.add("sorted");
      renderTable();
    });
  });
  // tabs
  document.querySelectorAll(".tabs .tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs .tab").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      const page = btn.dataset.tab;
      $("pageDashboard").classList.toggle("hidden", page !== "pageDashboard");
      $("pageSettings").classList.toggle("hidden", page !== "pageSettings");
      $("filterbar").classList.toggle("hidden", page !== "pageDashboard");
      if (page === "pageSettings") renderSettings();
    });
  });
  // profiles
  $("btnSaveSchedule").addEventListener("click", async () => {
    try {
      await postJSON("/api/schedule", {
        enabled: $("schedEnabled").checked,
        time: $("schedTime").value || "09:00",
      });
      $("schedMsg").textContent = "✓ " + t("schedSaved");
      setTimeout(() => { $("schedMsg").textContent = ""; }, 4000);
      await renderSchedule();   // refreshes enabled/time/last-run, keeps schedMsg
    } catch (e) { $("schedMsg").textContent = t("saveFailed") + e.message; }
  });
  $("btnPfCreateTpl").addEventListener("click", async () => {
    const name = $("pfNewName").value.trim();
    if (!name) { alert(t("pfNamePh")); return; }
    try {
      await postJSON("/api/profiles", { action: "create", name, from_template: true });
      $("pfNewName").value = "";
      await renderSettings();
    } catch (e) { alert(t("profileCreateFail") + e.message); }
  });
  $("btnPfCopy").addEventListener("click", async () => {
    const name = $("pfNewName").value.trim();
    if (!name) { alert(t("pfNamePh")); return; }
    try {
      await postJSON("/api/profiles", { action: "create", name, copy_from: state.activeProfile });
      $("pfNewName").value = "";
      await renderSettings();
    } catch (e) { alert(t("profileCreateFail") + e.message); }
  });
  $("profileSelect").addEventListener("change", async (e) => {
    const name = e.target.value;
    if (!name || name === state.activeProfile) return;
    try {
      await postJSON("/api/profiles", { action: "switch", name });
      await reloadViewData();     // dashboard now shows the new profile
      await renderSettings();
    } catch (err) { alert(t("profileSwitchFail") + err.message); }
  });
  $("profileList").addEventListener("click", async (ev) => {
    const btn = ev.target.closest("button[data-pf-action]");
    if (!btn) return;
    const name = btn.dataset.pfName;
    if (!confirm(t("confirmDelProfile"))) return;
    try {
      await postJSON("/api/profiles", { action: "delete", name });
      await renderSettings();
    } catch (err) { alert(t("profileDeleteFail") + err.message); }
  });
  // sources config
  $("btnSaveSources").addEventListener("click", async () => {
    $("sourcesMsg").textContent = t("saving");
    try {
      await postJSON("/api/sources", { config: state.sourcesCfg });
      $("sourcesMsg").textContent = t("savedOk");
      renderSources();
    } catch (e) { $("sourcesMsg").textContent = t("saveFailed") + e.message; }
  });
  $("btnExportConfig").addEventListener("click", exportConfig);
  $("btnImportConfig").addEventListener("click", () => $("importFile").click());
  $("importFile").addEventListener("change", importConfig);
  // blacklist (settings page)
  $("btnAddBlacklist").addEventListener("click", async () => {
    const entry = {
      symbol: $("blSymbol").value.trim(),
      token_id: $("blTokenId").value.trim(),
      name: $("blName").value.trim(),
      chain: $("blChain").value.trim(),
      note: "UI",
    };
    if (!entry.symbol && !entry.token_id && !entry.name) { alert(t("atLeastOne")); return; }
    try {
      await postJSON("/api/blacklist", { entry });
      ["blSymbol", "blTokenId", "blName", "blChain"].forEach((id) => { $(id).value = ""; });
      await reloadViewData();
    } catch (e) { alert(t("blAddFail") + e.message); }
  });
  // wallet management (settings page)
  $("btnAddWallet").addEventListener("click", async () => {
    const wallet = {
      name: $("wlName").value.trim(),
      type: $("wlType").value,
      address: $("wlAddress").value.trim(),
    };
    if (!wallet.name || !wallet.address) { alert(t("walletFields")); return; }
    try {
      await postJSON("/api/wallets", { wallet });
      $("wlName").value = "";
      $("wlAddress").value = "";
      await reloadViewData();
    } catch (e) { alert(t("walletAddFail") + e.message); }
  });
  // per-row blacklist button (event delegation)
  $("tokenBody").addEventListener("click", async (ev) => {
    const btn = ev.target.closest(".bl-btn");
    if (!btn) return;
    if (!confirm(t("confirmBl", btn.dataset.symbol, btn.dataset.name))) return;
    try {
      await postJSON("/api/blacklist", {
        entry: { symbol: btn.dataset.symbol, name: btn.dataset.name,
                 token_id: btn.dataset.tokenId, chain: btn.dataset.chain, note: "UI" },
      });
      await reloadViewData();
    } catch (e) { alert(t("blAddFail") + e.message); }
  });
}

function walletInCategory(name, category) {
  if (category === "all") return true;
  const v = state.view;
  if (v) {
    const w = v.wallets.find((x) => x.wallet === name);
    if (w) return w.type === category;
  }
  const c = state.wallets.find((x) => x.name === name);
  return c ? c.type === category : true;
}

function fillDateSelect(dates) {
  const sel = $("dateSelect");
  sel.innerHTML = "";
  for (const d of dates) {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d + " (" + t("snapDate") + ")";
    sel.appendChild(o);
  }
}

function chainName(id) {
  return state.chains[id] || id || "—";
}

/* ---------------- filtered views ---------------- */
function filteredView() {
  if (!state.view) return null;
  const f = state.filters;
  const walletSet = state.view.wallets.filter((w) =>
    (f.category === "all" || w.type === f.category) &&
    (!f.wallet || w.wallet === f.wallet));
  const wnames = new Set(walletSet.map((w) => w.wallet));
  const tokens = (state.tokens || []).filter((x) =>
    wnames.has(x.wallet) && (!f.chain || x.chain === f.chain));
  const byWallet = {}, byChain = {};
  let total = 0;
  for (const x of tokens) {
    byWallet[x.wallet] = (byWallet[x.wallet] || 0) + x.usd;
    byChain[x.chain] = (byChain[x.chain] || 0) + x.usd;
    total += x.usd;
  }
  const wallets = walletSet.map((w) => ({
    wallet: w.wallet, address: w.address, type: w.type,
    total_usd: byWallet[w.wallet] || 0,
    token_count: tokens.filter((x) => x.wallet === w.wallet).length,
  }));
  return { date: state.view.date, created_at: state.view.created_at,
           total_usd: total, by_chain: byChain, wallets,
           filtered: f.category !== "all" || !!f.wallet || !!f.chain };
}

function filteredHistory() {
  const h = state.history;
  if (!h) return h;
  const f = state.filters;
  const typeMap = {};
  (state.wallets || []).forEach((w) => { typeMap[w.name] = w.type; });
  if (state.view) state.view.wallets.forEach((w) => { typeMap[w.wallet] = w.type; });
  const names = Object.keys(h.wallets).filter((n) =>
    (f.category === "all" || typeMap[n] === f.category) &&
    (!f.wallet || n === f.wallet));
  const totals = h.dates.map((_, i) =>
    names.reduce((s, n) => s + (h.wallets[n][i] || 0), 0));
  const wallets = {};
  names.forEach((n) => { wallets[n] = h.wallets[n]; });
  const chains = {};
  if (f.chain) {
    if (h.chains[f.chain]) chains[f.chain] = h.chains[f.chain];
  } else {
    Object.keys(h.chains).forEach((c) => { chains[c] = h.chains[c]; });
  }
  return { dates: h.dates, totals, wallets, chains };
}

/* ---------------- load & render ---------------- */
async function loadDate(date) {
  state.selectedDate = date;
  try {
    const [view, tokens] = await Promise.all([
      api("/api/snapshot?date=" + encodeURIComponent(date)),
      api("/api/tokens?date=" + encodeURIComponent(date)),
    ]);
    state.view = view;
    state.tokens = tokens.tokens;
    renderAll();
    $("tokenDate").textContent = "(" + t("snapDate") + " " + date + ")";
    $("lastUpdated").textContent = t("snapDate") + " " + date + " · " + t("recorded") + " " +
      (view.created_at || "").replace("T", " ");
  } catch (e) {
    showError(t("loadingFailed") + e.message);
  }
}

function renderAll() {
  renderSummary();
  renderWalletCards();
  renderChainBars();
  renderPie();
  renderTable();
  renderChart();
}

function renderSummary() {
  const v = filteredView();
  if (!v) return;
  $("totalUsd").textContent = fmtUsdFull(v.total_usd);
  const ch = $("totalChange");
  if (v.filtered) {
    ch.className = "change";
    ch.textContent = t("filteredNote");
  } else if (state.view.change_usd != null) {
    const up = state.view.change_usd >= 0;
    ch.className = "change " + (up ? "up" : "down");
    ch.textContent = (up ? "▲ +" : "▼ ") + fmtUsd(Math.abs(state.view.change_usd))
      + "  (" + fmtPct(state.view.change_pct || 0) + ")   vs " + state.view.prev_date;
  } else {
    ch.className = "change";
    ch.textContent = "—";
  }
}

function renderWalletCards() {
  const wrap = $("walletCards");
  wrap.innerHTML = "";
  const v = filteredView();
  if (!v) return;
  $("walletCount").textContent = "(" + v.wallets.length + ")";
  v.wallets.forEach((w) => {
    const card = document.createElement("div");
    card.className = "card";
    const wlogo = w.type === "btc" ? "btc" : w.type === "sol" ? "sol" : w.type === "cex" ? "evm" : "evm";
    card.innerHTML =
      '<div class="w-name"><img class="logo-img" src="/static/logos/' + wlogo + '.svg" alt="">' + esc(w.wallet) +
        ' <span class="badge ' + esc(w.type) + '">' + (TYPE_LABEL[w.type] || w.type) + "</span></div>" +
      '<div class="w-usd">' + fmtUsd(w.total_usd) + "</div>" +
      '<div class="w-addr">' + esc(shortAddr(w.address, 10)) + "</div>" +
      '<div class="w-sub">' + t("items", w.token_count) + "</div>";
    card.addEventListener("click", () => {
      state.filters.wallet = w.wallet;
      $("filterWallet").value = w.wallet;
      renderAll();
      $("tokenTable").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    wrap.appendChild(card);
  });
}

function renderChainBars() {
  const wrap = $("chainBars");
  wrap.innerHTML = "";
  const v = filteredView();
  if (!v) return;
  const entries = Object.entries(v.by_chain).sort((a, b) => b[1] - a[1]).filter(([, val]) => val > 0);
  if (!entries.length) { wrap.innerHTML = '<span class="hint">' + t("noData") + "</span>"; return; }
  const total = entries.reduce((s, [, val]) => s + val, 0);
  entries.forEach(([cid, usd], i) => {
    const pct = total ? (usd / total * 100) : 0;
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML =
      '<div class="bar-label" title="' + esc(chainName(cid)) + '"><img class="logo-img" src="' + chainLogo(cid) + '" alt="">' + esc(chainName(cid)) + "</div>" +
      '<div class="bar-track"><div class="bar-fill" style="width:' + pct.toFixed(1) +
        '%;background:' + PALETTE[i % PALETTE.length] + '"></div></div>' +
      '<div class="bar-val">' + fmtUsd(usd) + " · " + pct.toFixed(1) + "%</div>";
    wrap.appendChild(row);
  });
}

function renderTable() {
  const tbody = $("tokenBody");
  const f = state.filters;
  let rows = (state.tokens || []).filter((x) => {
    if (f.hideZero && (x.usd || 0) === 0) return false;
    if (f.category !== "all" && !walletInCategory(x.wallet, f.category)) return false;
    if (f.wallet && x.wallet !== f.wallet) return false;
    if (f.chain && x.chain !== f.chain) return false;
    if (f.search) {
      const hay = (x.symbol + " " + x.name + " " + x.wallet + " " + x.chain).toLowerCase();
      if (!hay.includes(f.search)) return false;
    }
    return true;
  });
  rows = rows.slice().sort((a, b) => {
    let va = a[state.sortKey], vb = b[state.sortKey];
    if (typeof va === "string") { va = va.toLowerCase(); vb = vb.toLowerCase(); }
    if (va === vb) return 0;
    return (va > vb ? 1 : -1) * state.sortDir;
  });
  $("tokenCount").textContent = t("items", rows.length);
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">' +
      (state.view ? t("noMatch") : t("noData")) + "</td></tr>";
    return;
  }
  tbody.innerHTML = rows.map((x) =>
    '<tr>' +
    '<td class="sym">' + (x.logo ? '<img src="' + esc(x.logo) + '" loading="lazy" onerror="this.style.visibility=\'hidden\'">' : '<span class="dot"></span>')
      + esc(x.symbol) + "</td>" +
    '<td class="muted">' + esc(x.name || "") + "</td>" +
    '<td><span class="chain-tag"><img class="logo-img" src="' + chainLogo(x.chain) + '" alt="">' + esc(chainName(x.chain)) + "</span></td>" +
    '<td>' + esc(x.wallet) + "</td>" +
    '<td class="num amount">' + fmtAmount(x.amount) + "</td>" +
    '<td class="num">' + fmtUsd(x.price) + "</td>" +
    '<td class="num">' + fmtUsd(x.usd) + "</td>" +
    '<td class="op"><button class="bl-btn" data-wallet="' + esc(x.wallet) + '"' +
      ' data-symbol="' + esc(x.symbol) + '" data-name="' + esc(x.name || "") + '"' +
      ' data-token-id="' + esc(x.token_id || "") + '" data-chain="' + esc(x.chain) + '">' + t("blBtn") + "</button></td>" +
    "</tr>"
  ).join("");
}

/* ---------------- pie chart ---------------- */
function renderPie() {
  const v = filteredView();
  const items = (v && v.wallets ? v.wallets : [])
    .map((w, i) => ({ label: w.wallet, value: w.total_usd || 0, color: PALETTE[i % PALETTE.length] }))
    .filter((it) => it.value > 0);
  const total = (v && v.total_usd) || 0;
  drawPie($("walletPie"), items, total);

  const sorted = items.slice().sort((a, b) => b.value - a.value);
  $("pieLegend").innerHTML = sorted.length
    ? sorted.map((it) => {
        const pct = total ? (it.value / total * 100) : 0;
        return '<div class="legend-row" data-wallet="' + esc(it.label) + '">' +
          '<span class="t-dot" style="background:' + it.color + '"></span>' +
          '<span class="lg-name">' + esc(it.label) + "</span>" +
          '<span class="lg-val">' + fmtUsd(it.value) + "</span>" +
          '<span class="lg-pct">' + pct.toFixed(1) + "%</span></div>";
      }).join("")
    : '<div class="legend-empty">' + t("noValue") + "</div>";
  $("pieLegend").querySelectorAll(".legend-row").forEach((el) => {
    el.addEventListener("click", () => {
      state.filters.wallet = el.dataset.wallet;
      $("filterWallet").value = el.dataset.wallet;
      renderAll();
      $("tokenTable").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

function drawPie(canvas, items, total) {
  const tip = $("pieTip");
  const dpr = window.devicePixelRatio || 1;
  const box = canvas.parentElement;
  const size = box.clientWidth || 250;
  canvas.width = size * dpr;
  canvas.height = size * dpr;
  canvas.style.width = size + "px";
  canvas.style.height = size + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, size, size);

  const cx = size / 2, cy = size / 2;
  const outer = size / 2 - 8;
  const inner = outer * 0.58;
  let hovered = -1;

  function draw(hIdx) {
    ctx.clearRect(0, 0, size, size);
    if (!items.length || total <= 0) {
      ctx.strokeStyle = "rgba(120,140,170,.25)";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(cx, cy, inner + (outer - inner) / 2, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fillStyle = "#8b98a9";
      ctx.font = "600 13px -apple-system, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(t("noData"), cx, cy);
      return;
    }
    let a = -Math.PI / 2;
    items.forEach((it, i) => {
      const sweep = (it.value / total) * Math.PI * 2;
      const pop = i === hIdx ? 5 : 0;
      ctx.beginPath();
      ctx.arc(cx, cy, outer + pop, a, a + sweep);
      ctx.arc(cx, cy, inner + pop, a + sweep, a, true);
      ctx.closePath();
      ctx.fillStyle = it.color;
      ctx.fill();
      if (i === hIdx) {
        ctx.strokeStyle = "rgba(255,255,255,.85)";
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      a += sweep;
    });
    ctx.fillStyle = "#e6edf3";
    ctx.font = "700 14px -apple-system, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(fmtUsd(total), cx, cy - 8);
    ctx.fillStyle = "#8b98a9";
    ctx.font = "10.5px -apple-system, sans-serif";
    ctx.fillText(t("totalAssets"), cx, cy + 12);
  }

  function hitTest(mx, my) {
    const dx = mx - cx, dy = my - cy;
    const r = Math.hypot(dx, dy);
    if (r < inner || r > outer) return -1;
    let ang = Math.atan2(dy, dx);
    if (ang < -Math.PI / 2) ang += Math.PI * 2;
    let a = -Math.PI / 2;
    for (let i = 0; i < items.length; i++) {
      const sweep = (items[i].value / total) * Math.PI * 2;
      if (ang >= a && ang < a + sweep) return i;
      a += sweep;
    }
    return items.length - 1;
  }

  draw(-1);
  canvas.onmousemove = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
    const idx = hitTest(mx, my);
    if (idx !== hovered) { hovered = idx; draw(idx); }
    if (idx >= 0) {
      const it = items[idx];
      const pct = total ? (it.value / total * 100) : 0;
      tip.innerHTML =
        '<div class="t-row"><span><span class="t-dot" style="background:' + it.color + '"></span>' +
        esc(it.label) + "</span><span>" + fmtUsd(it.value) + "</span></div>" +
        '<div class="t-date">' + t("avg") + " " + pct.toFixed(1) + "%</div>";
      tip.classList.remove("hidden");
      const tipW = tip.offsetWidth, tipH = tip.offsetHeight;
      let tx = mx + 14, ty = my - tipH - 10;
      if (tx + tipW > size - 4) tx = mx - tipW - 14;
      if (ty < 4) ty = my + 14;
      tip.style.left = tx + "px";
      tip.style.top = ty + "px";
    } else {
      tip.classList.add("hidden");
    }
  };
  canvas.onmouseleave = () => { hovered = -1; draw(-1); tip.classList.add("hidden"); };
}

/* ---------------- chart ---------------- */
function renderChart() {
  const h = filteredHistory();
  if (!h || !h.dates.length) {
    $("seriesToggle").innerHTML = '<span class="hint">' + t("noHistory") + "</span>";
    return;
  }
  const series = [];
  series.push({ label: t("totalAssets"), color: "#58a6ff", values: h.totals });
  for (const name of Object.keys(h.wallets)) {
    series.push({ label: name, color: PALETTE[(series.length) % PALETTE.length], values: h.wallets[name] });
  }
  state.series = {};
  series.forEach((s) => { state.series[s.label] = true; });

  const wrap = $("seriesToggle");
  wrap.innerHTML = series.map((s, i) =>
    '<label><input type="checkbox" data-i="' + i + '" checked style="accent-color:' + s.color + '">' +
    '<span class="t-dot" style="background:' + s.color + '"></span>' + esc(s.label) + "</label>"
  ).join("");
  wrap.querySelectorAll("input").forEach((cb) => {
    cb.addEventListener("change", (e) => {
      const s = series[Number(e.target.dataset.i)];
      state.series[s.label] = e.target.checked;
      drawLineChart($("trendChart"), h.dates, series, state.series);
    });
  });
  drawLineChart($("trendChart"), h.dates, series, state.series);
}

function drawLineChart(canvas, labels, series, visible) {
  const wrap = canvas.parentElement;
  const tip = $("chartTip");
  const dpr = window.devicePixelRatio || 1;
  const W = wrap.clientWidth || 600;
  const H = canvas.clientHeight || 320;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + "px";
  canvas.style.height = H + "px";
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);

  const pad = { l: 78, r: 18, t: 14, b: 30 };
  const pw = W - pad.l - pad.r;
  const ph = H - pad.t - pad.b;
  const shown = series.filter((s) => visible[s.label] !== false);
  const allVals = shown.flatMap((s) => s.values).filter((v) => v != null && isFinite(v));
  let max = allVals.length ? Math.max(...allVals, 1) : 1;
  max = max * 1.08;
  const nice = niceMax(max);
  max = nice.max;
  const ticks = nice.ticks;

  const X = (i) => pad.l + (labels.length <= 1 ? pw / 2 : (i / (labels.length - 1)) * pw);
  const Y = (v) => pad.t + ph - (v / max) * ph;

  ctx.font = "11px -apple-system, sans-serif";
  ctx.textBaseline = "middle";
  for (const tv of ticks) {
    const y = Y(tv);
    ctx.strokeStyle = "rgba(120,140,170,.14)";
    ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
    ctx.fillStyle = "#8b98a9";
    ctx.textAlign = "right";
    ctx.fillText("$" + compactNum(tv), pad.l - 8, y);
  }
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  const step = Math.max(1, Math.ceil(labels.length / 10));
  labels.forEach((d, i) => {
    if (i % step !== 0 && i !== labels.length - 1) return;
    ctx.fillStyle = "#8b98a9";
    ctx.fillText(d.slice(5), X(i), pad.t + ph + 8);
  });

  shown.forEach((s, si) => {
    ctx.strokeStyle = s.color;
    ctx.lineWidth = si === 0 ? 2.4 : 1.8;
    ctx.lineJoin = "round";
    ctx.beginPath();
    let started = false;
    s.values.forEach((v, i) => {
      if (v == null || !isFinite(v)) { started = false; return; }
      const x = X(i), y = Y(v);
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
    });
    ctx.stroke();
    if (si === 0) {
      ctx.lineTo(X(labels.length - 1), pad.t + ph);
      ctx.lineTo(X(0), pad.t + ph);
      ctx.closePath();
      const g = ctx.createLinearGradient(0, pad.t, 0, pad.t + ph);
      g.addColorStop(0, "rgba(88,166,255,.25)");
      g.addColorStop(1, "rgba(88,166,255,0)");
      ctx.fillStyle = g;
      ctx.fill();
    }
  });

  let hovered = null;
  const drawHover = (i) => {
    const mx = (i / (labels.length - 1)) * pw + pad.l;
    ctx.strokeStyle = "rgba(139,152,169,.4)";
    ctx.setLineDash([4, 4]);
    ctx.beginPath(); ctx.moveTo(mx, pad.t); ctx.lineTo(mx, pad.t + ph); ctx.stroke();
    ctx.setLineDash([]);
    shown.forEach((s) => {
      const v = s.values[i];
      if (v == null || !isFinite(v)) return;
      ctx.fillStyle = s.color;
      ctx.beginPath(); ctx.arc(mx, Y(v), 3.6, 0, Math.PI * 2); ctx.fill();
    });
    const rows = shown.map((s) => {
      const v = s.values[i];
      return '<div class="t-row"><span><span class="t-dot" style="background:' + s.color + '"></span>' +
        esc(s.label) + '</span><span>' + (v == null ? "--" : fmtUsd(v)) + "</span></div>";
    }).join("");
    tip.innerHTML = '<div class="t-date">' + esc(labels[i]) + "</div>" + rows;
    tip.classList.remove("hidden");
    const tipW = tip.offsetWidth, tipH = tip.offsetHeight;
    const relX = mx;
    let tipX = relX + 14, tipY = pad.t + 8;
    if (tipX + tipW > W - 4) tipX = relX - tipW - 14;
    if (tipY + tipH > H - 4) tipY = H - tipH - 4;
    tip.style.left = tipX + "px";
    tip.style.top = tipY + "px";
  };
  const clearHover = () => {
    if (hovered === null) return;
    hovered = null;
    tip.classList.add("hidden");
    drawLineChart(canvas, labels, series, visible);
  };
  canvas.onmousemove = (ev) => {
    const rect = canvas.getBoundingClientRect();
    const mx = ev.clientX - rect.left;
    const i = Math.round(((mx - pad.l) / pw) * (labels.length - 1));
    if (i < 0 || i >= labels.length) { clearHover(); return; }
    if (hovered !== i) {
      hovered = i;
      drawLineChart(canvas, labels, series, visible);
      drawHover(i);
    }
  };
  canvas.onmouseleave = clearHover;
}

function compactNum(v) {
  if (v >= 1e6) return (v / 1e6).toFixed(1) + "M";
  if (v >= 1e3) return (v / 1e3).toFixed(1) + "k";
  return String(Math.round(v * 100) / 100);
}
function niceMax(v) {
  const exp = Math.floor(Math.log10(v));
  const base = Math.pow(10, exp);
  const mult = v / base;
  let nice;
  if (mult <= 1) nice = 1; else if (mult <= 2) nice = 2;
  else if (mult <= 2.5) nice = 2.5; else if (mult <= 5) nice = 5;
  else nice = 10;
  const max = nice * base;
  const ticks = [];
  for (let i = 0; i <= 5; i++) ticks.push((max / 5) * i);
  return { max, ticks };
}

/* ---------------- blacklist / wallets / sources ---------------- */
async function renderBlacklist() {
  try {
    const d = await api("/api/blacklist");
    const fn = d.file ? d.file.split(/[\\/]/).pop() : "";
    $("blacklistFile").textContent = fn ? "(" + fn + ")" : "";
    const list = $("blacklistEntries");
    if (!d.entries.length) {
      list.innerHTML = '<div class="bl-empty">' + t("emptyList") + "</div>";
      return;
    }
    list.innerHTML = d.entries.map((e) => {
      const meta = [
        e.token_id && "contract " + e.token_id,
        e.name && "name " + e.name,
        e.chain && "chain " + e.chain,
        e.note && e.note,
      ].filter(Boolean).join(" · ");
      const right = e.source === "user"
        ? '<button class="bl-del" data-index="' + e.index + '" title="' + t("remove") + '">✕ ' + t("remove") + "</button>"
        : '<span class="bl-tag config">' + t("config") + "</span>";
      return '<div class="bl-item"><span class="bl-sym">' + esc(e.symbol || "?") + "</span>" +
        '<span class="bl-meta">' + esc(meta) + "</span>" + right + "</div>";
    }).join("");
    list.querySelectorAll(".bl-del").forEach((b) => {
      b.addEventListener("click", async () => {
        try {
          await postJSON("/api/blacklist/remove", { index: Number(b.dataset.index) });
          await reloadViewData();
        } catch (e) { alert(t("blRemoveFail") + e.message); }
      });
    });
  } catch (e) { /* ignore */ }
}

async function renderWalletMgmt() {
  try {
    const d = await api("/api/wallets");
    state.wallets = d.wallets;
    const fn = d.file ? d.file.split(/[\\/]/).pop() : "";
    $("walletFile").textContent = fn ? "(" + fn + ")" : "";
    const list = $("walletList");
    if (!d.wallets.length) {
      list.innerHTML = '<div class="bl-empty">' + t("emptyList") + "</div>";
      return;
    }
    list.innerHTML = d.wallets.map((w) => {
      const right = w.source === "user"
        ? '<button class="bl-del" data-index="' + w.index + '" title="' + t("delete") + '">✕ ' + t("delete") + "</button>"
        : '<span class="bl-tag config">' + t("builtin") + "</span>";
      return '<div class="bl-item"><span class="bl-sym">' + esc(w.name) + "</span>" +
        '<span class="bl-tag ' + esc(w.type) + '">' + (TYPE_LABEL[w.type] || w.type) + "</span>" +
        '<span class="bl-meta">' + esc(w.address) + "</span>" + right + "</div>";
    }).join("");
    list.querySelectorAll(".bl-del").forEach((b) => {
      b.addEventListener("click", async () => {
        if (!confirm(t("confirmDelWallet"))) return;
        try {
          await postJSON("/api/wallets/remove", { index: Number(b.dataset.index) });
          await reloadViewData();
        } catch (e) { alert(t("walletRemoveFail") + e.message); }
      });
    });
  } catch (e) { /* ignore */ }
}

const SRC_META = {
  debank: { en: "EVM (DeBank)", zh: "EVM（DeBank）" },
  btc: { en: "BTC balances", zh: "BTC 余额" },
  prices: { en: "Native coin prices", zh: "原生币价格" },
  solana: { en: "Solana", zh: "Solana" },
  hyperliquid: { en: "Hyperliquid L1", zh: "Hyperliquid L1" },
  cex: { en: "CEX accounts", zh: "CEX 账户" },
};

function setByPath(obj, path, value) {
  const parts = path.split(".");
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i++) {
    cur = cur[parts[i]];
    if (cur === undefined) return;
  }
  cur[parts[parts.length - 1]] = value;
}

function srcProvidersHTML(basePath, providers, keyPh, links) {
  const keyPlaceholder = (p) => (typeof keyPh === "function" ? keyPh(p) : keyPh) || t("srcKeyPh");
  const linkFor = (p) => (links && links[p.name]) || (links && links[p.exchange])
    ? '<a class="src-link" href="' + esc((links[p.name] || links[p.exchange])) + '" target="_blank" rel="noopener noreferrer">' + t("getKey") + " ↗</a>"
    : "";
  return '<div class="src-providers">' + providers.map((p, i) => {
    const urlField = p.base_url !== undefined ? "base_url" : "url";
    const urlVal = p.base_url !== undefined ? (p.base_url || "") : (p.url || "");
    return '<div class="src-prov">' +
      '<label class="chk"><input type="checkbox" data-path="' + basePath + "." + i + '.enabled"' +
        (p.enabled !== false ? " checked" : "") + "></label>" +
      '<input data-path="' + basePath + "." + i + '.name" value="' + esc(p.name) + '" class="src-name" readonly>' +
      '<input data-path="' + basePath + "." + i + "." + urlField + '" value="' + esc(urlVal) + '" class="src-url" placeholder="' + t("urlPh") + '">' +
      (p.key !== undefined
        ? '<input data-path="' + basePath + "." + i + '.key" value="' + esc(p.key || "") + '" class="src-key" placeholder="' + esc(keyPlaceholder(p)) + '">'
        : "") +
      (p.paid ? '<span class="paid-badge">' + t("paidBadge") + "</span>" : "") +
      linkFor(p) +
      "</div>";
  }).join("") + "</div>";
}

const SRC_LINKS = {
  "debank-pro": "https://open.debank.com",
  binance: "https://www.binance.com/en/my/settings/api-management",
  bybit: "https://www.bybit.com/app/user/api-management",
  backpack: "https://app.backpack.exchange/settings/api-keys",
};

function chainLogo(cid) {
  const map = { btc: "btc", eth: "eth", sol: "sol", hyperliquid: "hyperliquid",
                binance: "binance", bybit: "bybit", backpack: "backpack" };
  return map[cid] ? '/static/logos/' + map[cid] + '.svg' : '/static/logos/evm.svg';
}
function typeLogo(type) {
  return '/static/logos/' + (type === "btc" ? "btc" : type === "sol" ? "sol" : type === "cex" ? "evm" : "evm") + '.svg';
}

function srcFieldHTML(path, label, value, placeholder) {
  return '<div class="src-field"><span>' + esc(label) + '</span><input data-path="' + path + '" value="' +
    esc(value || "") + '"' + (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + "></div>";
}

async function renderSources() {
  try {
    const d = await api("/api/sources");
    state.sourcesCfg = JSON.parse(JSON.stringify(d.config));
    state.sourcesLastOk = d.last_ok || {};
    const st = d.status || {};
    const lastOk = st.last_ok || {};
    $("sourcesFile").textContent = d.file ? d.file.split(/[\\/]/).pop() : "";
    const cfg = state.sourcesCfg;
    const body = $("sourcesBody");
    body.innerHTML = "";

    const fmtTime = (iso) => iso ? String(iso).replace("T", " ").slice(0, 16) : t("never");
    const blockOf = (key, srcKey) => {
      const b = document.createElement("div");
      b.className = "src-block";
      const meta = SRC_META[key] || { en: key, zh: key };
      let lastStr = "";
      const okTime = fmtTime(lastOk[srcKey || key]);
      if (key === "solana") {
        const parts = [];
        const rk = state.sourcesLastOk["solana_rpc"];
        const sk = state.sourcesLastOk["solana_spl"];
        if (rk !== undefined) parts.push("RPC: " + (((cfg.solana.rpc || [])[rk]) || {}).name);
        if (sk !== undefined) parts.push("SPL: " + ((((cfg.solana.spl_prices || {}).providers || [])[sk]) || {}).name);
        if (parts.length) lastStr = "(" + t("avg") + ": " + parts.join(" · ") + ")";
      } else {
        const lk = state.sourcesLastOk[key];
        if (lk !== undefined && cfg[key] && cfg[key].providers) {
          lastStr = "(" + t("avg") + ": " + ((cfg[key].providers[lk]) || {}).name + ")";
        }
      }
      b.innerHTML = '<div class="src-head"><label class="chk">' +
        '<input type="checkbox" data-path="' + key + '.enabled"' + (cfg[key].enabled !== false ? " checked" : "") + "> " +
        "<b>" + esc(meta[lang] || meta.en) + "</b></label>" +
        '<span class="hint src-oktime">' + t("lastOk") + ": " + esc(okTime) + "</span>" +
        '<span class="hint src-ok">' + esc(lastStr) + "</span></div>";
      body.appendChild(b);
      return b;
    };

    if (cfg.debank) {
      const b = blockOf("debank");
      b.insertAdjacentHTML("beforeend",
        '<div class="src-sub">' + t("providersHint") + "</div>" +
        srcProvidersHTML("debank.providers", cfg.debank.providers || [], (p) =>
          p.type === "pro" ? "AccessKey (required)" : "free - no key", SRC_LINKS) +
        srcFieldHTML("debank.chain_list_url", "chain_list_url", cfg.debank.chain_list_url, t("chainListPh")) +
        srcFieldHTML("debank.chains", "chains", cfg.debank.chains || "", t("chainsPh")) +
        '<p class="bl-desc">' + t("debankHint") + "</p>");
    }
    for (const key of ["btc", "prices", "hyperliquid"]) {
      if (!cfg[key]) continue;
      const b = blockOf(key);
      b.insertAdjacentHTML("beforeend", srcProvidersHTML(key + ".providers", cfg[key].providers || []));
    }
    if (cfg.solana) {
      const b = blockOf("solana");
      b.insertAdjacentHTML("beforeend",
        '<div class="src-sub">' + t("rpcLabel") + "</div>" +
        srcProvidersHTML("solana.rpc", cfg.solana.rpc || []) +
        '<div class="src-sub">' + t("splPricesLabel") + "</div>" +
        srcProvidersHTML("solana.spl_prices.providers", (cfg.solana.spl_prices || {}).providers || []) +
        '<div class="src-sub">' + t("birdeyeLabel") + "</div>" +
        '<div class="src-prov">' +
        '<label class="chk"><input type="checkbox" data-path="solana.birdeye.enabled"' +
          (cfg.solana.birdeye.enabled ? " checked" : "") + "> " + t("enabled") + "</label>" +
        '<input data-path="solana.birdeye.key" value="' + esc(cfg.solana.birdeye.key || "") + '" class="src-key" placeholder="' + t("srcKeyPh") + '">' +
        '<input data-path="solana.birdeye.url" value="' + esc(cfg.solana.birdeye.url || "") + '" class="src-url">' +
        "</div>");
    }
    if (cfg.cex) {
      const b = blockOf("cex");
      // always show the supported exchanges (binance / bybit / backpack); keys default empty.
      // merged rows are written back into the config so name/exchange persist on save.
      const byEx = {};
      (cfg.cex.accounts || []).forEach((a) => { if (a.exchange) byEx[a.exchange] = a; });
      const defaults = [
        { exchange: "binance", name: "binance_read" },
        { exchange: "bybit", name: "bybit_read" },
        { exchange: "backpack", name: "backpack_read" },
      ];
      const extra = (cfg.cex.accounts || []).filter((a) => !defaults.some((d) => d.exchange === a.exchange));
      const rows = defaults.map((dflt) => byEx[dflt.exchange] ||
        Object.assign({}, dflt, { key: "", secret: "", enabled: true })).concat(extra);
      state.sourcesCfg.cex.accounts = rows;
      cfg.cex.accounts = rows;
      rows.forEach((a, i) => {
        b.insertAdjacentHTML("beforeend",
          '<div class="src-sub">' + esc(a.name) + " (" + esc(a.exchange) + ")" +
          ' <span class="hint src-oktime">' + t("lastOk") + ": " + esc(fmtTime(lastOk["cex:" + a.exchange])) + "</span></div>" +
          '<div class="src-prov">' +
          '<label class="chk"><input type="checkbox" data-path="cex.accounts.' + i + '.enabled"' +
            (a.enabled !== false ? " checked" : "") + "></label>" +
          '<input data-path="cex.accounts.' + i + '.key" value="' + esc(a.key || "") + '" class="src-key" placeholder="' + t("cexKeyPh") + '">' +
          '<input data-path="cex.accounts.' + i + '.secret" value="' + esc(a.secret || "") + '" class="src-key" placeholder="' + t("cexSecretPh") + '">' +
          (SRC_LINKS[a.exchange]
            ? '<a class="src-link" href="' + esc(SRC_LINKS[a.exchange]) + '" target="_blank" rel="noopener noreferrer">' + t("getKey") + " ↗</a>"
            : "") +
          "</div>");
      });
      b.insertAdjacentHTML("beforeend", '<p class="bl-desc">' + t("cexDefaultHint") + "</p>");
    }

    body.querySelectorAll("[data-path]").forEach((el) => {
      const path = el.dataset.path;
      el.addEventListener(el.type === "checkbox" ? "change" : "input", () => {
        setByPath(state.sourcesCfg, path, el.type === "checkbox" ? el.checked : el.value);
      });
    });
  } catch (e) {
    $("sourcesMsg").textContent = t("loadingFailed") + e.message;
  }
}

/* ---------------- profiles & settings page ---------------- */
async function renderProfiles() {
  try {
    const d = await api("/api/profiles");
    state.activeProfile = d.active;
    // dropdown
    const sel = $("profileSelect");
    sel.innerHTML = d.profiles.map((p) =>
      '<option value="' + esc(p.name) + '"' + (p.is_active ? " selected" : "") + ">" +
      esc(p.name) + (p.is_default ? " (default)" : "") + "</option>").join("");
    // management list (switch is via dropdown)
    const list = $("profileList");
    list.innerHTML = d.profiles.map((p) => {
      const right = p.is_active
        ? '<span class="bl-tag user">' + t("activeProfile") + "</span>"
        : (p.is_default ? "" : '<button class="bl-del" data-pf-action="delete" data-pf-name="' + esc(p.name) + '">✕ ' + t("deleteProfile") + "</button>");
      return '<div class="bl-item"><span class="bl-sym">' + esc(p.name) + "</span>" +
        (p.is_default ? '<span class="bl-tag config">' + t("config") + "</span>" : "") +
        (p.has_db ? '<span class="hint">db</span>' : "") + right + "</div>";
    }).join("") || '<div class="bl-empty">' + t("emptyList") + "</div>";
  } catch (e) { /* ignore */ }
}

async function renderSchedule() {
  try {
    const d = await api("/api/schedule");
    $("schedEnabled").checked = !!d.enabled;
    $("schedTime").value = d.time || "09:00";
    $("schedLast").textContent = t("schedLastRun") + (d.last_run_date || t("never"));
  } catch (e) { /* ignore */ }
}

async function renderSettings() {
  await renderSchedule();
  await renderProfiles();
  await renderWalletMgmt();
  await renderSources();
  await renderBlacklist();
}

/* ---------------- config export / import ---------------- */
async function exportConfig() {
  try {
    const d = await api("/api/config/export");
    const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "portfolio-config-" + (d.exported_at || Date.now()).slice(0, 10) + ".json";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
    $("sourcesMsg").textContent = t("exportDone");
  } catch (e) {
    $("sourcesMsg").textContent = t("exportFailed") + e.message;
  }
}

async function importConfig(ev) {
  const file = ev.target.files && ev.target.files[0];
  ev.target.value = "";
  if (!file) return;
  try {
    const cfg = JSON.parse(await file.text());
    if (!cfg || typeof cfg !== "object" || !("sources" in cfg || "wallets" in cfg || "blacklist" in cfg)) {
      throw new Error("not a portfolio-config export file");
    }
    await postJSON("/api/config/import", { config: cfg });
    $("sourcesMsg").textContent = t("importDone");
    await reloadViewData();
  } catch (e) {
    $("sourcesMsg").textContent = t("importFailed") + e.message;
  }
}

/* ---------------- reload & refresh ---------------- */
async function reloadViewData() {
  try {
    const p = await api("/api/profiles");
    state.activeProfile = p.active;
    const sel = $("profileSelect");
    if (sel.options.length) sel.value = p.active;
  } catch (e) { /* ignore */ }
  const dates = (await api("/api/snapshots")).map((d) => d.date);
  state.dates = dates;
  fillDateSelect(dates);
  if (dates.length) {
    const keep = state.selectedDate && dates.includes(state.selectedDate);
    state.selectedDate = keep ? state.selectedDate : dates[dates.length - 1];
    $("dateSelect").value = state.selectedDate;
    await loadDate(state.selectedDate);
  } else {
    showEmpty();
  }
  const h = await api("/api/history?days=0");
  state.history = h;
  renderChart();
  await renderBlacklist();
  await renderWalletMgmt();
}

function fillFilterSelects() {
  const ws = $("filterWallet"), cs = $("filterChain");
  // wallet options: from current view wallets filtered by category + config wallets
  const names = new Set();
  if (state.view) {
    state.view.wallets.forEach((w) => {
      if (state.filters.category === "all" || w.type === state.filters.category) names.add(w.wallet);
    });
  }
  (state.wallets || []).forEach((w) => {
    if (state.filters.category === "all" || w.type === state.filters.category) names.add(w.name);
  });
  ws.innerHTML = '<option value="">' + t("fbWalletAll") + "</option>";
  [...names].sort().forEach((n) => {
    const o = document.createElement("option"); o.value = n; o.textContent = n; ws.appendChild(o);
  });
  if (state.filters.wallet && !names.has(state.filters.wallet)) state.filters.wallet = "";
  ws.value = state.filters.wallet;

  const v = filteredView();
  const chains = v ? v.by_chain : {};
  cs.innerHTML = '<option value="">' + t("fbChainAll") + "</option>";
  Object.keys(chains).sort((a, b) => chains[b] - chains[a]).forEach((c) => {
    const o = document.createElement("option"); o.value = c; o.textContent = chainName(c); cs.appendChild(o);
  });
  if (state.filters.chain && !(state.filters.chain in chains)) state.filters.chain = "";
  cs.value = state.filters.chain;
}

async function refresh() {
  const btn = $("btnRefresh");
  btn.disabled = true;
  const prog = $("progress");
  prog.classList.remove("hidden");
  $("progressFill").style.width = "2%";
  $("progressMsg").textContent = t("refreshStart");
  const timer = setInterval(async () => {
    try {
      const st = await api("/api/status");
      const pct = st.total ? Math.round((st.done / st.total) * 100) : 3;
      $("progressFill").style.width = Math.min(96, pct) + "%";
      $("progressMsg").textContent = st.running ? st.msg : t("refreshing");
    } catch (e) { /* ignore */ }
  }, 1500);
  try {
    await api("/api/refresh");
    $("progressFill").style.width = "100%";
    $("progressMsg").textContent = t("doneUpdating");
    const [history, dates] = await Promise.all([api("/api/history?days=0"), api("/api/snapshots")]);
    state.history = history;
    state.dates = dates.map((d) => d.date);
    fillDateSelect(state.dates);
    state.selectedDate = dates[dates.length - 1].date;
    $("dateSelect").value = state.selectedDate;
    await loadDate(state.selectedDate);
    renderChart();
  } catch (e) {
    $("progressMsg").textContent = t("refreshFailed") + e.message;
    setTimeout(() => prog.classList.add("hidden"), 4000);
  } finally {
    clearInterval(timer);
    setTimeout(() => { prog.classList.add("hidden"); }, 1200);
    btn.disabled = false;
  }
}

function showEmpty() {
  $("totalUsd").textContent = "--";
  $("walletCards").innerHTML = '<div class="hint">' + t("emptyWallets") + "</div>";
  $("tokenBody").innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">' +
    t("noSnapshot") + "</td></tr>";
  $("tokenDate").textContent = "";
  renderPie();
}
function showError(msg) {
  $("totalUsd").textContent = "!";
  $("tokenBody").innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--red);padding:24px">' + esc(msg) + "</td></tr>";
}

window.addEventListener("resize", () => { if (state.history) renderChart(); });
init();
