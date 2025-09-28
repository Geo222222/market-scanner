import asyncio
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from market_scanner.jobs.loop import run_cycle


async def main() -> None:
    bundles, ranked = await run_cycle(profile="scalp")
    print(f"Fetched bundles: {len(bundles)}")
    print(f"Ranked symbols: {len(ranked)}")
    for snap in ranked[:5]:
        flags = ",".join(snap.manip_flags or []) if snap.manip_flags else "none"
        manip_display = f"manip={snap.manip_score:.2f} ({flags})" if snap.manip_score is not None else "manip=—"
        print(
            f"{snap.symbol:<15} score={snap.score:.2f} qvol={snap.qvol_usdt:,.0f} "
            f"spread={snap.spread_bps:.2f}bps slip={snap.slip_bps:.2f}bps "
            f"ATR={snap.atr_pct:.2f}% ret1={snap.ret_1:.2f}% ret15={snap.ret_15:.2f}% {manip_display}"
        )
    if ranked:
        ts = ranked[0].ts
        if isinstance(ts, datetime):
            print("Snapshot timestamp:", ts.isoformat())


if __name__ == "__main__":
    asyncio.run(main())
