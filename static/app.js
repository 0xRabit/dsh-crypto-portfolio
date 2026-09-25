/* Crypto Portfolio Tracker — vanilla JS dashboard (no external libs) */
"use strict";

/* ================= i18n ================= */
const I18N = {
  en: {
    brand: "Crypto Portfolio Tracker",
    heroLine: "Free · self-hosted · any chain",
    heroLineFull: "Free & self-hosted · every chain, every wallet in one view · no account, no tracking — your keys never leave your machine",
    aboutLine: "Python stdlib + vanilla JS · no framework, no CDN · data sources are configurable per profile",
    siblingLabel: "Sibling project:",
    chromeExt: "Chrome extension",
    sourceCode: "source",
    btnSources: "Sources", btnRefresh: "Refresh", btnLang: "中文",
    viewDateTitle: "View last snapshot of a day",
    fbCategory: "Category", fbAll: "All", fbBtc: "BTC", fbEvm: "EVM", fbSol: "Solana", fbCex: "CEX",
    fbDoge: "Dogecoin", fbAda: "Cardano",
    fbWallet: "Wallet", fbChain: "Chain", fbWalletAll: "All wallets", fbChainAll: "All chains",
    assetTitle: "Total Assets (USD) · Wallet Share",
    totalAssets: "Total Assets",
    walletsTitle: "Wallets", btnManageWallets: "Manage Wallets",
    walletClickHint: "click a card to see that wallet's details",
    walletMgmtTitle: "Wallet Management",
    walletMgmtDesc: "Adding/removing wallets only affects future fetches; already stored historical snapshots are never touched.",
    wlNamePh: "Name (e.g. evm-new)", wlTypeEvm: "EVM (DeBank + Hyperliquid)", wlTypeBtc: "BTC", wlTypeSol: "Solana",
    wlTypeDoge: "Dogecoin", wlTypeAda: "Cardano",
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
    footer: "Data sources: DeBank (EVM), Hyperliquid L1, blockchain.info/mempool (BTC), Solana RPC (SOL/SPL/staked), Binance/Bybit/Backpack/OKX/Bitget (CEX). Refresh saves the last snapshot of the day and builds trend charts.",
    noData: "No data yet — click Refresh to fetch all wallets (first run ~30-60s)",
    noMatch: "No matching tokens",
    noSnapshot: "No snapshots yet, please click Refresh",
    noHistory: "No trend data yet — snapshots accumulate as you refresh",
    noValue: "All wallets are 0, nothing to show",
    emptyWallets: "No data",
    items: (n) => n + " items",
    snapDate: "snapshot",
    recorded: "recorded at",
    viewExplorer: "View on explorer",
    deselectHint: "click again to deselect",
    copyAddr: "Copy address", copy: "Copy", copied: "Copied ✓",
    btnCancel: "Cancel", cancelRequested: "Cancelling…", cancelled: "Refresh cancelled",
    btnShowKeys: "Show keys", btnHideKeys: "Hide keys",
    keysMasked: "Keys are masked — use Show keys to load the real values from this machine.",
    latest: "latest", viewingHistory: "Viewing a historical snapshot",
    walletShareCap: "By wallet", typeShareCap: "By asset type",
    catStable: "Stablecoins", catBtc: "Bitcoin", catEth: "Ethereum", catSol: "Solana",
    catHype: "HYPE", catOther: "Other", thLabel: "Label",
    labelNamePh: "Label (e.g. stable, btc, eth, sol, hype, or your own)",
    labelChanged: "Label updated",
    labelPopPh: "Find or create a label…", labelCreate: "Create",
    labelRename: "Rename label", labelDelete: "Delete label",
    labelNeedName: "Type a label name first", labelDeleteConfirm: "Delete label \u201c%s\u201d? Its tokens go back to \u201cOther\u201d.",
    thStable: "Stable", markStable: "stablecoin", unmarkStable: "not a stablecoin",
    labelRulesTitle: "Asset Label Rules", labelRulesSummary: "which tokens count as which label",
    labelBuiltinTitle: "Built-in wildcards", labelAutoBand: "Auto-detect price band",
    labelSymPh: "Symbol wildcard (e.g. USDT*, *USD)", labelTokenIdPh: "Contract/mint (optional, exact)",
    labelChainPh: "Chain (optional)", btnAddLabelRule: "+ Add Rule",
    labelRulesDesc: "Every token carries exactly one label, and the asset-type donut counts by it. The system detects stable / btc / eth / sol / hype on its own — by symbol wildcard (USDT*, *USDC, WBTC* …), plus a price band for stablecoins so a pegged asset under an unfamiliar ticker is still caught. Add a rule here, or use the picker on any row of the token table to set, create or rename a label.",
    labelRuleSaved: "Rule saved", labelRuleRemoved: "Rule removed", labelRuleFailed: "Rule failed: ",
    showMore: "Show", remaining: "more", showingAll: "all rows shown",
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
    renameProfile: "Rename",
    renamePrompt: "Rename this profile to (config and snapshots move with it):",
    profileRenameFail: "Rename failed: ",
    confirmDelProfile: "Delete this profile? Its snapshots and configs will be removed.",
    profileSwitchFail: "Switch failed: ", profileCreateFail: "Create failed: ", profileDeleteFail: "Delete failed: ",
    schedTitle: "Scheduled Daily Refresh",
    schedDesc: "Runs inside the Python server process (not the browser page) - closing the web page does not stop it. Fires at the exact local minute; the server must be running at that time. Saving a schedule resets today's once-per-day marker, so a future time fires the same day.",
    schedEnable: "Enable", btnSaveSched: "Save Schedule", schedSaved: "Schedule saved", schedLastRun: "Last auto-run: ",
    schedOff: "no schedule",
    pfSchedHint: "Each profile keeps its own daily auto-refresh schedule — click the clock tag on a profile to edit it. The scheduler runs every profile independently.",
    paidBadge: "PAID", lastOk: "last ok", never: "never",
    cexDefaultHint: "Enter read-only keys to enable; empty rows are skipped.",
    healthTitle: "Asset Health", healthScope: "whole portfolio, independent of the filters above",
    healthTiering: "On-chain risk", healthConcentration: "Concentration", healthStorage: "Storage security",
    healthTieringHint: "Share of the portfolio held on-chain outside BTC — the part a compromised hot wallet can reach.",
    healthTieringSub: (btc, onchain, cex) => "BTC " + btc + " · on-chain " + onchain + " · CEX " + cex,
    healthConcentrationHint: "Share of the largest single wallet.",
    healthConcentrationSub: (wallet, usd) => "largest: " + wallet + " (" + usd + ")",
    healthStorageHint: "Share held in cold storage; higher is safer.",
    healthStorageSub: (cold, hot, cex) => "cold " + cold + " · hot " + hot + " · exchange " + cex,
    healthLevelSafe: "Healthy", healthLevelWarning: "Watch", healthLevelHighRisk: "High risk",
    healthOk: "Nothing to act on — the three checks all pass.",
    healthOnChainRisk: (pct) => pct + "% of the portfolio is in on-chain assets outside BTC; moving part of it into BTC lowers that exposure.",
    healthConcentrationAdvice: (pct, wallet) => wallet + " alone holds " + pct + "% of the portfolio; spreading it across wallets (or converting part to BTC) lowers that risk.",
    healthStorageAdvice: (pct) => "Only " + pct + "% sits in cold storage; long-term holdings belong on a hardware wallet.",
    healthStorageAdviceNone: "Nothing is in cold storage yet; long-term holdings belong on a hardware wallet.",
    healthNoData: "No snapshot yet — run a refresh to compute the health report.",
    shareBtn: "Share", shareTotal: "Total assets", shareTop: "Top holdings",
    shareSnapshot: "snapshot", shareFiltered: "filtered view", shareFail: "Could not build the share card.",
    shareTitle: "Share your portfolio", shareClose: "Close",
    shareDownload: "Download PNG", shareCopyImg: "Copy image", shareCopyText: "Copy text",
    shareCopied: "Copied.", shareCopyImgFail: "This browser did not allow copying the image — use Download PNG.",
    shareCopyFail: "Copy blocked — the text is selected, press \u2318/Ctrl+C.",
    shareTextTpl: (total, change, date, top, repo) =>
      "My portfolio (" + date + "): " + total + (change ? " · " + change : "") +
      "\nTop holdings: " + top +
      "\nTracked with dsh-crypto-portfolio — self-hosted, no CDN, keys stay local: " + repo +
      "\n#crypto #portfolio",
    shareHint: "Draw a PNG summary of what you are looking at (no addresses).",
    healthTier1: "BTC", healthTier2: "On-chain", healthTier3: "CEX", healthRest: "other wallets",
    storageHot: "Hot wallet", storageCold: "Cold wallet",
    storageTitle: "Where the keys live: cold = hardware/offline, hot = browser or app wallet. Exchange accounts are always counted as exchange custody.",
    storageCex: "Exchange", storageCol: "Storage", storageMark: "cold storage",
    providersHint: "providers (paid first, free fallback)",
    getKey: "get API key",
    debankHint: "EVM source = DeBank. Fields: base_url = API endpoint (the paid pro provider needs the pro host); key = AccessKey for the paid provider, leave empty to use the free public API; chain_list_url = DeBank-specific endpoint that lists all supported chains (switch to a mirror if blocked); chains = optional comma-separated chain ids to fetch (e.g. eth,bsc,arb,base), empty = all.",
    urlPh: "API URL", chainListPh: "chain list API (DeBank-specific)", chainsPh: "optional: eth,bsc,arb,base (default: all)",
    profileActive: "Profile",
    apiKey: "API Key", enabled: "启用", rpcLabel: "RPC 节点", splPricesLabel: "SPL 价格",
    birdeyeLabel: "Birdeye", srcKeyPh: "key（可选）", cexKeyPh: "api key", cexSecretPh: "api secret",
    cexPassPh: "passphrase",
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
    heroLine: "免费 · 自托管 · 支持所有链",
    heroLineFull: "免费 · 自托管 · 所有链、所有钱包一屏总览 · 无需注册、无追踪——私钥永不离开你的机器",
    aboutLine: "Python 标准库 + 原生 JS · 无框架、无 CDN · 每个 Profile 独立配置数据源",
    siblingLabel: "兄弟版本：",
    chromeExt: "Chrome 扩展",
    sourceCode: "源码",
    btnSources: "数据源", btnRefresh: "刷新数据", btnLang: "EN",
    viewDateTitle: "查看某一天的最后一次快照",
    fbCategory: "分类", fbAll: "全部", fbBtc: "BTC", fbEvm: "EVM", fbSol: "Solana", fbCex: "CEX",
    fbDoge: "狗狗币", fbAda: "艾达币",
    fbWallet: "钱包", fbChain: "网络", fbWalletAll: "全部钱包", fbChainAll: "全部网络",
    assetTitle: "总资产（USD）· 各钱包占比",
    totalAssets: "总资产",
    walletsTitle: "钱包", btnManageWallets: "⚙ 钱包管理",
    walletClickHint: "点击选项卡可查看该钱包详情",
    walletMgmtTitle: "钱包管理",
    walletMgmtDesc: "增加/删除钱包仅影响之后的抓取；已存储的历史快照数据不受影响。",
    wlNamePh: "名称（如 evm-new）", wlTypeEvm: "EVM（DeBank + Hyperliquid）", wlTypeBtc: "BTC", wlTypeSol: "Solana",
    wlTypeDoge: "狗狗币 DOGE", wlTypeAda: "艾达币 ADA",
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
    footer: "数据来源：DeBank（EVM）、Hyperliquid L1、blockchain.info/mempool（BTC）、Solana RPC（SOL/SPL/质押）、Binance/Bybit/Backpack/OKX/Bitget（CEX）、CoinGecko/DexScreener（价格）。刷新即保存当天最后一次快照并形成趋势图。",
    noData: "暂无数据，请点击右上角「刷新数据」抓取全部钱包（首次约需 30~60 秒）",
    noMatch: "没有符合条件的代币",
    noSnapshot: "暂无快照，请先点击「刷新数据」",
    noHistory: "暂无趋势数据，刷新后生成",
    noValue: "所有钱包余额均为 0，暂无可展示占比",
    emptyWallets: "暂无数据",
    items: (n) => "共 " + n + " 项",
    snapDate: "快照",
    recorded: "记录于",
    viewExplorer: "在浏览器打开",
    deselectHint: "再次点击取消选中",
    copyAddr: "复制地址", copy: "复制", copied: "已复制 ✓",
    btnCancel: "取消", cancelRequested: "正在取消…", cancelled: "已取消刷新",
    btnShowKeys: "显示密钥", btnHideKeys: "隐藏密钥",
    keysMasked: "密钥已打码；点「显示密钥」才会从本机读取明文。",
    latest: "最新", viewingHistory: "正在查看历史快照",
    walletShareCap: "按钱包", typeShareCap: "按资产类型",
    catStable: "稳定币", catBtc: "比特币", catEth: "以太坊", catSol: "Solana",
    catHype: "HYPE", catOther: "其他", thLabel: "标签",
    labelNamePh: "标签（如 stable、btc、eth、sol、hype，或自定义）",
    labelChanged: "标签已更新",
    labelPopPh: "查找或新建标签…", labelCreate: "新建",
    labelRename: "重命名标签", labelDelete: "删除标签",
    labelNeedName: "请先输入标签名", labelDeleteConfirm: "删除标签「%s」？该标签下的代币会回到「其他」。",
    thStable: "稳定币", markStable: "标记为稳定币", unmarkStable: "取消稳定币标记",
    labelRulesTitle: "资产类别规则", labelRulesSummary: "哪些代币算哪一类",
    labelBuiltinTitle: "内置通配符", labelAutoBand: "自动识别价格带",
    labelSymPh: "符号通配符（如 USDT*、*USD）", labelTokenIdPh: "合约/铸币地址（可选，精确匹配）",
    labelChainPh: "网络（可选）", btnAddLabelRule: "+ 添加规则",
    labelRulesDesc: "每个代币带且只带一个标签，资产类型饼图按它统计。系统自己识别 稳定币 / 比特币 / 以太坊 / Solana / HYPE —— 靠符号通配符（USDT*、*USDC、WBTC* 等），稳定币再叠加价格带，所以冷门符号的锚定资产也认得出来。可以在这里加规则，也可以直接用代币明细表里的标签选择器来设置、新建或重命名标签。",
    labelRuleSaved: "规则已保存", labelRuleRemoved: "规则已删除", labelRuleFailed: "规则操作失败：",
    showMore: "再显示", remaining: "项", showingAll: "已显示全部",
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
    renameProfile: "重命名",
    renamePrompt: "将该 Profile 重命名为（配置与快照会一并迁移）：",
    profileRenameFail: "重命名失败：",
    confirmDelProfile: "删除该 Profile？其快照与配置将一并删除。",
    profileSwitchFail: "切换失败：", profileCreateFail: "创建失败：", profileDeleteFail: "删除失败：",
    schedTitle: "定时每日刷新",
    schedDesc: "定时器运行在 Python 服务进程内（与网页无关）——关闭网页不影响它。在设定分钟的整点触发；那一刻服务必须在运行。保存定时会重置当天的一次性标记：新时间若在今天之后，当天就会执行。",
    schedEnable: "启用", btnSaveSched: "保存定时", schedSaved: "定时已保存", schedLastRun: "上次自动执行：",
    schedOff: "无定时",
    pfSchedHint: "每个 Profile 各自维护独立的每日定时刷新——点击对应 Profile 上的时钟标签即可编辑。调度器会独立运行每个 Profile 的定时任务。",
    paidBadge: "付费", lastOk: "上次成功", never: "从未",
    cexDefaultHint: "填入只读 key 即启用；空行自动跳过。",
    healthTitle: "资产健康度", healthScope: "整个资产组合，不受上方筛选影响",
    healthTiering: "链上风险", healthConcentration: "集中度", healthStorage: "托管安全",
    healthTieringHint: "除 BTC 外的链上资产占比——这部分最容易被盗（热钱包/授权风险）。",
    healthTieringSub: (btc, onchain, cex) => "BTC " + btc + " · 链上 " + onchain + " · CEX " + cex,
    healthConcentrationHint: "单一钱包占总额的比例。",
    healthConcentrationSub: (wallet, usd) => "最大：" + wallet + "（" + usd + "）",
    healthStorageHint: "冷存储的占比，越高越安全。",
    healthStorageSub: (cold, hot, cex) => "冷 " + cold + " · 热 " + hot + " · 交易所 " + cex,
    healthLevelSafe: "健康", healthLevelWarning: "注意", healthLevelHighRisk: "高风险",
    healthOk: "三项检查都通过，暂无需调整。",
    healthOnChainRisk: (pct) => "链上资产占 " + pct + "%，建议把其中一部分换成 BTC 以降低链上暴露。",
    healthConcentrationAdvice: (pct, wallet) => wallet + " 一个钱包就占 " + pct + "%，建议分散到多个钱包，或把一部分换成 BTC。",
    healthStorageAdvice: (pct) => "只有 " + pct + "% 放在冷存储，长期持有的部分建议放进硬件钱包。",
    healthStorageAdviceNone: "目前还没有冷存储，长期持有的部分建议放进硬件钱包。",
    healthNoData: "还没有快照——先刷新一次即可生成健康度报告。",
    shareBtn: "分享", shareTotal: "总资产", shareTop: "主要持仓",
    shareSnapshot: "快照", shareFiltered: "筛选后的视图", shareFail: "生成分享卡片失败。",
    shareTitle: "分享你的资产组合", shareClose: "关闭",
    shareDownload: "下载 PNG", shareCopyImg: "复制图片", shareCopyText: "复制文字",
    shareCopied: "已复制。", shareCopyImgFail: "当前浏览器不允许复制图片——请用「下载 PNG」。",
    shareCopyFail: "复制被拦截——文字已选中，按 ⌘/Ctrl+C 即可。",
    shareTextTpl: (total, change, date, top, repo) =>
      "我的资产组合（" + date + "）：" + total + (change ? " · " + change : "") +
      "\n主要持仓：" + top +
      "\n用 dsh-crypto-portfolio 自建追踪，全本地、无 CDN、私钥不出本机：" + repo +
      "\n#crypto #portfolio",
    shareHint: "把当前视图画成一张 PNG（不含任何地址）。",
    healthTier1: "BTC", healthTier2: "链上", healthTier3: "CEX", healthRest: "其他钱包",
    storageHot: "热钱包", storageCold: "冷钱包",
    storageTitle: "私钥放在哪里：冷 = 硬件/离线，热 = 浏览器或 App 钱包。交易所账户一律按交易所托管计算。",
    storageCex: "交易所", storageCol: "托管", storageMark: "冷存储",
    providersHint: "providers（付费优先，免费兜底）",
    getKey: "获取 API key",
    debankHint: "EVM 数据源 = DeBank。字段说明：base_url = API 地址（付费 pro 需要 pro 域名）；key = 付费源的 AccessKey，留空则走免费公开 API；chain_list_url = DeBank 特有的链列表接口（被墙/失效可换镜像）；chains = 可选，逗号分隔要抓取的链（如 eth,bsc,arb,base），留空抓全部。",
    urlPh: "API URL", chainListPh: "链列表接口（Debank 特有）", chainsPh: "可选：eth,bsc,arb,base（默认全部）",
    profileActive: "Profile",
    apiKey: "API Key", enabled: "启用", rpcLabel: "RPC 节点", splPricesLabel: "SPL 价格",
    birdeyeLabel: "Birdeye", srcKeyPh: "key（可选）", cexKeyPh: "api key", cexSecretPh: "api secret",
    cexPassPh: "passphrase",
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

const APP_VERSION = "20260919c";
console.log("[dsh-crypto-portfolio] app v" + APP_VERSION);

const t = (key, ...args) => {
  const d = I18N[lang] || I18N.en;
  let v = d[key] !== undefined ? d[key] : (I18N.en[key] !== undefined ? I18N.en[key] : key);
  if (typeof v === "function") v = v(...args);
  return v;
};
function applyI18n() {
  const v = document.getElementById("versionTag");
  if (v) v.textContent = APP_VERSION;   // the "v" prefix lives in the markup
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

const TABLE_PAGE = 200;

const PALETTE = ["#58a6ff", "#f0b95c", "#7ee787", "#d2a8ff", "#ff7b72", "#56d4dd",
                 "#ffa657", "#bc8cff", "#3fb950", "#e3b341", "#79c0ff", "#f85149"];
const TYPE_LABEL = { evm: "EVM", btc: "BTC", sol: "SOL", cex: "CEX", doge: "DOGE", ada: "ADA" };

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
  tableLimit: TABLE_PAGE,   // P1: rows rendered so far
  tableSig: "",             // P1: signature of the inputs the page belongs to
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
    $("lastUpdated").textContent = t("recorded") + " " +
      (state.view.created_at || "").replace("T", " ");
  }
  renderAll();
  // an open share dialog holds generated text; re-render it in the new language
  if ($("shareModal") && !$("shareModal").classList.contains("hidden")) openShare();
  if (!$("pageSettings").classList.contains("hidden")) renderSettings();
}

/* URL routing: #pageSettings opens the settings page, #pageSettings/secWallets
   also opens that section — so a page or a single settings section is linkable
   and a refresh lands back where the user was. Runs AFTER the remembered
   <details> state, otherwise the restore would close the linked section again. */
function applyHashRoute() {
  const parts = location.hash.replace(/^#/, "").split("/");
  if (parts[0] !== "pageSettings") return;
  const tab = document.querySelector('.tabs .tab[data-tab="pageSettings"]');
  if (tab) tab.click();
  const sec = parts[1] ? document.getElementById(parts[1]) : null;
  if (sec) { sec.open = true; sec.scrollIntoView(); }
}

/* Settings sections are native <details>; remember which were left open so the
   page keeps a user's working layout between visits. */
const SECTION_KEY = "pt_sections";
function readSectionState() {
  try { return JSON.parse(localStorage.getItem(SECTION_KEY) || "{}") || {}; }
  catch (e) { return {}; }
}
function restoreSectionState() {
  const saved = readSectionState();
  document.querySelectorAll("details.panel[id]").forEach((d) => {
    if (Object.prototype.hasOwnProperty.call(saved, d.id)) {
      d.open = !!saved[d.id];
    }
    d.addEventListener("toggle", () => {
      const s = readSectionState();
      s[d.id] = d.open;
      try { localStorage.setItem(SECTION_KEY, JSON.stringify(s)); } catch (e) { /* ignore */ }
    });
  });
}

/* The value-proposition line is part of the top bar, not a dismissible
   banner — there is nothing to initialise. Any stale "dismissed" flag from the
   earlier strip implementation is cleared so the line always shows. */
function initHeroStrip() {
  try { localStorage.removeItem("pt_hero_dismissed"); } catch (e) { /* ignore */ }
  const el = $("heroStrip");
  if (el) el.hidden = false;
}

async function init() {
  bindEvents();
  applyI18n();
  // A4: restore the persisted filter choice, but only onto options that exist
  loadFilters();
  if ([...$("filterCategory").options].some((o) => o.value === state.filters.category)) {
    $("filterCategory").value = state.filters.category;
  } else {
    state.filters.category = "all";
  }
  $("hideZero").checked = state.filters.hideZero;
  restoreSectionState();
  applyHashRoute();
  initHeroStrip();
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
    renderStablecoins();
    renderWalletMgmt();
    renderProfiles();   // populate header profile dropdown
  } catch (e) {
    showError(t("loadingFailed") + e.message);
  }
}

// A4: the filter choice is worth keeping across reloads, like theme and language
const FILTER_KEY = "pt_filters";
function saveFilters() {
  try {
    localStorage.setItem(FILTER_KEY, JSON.stringify({
      category: state.filters.category, wallet: state.filters.wallet,
      chain: state.filters.chain, hideZero: state.filters.hideZero,
    }));
  } catch (e) { /* ignore */ }
}
function loadFilters() {
  try {
    const raw = localStorage.getItem(FILTER_KEY);
    if (!raw) return;
    const f = JSON.parse(raw) || {};
    if (typeof f.category === "string") state.filters.category = f.category;
    if (typeof f.wallet === "string") state.filters.wallet = f.wallet;
    if (typeof f.chain === "string") state.filters.chain = f.chain;
    if (typeof f.hideZero === "boolean") state.filters.hideZero = f.hideZero;
  } catch (e) { /* ignore */ }
}

function bindEvents() {
  bindLabelPop();
  $("btnRefresh").addEventListener("click", refresh);
  // A6: ask the server to stop between wallets; nothing is written on cancel
  $("btnCancelRefresh").addEventListener("click", async () => {
    const b = $("btnCancelRefresh");
    b.disabled = true;
    b.textContent = t("cancelRequested");
    try { await postJSON("/api/refresh/cancel", {}); } catch (e) { /* surfaced by refresh() */ }
  });
  // S1: keys come back masked; this pulls the real values from this machine only
  $("btnRevealKeys").addEventListener("click", () => {
    state.revealKeys = !state.revealKeys;
    renderSources();
  });
  $("btnTheme").addEventListener("click", () => {
    theme = theme === "light" ? "dark" : "light";
    try { localStorage.setItem("pt_theme", theme); } catch (e) { /* ignore */ }
    document.documentElement.setAttribute("data-theme", theme);
    $("btnTheme").textContent = themeBtnIcon();
  });
  // share dialog: open from the header, close with ✕, Escape or a click outside
  $("btnShare").addEventListener("click", openShare);
  $("shareClose").addEventListener("click", closeShare);
  $("shareDownload").addEventListener("click", shareDownload);
  $("shareCopyImg").addEventListener("click", shareCopyImage);
  $("shareCopyText").addEventListener("click", shareCopyText);
  $("shareModal").addEventListener("click", (ev) => {
    if (ev.target === $("shareModal")) closeShare();
  });
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !$("shareModal").classList.contains("hidden")) closeShare();
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
    saveFilters();
  });
  $("filterWallet").addEventListener("change", (e) => { state.filters.wallet = e.target.value; saveFilters(); renderAll(); });
  $("filterChain").addEventListener("change", (e) => { state.filters.chain = e.target.value; saveFilters(); renderAll(); });
  // table locals
  $("search").addEventListener("input", (e) => { state.filters.search = e.target.value.trim().toLowerCase(); renderTable(); });
  $("hideZero").addEventListener("change", (e) => { state.filters.hideZero = e.target.checked; saveFilters(); renderTable(); });
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
  // tabs. The chosen page lives in the URL fragment so a refresh (or a link to
  // #pageSettings) lands back on the same page instead of resetting to the dashboard.
  document.querySelectorAll(".tabs .tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tabs .tab").forEach((x) => x.classList.remove("active"));
      btn.classList.add("active");
      const page = btn.dataset.tab;
      $("pageDashboard").classList.toggle("hidden", page !== "pageDashboard");
      $("pageSettings").classList.toggle("hidden", page !== "pageSettings");
      $("filterbar").classList.toggle("hidden", page !== "pageDashboard");
      try { history.replaceState(null, "", "#" + page); } catch (e) { /* ignore */ }
      if (page === "pageSettings") renderSettings();
    });
  });
  // profiles (schedule editing is per-profile — handled in the profileList delegate)
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
    // --- per-profile schedule: toggle its inline editor / save it ---
    const schedToggle = ev.target.closest("button[data-pf-sched]");
    if (schedToggle) {
      const nm = schedToggle.dataset.pfSched;
      const box = document.querySelector('[data-sched-box="' + CSS.escape(nm) + '"]');
      if (!box) return;
      const opening = box.hasAttribute("hidden");
      box.toggleAttribute("hidden", !opening);
      schedToggle.classList.toggle("open", opening);
      if (opening) {
        // always show the profile's CURRENT stored schedule
        try {
          const s = await api("/api/schedule?profile=" + encodeURIComponent(nm));
          const cb = box.querySelector("[data-sched-enabled]");
          const tm = box.querySelector("[data-sched-time]");
          const last = box.querySelector("[data-sched-last]");
          if (cb) cb.checked = !!s.enabled;
          if (tm) tm.value = s.time || "09:00";
          if (last) last.textContent = t("schedLastRun") + (s.last_run_date || t("never"));
        } catch (e) { /* ignore */ }
      }
      return;
    }
    const saveBtn = ev.target.closest("button[data-sched-save]");
    if (saveBtn) {
      const nm = saveBtn.dataset.schedSave;
      const box = document.querySelector('[data-sched-box="' + CSS.escape(nm) + '"]');
      if (!box) return;
      const msg = box.querySelector("[data-sched-msg]");
      try {
        const r = await postJSON("/api/schedule", {
          profile: nm,
          enabled: box.querySelector("[data-sched-enabled]").checked,
          time: box.querySelector("[data-sched-time]").value || "09:00",
        });
        if (msg) msg.textContent = t("schedSaved");
        const last = box.querySelector("[data-sched-last]");
        if (last) last.textContent = t("schedLastRun") + (r.last_run_date || t("never"));
        await renderProfiles();          // refresh the clock tag
        // re-open the editor the user was working in
        const again = document.querySelector('button[data-pf-sched="' + CSS.escape(nm) + '"]');
        const box2 = document.querySelector('[data-sched-box="' + CSS.escape(nm) + '"]');
        if (again && box2) { box2.removeAttribute("hidden"); again.classList.add("open"); }
      } catch (e) { if (msg) msg.textContent = t("saveFailed") + e.message; }
      return;
    }
    // --- profile row actions ---
    const btn = ev.target.closest("button[data-pf-action]");
    if (!btn) return;
    const name = btn.dataset.pfName;
    const act = btn.dataset.pfAction;
    if (act === "rename") {
      const input = prompt(t("renamePrompt") + "\n\n" + name, name);
      if (input == null) return;
      const newName = input.trim();
      if (!newName || newName === name) return;
      try {
        await postJSON("/api/profiles", { action: "rename", name, new_name: newName });
        await reloadViewData();     // the active profile may have been renamed
        await renderSettings();
      } catch (err) { alert(t("profileRenameFail") + err.message); }
      return;
    }
    // default action: delete
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
  $("btnAddLabelRule").addEventListener("click", async () => {
    const sym = $("labelSym").value.trim();
    const tid = $("labelTokenId").value.trim();
    const cat = $("labelName").value;
    const chain = $("labelChain").value.trim();
    if (!sym && !tid) { $("labelRuleMsg").textContent = t("atLeastOne"); return; }
    try {
      await postJSON("/api/labels", { entry: {
        symbol: sym, token_id: tid, chain, category: cat, action: "include" } });
      $("labelSym").value = ""; $("labelTokenId").value = ""; $("labelChain").value = "";
      $("labelRuleMsg").textContent = t("labelRuleSaved");
      renderStablecoins();
      await reloadViewData();
    } catch (e) { $("labelRuleMsg").textContent = t("labelRuleFailed") + e.message; }
  });
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
      storage: $("wlStorage") ? $("wlStorage").value : "hot",
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

