from pathlib import Path
text = Path('src/market_scanner/jobs/loop.py').read_text().splitlines()
for i, line in enumerate(text, start=1):
    if 150 <= i <= 260:
        print(f"{i:03}: {line}")
