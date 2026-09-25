# dsh-crypto-portfolio

[English](README.md) | 中文

免费、100% 自托管的 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（DSH）插件：把**链上与 CEX 资产**统一到一张自包含的 Web 仪表盘上。

**依赖** `dsh` `0.1.1-rc.2`（Node `^22.19 || >=24`）· Python 3.9+ · `pip3 install requests pynacl`

```sh
dsh plugin --profile demo add dsh-crypto-portfolio   # npm
dsh --profile demo                                    # 仪表盘 http://127.0.0.1:8080
```

![Crypto Portfolio Tracker —— 所有链、所有钱包，一张自托管仪表盘](assets/screenshot.png)

> 非官方项目，由社区成员独立开发和维护，与 DeepSeek 官方无关。

---

## 为什么写它 / 痛点

我写它是因为痛点是真的疼。

### 一、我的钱散在七个地方，想看个总数要开六个页面

EVM 资产在 DeBank、SOL 和质押在 Solana 链上、BTC 在区块浏览器、还有 Binance / Bybit / Backpack / OKX / Bitget 五个交易所各一套 App。每次想看"我到底有多少钱"，都得打开 DeBank 翻几个链、再去查质押、最后挨个登录三个交易所——手一抖还容易看漏钱包。

**这个插件把这些全拼到一张图上。**

### 二、链上浏览器看不到的"隐形资产"

有些钱是真的看不见：Solana 的原生质押账户（`getParsedStakeAccounts` 会漏）、Hyperliquid L1 的质押 HYPE 和现货、交易所的理财/资金账户——这些都不是普通 SPL/ERC20 代币，普通工具根本读不到。

**这个插件专门把它们挖出来，全部计价进总资产**——包括上面的账户里质押的 12.1 SOL、Hyperliquid 上质押的约 318 枚 HYPE。

### 三、空气币和钓鱼代币把数字搞得虚高

DeBank 会把一堆假代币也列出来，比如 ETHG 这种**价格被操纵的钓鱼币**，一个账户能虚报出 57 万美元。

**一键拉黑**：你点掉的每一笔都会从总额、趋势、历史快照里同步剔除。

### 四、我想知道"上周这时候我到底有多少钱"

没有历史就没有安全感。

**每次刷新自动保存当天最后一次快照**（SQLite，按天去重）；日子久了，就长出一条属于你自己的资产趋势线：

![每日快照如何变成趋势图](assets/flow.svg)

---

## 它做了什么

- **一个 DSH 插件，拉起一个零依赖的 Web 仪表盘。** 没有框架、没有 CDN，Python 标准库 + 原生 JS。
- **覆盖 BTC / EVM / Solana / 狗狗币 / 艾达币 / Hyperliquid L1 / CEX。** DeBank 全 73 条链、BTC 双地址（P2SH + P2TR）、Solana 原生质押、狗狗币（BlockCypher）、艾达币（Koios，支持 stake 地址）、Hyperliquid 官方 API（质押 HYPE + 现货 + 永续权益 + 金库权益）、五个交易所只读 key（Binance / Bybit / Backpack / OKX / Bitget，命名 `<交易所>_read`）；OKX 同时读交易账户与资金账户，Bitget 汇总现货与真实合约账户（跳过 S 开头的模拟盘，避免把「练习钱」算进总资产）。
- **全局筛选。** 分类（BTC / EVM / Solana / 狗狗币 / 艾达币 / CEX）、钱包、网络三个下拉作用于所有面板——总额、钱包占比饼图、趋势、网络分布、代币表一起联动。
- **每个钱包最多 5 个区块浏览器。** 钱包卡片底部是一排浏览器图标：排第一的是本程序实际取数的来源（DeBank · bitaps · Jupiter · Dogechain · Cardanoscan），后面按知名度依次是 Etherscan、mempool.space、Solscan、Blockchair、CExplorer 等。狗狗币只有 3 个、艾达币只有 4 个——这两个生态确实凑不满 5 个可信浏览器。交易所账户没有链上浏览器页面，因此只显示交易所图标。
- **免费 + 付费数据源，显著区分。** EVM 走 DeBank 双 provider：付费 `debank-pro`（标注「付费」，带注册链接）与免费免 key 的 `debank-public` 兜底；CEX 五行（Binance/Bybit/Backpack/OKX/Bitget）常驻显示并带各家「获取 API key」链接（OKX、Bitget 还需填 passphrase）；每个数据源显示最近一次成功时间。
- **多 API 源自动切换。** 每个数据源配了多个 provider（价格：CoinGecko → Binance → Coinbase → OKX；BTC：blockchain.info → mempool.space；Solana RPC 多节点；Hyperliquid 双端点），挂了自动切下一个，并记住最近能用的。
- **定时每日刷新。** 每个 Profile 可设置本地时间自动刷新（服务端守护线程，关闭网页不影响）；设置页显示各数据源最后成功时间。
- **多 Profile 配置隔离。** `default` Profile 内置公开模板钱包（vitalik.eth、创世 BTC、公开 SOL、公开 DOGE、公开 ADA）与空 key；你的私人钱包和 key 放在独立命名的 Profile 里，拥有各自的快照历史。每个 Profile 可重命名（快照随之迁移），并各自维护独立的每日定时刷新时间。
- **资产健康度。** 代币明细表上方一个面板用三张卡片给组合打分——**波动性风险**（稳定币 · 比特币 · 其他，按高波动占比评级）、**集中度**（最大钱包占比，画成带两条阈值刻度的量尺）、**托管安全**（冷 · 热 · 交易所）。每一行都同时给出余额和占比，未通过的项各配一句人话建议。三条阈值都能在设置页里改（按 Profile 保存、带校验，托管安全那对是反向的），数据取自同一份已过滤黑名单的快照，因此永远和上面的总额一致。在设置里把钱包标成「冷钱包」，托管安全那项**立刻**跟着变（冷热以当前钱包列表为准，快照里的值只作为已删除钱包的兜底）。
- **分享卡片。** 顶栏「分享」按钮（就在「刷新」旁边）弹出对话框，实时预览一张 1200×630 的 PNG——总额、日环比、按币种合并的前五大持仓、资产类别甜甜圈、三条健康度结论。可以直接下载、复制图片、复制文案，或一键跳转 **X / Facebook / WhatsApp / Telegram**。全部用 canvas 手绘：不引入 `html2canvas`、不依赖 CDN，图片里也不含任何钱包地址。
- **作者链接 + 打赏。** 设置页底部有作者的社交链接（X / Discord / GitHub）与「请我喝杯咖啡」弹窗，内含 tip.md 徽章和币安支付二维码；徽章已本地内置，页面不会发出任何第三方请求。
- **可链接的页面。** `#pageSettings` 直达设置页，`#pageSettings/secWallets` 直达某个设置分区——刷新或收藏后回到原处。
- **主题与多语言。** 深/浅色主题切换、中英双语（默认英文）、全站链与交易所图标。