// Per-type block explorers: a list of {url, label, logo} for a wallet's own
// address/history page. logo = file name (with extension) in static/logos/.
//
// Order matters: the explorer we actually fetch data from comes first, the
// rest follow in rough order of popularity for that chain. Chains with fewer
// than 5 credible explorers simply return fewer entries.
const EXPLORERS = {
  evm: [
    { label: "DeBank", logo: "debank.svg", tone: "light", url: (a) => "https://debank.com/profile/" + a + "/history" },
    { label: "Etherscan", logo: "etherscan.svg", url: (a) => "https://etherscan.io/address/" + a },
    { label: "Zerion", logo: "zerion.png", tone: "dark", url: (a) => "https://app.zerion.io/" + a + "/overview" },
    { label: "Blockscout", logo: "blockscout.png", tone: "dark", url: (a) => "https://eth.blockscout.com/address/" + a },
    { label: "Blockchair", logo: "blockchair.png", tone: "dark", url: (a) => "https://blockchair.com/ethereum/address/" + a },
  ],
  btc: [
    { label: "bitaps", logo: "bitaps.svg", tone: "light", url: (a) => "https://bitaps.com/" + a },
    { label: "mempool.space", logo: "mempool.png", tone: "dark", url: (a) => "https://mempool.space/address/" + a },
    { label: "Blockstream", logo: "blockstream.png", tone: "light", url: (a) => "https://blockstream.info/address/" + a },
    { label: "Blockchain.com", logo: "blockchain.png", tone: "dark", url: (a) => "https://www.blockchain.com/explorer/addresses/btc/" + a },
    { label: "Blockchair", logo: "blockchair.png", tone: "dark", url: (a) => "https://blockchair.com/bitcoin/address/" + a },
  ],
  sol: [
    { label: "Jupiter", logo: "jupiter.svg", url: (a) => "https://jup.ag/portfolio/" + a },
    { label: "Solscan", logo: "solscan.png", tone: "light", url: (a) => "https://solscan.io/account/" + a },
    { label: "Solana Explorer", logo: "solanaexp.png", tone: "dark", url: (a) => "https://explorer.solana.com/address/" + a },
    { label: "SolanaFM", logo: "solanafm.png", tone: "light", url: (a) => "https://solana.fm/address/" + a },
    { label: "Birdeye", logo: "birdeye.png", tone: "dark", url: (a) => "https://birdeye.so/solana/owner/" + a },
  ],
  doge: [
    { label: "Dogechain", logo: "doge.svg", tone: "light", url: (a) => "https://dogechain.info/address/" + a },
    { label: "Blockchair", logo: "blockchair.png", tone: "dark", url: (a) => "https://blockchair.com/dogecoin/address/" + a },
    { label: "BlockCypher", logo: "blockcypher.png", tone: "dark", url: (a) => "https://live.blockcypher.com/doge/address/" + a },
  ],
  ada: [
    { label: "Cardanoscan", logo: "cardanoscan.png", tone: "dark", url: (a) => "https://cardanoscan.io/address/" + a },
    { label: "CExplorer", logo: "cexplorer.png", tone: "dark", url: (a) => "https://cexplorer.io/address/" + a },
    { label: "Cardano Explorer", logo: "cardanoexp.png", tone: "light", url: (a) => "https://explorer.cardano.org/address/" + a },
    { label: "AdaStat", logo: "adastat.png", tone: "light", url: (a) => "https://adastat.net/addresses/" + a },
  ],
};

