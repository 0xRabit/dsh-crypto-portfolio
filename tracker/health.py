# -*- coding: utf-8 -*-
"""Asset health analysis: three indicators plus optimisation advice.

The three checks a portfolio reviewer actually asks about:

1. **Volatility risk** — the portfolio split into stablecoins, BTC and everything
   else. Stablecoins barely move, BTC is the benchmark, and the third bucket is
   where a drawdown comes from, so its *share* is the risk figure.
2. **Concentration** — the largest single wallet's share. One wallet holding most
   of the portfolio is a single point of failure.
3. **Storage security** — cold vs hot vs exchange custody, judged by the *cold*
   share, because that is the part that cannot be drained by a compromised
   browser or a failed exchange.

Each indicator lands on `safe` / `warning` / `highRisk`, and the suggestions block
carries one line per failing check. The thresholds are per profile
(`tracker/healthconfig.py`, editable in Settings) and default to
volatility 60/70 %, concentration 50/75 %, cold 50/20 % — the storage pair is
inverted, because more cold is better.

All figures come from blacklist-filtered totals, so the numbers here always agree
with the dashboard.
"""
from . import healthconfig

SAFE, WARNING, HIGH_RISK = "safe", "warning", "highRisk"

BTC_TYPES = ("btc", "bitcoin")
STORAGE_KINDS = ("cold", "hot", "cex")
VOLATILITY_BUCKETS = ("stable", "btc", "other")


def _pct(part, whole):
    return round(part / whole * 100.0, 1) if whole > 0 else 0.0


def _usd(wallet):
    try:
        return float(wallet.get("total_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _level_high_is_bad(value, thresholds):
    if value >= thresholds["danger"]:
        return HIGH_RISK
    if value >= thresholds["warning"]:
        return WARNING
    return SAFE


def is_cex(wallet):
    return str(wallet.get("type") or "").lower() == "cex"


def is_btc(wallet):
    return str(wallet.get("type") or "").lower() in BTC_TYPES


def storage_kind(wallet):
    """`cold` / `hot` / `cex` for one wallet.

    A CEX account is exchange custody by definition, so the stored preference is
    ignored for it. A missing field means `hot`: the pessimistic reading, and the
    one that matches how an unclassified wallet usually behaves.
    """
    if is_cex(wallet):
        return "cex"
    kind = str(wallet.get("storage") or "hot").strip().lower()
    return kind if kind in STORAGE_KINDS else "hot"


def volatility(by_label, thresholds=None):
    """Stablecoins / BTC / everything else, and the risk level of "everything else".

    `by_label` is {"stable": usd, "btc": usd, "other": usd} as computed by
    views.volatility_totals(); callers that only have whole wallets should build it
    with `wallet_volatility()`.
    """
    thresholds = (thresholds or healthconfig.DEFAULTS)["volatility"]
    buckets = {}
    for key in VOLATILITY_BUCKETS:
        try:
            amount = float((by_label or {}).get(key) or 0.0)
        except (TypeError, ValueError):
            amount = 0.0
        buckets[key] = {"balance": round(amount, 2)}
    total = round(sum(b["balance"] for b in buckets.values()), 2)
    for b in buckets.values():
        b["percent"] = _pct(b["balance"], total)
    return {"buckets": buckets, "total": total,
            "level": _level_high_is_bad(buckets["other"]["percent"], thresholds),
            "thresholds": dict(thresholds)}


def wallet_volatility(wallets):
    """Fallback split when only wallet totals are available.

    A wallet is one thing or another, so a BTC wallet counts as BTC and every other
    wallet counts as volatile. That over-states "other" for a BTC wallet that also
    holds stablecoins, which is why the API path classifies the token rows instead.
    """
    out = {k: 0.0 for k in VOLATILITY_BUCKETS}
    for w in wallets:
        out["btc" if is_btc(w) else "other"] += _usd(w)
    return out


def concentration(wallets, thresholds=None):
    """The single largest wallet's share of the portfolio."""
    thresholds = (thresholds or healthconfig.DEFAULTS)["concentration"]
    priced = [w for w in wallets if _usd(w) > 0]
    total = round(sum(_usd(w) for w in priced), 2)
    if not priced or total <= 0:
        return {"percent": 0.0, "maxWallet": None, "maxWalletIsBtc": False,
                "level": SAFE, "total": 0.0, "thresholds": dict(thresholds)}
    top = max(priced, key=_usd)
    percent = _pct(_usd(top), total)
    return {"percent": percent, "maxWallet": top.get("wallet") or "",
            "maxWalletType": top.get("type") or "",
            "maxWalletUsd": round(_usd(top), 2),
            "maxWalletIsBtc": is_btc(top),
            "level": _level_high_is_bad(percent, thresholds),
            "total": total, "thresholds": dict(thresholds)}


def storage_security(wallets, thresholds=None):
    """Cold / hot / exchange split, judged by the cold share."""
    thresholds = (thresholds or healthconfig.DEFAULTS)["storage"]
    buckets = {k: {"balance": 0.0, "percent": 0.0, "wallets": []} for k in STORAGE_KINDS}
    for w in wallets:
        kind = storage_kind(w)
        buckets[kind]["balance"] = round(buckets[kind]["balance"] + _usd(w), 2)
        buckets[kind]["wallets"].append(w.get("wallet") or "")
    total = round(sum(b["balance"] for b in buckets.values()), 2)
    for b in buckets.values():
        b["percent"] = _pct(b["balance"], total)

    cold = buckets["cold"]["percent"]
    if total <= 0 or cold >= thresholds["safe"]:
        level = SAFE           # an empty portfolio has nothing at risk
    elif cold >= thresholds["warning"]:
        level = WARNING
    else:
        level = HIGH_RISK
    return {"storage": buckets, "securityLevel": level, "total": total,
            "thresholds": dict(thresholds)}


def suggestions(vol, conc, store):
    """One entry per failing indicator, or a single all-clear.

    Entries carry an i18n key plus the numbers the sentence needs, so the wording
    lives in the frontend's dictionary and is never duplicated here.
    """
    out = []
    if vol["level"] != SAFE:
        out.append({"key": "healthVolatilityRisk", "level": vol["level"],
                    "pct": vol["buckets"]["other"]["percent"]})
    # a portfolio concentrated in BTC needs no advice to buy more BTC
    if conc["level"] != SAFE and not conc["maxWalletIsBtc"]:
        out.append({"key": "healthConcentrationAdvice", "level": conc["level"],
                    "pct": conc["percent"], "wallet": conc["maxWallet"]})
    if store["securityLevel"] != SAFE:
        out.append({"key": "healthStorageAdvice", "level": store["securityLevel"],
                    "pct": store["storage"]["cold"]["percent"]})
    if not out:
        out.append({"key": "healthOk", "level": SAFE, "pct": None})
    return out


def analyze(wallets, by_label=None, thresholds=None):
    """Full health report for blacklist-filtered wallet (and label) totals.

    `wallets` rows are {wallet, type, storage, total_usd}; `by_label` is the
    stable/BTC/other split of the same snapshot. Without `by_label` the volatility
    card falls back to classifying whole wallets (see `wallet_volatility`).
    """
    rows = [w for w in (wallets or []) if isinstance(w, dict)]
    cfg = thresholds or healthconfig.load()
    vol = volatility(by_label if by_label is not None else wallet_volatility(rows), cfg)
    conc = concentration(rows, cfg)
    store = storage_security(rows, cfg)
    return {"total": vol["total"] or conc["total"] or store["total"],
            "volatility": vol, "concentration": conc, "storage": store,
            "suggestions": suggestions(vol, conc, store)}
