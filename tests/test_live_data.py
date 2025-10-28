#!/usr/bin/env python3
"""
Test Live Data Integration
"""
import asyncio
import json
from live_data_engine import live_data_engine
from ai_engine import ai_engine

async def test_live_ai_integration():
    """Test live data with AI integration"""
    print("Testing Live Data + AI Integration")
    print("=" * 40)
    
    # Start live data collection
    print("Starting live data collection...")
    data_task = asyncio.create_task(live_data_engine.start_live_data())
    
    # Wait for data
    await asyncio.sleep(15)
    
    # Get live data
    live_data = live_data_engine.get_live_data()
    print(f"Collected data for {len(live_data)} symbols/exchanges")
    
    if live_data:
        # Test AI processing on first symbol
        first_key = list(live_data.keys())[0]
        market_data = live_data[first_key]
        
        print(f"\nTesting AI on: {first_key}")
        print(f"Price: ${market_data.price}")
        print(f"Spread: {market_data.spread:.2f} bps")
        print(f"Volume: ${market_data.volume_usdt:,.0f}")
        
        # Convert to AI input
        ai_input = {
            'symbol': market_data.symbol,
            'score': 60.0,  # Mock score
            'spread_bps': market_data.spread,
            'qvol_usdt': market_data.volume_usdt,
            'atr_pct': 2.0,  # Mock ATR
            'liquidity_edge': 1.0,  # Mock liquidity
            'momentum_edge': 0.5,  # Mock momentum
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
        print("\nRunning AI analysis...")
        ai_signal = await ai_engine.analyze_market(ai_input)
        
        print(f"AI Action: {ai_signal.action}")
        print(f"AI Confidence: {ai_signal.confidence:.1f}%")
        print(f"AI Risk: {ai_signal.risk_level}")
        print(f"AI Reasoning: {ai_signal.reasoning}")
        print(f"AI Duration: {ai_signal.expected_duration}")
        
        print("\nAI Insights:")
        for insight in ai_signal.ai_insights:
            print(f"  - {insight}")
        
        print("\nMarket Conditions:")
        for key, value in ai_signal.market_conditions.items():
            print(f"  - {key}: {value}")
    
    # Stop data collection
    live_data_engine.stop()
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_live_ai_integration())