function walletExplorers(type, address, name) {
  const a = (address || "").trim();
  const list = EXPLORERS[type];
  if (list && a) {
    return list.map((e) => ({ url: e.url(encodeURIComponent(a)), logo: e.logo,
                              label: e.label, tone: e.tone || null }));
  }
  if (type === "cex") {
    // CEX accounts have no external explorer page: show the exchange mark only.
    const n = (name || "").toLowerCase();
    if (n.includes("binance")) return [{ url: null, logo: "binance.svg", label: "Binance" }];
    if (n.includes("bybit"))   return [{ url: null, logo: "bybit.svg", label: "Bybit" }];
    if (n.includes("backpack")) return [{ url: null, logo: "backpack.svg", label: "Backpack" }];
    return [{ url: null, logo: "evm.svg", label: "CEX" }];
  }
  return [];
}

function fillDateSelect(dates) {
  const sel = $("dateSelect");
  sel.innerHTML = "";
  // A5: the newest date is called out, so "which day am I looking at" needs no guessing
  const newest = dates.length ? dates[dates.length - 1] : null;
  for (const d of dates) {
    const o = document.createElement("option");
    o.value = d;
    o.textContent = d + " (" + t("snapDate") + ")" + (d === newest ? " · " + t("latest") : "");
    sel.appendChild(o);
  }
}

