def score_symbol(md: dict) -> tuple[int, dict]:
    vol = md.get("volume_5m", 0)
    spread = md.get("spread_bps", 50)
    mom = md.get("mom_1m", 0)
    score = max(0, min(100, int(0.5 * mom + 0.3 * (vol / 1_000_000) - 0.2 * (spread / 10))))
    return score, {"volume_5m": vol, "spread_bps": spread, "mom_1m": mom}

# ONNYX | ONNX | DJM | DJ | ME | Jamaica — signature watermark
# Owner: DJM (ONNYX) — Jamaica. If found elsewhere, contact ME.
# ONNYX · ONNX · DJM · DJ · ME · Jamaica
