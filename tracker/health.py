# -*- coding: utf-8 -*-
"""Asset health analysis: three indicators plus optimisation advice.

The model follows the three checks a portfolio reviewer actually asks about:

1. **Tiering / on-chain risk** — BTC (tier 1) vs on-chain alts (tier 2) vs CEX
   (tier 3). Alts held in a hot wallet carry the most risk, so the *share* of
   tier 2 is the risk figure; BTC and CEX are not penalised here.
2. **Concentration** — the largest single wallet's share. One wallet holding
   most of the portfolio is a single point of failure.
3. **Storage security** — cold vs hot vs exchange custody, judged by the *cold*
   share, because that is the part that cannot be drained by a compromised
   browser or a failed exchange.

Each indicator is `safe` / `warning` / `highRisk`; the suggestions block lists
one warning per failing indicator and nothing else. Thresholds:
on-chain 60/70 %, concentration 50/75 %, cold 50/20 % (cold is inverted: more is
better). A wallet whose type is `cex` is always exchange custody regardless of
its configured storage field.

All figures come from blacklist-filtered totals, so the numbers here always
agree with the dashboard.
"""

# Thresholds (percentages)
ONCHAIN_WARNING = 60.0
ONCHAIN_DANGER = 70.0
CONCENTRATION_WARNING = 50.0
CONCENTRATION_DANGER = 75.0
STORAGE_SAFE = 50.0
STORAGE_WARNING = 20.0

SAFE, WARNING, HIGH_RISK = "safe", "warning", "highRisk"

BTC_TYPES = ("btc", "bitcoin")
STORAGE_KINDS = ("cold", "hot", "cex")


def _pct(part, whole):
    return round(part / whole * 100.0, 1) if whole > 0 else 0.0


def _usd(wallet):
    try:
        return float(wallet.get("total_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


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


def tiering(wallets):
    """BTC / on-chain alts / CEX pyramid, and the risk level of the middle tier."""
    tiers = {
        "tier1": {"name": "BTC", "balance": 0.0, "percent": 0.0, "wallets": []},
        "tier2": {"name": "on-chain", "balance": 0.0, "percent": 0.0, "wallets": []},
        "tier3": {"name": "CEX", "balance": 0.0, "percent": 0.0, "wallets": []},
    }
    for w in wallets:
        if is_cex(w):
            key = "tier3"
        elif is_btc(w):
            key = "tier1"
        else:
            key = "tier2"
        amount = _usd(w)
        tiers[key]["balance"] = round(tiers[key]["balance"] + amount, 2)
        if amount:
            tiers[key]["wallets"].append(w.get("wallet") or "")

    total = round(sum(t["balance"] for t in tiers.values()), 2)
    for t in tiers.values():
        t["percent"] = _pct(t["balance"], total)

    tier2 = tiers["tier2"]["percent"]
    if tier2 >= ONCHAIN_DANGER:
        level = HIGH_RISK
    elif tier2 >= ONCHAIN_WARNING:
        level = WARNING
    else:
        level = SAFE
    return {"tiers": tiers, "total": total, "onChainRiskLevel": level}


def concentration(wallets):
    """The single largest wallet's share of the portfolio."""
    priced = [w for w in wallets if _usd(w) > 0]
    total = round(sum(_usd(w) for w in priced), 2)
    if not priced or total <= 0:
        return {"percent": 0.0, "maxWallet": None, "maxWalletIsBtc": False,
                "level": SAFE, "total": 0.0}
    top = max(priced, key=_usd)
    percent = _pct(_usd(top), total)
    if percent >= CONCENTRATION_DANGER:
        level = HIGH_RISK
    elif percent >= CONCENTRATION_WARNING:
        level = WARNING
    else:
        level = SAFE
    return {"percent": percent, "maxWallet": top.get("wallet") or "",
            "maxWalletType": top.get("type") or "",
            "maxWalletUsd": round(_usd(top), 2),
            "maxWalletIsBtc": is_btc(top), "level": level, "total": total}


def storage_security(wallets):
    """Cold / hot / exchange split, judged by the cold share."""
    buckets = {k: {"balance": 0.0, "percent": 0.0, "wallets": []} for k in STORAGE_KINDS}
    for w in wallets:
        kind = storage_kind(w)
        buckets[kind]["balance"] = round(buckets[kind]["balance"] + _usd(w), 2)
        buckets[kind]["wallets"].append(w.get("wallet") or "")
    total = round(sum(b["balance"] for b in buckets.values()), 2)
    for b in buckets.values():
        b["percent"] = _pct(b["balance"], total)

    cold = buckets["cold"]["percent"]
    if total <= 0:
        level = SAFE           # nothing is at risk yet
    elif cold >= STORAGE_SAFE:
        level = SAFE
    elif cold >= STORAGE_WARNING:
        level = WARNING
    else:
        level = HIGH_RISK
    return {"storage": buckets, "securityLevel": level, "total": total}


def suggestions(tier, conc, store):
    """One entry per failing indicator, or a single all-clear.

    Entries carry an i18n key plus the numbers the sentence needs, so the wording
    lives in the frontend's dictionary and is never duplicated here.
    """
    out = []
    if tier["onChainRiskLevel"] != SAFE:
        out.append({"key": "healthOnChainRisk", "level": tier["onChainRiskLevel"],
                    "pct": tier["tiers"]["tier2"]["percent"]})
    # a portfolio concentrated in BTC needs no advice to buy more BTC
    if conc["level"] != SAFE and not conc["maxWalletIsBtc"]:
        out.append({"key": "healthConcentration", "level": conc["level"],
                    "pct": conc["percent"], "wallet": conc["maxWallet"]})
    if store["securityLevel"] != SAFE:
        out.append({"key": "healthStorageAdvice", "level": store["securityLevel"],
                    "pct": store["storage"]["cold"]["percent"]})
    if not out:
        out.append({"key": "healthOk", "level": SAFE, "pct": None})
    return out


def analyze(wallets):
    """Full health report for a list of {wallet, type, storage, total_usd} rows."""
    rows = [w for w in (wallets or []) if isinstance(w, dict)]
    tier = tiering(rows)
    conc = concentration(rows)
    store = storage_security(rows)
    return {"total": tier["total"], "tiering": tier, "concentration": conc,
            "storage": store, "suggestions": suggestions(tier, conc, store)}