function chainName(id) {
  return state.chains[id] || id || "—";
}

/**
 * wallet name -> share of the current view's total, as a percentage number.
 * Derived from the same token-summed per-wallet values the pie and its legend
 * use, so the figure printed on a wallet card always equals the legend's.
 */
function walletShares() {
  const v = filteredView({ ignoreWallet: true });
  const total = (v && v.total_usd) || 0;
  const map = {};
  for (const w of (v && v.wallets) || []) {
    map[w.wallet] = total > 0 ? ((w.total_usd || 0) / total) * 100 : 0;
  }
  return map;
}

/* ---------------- filtered views ---------------- */
/**
 * @param opts.ignoreWallet - drop the wallet filter for this call. The wallet
 *   cards need it: they always render every wallet in the category, and while
 *   one wallet is selected the pie collapses to that single wallet, so a share
 *   read off the filtered view would print 100% on every card.
 */
function filteredView(opts) {
  if (!state.view) return null;
  const f = state.filters;
  const ignoreWallet = !!(opts && opts.ignoreWallet);
  const walletSet = state.view.wallets.filter((w) =>
    (f.category === "all" || w.type === f.category) &&
    (ignoreWallet || !f.wallet || w.wallet === f.wallet));
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
    state.labels = tokens.labels || state.labels;
    state.labelNames = tokens.label_names || state.labelNames || {};
    state.builtinLabels = tokens.builtin_labels || state.builtinLabels || [];
    renderAll();
    $("tokenDate").textContent = "(" + t("snapDate") + " " + date + ")";
    // only the "recorded at" half: the snapshot date is already in the picker and
    // the panel title, so printing it here too was noise
    $("lastUpdated").textContent = t("recorded") + " " +
      (view.created_at || "").replace("T", " ");
    // A5: make it obvious when this view is history rather than the latest run
    const isLatest = !state.dates.length || date === state.dates[state.dates.length - 1];
    $("historyNote").classList.toggle("hidden", isLatest);
  } catch (e) {
    showError(t("loadingFailed") + e.message);
  }
}

/**
 * Names the focused wallet in the title of every panel below the wallet cards.
 * A card click does not scroll the page, so these titles are what tells the
 * reader that the panels underneath are showing one wallet rather than all.
 */
function updateFilterChips() {
  const w = state.filters.wallet || "";
  document.querySelectorAll("[data-filter-chip]").forEach((el) => {
    el.textContent = w ? "· " + w : "";
  });
}

/* ---------- asset health (server-computed: tracker/health.py) ---------- */
// The report is computed from the blacklist-filtered snapshot on the server, so
// the three figures here always agree with the dashboard totals. It is
// deliberately NOT filter-aware: hiding the CEX wallets would change the tiering
// maths and turn a real risk figure into a misleading one.
const HEALTH_COLORS = { tier1: "#f7931a", tier2: "#627eea", tier3: "#8b5cf6",
                        cold: "#3fb950", hot: "#d29922", cex: "#f85149",
                        rest: "#30363d" };

function healthLevelLabel(level) {
  if (level === "highRisk") return t("healthLevelHighRisk");
  if (level === "warning") return t("healthLevelWarning");
  return t("healthLevelSafe");
}

// Every card's bar is a composition, not a repeat of the headline figure: the
// figure says how much of the risky thing there is, the bar says where it sits.
function healthSegments(parts) {
  return '<div class="health-stack">' + parts.map((seg) =>
    '<div class="health-seg" style="width:' + (seg.pct || 0).toFixed(1) + "%;background:" +
      seg.color + '" title="' + esc(seg.title + " " + (seg.pct || 0).toFixed(1) + "%" +
      (seg.usd ? " · " + seg.usd : "")) + '"></div>').join("") + "</div>";
}

function healthCard(nameKey, level, figure, segments, hint, sub) {
  return '<div class="health-card" data-level="' + esc(level) + '">' +
    '<div class="health-head"><span class="health-name">' + esc(t(nameKey)) + "</span>" +
      '<span class="health-pill ' + esc(level) + '">' + esc(healthLevelLabel(level)) + "</span></div>" +
    '<div class="health-figure">' + esc(figure) + "</div>" +
    healthSegments(segments) +
    '<div class="health-sub">' + esc(sub) + "</div>" +
    '<div class="health-hint">' + esc(t(hint)) + "</div></div>";
}

function renderHealth() {
  const grid = $("healthGrid");
  const advice = $("healthAdvice");
  if (!grid || !advice) return;
  const h = state.view && state.view.health;
  if (!h) { grid.innerHTML = ""; advice.innerHTML = '<span class="hint">' + t("healthNoData") + "</span>"; return; }

  const pct = (x) => (x || 0).toFixed(1) + "%";
  const tiers = h.tiering.tiers;
  const store = h.storage.storage;
  const conc = h.concentration;

  grid.innerHTML =
    healthCard("healthTiering", h.tiering.onChainRiskLevel, pct(tiers.tier2.percent),
      [{ pct: tiers.tier1.percent, color: HEALTH_COLORS.tier1, title: t("healthTier1"), usd: fmtUsd(tiers.tier1.balance) },
       { pct: tiers.tier2.percent, color: HEALTH_COLORS.tier2, title: t("healthTier2"), usd: fmtUsd(tiers.tier2.balance) },
       { pct: tiers.tier3.percent, color: HEALTH_COLORS.tier3, title: t("healthTier3"), usd: fmtUsd(tiers.tier3.balance) }],
      "healthTieringHint",
      t("healthTieringSub", fmtUsd(tiers.tier1.balance), fmtUsd(tiers.tier2.balance),
        fmtUsd(tiers.tier3.balance))) +
    healthCard("healthConcentration", conc.level, pct(conc.percent),
      [{ pct: conc.percent, color: conc.maxWalletIsBtc ? HEALTH_COLORS.tier1 : HEALTH_COLORS.tier2,
         title: conc.maxWallet || t("noData"), usd: fmtUsd(conc.maxWalletUsd || 0) },
       { pct: 100 - conc.percent, color: HEALTH_COLORS.rest, title: t("healthRest") }],
      "healthConcentrationHint",
      conc.maxWallet ? t("healthConcentrationSub", conc.maxWallet, fmtUsd(conc.maxWalletUsd || 0))
                     : t("noData")) +
    healthCard("healthStorage", h.storage.securityLevel, pct(store.cold.percent),
      [{ pct: store.cold.percent, color: HEALTH_COLORS.cold, title: t("storageCold"), usd: fmtUsd(store.cold.balance) },
       { pct: store.hot.percent, color: HEALTH_COLORS.hot, title: t("storageHot"), usd: fmtUsd(store.hot.balance) },
       { pct: store.cex.percent, color: HEALTH_COLORS.cex, title: t("storageCex"), usd: fmtUsd(store.cex.balance) }],
      "healthStorageHint",
      t("healthStorageSub", pct(store.cold.percent), pct(store.hot.percent), pct(store.cex.percent)));

  // each suggestion key is an i18n function taking what its sentence needs; the
  // "%" belongs to the sentence, so the number is passed on its own
  const num = (x) => (x || 0).toFixed(1);
  advice.innerHTML = h.suggestions.map((sg) => {
    let body;
    if (sg.key === "healthOk") body = t(sg.key);
    else if (sg.key === "healthConcentrationAdvice") body = t(sg.key, num(sg.pct), sg.wallet);
    else if (sg.key === "healthStorageAdvice" && !(sg.pct > 0.05)) body = t("healthStorageAdviceNone");
    else body = t(sg.key, num(sg.pct));
    return '<div class="health-item ' + esc(sg.level) + '">' +
      '<span class="health-dot"></span><span>' + esc(body) + "</span></div>";
  }).join("");
}

/* ---------- share card (hand-drawn PNG, no html2canvas) ---------- */
// 1200x630 is the link-preview / X card ratio. Everything is drawn with the 2D
// context on an offscreen canvas, so there is no library to vendor and no DOM to
// screenshot: the card is deterministic and works in any browser.
// Privacy: the card carries totals, symbols and label names — never an address.
const SHARE_W = 1200, SHARE_H = 630;
const SHARE_THEME = { bg: "#0d1117", panel: "#161b22", border: "#2a3242",
                      text: "#e6edf3", muted: "#8b98a9", accent: "#58a6ff",
                      success: "#3fb950", danger: "#f85149", warning: "#d29922" };
const SHARE_FONT = '-apple-system, "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif';

function shareRoundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function shareText(ctx, text, x, y, opts) {
  const o = opts || {};
  ctx.font = (o.weight || 400) + " " + (o.size || 14) + "px " + SHARE_FONT;
  ctx.fillStyle = o.color || SHARE_THEME.text;
  ctx.textAlign = o.align || "left";
  ctx.textBaseline = o.baseline || "alphabetic";
  ctx.fillText(text, x, y);
  return ctx.measureText(text).width;
}

function shareLevelColor(level) {
  return level === "highRisk" ? SHARE_THEME.danger
    : (level === "warning" ? SHARE_THEME.warning : SHARE_THEME.success);
}

