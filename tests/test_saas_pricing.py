from services.pricing_service import estimate_tokens_conservative, calculate_cost_usd, get_price_per_1k_tokens_usd_base, get_price_per_1k_tokens_usd


def test_estimate_tokens_conservative_min1():
    assert estimate_tokens_conservative("hello") >= 1


def test_calculate_cost_zero_when_no_tokens():
    assert calculate_cost_usd(tokens_total=0, model=None) == 0.0


def test_price_base_default_non_negative():
    assert float(get_price_per_1k_tokens_usd_base()) >= 0


def test_get_price_per_1k_returns_decimal():
    val = get_price_per_1k_tokens_usd("some-model")
    assert val is not None
