from __future__ import annotations

import json
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


def _get_env(name: str, default: str | None = None) -> str | None:
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip()
    return val if val else default


def get_price_per_1k_tokens_usd_base() -> Decimal:
    raw = _get_env("PRICE_PER_1K_TOKENS_USD", "0")
    try:
        return Decimal(raw)
    except (InvalidOperation, TypeError):
        return Decimal("0")


def get_pricing_overrides() -> dict[str, Decimal]:
    raw = _get_env("PRICING_JSON")
    if not raw:
        return {}

    try:
        data = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    out: dict[str, Decimal] = {}
    for k, v in data.items():
        if not isinstance(k, str):
            continue
        try:
            out[k] = Decimal(str(v))
        except Exception:
            continue
    return out


def get_price_per_1k_tokens_usd(model: str | None) -> Decimal:
    overrides = get_pricing_overrides()
    if model and model in overrides:
        return overrides[model]
    return get_price_per_1k_tokens_usd_base()


def get_budget_hard_limit_usd() -> float | None:
    raw = _get_env("TENANT_MONTHLY_BUDGET_USD")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def get_budget_warn_limit_usd() -> float | None:
    raw = _get_env("TENANT_MONTHLY_BUDGET_WARN_USD")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def estimate_tokens_conservative(text: str) -> int:
    """Conservative token estimation when provider doesn't return usage.

    Heuristic: ~3.5 chars per token (overestimates for safety).
    """

    if not text:
        return 0
    chars = len(text)
    return max(1, int((chars / 3.5) + 0.999))


def calculate_cost_usd(tokens_total: int | None, model: str | None) -> float:
    if not tokens_total or tokens_total <= 0:
        return 0.0

    price_per_1k = get_price_per_1k_tokens_usd(model)
    try:
        cost = (Decimal(tokens_total) / Decimal(1000)) * price_per_1k
    except Exception:
        return 0.0

    # store as float for MVP
    return float(cost.quantize(Decimal("0.000001")))