/** Everything the card shows, derived from the same view the dashboard renders. */
function shareCardData() {
  const v = filteredView();
  if (!v) return null;
  const byCat = typeTotals();
  const order = state.labels || ["other"];
  const pie = order.map((k, i) => ({ name: labelText(k), value: byCat[k] || 0, color: labelColor(k, i) }))
    .filter((it) => it.value > 0).sort((a, b) => b.value - a.value);
  const pieTotal = pie.reduce((a, it) => a + it.value, 0);
  return {
    total: v.total_usd,
    change: state.view.change_usd,
    changePct: state.view.change_pct,
    prevDate: state.view.prev_date,
    created: state.view.created_at,
    filtered: !!v.filtered,
    pie: pie, pieTotal: pieTotal,
    top: topHoldings(5),
    health: state.view.health || null,
  };
}

/** Largest holdings by SYMBOL (not by row): the same coin in two wallets is one
 *  line on the card. The label colour comes from the row's asset label. */
function topHoldings(limit) {
  const bySymbol = new Map();
  (state.tokens || []).forEach((x) => {
    if (!(x.usd > 0)) return;
    const key = String(x.symbol || "");
    const prev = bySymbol.get(key);
    if (prev) prev.usd += x.usd;
    else bySymbol.set(key, { symbol: key, usd: x.usd, cat: x.cat, chain: x.chain });
  });
  return Array.from(bySymbol.values()).sort((a, b) => b.usd - a.usd).slice(0, limit || 5);
}

function drawShareCard(ctx, data) {
  const T = SHARE_THEME;
  ctx.clearRect(0, 0, SHARE_W, SHARE_H);
  // card body
  shareRoundRect(ctx, 0, 0, SHARE_W, SHARE_H, 28);
  ctx.fillStyle = T.bg;
  ctx.fill();
  ctx.strokeStyle = T.border;
  ctx.lineWidth = 2;
  ctx.stroke();

  // header
  shareText(ctx, t("brand"), 56, 74, { size: 20, weight: 700 });
  shareText(ctx, t("shareSnapshot") + " " + state.selectedDate, SHARE_W - 56, 74,
            { size: 15, color: T.muted, align: "right" });
  shareText(ctx, APP_VERSION ? "dsh-crypto-portfolio " + APP_VERSION : "dsh-crypto-portfolio",
            SHARE_W - 56, 98, { size: 12, color: T.muted, align: "right" });

  // left column — the number a share card is about
  shareText(ctx, t("shareTotal"), 56, 158, { size: 14, color: T.muted });
  shareText(ctx, fmtUsdFull(data.total), 56, 218, { size: 52, weight: 700 });
  if (data.filtered) {
    shareText(ctx, t("shareFiltered"), 56, 254, { size: 16, color: T.accent });
  } else if (data.change != null) {
    const up = data.change >= 0;
    shareText(ctx, (up ? "▲ +" : "▼ ") + fmtUsd(Math.abs(data.change)) +
      "  (" + fmtPct(data.changePct || 0) + ")   vs " + data.prevDate, 56, 254,
      { size: 17, weight: 600, color: up ? T.success : T.danger });
  }
  ctx.strokeStyle = T.border;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(56, 288); ctx.lineTo(608, 288); ctx.stroke();

  shareText(ctx, t("shareTop"), 56, 326, { size: 14, color: T.muted });
  data.top.forEach((row, i) => {
    const y = 356 + i * 34;
    const col = labelColor((state.labels || []).includes(row.cat) ? row.cat : "other",
                           (state.labels || []).indexOf(row.cat));
    ctx.beginPath();
    ctx.arc(62, y - 5, 5, 0, Math.PI * 2);
    ctx.fillStyle = col;
    ctx.fill();
    const symbol = String(row.symbol || "").slice(0, 14);
    shareText(ctx, symbol, 80, y, { size: 17, weight: 600 });
    shareText(ctx, fmtUsd(row.usd), 608, y, { size: 17, weight: 600, align: "right" });
  });

  // right column — asset-type donut with its legend beside it (stacking the two
  // pushed the last legend rows into the footer pills)
  const cx = 838, cy = 292, outer = 96, inner = 58;
  let angle = -Math.PI / 2;
  const donutTotal = data.pieTotal || 0;
  if (!donutTotal) {
    ctx.beginPath();
    ctx.arc(cx, cy, (outer + inner) / 2, 0, Math.PI * 2);
    ctx.strokeStyle = "rgba(120,140,170,.3)";
    ctx.lineWidth = outer - inner;
    ctx.stroke();
  }
  data.pie.forEach((it) => {
    const sweep = (it.value / donutTotal) * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(cx, cy, outer, angle, angle + sweep);
    ctx.arc(cx, cy, inner, angle + sweep, angle, true);
    ctx.closePath();
    ctx.fillStyle = it.color;
    ctx.fill();
    angle += sweep;
  });
  shareText(ctx, t("typeShareCap"), 960, 186, { size: 14, color: T.muted });
  data.pie.slice(0, 6).forEach((it, i) => {
    const y = 216 + i * 26;
    ctx.beginPath();
    ctx.arc(966, y - 5, 5, 0, Math.PI * 2);
    ctx.fillStyle = it.color;
    ctx.fill();
    shareText(ctx, String(it.name).slice(0, 12), 982, y, { size: 14 });
    shareText(ctx, donutTotal ? ((it.value / donutTotal) * 100).toFixed(1) + "%" : "0%",
              SHARE_W - 56, y, { size: 14, color: T.muted, align: "right" });
  });

  // footer — the health verdicts, so the card says something about risk too
  const h = data.health;
  if (h) {
    const pills = [
      { name: t("healthTiering"), level: h.tiering.onChainRiskLevel },
      { name: t("healthConcentration"), level: h.concentration.level },
      { name: t("healthStorage"), level: h.storage.securityLevel },
    ];
    let x = 56;
    pills.forEach((pl) => {
      const label = pl.name + " · " + healthLevelLabel(pl.level);
      ctx.font = "600 14px " + SHARE_FONT;
      const w = ctx.measureText(label).width + 26;
      shareRoundRect(ctx, x, SHARE_H - 76, w, 30, 15);
      ctx.fillStyle = "rgba(255,255,255,.04)";
      ctx.fill();
      ctx.strokeStyle = shareLevelColor(pl.level);
      ctx.lineWidth = 1;
      ctx.stroke();
      shareText(ctx, label, x + 13, SHARE_H - 56, { size: 14, weight: 600,
                color: shareLevelColor(pl.level) });
      x += w + 12;
    });
  }
}

/* Public project page: the social intents need a URL to attach, and it is the
   honest thing to share alongside a screenshot of your own numbers. */
const SHARE_REPO = "https://github.com/0xRabit/dsh-crypto-portfolio";

function shareFileName() {
  return "portfolio-" + (state.selectedDate || "snapshot") + ".png";
}

/** The text that goes with the card: facts first, no marketing. */
function shareTextFor(data) {
  const up = (data.change || 0) >= 0;
  const change = data.change == null ? ""
    : (up ? "\u25b2 +" : "\u25bc ") + fmtUsd(Math.abs(data.change)) +
      " (" + fmtPct(data.changePct || 0) + ")";
  const top = (data.top || []).slice(0, 3)
    .map((r) => r.symbol + " " + fmtUsd(r.usd)).join(" · ");
  return t("shareTextTpl", fmtUsdFull(data.total), change, state.selectedDate || "", top, SHARE_REPO);
}

let _shareState = { blob: null, text: "" };

function openShare() {
  const data = shareCardData();
  if (!data) { alert(t("shareFail")); return; }
  const canvas = document.createElement("canvas");
  canvas.width = SHARE_W;
  canvas.height = SHARE_H;
  drawShareCard(canvas.getContext("2d"), data);

  const text = shareTextFor(data);
  _shareState = { blob: null, text: text };
  $("shareImg").src = canvas.toDataURL("image/png");
  $("shareText").value = text;
  $("shareMsg").textContent = "";
  // intents: X and WhatsApp take the text, Facebook and Telegram want a URL too
  const enc = encodeURIComponent;
  $("shareX").href = "https://twitter.com/intent/tweet?text=" + enc(text);
  $("shareWa").href = "https://wa.me/?text=" + enc(text);
  $("shareFb").href = "https://www.facebook.com/sharer/sharer.php?u=" + enc(SHARE_REPO) +
    "&quote=" + enc(text);
  $("shareTg").href = "https://t.me/share/url?url=" + enc(SHARE_REPO) + "&text=" + enc(text);
  if (canvas.toBlob) canvas.toBlob((blob) => { _shareState.blob = blob; }, "image/png");
  $("shareModal").classList.remove("hidden");
  $("btnShare").setAttribute("aria-expanded", "true");
}

function closeShare() {
  $("shareModal").classList.add("hidden");
  if ($("btnShare").setAttribute) $("btnShare").setAttribute("aria-expanded", "false");
}

