#!/usr/bin/env python3
"""
Simple Live Data Test
"""
import asyncio
import json
from live_data_engine import live_data_engine
from ai_engine import ai_engine

async def test_simple_live_data():
    """Simple test of live data"""
    print("Simple Live Data Test")
    print("=" * 30)
    
    # Start live data collection
    print("Starting live data collection...")
    data_task = asyncio.create_task(live_data_engine.start_live_data())
    
    # Wait for data
    await asyncio.sleep(10)
    
    # Get live data
    live_data = live_data_engine.get_live_data()
    print(f"Collected data for {len(live_data)} symbols/exchanges")
    
    if live_data:
        # Show first few entries
        for i, (key, data) in enumerate(list(live_data.items())[:3]):
            print(f"\n{i+1}. {key}")
            print(f"   Symbol: {data.symbol}")
            print(f"   Exchange: {data.exchange}")
            print(f"   Price: ${data.price}")
            print(f"   Spread: {data.spread:.2f} bps")
            print(f"   Volume: ${data.volume_usdt:,.0f}")
            print(f"   Change 24h: {data.change_percent_24h:.2f}%")
            print(f"   Status: {data.status}")
        
        # Test AI on first symbol
        first_key = list(live_data.keys())[0]
        market_data = live_data[first_key]
        
        print(f"\nTesting AI on: {first_key}")
        
        # Convert to AI input
        ai_input = {
            'symbol': market_data.symbol,
            'score': 60.0,
            'spread_bps': market_data.spread,
            'qvol_usdt': market_data.volume_usdt,
            'atr_pct': 2.0,
            'liquidity_edge': 1.0,
            'momentum_edge': 0.5,
            'price': market_data.price,
            'change_24h': market_data.change_percent_24h,
            'volume_24h': market_data.volume_24h,
            'high_24h': market_data.high_24h,
            'low_24h': market_data.low_24h,
            'bid': market_data.bid,
            'ask': market_data.ask,
            'timestamp': market_data.timestamp
        }
        
        # AI Analysis
        print("Running AI analysis...")
        ai_signal = await ai_engine.analyze_market(ai_input)
        
        print(f"AI Action: {ai_signal.action}")
        print(f"AI Confidence: {ai_signal.confidence:.1f}%")
        print(f"AI Risk: {ai_signal.risk_level}")
        print(f"AI Reasoning: {ai_signal.reasoning}")
        print(f"AI Duration: {ai_signal.expected_duration}")
        
        print("\nAI Insights:")
        for insight in ai_signal.ai_insights:
            print(f"  - {insight}")
    
    # Stop data collection
    live_data_engine.stop()
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_simple_live_data())