架构长这样——每个方框都是一条真实的数据管线：

![架构图](assets/arch.svg)

## 与 DSH 的集成方式

不是套壳，是真插件：

- 声明 `dsh.bundle` manifest（`cordis.patch.yml`），`dsh plugin add` 直接安装。
- `apply(ctx)` 接入 Cordis 生命周期：首次运行用公开模板生成用户本地的 `profiles/default`，以子进程拉起仪表盘，`ctx.on('dispose')` 时优雅停掉。
- 除 Web UI 外还暴露 JSON API（`GET /api/refresh`、`/api/history`、`/api/tokens` 等），agent 可直接调用。

## 隐私声明（重要）

本仓库**不含任何私钥、私人钱包或余额**——`tracker/config.py` 只有 `WALLETS = []` 和空 key。所有私人配置都存放在本地 git-ignored 的 `profiles/` 里。你可以放心 clone、放心 review、放心跑。

## 安装

### 依赖前提

- **`dsh` `0.1.1-rc.2`**（同一预发布线内的兼容版本）与 **Node `^22.19.0 || >=24.0.0`** —— 即 DSH 自身声明的区间。
- **Python 3.9+**，并安装两个 pip 包：

  ```sh
  pip3 install requests pynacl
  ```

  两者都是普通运行时依赖，**没有**随包 vendored —— 这样 pip 才能按你的平台/版本挑到正确的构建。

### 从 npm 安装（推荐）

装的是预构建产物，**不需要任何 build 授权**：

```sh
dsh plugin --profile demo add dsh-crypto-portfolio
dsh --profile demo
```

### 从 tarball 安装（离线 / 内网）

```sh
pnpm pack                                    # 生成 dsh-crypto-portfolio-0.1.0.tgz
dsh plugin --profile demo add ./dsh-crypto-portfolio-0.1.0.tgz
```

### 从 GitHub 安装

```sh
dsh plugin --profile demo add github:0xRabit/dsh-crypto-portfolio#<commit-sha>
```

本包是纯 JavaScript + Python，**没有任何构建步骤**，`prepare` 是空操作，因此 pnpm **不需要**你给 build 脚本放行 —— 这一点比那些以 TypeScript 源码分发的插件摩擦更小。不过仍**建议 pin 一个 commit SHA**，避免之后的推送悄悄改变你机器上执行的代码。

### 启动前先验证层是否生效

```sh
dsh --profile demo --dump-config      # 应能看到： # == dsh-crypto-portfolio
```

**看不到这一行 = bundle 没有激活**（包只被当成普通依赖装了进去）。重新 `add` 并留意它打印的警告。

### 覆盖端口

patch 会**整体替换**某一行的 `config`，所以必须把你需要的键全部写全。放到 `$DSH_HOME/profiles/demo/cordis.patch.yml`：

```yaml
- id: portfolio-tracker
  name: dsh-crypto-portfolio
  config:
    port: 8199
    host: 127.0.0.1
```

也可以设环境变量 `PORTFOLIO_PORT`。

### 脱离 DSH 独立运行

```sh
python3 run.py --init-template --port 8080   # 用公开模板初始化 profiles/default
```

## 目录结构

```
profiles/default/   sources.json + wallets.json（公开模板，自动生成）
templates/          公开示例配置（无任何密钥）
tracker/            后端抓取器（debank/btc/solana/hyperliquid/cex/prices）
static/             Web 仪表盘（原生 JS，零外部依赖）
run.py / fetch.py   Web 服务 / 命令行快照
```

## 许可证

MIT — 见 [LICENSE](LICENSE)。