function shareDownload() {
  if (!_shareState.blob) { alert(t("shareFail")); return; }
  const url = URL.createObjectURL(_shareState.blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = shareFileName();
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

async function shareCopyImage() {
  // posting the picture directly is what most people want; the Clipboard API
  // refuses anything but a user gesture, which this click is
  try {
    if (!navigator.clipboard || !window.ClipboardItem || !_shareState.blob) throw new Error("unsupported");
    await navigator.clipboard.write([new ClipboardItem({ "image/png": _shareState.blob })]);
    $("shareMsg").textContent = t("shareCopied");
  } catch (e) {
    $("shareMsg").textContent = t("shareCopyImgFail");
  }
}

async function shareCopyText() {
  try {
    await navigator.clipboard.writeText($("shareText").value);
    $("shareMsg").textContent = t("shareCopied");
  } catch (e) {
    // clipboard can be blocked (insecure origin, permissions); the textarea is
    // already there, so selecting it is a usable fallback
    $("shareText").select();
    $("shareMsg").textContent = t("shareCopyFail");
  }
}

function renderAll() {
  updateFilterChips();
  renderTypePie();
  renderSummary();
  renderWalletCards();
  renderChainBars();
  renderHealth();
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
  if (!state.view) return;
  const f = state.filters;
  const selected = f.wallet;
  // Show ALL wallets in the current category (not just the selected one), so
  // selecting a wallet grays the others instead of hiding them.
  const list = state.view.wallets
    .filter((w) => (f.category === "all" || w.type === f.category))
    .sort((a, b) => (b.total_usd || 0) - (a.total_usd || 0));
  $("walletCount").textContent = "(" + list.length + ")";
  const shares = walletShares();
  list.forEach((w) => {
    const card = document.createElement("div");
    const isSel = selected === w.wallet;
    const wlogo = typeLogoFile(w.type);
    const plats = walletExplorers(w.type, w.address, w.wallet);
    card.className = "card" + (isSel ? " active" : "") + (selected ? " dimmed" : "");
    // A1: the card is a control, so it must be reachable and operable by keyboard
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-pressed", isSel ? "true" : "false");
    card.setAttribute("aria-label", (isSel ? t("deselectHint") + ": " : "") +
      w.wallet + " " + fmtUsd(w.total_usd) + " " + w.type);
    // The card is a fixed four-row stack:
    //   1 wallet name   2 balance   3 address + copy   4 type badge | explorers
    // The deselect hint used to occupy the footer, but row 4 must hold the badge
    // plus up to five explorer icons; on a narrow card the hint pushed that row
    // past the card width, so it lives in the card tooltip instead.
    if (isSel) card.title = t("deselectHint");
    card.innerHTML =
      // row 1 — name only: with the badge gone the name gets the full card width.
      // It truncates rather than wraps, so the full name is also the tooltip.
      '<div class="w-name"><img class="logo-img" src="/static/logos/' + wlogo + '.svg" alt="">' +
        '<span class="w-name-txt" title="' + esc(w.wallet) + '">' + esc(w.wallet) + "</span>" +
        // cold storage is worth a mark; hot is the default and stays unmarked so
        // the row keeps the width it needs for long wallet names
        (w.storage === "cold" ? '<span class="w-cold" title="' + esc(t("storageMark")) + '">❄</span>' : "") +
        "</div>" +
      // row 2 — balance, with this wallet's share of the total right after it
      '<div class="w-usd">' + fmtUsd(w.total_usd) +
        '<span class="w-share">' + (shares[w.wallet] || 0).toFixed(1) + "%</span></div>" +
      // row 3 — address + copy button
      '<div class="w-addr">' + esc(shortAddr(w.address, 10)) +
        ' <button class="w-copy" data-addr="' + esc(w.address) + '" title="' + esc(t("copyAddr")) + '">' +
          '<svg class="copy-icon" viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg></button></div>' +
      // row 4 — top-level type badge on the left, block explorers on the right
      '<div class="w-foot">' +
        '<span class="badge ' + esc(w.type) + '">' + (TYPE_LABEL[w.type] || w.type) + "</span>" +
        (plats.length
          ? '<div class="w-plats">' + plats.map((p) => {
              const cls = "w-plat" + (p.tone ? " tone-" + p.tone : "");
              const img = '<img src="/static/logos/' + esc(p.logo) + '" alt="' + esc(p.label) + '" loading="lazy">';
              return p.url
                ? '<a class="' + cls + '" href="' + esc(p.url) + '" target="_blank" rel="noopener" title="' + esc(p.label) + '">' + img + "</a>"
                : '<span class="' + cls + '" title="' + esc(p.label) + '">' + img + "</span>";
            }).join("") + "</div>"
          : "") +
      "</div>";
    // copy-to-clipboard (icon only; no visible text)
    const copyBtn = card.querySelector(".w-copy");
    if (copyBtn) copyBtn.addEventListener("click", async (e) => {
      e.stopPropagation();
      try {
        await navigator.clipboard.writeText(copyBtn.dataset.addr);
        copyBtn.classList.add("done");
        setTimeout(() => copyBtn.classList.remove("done"), 1400);
      } catch (err) { /* ignore */ }
    });
    // explorer icons link out; don't let the click toggle the wallet filter
    card.querySelectorAll("a.w-plat").forEach((el) =>
      el.addEventListener("click", (e) => e.stopPropagation()));
    card.addEventListener("click", () => {
      // toggle: clicking the already-selected wallet restores all
      if (state.filters.wallet === w.wallet) {
        state.filters.wallet = "";
      } else {
        state.filters.wallet = w.wallet;
      }
      $("filterWallet").value = state.filters.wallet;
      fillFilterSelects();
      renderAll();
      // NOTE: deliberately no scrollIntoView here. Jumping the page on every
      // card click disoriented the reader; the panels below announce the active
      // wallet in their own titles instead.
    });
    wrap.appendChild(card);
    // A1: Enter/Space are what a keyboard user expects from a button
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " " || e.key === "Spacebar") {
        e.preventDefault();
        card.click();
      }
    });
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
  // P1: with "Hide USD≈0" off this list can reach ~1.4k rows (~12k DOM nodes) in a
  // single innerHTML. Page it instead: the first slice renders immediately and the
  // rest arrives on demand. The page resets whenever the result set changes, which
  // is detected from a signature of every input that can change it.
  const sig = JSON.stringify([f.category, f.wallet, f.chain, f.search, f.hideZero,
                              state.selectedDate, state.sortKey, state.sortDir]);
  if (sig !== state.tableSig) {
    state.tableSig = sig;
    state.tableLimit = TABLE_PAGE;
  }
  const shown = rows.slice(0, state.tableLimit);
  $("tokenCount").textContent = t("items", rows.length) +
    (rows.length > shown.length ? " · " + shown.length + "/" + rows.length : "");
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:24px">' +
      (state.view ? t("noMatch") : t("noData")) + "</td></tr>";
    return;
  }
  tbody.innerHTML = shown.map((x) =>
    '<tr>' +
    '<td class="sym">' + (x.logo ? '<img src="' + esc(x.logo) + '" loading="lazy" onerror="this.style.visibility=\'hidden\'">' : '<span class="dot"></span>')
      + esc(x.symbol) + "</td>" +
    '<td class="muted">' + esc(x.name || "") + "</td>" +
    '<td><span class="chain-tag"><img class="logo-img" src="' + chainLogo(x.chain) + '" alt="">' + esc(chainName(x.chain)) + "</span></td>" +
    '<td>' + esc(x.wallet) + "</td>" +
    '<td class="num amount">' + fmtAmount(x.amount) + "</td>" +
    '<td class="num">' + fmtUsd(x.price) + "</td>" +
    '<td class="num">' + fmtUsd(x.usd) + "</td>" +
    // one row carries exactly one label, so this is a single-select; picking one
    // writes a rule for this exact token, and the server replaces any previous
    // rule for the same target so the last choice is the one that sticks
    // a chip that opens the shared label picker: pick, create or rename
    '<td class="op stable-col"><button type="button" class="cat-chip cat-' + esc(x.cat || "other") + '"' +
      ' data-wallet="' + esc(x.wallet) + '" data-symbol="' + esc(x.symbol) + '"' +
      ' data-token-id="' + esc(x.token_id || "") + '" data-chain="' + esc(x.chain) + '"' +
      ' data-cat="' + esc(x.cat || "other") + '">' +
      esc(labelText(x.cat || "other")) + "</button></td>" +
    '<td class="op"><button class="bl-btn" data-wallet="' + esc(x.wallet) + '"' +
      ' data-symbol="' + esc(x.symbol) + '" data-name="' + esc(x.name || "") + '"' +
      ' data-token-id="' + esc(x.token_id || "") + '" data-chain="' + esc(x.chain) + '">' + t("blBtn") + "</button></td>" +
    "</tr>"
  ).join("");
  // The tag toggles an exact-token rule, so a wildcard hit or the price
  // heuristic can be corrected for one asset without editing the built-in list.
  tbody.querySelectorAll(".cat-chip").forEach((b) => b.addEventListener("click", (e) => {
    e.stopPropagation();
    popOpen(b, { token_id: b.dataset.tokenId || "", symbol: b.dataset.symbol,
                     chain: b.dataset.chain, cat: b.dataset.cat });
  }));

  // P1: offer the next page rather than pushing every remaining row into the DOM
  if (rows.length > shown.length) {
    const moreRow = document.createElement("tr");
    moreRow.className = "table-more";
    const cell = document.createElement("td");
    cell.colSpan = 8;
    const more = document.createElement("button");
    more.className = "btn-ghost";
    more.textContent = t("showMore") + " " +
      Math.min(TABLE_PAGE, rows.length - shown.length) + " / " +
      (rows.length - shown.length) + " " + t("remaining");
    more.addEventListener("click", () => {
      state.tableLimit += TABLE_PAGE;
      renderTable();
    });
    cell.appendChild(more);
    moreRow.appendChild(cell);
    tbody.appendChild(moreRow);
  }}

/* ---------------- asset type donut ---------------- */
// Three buckets: stablecoins / bitcoin / other. The server classifies each token
// (tracker/stablecoins.py) and ships a `cat` field, so the client only aggregates.
// Fixed hues for the labels the system detects itself; anything the user invents
// takes the next palette colour, so a custom label still gets its own slice.
const LABEL_COLORS = { stable: "#3fb950", btc: "#f0b95c", eth: "#8b7cf6",
                       sol: "#14f195", hype: "#2dd4bf", other: "#58a6ff" };
const LABEL_PALETTE = ["#f778ba", "#e3b341", "#79c0ff", "#ffa657", "#a5d6ff", "#d2a8ff"];
function labelColor(name, idx) {
  return LABEL_COLORS[name] || LABEL_PALETTE[idx % LABEL_PALETTE.length];
}
/** Display name: translated for the auto labels, verbatim for an invented one. */
function labelText(name) {
  // a user-chosen display name wins; then the translated built-in; then the raw id
  const custom = (state.labelNames || {})[name];
  if (custom) return custom;
  const key = { stable: "catStable", btc: "catBtc", eth: "catEth", sol: "catSol",
                hype: "catHype", other: "catOther" }[name];
  return key ? t(key) : name;
}
function labelIsBuiltin(name) {
  return (state.builtinLabels || []).includes(name);
}

/** USD per asset-type bucket over the same filtered rows the table shows. */
function typeTotals() {
  const f = state.filters;
  const names = new Set((state.view && state.view.wallets ? state.view.wallets : [])
    .filter((w) => (f.category === "all" || w.type === f.category) &&
                   (!f.wallet || w.wallet === f.wallet))
    .map((w) => w.wallet));
  const totals = {};
  for (const label of state.labels || ["other"]) totals[label] = 0;
  for (const x of state.tokens || []) {
    if (!names.has(x.wallet)) continue;
    if (f.chain && x.chain !== f.chain) continue;
    // the server assigns one label per row; anything unknown lands in "other"
    const cat = (state.labels || []).includes(x.cat) ? x.cat : "other";
    totals[cat] = (totals[cat] || 0) + (Number(x.usd) || 0);
  }
  return totals;
}

function renderTypePie() {
  // NOTE: do not name this `t` — that shadows the global t() translator used
  // two lines down, and the TypeError takes the whole renderAll() with it.
  const byCat = typeTotals();
  const order = state.labels || ["other"];
  const items = order.map((k, i) => ({ label: labelText(k), value: byCat[k] || 0,
                                       color: labelColor(k, i) }))
    .filter((it) => it.value > 0);
  const total = order.reduce((a, k) => a + (byCat[k] || 0), 0);
  drawPie($("typePie"), items, total, "typePieTip");
  const pctOf = (k) => (total ? ((byCat[k] || 0) / total) * 100 : 0);
  // only labels that actually carry value appear in the legend, so a user with no
  // HYPE is not shown an empty row
  $("typeLegend").innerHTML = order.filter((k) => (byCat[k] || 0) > 0).map((k) =>
    '<div class="type-row" data-label="' + esc(k) + '">' +
      '<span class="t-dot" style="background:' + labelColor(k, order.indexOf(k)) + '"></span>' +
      '<span class="lg-name">' + esc(labelText(k)) + "</span>" +
      '<span class="lg-pct">' + pctOf(k).toFixed(1) + "%</span></div>").join("");
  // A2: text alternative for the second canvas
  $("typePie").setAttribute("aria-label", t("typeShareCap") + ": " +
    order.map((k) => labelText(k) + " " + pctOf(k).toFixed(1) + "%").join(", "));
}


/* ---------------- label picker (Notion-style) ----------------
   One popover shared by every row: type to filter, Enter or click to apply, and a
   "Create …" entry appears for any name that does not exist yet. Each row also
   offers rename and delete, so labels are managed where they are used instead of
   only in Settings. */
const labelPop = {
  row: null,        // { token_id, symbol, chain } of the row being edited
  active: 0,        // keyboard highlight
  items: [],        // [{label, create?:bool}]
};

