from market_scanner.engine.runtime import (
    get_manipulation_threshold,
    get_notional_override,
    set_manipulation_threshold,
    set_notional_override,
)


def test_runtime_overrides():
    set_notional_override(7000)
    assert get_notional_override() == 7000
    set_notional_override(None)
    assert get_notional_override() is None

    set_manipulation_threshold(42)
    assert get_manipulation_threshold() == 42
    set_manipulation_threshold(None)
    assert get_manipulation_threshold() is None
