from pathlib import Path
path = Path('src/market_scanner/routers/opps.py')
print(list(path.read_bytes()[:4]))