function popOpen(anchorEl, row) {
  labelPop.row = row;
  const pop = $("labelPop");
  pop.classList.remove("hidden");
  const search = $("labelPopSearch");
  search.value = "";
  popRender("");
  // place it under the chip, nudged to stay inside the viewport
  const r = anchorEl.getBoundingClientRect();
  const w = pop.offsetWidth || 230;
  let left = Math.min(r.left + window.scrollX, window.scrollX + document.documentElement.clientWidth - w - 8);
  pop.style.left = Math.max(8, left) + "px";
  pop.style.top = (r.bottom + window.scrollY + 4) + "px";
  search.focus();
}

function popClose() {
  $("labelPop").classList.add("hidden");
  labelPop.row = null;
}

function popRender(filter) {
  const q = (filter || "").trim();
  const lower = q.toLowerCase();
  const labels = state.labels || ["other"];
  const shown = labels.filter((l) => !lower || l.toLowerCase().includes(lower));
  const exact = labels.some((l) => l.toLowerCase() === lower);
  labelPop.items = [];
  if (q && !exact) labelPop.items.push({ label: q, create: true });
  shown.forEach((l) => labelPop.items.push({ label: l }));
  if (labelPop.active >= labelPop.items.length) labelPop.active = 0;

  const current = labelPop.row ? labelPop.row.cat : null;
  $("labelPopList").innerHTML = labelPop.items.map((it, i) => {
    const dot = '<span class="t-dot" style="background:' +
      labelColor(it.label, labels.indexOf(it.label)) + '"></span>';
    // every label can be renamed (a built-in keeps its id and takes a display name),
    // but only a user-created one can be deleted
    const tail = it.create
      ? '<span class="lp-hint">' + esc(t("labelCreate")) + "</span>"
      : '<button class="lp-act" data-act="rename" data-label="' + esc(it.label) + '" title="' +
        esc(t("labelRename")) + '">\u270e</button>' +
        (labelIsBuiltin(it.label) ? ""
          : '<button class="lp-act" data-act="delete" data-label="' + esc(it.label) + '" title="' +
            esc(t("labelDelete")) + '">\u2715</button>');
    return '<div class="lp-row' + (i === labelPop.active ? " hl" : "") +
      (it.label === current ? " on" : "") + (it.create ? " create" : "") +
      '" data-i="' + i + '">' + dot +
      '<span class="lp-name">' + esc(it.create ? it.label : labelText(it.label)) + "</span>" + tail + "</div>";
  }).join("");

  $("labelPopList").querySelectorAll(".lp-row").forEach((row) => {
    row.addEventListener("mousedown", (ev) => {
      if (ev.target.classList.contains("lp-act")) return;   // handled below
      ev.preventDefault();
      popApply(labelPop.items[Number(row.dataset.i)]);
    });
  });
  $("labelPopList").querySelectorAll(".lp-act").forEach((b) => {
    b.addEventListener("mousedown", async (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const name = b.dataset.label;
      if (b.dataset.act === "delete") {
        if (!confirm(t("labelDeleteConfirm").replace("%s", name))) return;
        await labelApi("/api/labels/delete", { name });
      } else {
        const to = prompt(t("labelRename"), labelText(name));
        if (to === null) return;
        if (!to.trim()) { showError(t("labelNeedName")); return; }
        await labelApi("/api/labels/rename", { from: name, to: to.trim() });
      }
      await reloadViewData();
      if (labelPop.row) popRender($("labelPopSearch").value);
    });
  });
}

async function labelApi(path, body) {
  try {
    await postJSON(path, body);
  } catch (e) { showError(t("labelRuleFailed") + e.message); }
}

async function popApply(item) {
  if (!item || !labelPop.row) return;
  const row = labelPop.row;
  const exact = row.token_id || "";
  popClose();
  try {
    await postJSON("/api/labels", { entry: {
      category: item.label, action: "include",
      token_id: exact, symbol: exact ? "" : row.symbol, chain: row.chain } });
    await reloadViewData();
  } catch (e) { showError(t("labelRuleFailed") + e.message); }
}

function bindLabelPop() {
  $("labelPopSearch").addEventListener("input", (e) => { labelPop.active = 0; popRender(e.target.value); });
  $("labelPopSearch").addEventListener("keydown", (e) => {
    if (e.key === "Escape") { e.preventDefault(); popClose(); return; }
    if (e.key === "ArrowDown") { e.preventDefault(); labelPop.active = Math.min(labelPop.active + 1, labelPop.items.length - 1); popRender($("labelPopSearch").value); return; }
    if (e.key === "ArrowUp") { e.preventDefault(); labelPop.active = Math.max(labelPop.active - 1, 0); popRender($("labelPopSearch").value); return; }
    if (e.key === "Enter") { e.preventDefault(); popApply(labelPop.items[labelPop.active]); }
  });
  // clicking anywhere else closes it
  document.addEventListener("mousedown", (e) => {
    if ($("labelPop").classList.contains("hidden")) return;
    if (e.target.closest("#labelPop") || e.target.closest(".cat-chip")) return;
    popClose();
  });
}

/* ---------------- pie chart ---------------- */
// The donut is drawn from the filtered view; the hover tooltip names each
// slice. The clickable legend that used to sit under it was removed: every
// figure it listed (name, value, share) is already on the wallet cards, and
// those cards are the click target for focusing one wallet.
function renderPie() {
  const v = filteredView();
  const items = (v && v.wallets ? v.wallets : [])
    .map((w, i) => ({ label: w.wallet, value: w.total_usd || 0, color: PALETTE[i % PALETTE.length] }))
    .filter((it) => it.value > 0)
    .sort((a, b) => b.value - a.value);
  const total = (v && v.total_usd) || 0;
  drawPie($("walletPie"), items, total, "pieTip");
  // A2: a canvas exposes nothing to assistive tech, so carry the numbers in the label
  const pieTop = items.slice(0, 3)
    .map((it) => it.label + " " + (total ? ((it.value / total) * 100).toFixed(1) : "0.0") + "%")
    .join(", ");
  $("walletPie").setAttribute("aria-label",
    t("assetTitle") + ": " + fmtUsdFull(total) + (pieTop ? " — " + pieTop : ""));
}

function drawPie(canvas, items, total, tipId) {
  const tip = $(tipId || "pieTip");
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
  // A2: text alternative for the canvas — range, endpoints and direction
  const first = h.totals[0], last = h.totals[h.totals.length - 1];
  $("trendChart").setAttribute("aria-label",
    t("trendTitle") + ": " + h.dates[0] + " \u2192 " + h.dates[h.dates.length - 1] +
    ", " + fmtUsdFull(first) + " \u2192 " + fmtUsdFull(last) +
    " (" + (last >= first ? "+" : "") + (first ? (((last - first) / first) * 100).toFixed(1) : "0.0") + "%)");
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
async function renderStablecoins() {
  try {
    const d = await api("/api/labels");
    const fn = d.file ? d.file.split(/[\\/]/).pop() : "";
    $("labelAuto").textContent = t("labelAutoBand") + ": " +
      (d.auto && d.auto.price_band ? d.auto.price_band.join(" – ") : "") + "  ·  " + fn;
    const list = $("labelRuleList");
    list.innerHTML = "";
    const user = d.user || [];
    if (!user.length) {
      list.innerHTML = '<div class="bl-empty">' + t("labelRulesSummary") + "</div>";
    } else {
      user.forEach((e) => {
        const row = document.createElement("div");
        row.className = "bl-item";
        row.innerHTML = '<span class="bl-sym">' + esc(e.symbol || e.token_id || e.name || "") +
          '</span><span class="st-cat st-cat-' + esc(e.category) + '">' +
          esc(t(e.category === "stable" ? "catStable" : e.category === "btc" ? "catBtc" : "catOther")) +
          (e.action === "exclude" ? " ✕" : "") + "</span>" +
          '<span class="bl-meta">' + esc([e.chain, e.name].filter(Boolean).join(" · ")) + "</span>";
        const del = document.createElement("button");
        del.className = "bl-btn";
        del.textContent = "✕ " + t("remove");
        del.addEventListener("click", async () => {
          try {
            await postJSON("/api/labels/remove", { index: e.index });
            $("labelRuleMsg").textContent = t("labelRuleRemoved");
            renderStablecoins();
          } catch (err) { $("labelRuleMsg").textContent = t("labelRuleFailed") + err.message; }
        });
        row.appendChild(del);
        list.appendChild(row);
      });
    }
    const dl = $("labelNameList");
    dl.innerHTML = (d.labels || []).map((l) =>
      '<option value="' + esc(l) + '">' + esc(labelText(l)) + "</option>").join("");
    // every label with its rule count, renameable/deletable where a user label is
    // concerned (a built-in keeps its id and only takes a display name)
    const counts = {};
    user.forEach((e) => { counts[e.category] = (counts[e.category] || 0) + 1; });
    $("labelChips").innerHTML = (d.labels || []).map((l, i) => {
      const builtin = (d.builtin_labels || []).includes(l);
      const acts = '<button class="lp-act" data-act="rename" data-label="' + esc(l) + '">\u270e</button>' +
        (builtin ? "" : '<button class="lp-act" data-act="delete" data-label="' + esc(l) + '">\u2715</button>');
      return '<span class="src-block" style="display:inline-flex;align-items:center;gap:6px;margin:2px 4px 2px 0;padding:3px 8px">' +
        '<span class="t-dot" style="background:' + labelColor(l, i) + '"></span>' +
        '<b style="font-size:12px">' + esc(labelText(l)) + "</b>" +
        '<span class="lp-hint">' + (counts[l] || 0) + "</span>" + acts + "</span>";
    }).join("");
    $("labelChips").querySelectorAll(".lp-act").forEach((b) => {
      b.addEventListener("click", async () => {
        const name = b.dataset.label;
        if (b.dataset.act === "delete") {
          if (!confirm(t("labelDeleteConfirm").replace("%s", labelText(name)))) return;
          await labelApi("/api/labels/delete", { name });
        } else {
          const to = prompt(t("labelRename"), labelText(name));
          if (to === null || !to.trim()) return;
          await labelApi("/api/labels/rename", { from: name, to: to.trim() });
        }
        await reloadViewData();
        await renderStablecoins();
      });
    });
    const bi = $("labelBuiltin");
    bi.innerHTML = (d.builtin || []).map((e) =>
      '<span class="st-chip ' + esc(e.category) + '">' + esc(e.symbol) + "</span>").join("");
  } catch (e) {
    $("labelRuleMsg").textContent = t("labelRuleFailed") + e.message;
  }
}

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
      // A CEX account is custody by definition, so it gets a fixed label instead
      // of a selector that the server would ignore anyway.
      const storage = w.type === "cex"
        ? '<span class="bl-tag config" title="' + esc(t("storageTitle")) + '">' + t("storageCex") + "</span>"
        : (w.source === "user"
            ? '<select class="wl-storage" data-index="' + w.index + '" title="' + esc(t("storageTitle")) + '">' +
              ["hot", "cold"].map((k) => '<option value="' + k + '"' +
                ((w.storage || "hot") === k ? " selected" : "") + ">" +
                t(k === "cold" ? "storageCold" : "storageHot") + "</option>").join("") +
              "</select>"
            : "");
      return '<div class="bl-item">' +
        '<img class="logo-img bl-logo" src="' + typeLogo(w.type) + '" alt="">' +
        '<span class="bl-sym">' + esc(w.name) + "</span>" +
        '<span class="bl-tag ' + esc(w.type) + '">' + (TYPE_LABEL[w.type] || w.type) + "</span>" +
        storage +
        '<span class="bl-meta">' + esc(w.address) + "</span>" + right + "</div>";
    }).join("");
    list.querySelectorAll(".wl-storage").forEach((sel) => {
      sel.addEventListener("change", async () => {
        try {
          await postJSON("/api/wallets/storage", { index: Number(sel.dataset.index),
                                                   storage: sel.value });
          await reloadViewData();
        } catch (e) { alert(t("walletAddFail") + e.message); sel.value = sel.dataset.prev || "hot"; }
      });
    });
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
  doge: { en: "Dogecoin balances", zh: "狗狗币余额" },
  ada: { en: "Cardano balances", zh: "艾达币余额" },
  prices: { en: "Native coin prices", zh: "原生币价格" },
  solana: { en: "Solana", zh: "Solana" },
  hyperliquid: { en: "Hyperliquid L1", zh: "Hyperliquid L1" },
  cex: { en: "CEX accounts", zh: "CEX 账户" },
  etherscan: { en: "Etherscan (EVM explorer, free = Ethereum)", zh: "Etherscan（EVM 浏览器，免费=以太坊）" },
};

// one icon system across the whole app: the same files the dashboard uses
const SRC_LOGO = {
  debank: "debank", btc: "btc", doge: "doge", ada: "ada", solana: "sol",
  hyperliquid: "hyperliquid", prices: "coingecko", cex: "binance", etherscan: "etherscan",
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
  okx: "https://www.okx.com/account/my-api",
  bitget: "https://www.bitget.com/account/newapi",
};

function chainLogo(cid) {
  const map = { btc: "btc", eth: "eth", sol: "sol", hyperliquid: "hyperliquid",
                binance: "binance", bybit: "bybit", backpack: "backpack",
                okx: "okx", bitget: "bitget",
                doge: "doge", ada: "ada" };
  return map[cid] ? '/static/logos/' + map[cid] + '.svg' : '/static/logos/evm.svg';
}
// wallet type -> logo file (evm/cex fall back to the generic evm mark)
function typeLogoFile(type) {
  const map = { btc: "btc", sol: "sol", doge: "doge", ada: "ada" };
  return map[type] || "evm";
}
function typeLogo(type) {
  return '/static/logos/' + typeLogoFile(type) + '.svg';
}

function srcFieldHTML(path, label, value, placeholder) {
  return '<div class="src-field"><span>' + esc(label) + '</span><input data-path="' + path + '" value="' +
    esc(value || "") + '"' + (placeholder ? ' placeholder="' + esc(placeholder) + '"' : "") + "></div>";
}

async function renderSources() {
  try {
    // S1: /api/sources masks secrets by default; reveal only on request
    const d = await api("/api/sources" + (state.revealKeys ? "?reveal=1" : ""));
    state.maskedKeys = !!d.masked;
    $("btnRevealKeys").textContent = t(state.revealKeys ? "btnHideKeys" : "btnShowKeys");
    state.sourcesCfg = JSON.parse(JSON.stringify(d.config));
    state.sourcesLastOk = d.last_ok || {};
    const st = d.status || {};
    const lastOk = st.last_ok || {};
    $("sourcesFile").textContent = d.file ? d.file.split(/[\\/]/).pop() : "";
    $("keysNote").textContent = state.maskedKeys ? t("keysMasked") : "";
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
      b.innerHTML = '<div class="src-head">' +
        '<img class="logo-img src-logo" src="/static/logos/' + esc(SRC_LOGO[key] || "evm") + '.svg" alt="">' +
        '<label class="chk">' +
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
    for (const key of ["btc", "doge", "ada", "prices", "hyperliquid"]) {
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
      // always show the supported exchanges (binance / bybit / backpack / okx / bitget);
      // keys default empty.
      // merged rows are written back into the config so name/exchange persist on save.
      const byEx = {};
      (cfg.cex.accounts || []).forEach((a) => { if (a.exchange) byEx[a.exchange] = a; });
      const defaults = [
        { exchange: "binance", name: "binance_read" },
        { exchange: "bybit", name: "bybit_read" },
        { exchange: "backpack", name: "backpack_read" },
        { exchange: "okx", name: "okx_read" },
        { exchange: "bitget", name: "bitget_read" },
      ];
      // OKX and Bitget also require the passphrase that was set with the API key
      const NEEDS_PASSPHRASE = { okx: true, bitget: true };
      const extra = (cfg.cex.accounts || []).filter((a) => !defaults.some((d) => d.exchange === a.exchange));
      const rows = defaults.map((dflt) => byEx[dflt.exchange] ||
        Object.assign({}, dflt, { key: "", secret: "", enabled: true })).concat(extra);
      state.sourcesCfg.cex.accounts = rows;
      cfg.cex.accounts = rows;
      rows.forEach((a, i) => {
        b.insertAdjacentHTML("beforeend",
          '<div class="src-sub src-sub-logo">' +
          '<img class="logo-img" src="' + chainLogo(a.exchange) + '" alt="">' +
          esc(a.name) + " (" + esc(a.exchange) + ")" +
          ' <span class="hint src-oktime">' + t("lastOk") + ": " + esc(fmtTime(lastOk["cex:" + a.exchange])) + "</span></div>" +
          '<div class="src-prov">' +
          '<label class="chk"><input type="checkbox" data-path="cex.accounts.' + i + '.enabled"' +
            (a.enabled !== false ? " checked" : "") + "></label>" +
          '<input data-path="cex.accounts.' + i + '.key" value="' + esc(a.key || "") + '" class="src-key" placeholder="' + t("cexKeyPh") + '">' +
          '<input data-path="cex.accounts.' + i + '.secret" value="' + esc(a.secret || "") + '" class="src-key" placeholder="' + t("cexSecretPh") + '">' +
          (NEEDS_PASSPHRASE[a.exchange]
            ? '<input data-path="cex.accounts.' + i + '.passphrase" value="' + esc(a.passphrase || "") +
              '" class="src-key" placeholder="' + t("cexPassPh") + '">'
            : "") +
          (SRC_LINKS[a.exchange]
            ? '<a class="src-link" href="' + esc(SRC_LINKS[a.exchange]) + '" target="_blank" rel="noopener noreferrer">' + t("getKey") + " ↗</a>"
            : "") +
          "</div>");
      });
      b.insertAdjacentHTML("beforeend", '<p class="bl-desc">' + t("cexDefaultHint") + "</p>");
    }

    if (cfg.etherscan) {
      const b = blockOf("etherscan");
      // NOTE: do not name this `esc` — that would shadow the global esc() helper.
      const escTime = lastOk["etherscan"] ? fmtTime(lastOk["etherscan"]) : t("never");
      const readout = (lastOk && st.etherscan_native) ? st.etherscan_native : null;
      let detailHTML = "";
      if (readout) {
        detailHTML = Object.keys(readout).map((wname) => {
          const tot = readout[wname].reduce((s, r) => s + (r.usd || 0), 0);
          return '<div class="src-sub">' + esc(wname) + " · " + fmtUsd(tot) +
            '<span class="src-oktime"> ' + readout[wname].map((r) => esc(r.symbol) + " " + fmtAmount(r.amount)).join(" · ") + "</span></div>";
        }).join("");
      }
      b.insertAdjacentHTML("beforeend",
        srcFieldHTML("etherscan.api_key", "API Key", cfg.etherscan.api_key, "Etherscan V2 API key") +
        srcFieldHTML("etherscan.chains", "chains", cfg.etherscan.chains || "eth", t("chainsPh")) +
        (detailHTML || '<p class="bl-desc">' + t("lastOk") + ": " + esc(escTime) + "</p>"));
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
    // management list (switch is via dropdown). Each profile owns its own
    // schedule, so the clock tag expands an editor for THAT profile.
    const list = $("profileList");
    list.innerHTML = d.profiles.map((p) => {
      const nm = esc(p.name);
      const actions = [];
      if (!p.is_default) {
        // rename any profile that is not the public template
        actions.push('<button class="bl-edit" data-pf-action="rename" data-pf-name="' + nm +
          '" title="' + esc(t("renameProfile")) + '">✎ ' + t("renameProfile") + "</button>");
      }
      if (!p.is_active && !p.is_default) {
        actions.push('<button class="bl-del" data-pf-action="delete" data-pf-name="' + nm +
          '">✕ ' + t("deleteProfile") + "</button>");
      }
      const right = (p.is_active ? '<span class="bl-tag user">' + t("activeProfile") + "</span>" : "") +
        (actions.length ? '<span class="pf-actions">' + actions.join("") + "</span>" : "");
      const sc = p.schedule || {};
      const schedTag = '<button class="pf-sched' + (sc.enabled ? " on" : "") +
        '" data-pf-sched="' + nm + '" title="' + esc(t("schedTitle")) + '">' +
        (sc.enabled ? "⏰ " + esc(sc.time || "") : esc(t("schedOff"))) + "</button>";
      const row = '<div class="bl-item"><span class="bl-sym">' + nm + "</span>" +
        (p.is_default ? '<span class="bl-tag config">' + t("config") + "</span>" : "") +
        (p.has_db ? '<span class="hint">db</span>' : "") + schedTag + right + "</div>";
      // inline editor, hidden until the clock tag is clicked
      const editor = '<div class="pf-sched-box" data-sched-box="' + nm + '" hidden>' +
        '<label class="chk"><input type="checkbox" data-sched-enabled' + (sc.enabled ? " checked" : "") +
          "> " + t("schedEnable") + "</label>" +
        '<input type="time" data-sched-time value="' + esc(sc.time || "09:00") + '">' +
        '<button class="btn-ghost" data-sched-save="' + nm + '">' + t("btnSaveSched") + "</button>" +
        '<span class="hint" data-sched-msg></span>' +
        '<span class="hint" data-sched-last>' + esc(t("schedLastRun")) +
          esc(sc.last_run_date || t("never")) + "</span>" +
        "</div>";
      return row + editor;
    }).join("") || '<div class="bl-empty">' + t("emptyList") + "</div>";
  } catch (e) { /* ignore */ }
}

async function renderSettings() {
  await renderProfiles();   // also renders each profile's own schedule editor
  await renderWalletMgmt();
  await renderSources();
  await renderBlacklist();
  await renderStablecoins();
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
  await renderStablecoins();
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
  const cancelBtn = $("btnCancelRefresh");
  cancelBtn.disabled = false;
  cancelBtn.textContent = t("btnCancel");
  const timer = setInterval(async () => {
    try {
      const st = await api("/api/status");
      const pct = st.total ? Math.round((st.done / st.total) * 100) : 3;
      $("progressFill").style.width = Math.min(96, pct) + "%";
      $("progressMsg").textContent = st.running ? st.msg : t("refreshing");
    } catch (e) { /* ignore */ }
  }, 1500);
  try {
    // POST, not GET: a GET with side effects is reachable from a bare <img> tag,
    // and the server refuses cross-site writes on the POST path (see _write_guard).
    const res = await postJSON("/api/refresh", {});
    if (res && res.cancelled) {
      // nothing was written; the snapshot is only saved once the fetch completes
      $("progressMsg").textContent = t("cancelled");
      return;
    }
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
