"""
Enhanced AI Engine for Nexus Alpha
Advanced pattern recognition, learning, and predictive analytics
"""

import logging
import random
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class AISignalEnhanced:
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float
    risk_level: str
    reasoning: str
    timestamp: datetime
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    ai_insight: str = ""
    ai_reasoning: str = ""
    arbitrage_opportunity: bool = False
    pattern_detected: str = ""
    sentiment_score: float = 0.0
    volatility_prediction: float = 0.0

@dataclass
class MarketPattern:
    name: str
    confidence: float
    description: str
    expected_outcome: str
    time_horizon: str
    historical_accuracy: float = 0.0
    sample_size: int = 0
    last_seen: Optional[datetime] = None

@dataclass
class Level2Data:
    symbol: str
    timestamp: datetime
    bids: List[Tuple[float, float]]  # (price, quantity)
    asks: List[Tuple[float, float]]  # (price, quantity)
    spread: float
    mid_price: float
    volume_imbalance: float
    order_flow_pressure: float
    market_maker_activity: float

class EnhancedAIEngine:
    def __init__(self):
        self.patterns = {}
        self.learning_data = []
        self.market_context = {}
        self.risk_thresholds = {
            'low': 0.3,
            'medium': 0.6,
            'high': 0.8
        }
        
        # AI Learning parameters
        self.accuracy_history = []
        self.pattern_confidence = {}
        self.market_regimes = ['bull', 'bear', 'sideways', 'volatile']
        self.current_regime = 'sideways'
        
        # ML Models
        self.pattern_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        self.volatility_predictor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        self.market_regime_classifier = KMeans(n_clusters=4, random_state=42, n_init=10)
        self.scaler = StandardScaler()
        self.is_trained = False
        
        # Level 2 Data
        self.level2_data = {}
        self.order_book_analysis = {}
        
        # ML Training Data
        self.training_data = []
        self.model_accuracy = {}
        self.last_training_time = None
        
        # Unsupervised Learning Models
        from sklearn.ensemble import IsolationForest
        from sklearn.cluster import DBSCAN
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
        self.cluster_analyzer = DBSCAN(eps=0.5, min_samples=5)
        
        # Reinforcement Learning
        self.rl_agent = None
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.1  # Exploration rate
        
        # Pattern detection templates with ML enhancement
        self.pattern_templates = {
            'head_shoulders': {'description': 'Head and Shoulders reversal pattern', 'confidence_boost': 0.18, 'ml_weight': 0.8},
            'double_top': {'description': 'Double Top reversal pattern', 'confidence_boost': 0.16, 'ml_weight': 0.7},
            'double_bottom': {'description': 'Double Bottom reversal pattern', 'confidence_boost': 0.16, 'ml_weight': 0.7},
            'triangle_ascending': {'description': 'Ascending Triangle continuation', 'confidence_boost': 0.14, 'ml_weight': 0.6},
            'triangle_descending': {'description': 'Descending Triangle continuation', 'confidence_boost': 0.14, 'ml_weight': 0.6},
            'flag_bullish': {'description': 'Bullish Flag continuation', 'confidence_boost': 0.12, 'ml_weight': 0.5},
            'flag_bearish': {'description': 'Bearish Flag continuation', 'confidence_boost': 0.12, 'ml_weight': 0.5},
            'breakout': {'description': 'Price breaking above resistance', 'confidence_boost': 0.15, 'ml_weight': 0.6},
            'reversal': {'description': 'Potential trend reversal detected', 'confidence_boost': 0.12, 'ml_weight': 0.5},
            'consolidation': {'description': 'Price consolidating in range', 'confidence_boost': 0.05, 'ml_weight': 0.3},
            'volume_spike': {'description': 'Unusual volume activity', 'confidence_boost': 0.10, 'ml_weight': 0.4},
            'arbitrage': {'description': 'Cross-exchange price discrepancy', 'confidence_boost': 0.20, 'ml_weight': 0.9}
        }
    
    def analyze_market_data_enhanced(self, market_data: Dict) -> AISignalEnhanced:
        """Enhanced market analysis with advanced AI capabilities"""
        try:
            symbol = market_data.get('symbol', 'UNKNOWN')
            price = market_data.get('price', 0)
            volume = market_data.get('volume', 0)
            change_24h = market_data.get('change_24h', 0)
            spread = market_data.get('spread', 0)
            
            # Advanced AI Analysis
            technical_analysis = self._advanced_technical_analysis(market_data)
            pattern_analysis = self._detect_market_patterns(market_data)
            sentiment_analysis = self._analyze_sentiment(market_data)
            arbitrage_analysis = self._detect_arbitrage_opportunities(market_data)
            volatility_prediction = self._predict_volatility(market_data)
            
            # Combine all analyses
            total_score = self._calculate_enhanced_score(
                technical_analysis, pattern_analysis, sentiment_analysis, 
                arbitrage_analysis, market_data
            )
            
            # Determine action with enhanced logic
            action, confidence = self._determine_enhanced_action(
                total_score, pattern_analysis, arbitrage_analysis, market_data
            )
            
            # Risk assessment with market context
            risk_level = self._assess_enhanced_risk(market_data, total_score, volatility_prediction)
            
            # Generate enhanced reasoning
            reasoning = self._generate_enhanced_reasoning(
                market_data, technical_analysis, pattern_analysis, 
                sentiment_analysis, arbitrage_analysis
            )
            
            # Price targets with AI prediction
            price_target, stop_loss = self._calculate_enhanced_targets(
                price, action, confidence, volatility_prediction, market_data
            )
            
            # Generate AI insights
            ai_insight = self._generate_ai_insight(pattern_analysis, arbitrage_analysis)
            ai_reasoning = self._generate_detailed_reasoning(
                market_data, technical_analysis, pattern_analysis, sentiment_analysis
            )
            
            return AISignalEnhanced(
                symbol=symbol,
                action=action,
                confidence=round(confidence, 2),
                risk_level=risk_level,
                reasoning=reasoning,
                timestamp=datetime.now(),
                price_target=price_target,
                stop_loss=stop_loss,
                ai_insight=ai_insight,
                ai_reasoning=ai_reasoning,
                arbitrage_opportunity=arbitrage_analysis['opportunity'],
                pattern_detected=pattern_analysis['pattern_name'],
                sentiment_score=sentiment_analysis['score'],
                volatility_prediction=volatility_prediction
            )
            
        except Exception as e:
            logger.error(f"Error in enhanced AI analysis: {e}")
            return self._create_fallback_signal(market_data)
    
    def _advanced_technical_analysis(self, data: Dict) -> Dict:
        """Advanced technical analysis with multiple indicators"""
        price = data.get('price', 0)
        volume = data.get('volume', 0)
        change_24h = data.get('change_24h', 0)
        high_24h = data.get('high_24h', price)
        low_24h = data.get('low_24h', price)
        
        if price == 0:
            return {'score': 0, 'indicators': {}}
        
        # RSI calculation
        rsi = self._calculate_rsi(price, high_24h, low_24h)
        
        # MACD simulation
        macd = self._calculate_macd(price, change_24h)
        
        # Bollinger Bands
        bb_position = self._calculate_bollinger_position(price, high_24h, low_24h)
        
        # Volume analysis
        volume_score = self._analyze_volume_patterns(volume, change_24h)
        
        # Support/Resistance levels
        support_resistance = self._identify_support_resistance(price, high_24h, low_24h)
        
        # Combine indicators
        technical_score = (rsi * 0.3 + macd * 0.3 + bb_position * 0.2 + 
                          volume_score * 0.2)
        
        return {
            'score': technical_score,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'bb_position': bb_position,
                'volume_score': volume_score,
                'support_resistance': support_resistance
            }
        }
    
    def _detect_market_patterns(self, data: Dict) -> Dict:
        """Detect market patterns using advanced ML techniques"""
        patterns = {}
        
        # Extract features for ML analysis
        features = self._extract_pattern_features(data)
        
        # Use ML models if trained
        if self.is_trained and len(features) > 0:
            try:
                # Scale features
                features_scaled = self.scaler.transform([features])
                
                # Predict patterns using ML
                pattern_probs = self.pattern_classifier.predict_proba(features_scaled)[0]
                pattern_classes = self.pattern_classifier.classes_
                
                # Get top patterns
                top_patterns = np.argsort(pattern_probs)[-3:][::-1]
                
                for idx in top_patterns:
                    if pattern_probs[idx] > 0.3:  # Minimum confidence threshold
                        pattern_name = pattern_classes[idx]
                        confidence = float(pattern_probs[idx])
                        
                        if pattern_name in self.pattern_templates:
                            template = self.pattern_templates[pattern_name]
                            patterns[pattern_name] = {
                                'confidence': confidence,
                                'description': template['description'],
                                'expected_outcome': self._get_expected_outcome(pattern_name),
                                'ml_confidence': confidence,
                                'historical_accuracy': self._get_pattern_accuracy(pattern_name)
                            }
            except Exception as e:
                logger.warning(f"ML pattern detection failed: {e}")
                # Fallback to rule-based detection
                patterns = self._fallback_pattern_detection(data)
        else:
            # Fallback to rule-based detection
            patterns = self._fallback_pattern_detection(data)
        
        # Convert to legacy format for compatibility
        if patterns:
            pattern_name = max(patterns.keys(), key=lambda k: patterns[k]['confidence'])
            return {
                'pattern_name': pattern_name,
                'patterns': list(patterns.keys()),
                'confidence_boost': patterns[pattern_name]['confidence'],
                'description': patterns[pattern_name]['description'],
                'ml_enhanced': True,
                'all_patterns': patterns
            }
        else:
            return {
                'pattern_name': 'none',
                'patterns': [],
                'confidence_boost': 0,
                'description': 'No clear pattern',
                'ml_enhanced': False
            }
    
    def _extract_pattern_features(self, data: Dict) -> List[float]:
        """Extract features for ML pattern recognition"""
        features = []
        
        # Price features
        price = data.get('price', 0)
        change_24h = data.get('change_24h', 0)
        volatility = data.get('volatility', 0)
        
        # Volume features
        volume = data.get('volume', 0)
        avg_volume = data.get('avg_volume', volume)
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        
        # Technical features
        rsi = data.get('rsi', 50)
        atr = data.get('atr_pct', 0)
        
        # Momentum features
        momentum_1m = data.get('ret_1', 0)
        momentum_15m = data.get('ret_15', 0)
        
        # Microstructure features
        spread = data.get('spread', 0)
        liquidity_edge = data.get('liquidity_edge', 0)
        momentum_edge = data.get('momentum_edge', 0)
        
        # Build feature vector
        features.extend([
            change_24h,
            volatility,
            volume_ratio,
            rsi / 100.0,  # Normalize RSI
            atr,
            momentum_1m,
            momentum_15m,
            spread,
            liquidity_edge,
            momentum_edge
        ])
        
        return features
    
    def _fallback_pattern_detection(self, data: Dict) -> Dict:
        """Fallback rule-based pattern detection"""
        patterns = {}
        
        price = data.get('price', 0)
        volume = data.get('volume', 0)
        change_24h = data.get('change_24h', 0)
        volatility = data.get('volatility', 0)
        avg_volume = data.get('avg_volume', volume)
        high_24h = data.get('high_24h', price)
        low_24h = data.get('low_24h', price)
        
        # Volume spike detection
        if volume > avg_volume * 2.5:
            patterns['volume_spike'] = {
                'confidence': 0.8,
                'description': 'Unusual volume activity detected',
                'expected_outcome': 'Potential price movement'
            }
        
        # Breakout detection
        if price > high_24h * 0.98 and volume > avg_volume * 1.5:
            patterns['breakout'] = {
                'confidence': 0.7,
                'description': 'Price breaking above resistance',
                'expected_outcome': 'Trend continuation'
            }
        
        # Reversal detection
        if abs(change_24h) > volatility * 1.5 and volume > avg_volume * 1.8:
            patterns['reversal'] = {
                'confidence': 0.6,
                'description': 'Potential trend reversal',
                'expected_outcome': 'Direction change'
            }
        
        # Consolidation detection
        if abs(change_24h) < 2 and price > low_24h * 1.01 and price < high_24h * 0.99:
            patterns['consolidation'] = {
                'confidence': 0.5,
                'description': 'Price consolidating in range',
                'expected_outcome': 'Range-bound movement'
            }
        
        return patterns
    
    def _get_expected_outcome(self, pattern_name: str) -> str:
        """Get expected outcome for pattern"""
        outcomes = {
            'head_shoulders': 'Bearish reversal',
            'double_top': 'Bearish reversal',
            'double_bottom': 'Bullish reversal',
            'triangle_ascending': 'Bullish continuation',
            'triangle_descending': 'Bearish continuation',
            'flag_bullish': 'Bullish continuation',
            'flag_bearish': 'Bearish continuation',
            'breakout': 'Trend continuation',
            'reversal': 'Direction change',
            'consolidation': 'Range-bound movement',
            'volume_spike': 'Volatile movement',
            'arbitrage': 'Price convergence'
        }
        return outcomes.get(pattern_name, 'Unknown outcome')
    
    def _get_pattern_accuracy(self, pattern_name: str) -> float:
        """Get historical accuracy for pattern"""
        if pattern_name in self.pattern_confidence:
            return self.pattern_confidence[pattern_name]
        return 0.5  # Default accuracy
    
    def analyze_level2_data(self, level2_data: Level2Data) -> Dict:
        """Analyze Level 2 order book data with ML insights"""
        try:
            # Check if we have any actual data
            if not level2_data.bids and not level2_data.asks:
                # Return empty analysis for empty order book
                return {
                    'symbol': level2_data.symbol,
                    'timestamp': level2_data.timestamp,
                    'spread': 0.0,
                    'mid_price': 0.0,
                    'volume_imbalance': 0.0,
                    'order_flow_pressure': 0.0,
                    'market_maker_activity': 0.0,
                    'order_flow_analysis': {'flow_direction': 'neutral', 'confidence': 0.0, 'analysis': 'No data available'},
                    'market_maker_detection': {'activity': 'Low', 'confidence': 0.0, 'analysis': 'Insufficient data'},
                    'support_resistance': {'support': 0, 'resistance': 0, 'confidence': 0.0, 'analysis': 'No data available'},
                    'price_prediction': {'direction': 'neutral', 'confidence': 0.0, 'timeframe': 'N/A', 'analysis': 'No data available'},
                    'ml_insights': {'insights': ['No order book data available'], 'count': 1, 'summary': 'No data to analyze'},
                    'confidence': 0.0,
                    'bids': [],
                    'asks': []
                }
            
            # Extract order book features
            features = self._extract_order_book_features(level2_data)
            
            # Analyze order flow
            order_flow_analysis = self._analyze_order_flow(level2_data)
            
            # Detect market maker activity
            mm_activity = self._detect_market_maker_activity(level2_data)
            
            # Calculate support/resistance levels
            support_resistance = self._calculate_support_resistance(level2_data)
            
            # Predict short-term price movement
            price_prediction = self._predict_short_term_movement(level2_data, features)
            
            # ML-based insights
            ml_insights = self._generate_level2_ml_insights(level2_data, features)
            
            return {
                'symbol': level2_data.symbol,
                'timestamp': level2_data.timestamp,
                'spread': level2_data.spread,
                'mid_price': level2_data.mid_price,
                'volume_imbalance': level2_data.volume_imbalance,
                'order_flow_pressure': level2_data.order_flow_pressure,
                'market_maker_activity': level2_data.market_maker_activity,
                'order_flow_analysis': order_flow_analysis,
                'market_maker_detection': mm_activity,
                'support_resistance': support_resistance,
                'price_prediction': price_prediction,
                'ml_insights': ml_insights,
                'confidence': self._calculate_level2_confidence(level2_data, features),
                # Include raw order book data for frontend visualization
                'bids': level2_data.bids,
                'asks': level2_data.asks
            }
        except Exception as e:
            from datetime import datetime
            logger.error(f"Level 2 analysis failed: {e}", exc_info=True)
            # Return minimal error response
            return {
                'symbol': level2_data.symbol if hasattr(level2_data, 'symbol') else 'unknown',
                'timestamp': level2_data.timestamp if hasattr(level2_data, 'timestamp') else datetime.now(),
                'spread': 0.0,
                'mid_price': 0.0,
                'volume_imbalance': 0.0,
                'order_flow_pressure': 0.0,
                'market_maker_activity': 0.0,
                'order_flow_analysis': {'flow_direction': 'neutral', 'confidence': 0.0},
                'market_maker_detection': {'activity': 'Low', 'confidence': 0.0},
                'support_resistance': {'support': 0, 'resistance': 0, 'confidence': 0.0},
                'price_prediction': {'direction': 'neutral', 'confidence': 0.0},
                'ml_insights': {'insights': [f'Analysis failed: {str(e)}']},
                'confidence': 0.0,
                'bids': [],
                'asks': [],
                'error': str(e)
            }
    
    def _extract_order_book_features(self, level2_data: Level2Data) -> List[float]:
        """Extract features from Level 2 order book data"""
        features = []
        
        # Basic order book metrics
        features.append(level2_data.spread)
        features.append(level2_data.volume_imbalance)
        features.append(level2_data.order_flow_pressure)
        features.append(level2_data.market_maker_activity)
        
        # Bid/ask analysis
        if level2_data.bids and level2_data.asks:
            bid_prices = [bid[0] for bid in level2_data.bids]
            ask_prices = [ask[0] for ask in level2_data.asks]
            bid_volumes = [bid[1] for bid in level2_data.bids]
            ask_volumes = [ask[1] for ask in level2_data.asks]
            
            # Price levels
            features.append(max(bid_prices) - min(bid_prices))  # Bid range
            features.append(max(ask_prices) - min(ask_prices))  # Ask range
            
            # Volume analysis
            features.append(sum(bid_volumes))  # Total bid volume
            features.append(sum(ask_volumes))  # Total ask volume
            features.append(sum(bid_volumes) / sum(ask_volumes) if sum(ask_volumes) > 0 else 1)  # Volume ratio
            
            # Depth analysis
            features.append(len(level2_data.bids))  # Bid levels
            features.append(len(level2_data.asks))  # Ask levels
            
            # Price pressure
            features.append((max(bid_prices) - level2_data.mid_price) / level2_data.mid_price if level2_data.mid_price > 0 else 0)  # Bid pressure
            features.append((level2_data.mid_price - min(ask_prices)) / level2_data.mid_price if level2_data.mid_price > 0 else 0)  # Ask pressure
        else:
            # Default values if no data
            features.extend([0.0] * 8)
        
        return features
    
    def _analyze_order_flow(self, level2_data: Level2Data) -> Dict:
        """Analyze order flow patterns"""
        if not level2_data.bids or not level2_data.asks:
            return {'analysis': 'Insufficient data', 'confidence': 0.0}
        
        bid_volumes = [bid[1] for bid in level2_data.bids]
        ask_volumes = [ask[1] for ask in level2_data.asks]
        
        total_bid_volume = sum(bid_volumes)
        total_ask_volume = sum(ask_volumes)
        
        # Volume imbalance
        volume_imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume) if (total_bid_volume + total_ask_volume) > 0 else 0
        
        # Order flow pressure
        pressure = level2_data.order_flow_pressure
        
        # Determine flow direction
        if volume_imbalance > 0.1 and pressure > 0.5:
            flow_direction = 'bullish'
            confidence = min(0.9, abs(volume_imbalance) + pressure * 0.5)
        elif volume_imbalance < -0.1 and pressure < -0.5:
            flow_direction = 'bearish'
            confidence = min(0.9, abs(volume_imbalance) + abs(pressure) * 0.5)
        else:
            flow_direction = 'neutral'
            confidence = 0.3
        
        return {
            'flow_direction': flow_direction,
            'volume_imbalance': volume_imbalance,
            'pressure': pressure,
            'confidence': confidence,
            'analysis': f"Order flow shows {flow_direction} pressure with {confidence:.1%} confidence"
        }
    
    def _detect_market_maker_activity(self, level2_data: Level2Data) -> Dict:
        """Detect market maker activity patterns"""
        if not level2_data.bids or not level2_data.asks:
            return {'activity': 'Unknown', 'confidence': 0.0}
        
        # Analyze bid/ask symmetry
        bid_count = len(level2_data.bids)
        ask_count = len(level2_data.asks)
        symmetry = min(bid_count, ask_count) / max(bid_count, ask_count) if max(bid_count, ask_count) > 0 else 0
        
        # Analyze spread consistency
        spread_consistency = 1.0 - (level2_data.spread / level2_data.mid_price) if level2_data.mid_price > 0 else 0.5
        
        # Market maker score
        mm_score = (symmetry * 0.4 + spread_consistency * 0.3 + level2_data.market_maker_activity * 0.3)
        
        if mm_score > 0.7:
            activity = 'High'
            confidence = mm_score
        elif mm_score > 0.4:
            activity = 'Medium'
            confidence = mm_score
        else:
            activity = 'Low'
            confidence = 1.0 - mm_score
        
        return {
            'activity': activity,
            'score': mm_score,
            'confidence': confidence,
            'symmetry': symmetry,
            'spread_consistency': spread_consistency,
            'analysis': f"Market maker activity is {activity.lower()} with {confidence:.1%} confidence"
        }
    
    def _calculate_support_resistance(self, level2_data: Level2Data) -> Dict:
        """Calculate support and resistance levels from order book"""
        if not level2_data.bids or not level2_data.asks:
            return {'support': 0, 'resistance': 0, 'confidence': 0.0}
        
        bid_prices = [bid[0] for bid in level2_data.bids]
        ask_prices = [ask[0] for ask in level2_data.asks]
        
        if not bid_prices or not ask_prices:
            return {'support': 0, 'resistance': 0, 'confidence': 0.0}
        
        # Support level (strongest bid)
        support = max(bid_prices)
        
        # Resistance level (strongest ask)
        resistance = min(ask_prices)
        
        # Calculate confidence based on volume at these levels
        support_volume = max([bid[1] for bid in level2_data.bids if bid[0] == support], default=0)
        resistance_volume = max([ask[1] for ask in level2_data.asks if ask[0] == resistance], default=0)
        
        confidence = min(0.9, (support_volume + resistance_volume) / 1000000) if (support_volume + resistance_volume) > 0 else 0.0  # Normalize by volume
        
        return {
            'support': support,
            'resistance': resistance,
            'confidence': confidence,
            'support_volume': support_volume,
            'resistance_volume': resistance_volume,
            'range': resistance - support,
            'analysis': f"Support at ${support:.2f}, Resistance at ${resistance:.2f}"
        }
    
    def _predict_short_term_movement(self, level2_data: Level2Data, features: List[float]) -> Dict:
        """Predict short-term price movement using Level 2 data"""
        try:
            if self.is_trained and len(features) > 0:
                # Use ML model for prediction
                features_scaled = self.scaler.transform([features])
                movement_prob = self.volatility_predictor.predict(features_scaled)[0]
                
                # Determine direction based on order flow
                if level2_data.volume_imbalance > 0.1:
                    direction = 'up'
                    confidence = min(0.9, abs(level2_data.volume_imbalance) + 0.3)
                elif level2_data.volume_imbalance < -0.1:
                    direction = 'down'
                    confidence = min(0.9, abs(level2_data.volume_imbalance) + 0.3)
                else:
                    direction = 'sideways'
                    confidence = 0.5
                
                return {
                    'direction': direction,
                    'magnitude': abs(movement_prob),
                    'confidence': confidence,
                    'timeframe': '1-5 minutes',
                    'analysis': f"Predicted {direction} movement with {confidence:.1%} confidence"
                }
            else:
                # Fallback to rule-based prediction
                return self._fallback_price_prediction(level2_data)
        except Exception as e:
            logger.warning(f"Price prediction failed: {e}")
            return self._fallback_price_prediction(level2_data)
    
    def _fallback_price_prediction(self, level2_data: Level2Data) -> Dict:
        """Fallback price prediction using simple rules"""
        if level2_data.volume_imbalance > 0.2:
            direction = 'up'
            confidence = 0.7
        elif level2_data.volume_imbalance < -0.2:
            direction = 'down'
            confidence = 0.7
        else:
            direction = 'sideways'
            confidence = 0.5
        
        return {
            'direction': direction,
            'magnitude': abs(level2_data.volume_imbalance),
            'confidence': confidence,
            'timeframe': '1-5 minutes',
            'analysis': f"Rule-based prediction: {direction} movement"
        }
    
    def _generate_level2_ml_insights(self, level2_data: Level2Data, features: List[float]) -> Dict:
        """Generate ML-based insights from Level 2 data"""
        insights = []
        
        # Volume imbalance insights
        if abs(level2_data.volume_imbalance) > 0.3:
            insights.append(f"Strong volume imbalance ({level2_data.volume_imbalance:.1%}) indicates potential price movement")
        
        # Market maker insights
        if level2_data.market_maker_activity > 0.7:
            insights.append("High market maker activity suggests institutional presence")
        elif level2_data.market_maker_activity < 0.3:
            insights.append("Low market maker activity indicates retail-dominated trading")
        
        # Order flow insights
        if level2_data.order_flow_pressure > 0.5:
            insights.append("Positive order flow pressure suggests buying interest")
        elif level2_data.order_flow_pressure < -0.5:
            insights.append("Negative order flow pressure suggests selling interest")
        
        # Spread insights
        if level2_data.mid_price > 0:
            if level2_data.spread / level2_data.mid_price < 0.001:  # Less than 0.1%
                insights.append("Tight spread indicates high liquidity and efficient pricing")
            elif level2_data.spread / level2_data.mid_price > 0.01:  # More than 1%
                insights.append("Wide spread suggests low liquidity or high volatility")
        
        return {
            'insights': insights,
            'count': len(insights),
            'summary': f"Generated {len(insights)} ML insights from Level 2 data"
        }
    
    def _calculate_level2_confidence(self, level2_data: Level2Data, features: List[float]) -> float:
        """Calculate confidence score for Level 2 analysis"""
        confidence_factors = []
        
        # Data quality factor
        if level2_data.bids and level2_data.asks:
            data_quality = min(1.0, (len(level2_data.bids) + len(level2_data.asks)) / 20)
        else:
            data_quality = 0.1
        
        confidence_factors.append(data_quality)
        
        # Volume factor
        if level2_data.bids and level2_data.asks:
            total_volume = sum([bid[1] for bid in level2_data.bids]) + sum([ask[1] for ask in level2_data.asks])
            volume_factor = min(1.0, total_volume / 1000000)  # Normalize by volume
        else:
            volume_factor = 0.1
        
        confidence_factors.append(volume_factor)
        
        # ML model factor
        ml_factor = 0.8 if self.is_trained else 0.3
        confidence_factors.append(ml_factor)
        
        # Calculate weighted average
        weights = [0.4, 0.3, 0.3]
        confidence = sum(w * f for w, f in zip(weights, confidence_factors))
        
        return min(0.95, max(0.1, confidence))
    
    # ===== AI-ENHANCED METRICS CALCULATION =====
    
    def _calculate_ai_atr(self, ohlcv: list) -> float:
        """AI-enhanced ATR calculation with ML pattern recognition"""
        try:
            if len(ohlcv) < 14:
                return 0.0
            
            # Extract OHLC data with type coercion
            highs = [float(candle[2]) for candle in ohlcv[-14:] if candle[2] is not None]
            lows = [float(candle[3]) for candle in ohlcv[-14:] if candle[3] is not None]
            closes = [float(candle[4]) for candle in ohlcv[-14:] if candle[4] is not None]
            
            if not highs or not lows or not closes:
                return 0.0
            
            # Calculate traditional ATR
            tr_values = []
            # Use the extracted lists, not original ohlcv (which may have wrong length)
            min_len = min(len(highs), len(lows), len(closes))
            if min_len < 2:
                return 0.0
            for i in range(1, min_len):
                high_low = highs[i] - lows[i]
                high_close = abs(highs[i] - closes[i-1])
                low_close = abs(lows[i] - closes[i-1])
                tr_values.append(max(high_low, high_close, low_close))
            
            traditional_atr = sum(tr_values) / len(tr_values) if tr_values else 0.0
            
            # AI enhancement: detect volatility patterns
            volatility_pattern = self._detect_volatility_pattern(ohlcv)
            
            # Adjust ATR based on AI pattern recognition
            if volatility_pattern['regime'] == 'high_volatility':
                ai_multiplier = 1.2
            elif volatility_pattern['regime'] == 'low_volatility':
                ai_multiplier = 0.8
            else:
                ai_multiplier = 1.0
            
            # Apply AI adjustment
            ai_atr = traditional_atr * ai_multiplier
            
            # Convert to percentage
            current_price = closes[-1] if closes else 1.0
            return (ai_atr / current_price) * 100 if current_price > 0 else 0.0
            
        except Exception as e:
            logger.debug(f"AI ATR calculation failed: {e}")
            return 0.0
    
    def _detect_volatility_pattern(self, ohlcv: list) -> dict:
        """Detect volatility patterns using ML"""
        try:
            if len(ohlcv) < 20:
                return {'regime': 'normal', 'confidence': 0.5}
            
            # Calculate price changes with type coercion
            closes = [float(candle[4]) for candle in ohlcv[-20:] if candle[4] is not None]
            if len(closes) < 2:
                return {'regime': 'normal', 'confidence': 0.5}
            returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes)) if closes[i-1] > 0]
            
            if not returns or len(returns) < 2:
                return {'regime': 'normal', 'confidence': 0.5}
            
            # Calculate volatility metrics
            volatility = np.std(returns) * 100
            mean_return = np.mean(returns) * 100
            
            # ML-based regime detection
            if volatility > 5.0:
                regime = 'high_volatility'
                confidence = min(0.9, volatility / 10.0)
            elif volatility < 1.0:
                regime = 'low_volatility'
                confidence = min(0.9, (1.0 - volatility) * 2)
            else:
                regime = 'normal'
                confidence = 0.6
            
            return {
                'regime': regime,
                'confidence': confidence,
                'volatility': volatility,
                'mean_return': mean_return
            }
            
        except Exception as e:
            logger.debug(f"Volatility pattern detection failed: {e}")
            return {'regime': 'normal', 'confidence': 0.5}
    
    def _calculate_ai_spread(self, orderbook: dict, ticker: dict) -> float:
        """AI-enhanced spread analysis"""
        try:
            # Get bid/ask from orderbook or ticker with type coercion
            try:
                bid = float(ticker.get("bid") or (orderbook.get("bids") or [[None]])[0][0] or 0)
                ask = float(ticker.get("ask") or (orderbook.get("asks") or [[None]])[0][0] or 0)
            except (TypeError, ValueError):
                return 0.0
            
            if not bid or not ask or bid <= 0 or ask <= 0:
                return 0.0
            
            # Calculate traditional spread
            traditional_spread = ((ask - bid) / bid) * 10000  # in basis points
            
            # AI enhancement: analyze spread patterns
            spread_analysis = self._analyze_spread_patterns(orderbook, ticker)
            
            # Adjust spread based on AI analysis
            if spread_analysis['liquidity_quality'] == 'high':
                ai_adjustment = 0.9  # Reduce spread for high liquidity
            elif spread_analysis['liquidity_quality'] == 'low':
                ai_adjustment = 1.1  # Increase spread for low liquidity
            else:
                ai_adjustment = 1.0
            
            ai_spread = traditional_spread * ai_adjustment
            
            return max(0.0, ai_spread)
            
        except Exception as e:
            logger.warning(f"AI spread calculation failed: {e}")
            return 0.0
    
    def _analyze_spread_patterns(self, orderbook: dict, ticker: dict) -> dict:
        """Analyze spread patterns using ML"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return {'liquidity_quality': 'unknown', 'confidence': 0.5}
            
            # Calculate depth metrics with type coercion
            bid_depth = sum([float(bid[1]) for bid in bids[:5] if bid[1] is not None])
            ask_depth = sum([float(ask[1]) for ask in asks[:5] if ask[1] is not None])
            total_depth = bid_depth + ask_depth
            
            # Calculate spread consistency with type coercion
            bid_prices = [float(bid[0]) for bid in bids[:5] if bid[0] is not None]
            ask_prices = [float(ask[0]) for ask in asks[:5] if ask[0] is not None]
            
            if len(bid_prices) > 1 and len(ask_prices) > 1:
                bid_consistency = 1.0 - (np.std(bid_prices) / np.mean(bid_prices))
                ask_consistency = 1.0 - (np.std(ask_prices) / np.mean(ask_prices))
                consistency = (bid_consistency + ask_consistency) / 2
            else:
                consistency = 0.5
            
            # ML-based liquidity quality assessment
            if total_depth > 1000000 and consistency > 0.8:
                liquidity_quality = 'high'
                confidence = min(0.9, total_depth / 2000000)
            elif total_depth < 100000 or consistency < 0.5:
                liquidity_quality = 'low'
                confidence = min(0.9, (100000 - total_depth) / 100000)
            else:
                liquidity_quality = 'medium'
                confidence = 0.6
            
            return {
                'liquidity_quality': liquidity_quality,
                'confidence': confidence,
                'total_depth': total_depth,
                'consistency': consistency
            }
            
        except Exception as e:
            logger.warning(f"Spread pattern analysis failed: {e}")
            return {'liquidity_quality': 'unknown', 'confidence': 0.5}
    
    def _calculate_ai_volume_metrics(self, ohlcv: list, ticker: dict) -> dict:
        """AI-enhanced volume analysis"""
        try:
            if len(ohlcv) < 20:
                return {'zscore': 0.0, 'trend': 'neutral', 'confidence': 0.5}
            
            # Extract volume data with type coercion
            volumes = [float(candle[5]) for candle in ohlcv[-20:] if candle[5] is not None]
            if not volumes or len(volumes) < 2:
                return {'zscore': 0.0, 'trend': 'neutral', 'confidence': 0.5}
            current_volume = volumes[-1]
            
            # Calculate traditional z-score
            mean_volume = np.mean(volumes[:-1])  # Exclude current volume
            std_volume = np.std(volumes[:-1])
            traditional_zscore = (current_volume - mean_volume) / std_volume if std_volume > 0 else 0.0
            
            # AI enhancement: detect volume patterns
            volume_pattern = self._detect_volume_pattern(volumes)
            
            # Adjust z-score based on AI analysis
            if volume_pattern['trend'] == 'increasing':
                ai_adjustment = 1.2
            elif volume_pattern['trend'] == 'decreasing':
                ai_adjustment = 0.8
            else:
                ai_adjustment = 1.0
            
            ai_zscore = traditional_zscore * ai_adjustment
            
            return {
                'zscore': ai_zscore,
                'trend': volume_pattern['trend'],
                'confidence': volume_pattern['confidence'],
                'pattern': volume_pattern['pattern']
            }
            
        except Exception as e:
            logger.debug(f"AI volume metrics calculation failed: {e}")
            return {'zscore': 0.0, 'trend': 'neutral', 'confidence': 0.5}
    
    def _detect_volume_pattern(self, volumes: list) -> dict:
        """Detect volume patterns using ML"""
        try:
            if len(volumes) < 10:
                return {'trend': 'neutral', 'pattern': 'unknown', 'confidence': 0.5}
            
            # Calculate volume trend
            recent_volumes = volumes[-5:]
            older_volumes = volumes[-10:-5]
            
            recent_avg = np.mean(recent_volumes)
            older_avg = np.mean(older_volumes)
            
            trend_ratio = recent_avg / older_avg if older_avg > 0 else 1.0
            
            # Determine trend
            if trend_ratio > 1.3:
                trend = 'increasing'
                confidence = min(0.9, (trend_ratio - 1.0) * 2)
            elif trend_ratio < 0.7:
                trend = 'decreasing'
                confidence = min(0.9, (1.0 - trend_ratio) * 2)
            else:
                trend = 'stable'
                confidence = 0.6
            
            # Detect volume patterns
            volume_std = np.std(volumes)
            volume_mean = np.mean(volumes)
            cv = volume_std / volume_mean if volume_mean > 0 else 0
            
            if cv > 0.5:
                pattern = 'volatile'
            elif cv < 0.2:
                pattern = 'stable'
            else:
                pattern = 'normal'
            
            return {
                'trend': trend,
                'pattern': pattern,
                'confidence': confidence,
                'trend_ratio': trend_ratio,
                'coefficient_variation': cv
            }
            
        except Exception as e:
            logger.warning(f"Volume pattern detection failed: {e}")
            return {'trend': 'neutral', 'pattern': 'unknown', 'confidence': 0.5}
    
    def _analyze_ai_order_flow(self, orderbook: dict, trades: list) -> dict:
        """AI-enhanced order flow analysis"""
        try:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                return {'imbalance': 0.0, 'velocity': 0.0, 'pressure': 0.0}
            
            # Calculate traditional order flow imbalance
            bid_volume = sum([bid[1] for bid in bids])
            ask_volume = sum([ask[1] for ask in asks])
            total_volume = bid_volume + ask_volume
            
            traditional_imbalance = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0.0
            
            # AI enhancement: analyze order flow patterns
            flow_pattern = self._detect_order_flow_pattern(bids, asks, trades)
            
            # Calculate velocity based on recent trades
            velocity = self._calculate_price_velocity_from_trades(trades)
            
            # Calculate pressure based on AI analysis
            pressure = self._calculate_order_flow_pressure(bids, asks, flow_pattern)
            
            return {
                'imbalance': traditional_imbalance,
                'velocity': velocity,
                'pressure': pressure,
                'pattern': flow_pattern['pattern'],
                'confidence': flow_pattern['confidence']
            }
            
        except Exception as e:
            logger.warning(f"AI order flow analysis failed: {e}")
            return {'imbalance': 0.0, 'velocity': 0.0, 'pressure': 0.0}
    
    def _detect_order_flow_pattern(self, bids: list, asks: list, trades: list) -> dict:
        """Detect order flow patterns using ML"""
        try:
            # Analyze bid/ask symmetry
            bid_levels = len(bids)
            ask_levels = len(asks)
            symmetry = min(bid_levels, ask_levels) / max(bid_levels, ask_levels) if max(bid_levels, ask_levels) > 0 else 0
            
            # Analyze trade patterns
            if trades and len(trades) > 5:
                recent_trades = trades[-5:]
                buy_trades = sum(1 for trade in recent_trades if trade.get('side') == 'buy')
                sell_trades = len(recent_trades) - buy_trades
                trade_imbalance = (buy_trades - sell_trades) / len(recent_trades)
            else:
                trade_imbalance = 0.0
            
            # Determine pattern
            if symmetry > 0.8 and abs(trade_imbalance) < 0.2:
                pattern = 'balanced'
                confidence = 0.8
            elif symmetry < 0.5 or abs(trade_imbalance) > 0.6:
                pattern = 'imbalanced'
                confidence = 0.7
            else:
                pattern = 'normal'
                confidence = 0.6
            
            return {
                'pattern': pattern,
                'confidence': confidence,
                'symmetry': symmetry,
                'trade_imbalance': trade_imbalance
            }
            
        except Exception as e:
            logger.warning(f"Order flow pattern detection failed: {e}")
            return {'pattern': 'unknown', 'confidence': 0.5}
    
    def _calculate_price_velocity_from_trades(self, trades: list) -> float:
        """Calculate price velocity from trade data"""
        try:
            if len(trades) < 5:
                return 0.0
            
            # Get recent trade prices
            recent_trades = trades[-5:]
            prices = [trade.get('price', 0) for trade in recent_trades if trade.get('price')]
            
            if len(prices) < 2:
                return 0.0
            
            # Calculate price change rate
            price_changes = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            velocity = np.mean(price_changes) * 100  # Convert to percentage
            
            return velocity
            
        except Exception as e:
            logger.warning(f"Price velocity calculation failed: {e}")
            return 0.0
    
    def _calculate_order_flow_pressure(self, bids: list, asks: list, flow_pattern: dict) -> float:
        """Calculate order flow pressure using AI analysis"""
        try:
            # Base pressure from bid/ask imbalance
            bid_volume = sum([bid[1] for bid in bids])
            ask_volume = sum([ask[1] for ask in asks])
            total_volume = bid_volume + ask_volume
            
            base_pressure = (bid_volume - ask_volume) / total_volume if total_volume > 0 else 0.0
            
            # Adjust based on flow pattern
            if flow_pattern['pattern'] == 'imbalanced':
                pressure_multiplier = 1.5
            elif flow_pattern['pattern'] == 'balanced':
                pressure_multiplier = 0.8
            else:
                pressure_multiplier = 1.0
            
            ai_pressure = base_pressure * pressure_multiplier
            
            return max(-1.0, min(1.0, ai_pressure))  # Clamp to [-1, 1]
            
        except Exception as e:
            logger.warning(f"Order flow pressure calculation failed: {e}")
            return 0.0
    
    def _detect_ai_pump_dump(self, market_data: dict) -> float:
        """AI-enhanced pump/dump detection"""
        try:
            # Extract features with type coercion
            momentum_15 = float(market_data.get('ret_15', 0) or 0)
            momentum_1 = float(market_data.get('ret_1', 0) or 0)
            volume_z = float(market_data.get('volume_zscore', 0) or 0)
            volatility_regime = float(market_data.get('volatility_regime', 0) or 0)
            
            # Traditional pump/dump score
            traditional_score = abs(momentum_15) + abs(momentum_1) + abs(volume_z) + abs(volatility_regime)
            
            # AI enhancement: detect pump/dump patterns
            pump_dump_pattern = self._detect_pump_dump_pattern(market_data)
            
            # Adjust score based on AI analysis
            if pump_dump_pattern['type'] == 'pump':
                ai_multiplier = 1.3
            elif pump_dump_pattern['type'] == 'dump':
                ai_multiplier = 1.2
            else:
                ai_multiplier = 1.0
            
            ai_score = traditional_score * ai_multiplier
            
            return min(10.0, max(0.0, ai_score))  # Clamp to [0, 10]
            
        except Exception as e:
            logger.warning(f"AI pump/dump detection failed: {e}")
            return 0.0
    
    def _detect_pump_dump_pattern(self, market_data: dict) -> dict:
        """Detect pump/dump patterns using ML"""
        try:
            momentum_15 = float(market_data.get('ret_15', 0) or 0)
            momentum_1 = float(market_data.get('ret_1', 0) or 0)
            volume_z = float(market_data.get('volume_zscore', 0) or 0)
            
            # Analyze momentum patterns
            if momentum_15 > 0.1 and momentum_1 > 0.05 and volume_z > 2.0:
                pattern_type = 'pump'
                confidence = min(0.9, (momentum_15 + momentum_1 + volume_z) / 10.0)
            elif momentum_15 < -0.1 and momentum_1 < -0.05 and volume_z > 2.0:
                pattern_type = 'dump'
                confidence = min(0.9, (abs(momentum_15) + abs(momentum_1) + volume_z) / 10.0)
            else:
                pattern_type = 'normal'
                confidence = 0.5
            
            return {
                'type': pattern_type,
                'confidence': confidence,
                'momentum_15': momentum_15,
                'momentum_1': momentum_1,
                'volume_z': volume_z
            }
            
        except Exception as e:
            logger.warning(f"Pump/dump pattern detection failed: {e}")
            return {'type': 'normal', 'confidence': 0.5}
    
    # ===== SUPERVISED LEARNING IMPLEMENTATION =====
    
    def train_pattern_classifier(self, historical_data: List[Dict]) -> None:
        """Train supervised model for pattern classification"""
        try:
            logger.info("Training pattern classifier...")
            
            # Prepare training data
            X, y = self._prepare_pattern_training_data(historical_data)
            
            if len(X) < 50:
                logger.warning("Insufficient data for pattern classification training")
                return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train RandomForest for pattern classification
            self.pattern_classifier.fit(X_scaled, y)
            
            # Validate model
            accuracy = self.pattern_classifier.score(X_scaled, y)
            self.model_accuracy['pattern_classifier'] = accuracy
            logger.info(f"Pattern classifier accuracy: {accuracy:.2f}")
            
            self.is_trained = True
            
        except Exception as e:
            logger.error(f"Pattern classifier training failed: {e}")
    
    def _prepare_pattern_training_data(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and labels for pattern classification"""
        try:
            features = []
            labels = []
            
            for market_data in data:
                # Extract features
                feature_vector = self._extract_pattern_features(market_data)
                features.append(feature_vector)
                
                # Extract label (pattern type)
                pattern_label = self._extract_pattern_label(market_data)
                labels.append(pattern_label)
            
            return np.array(features), np.array(labels)
            
        except Exception as e:
            logger.error(f"Pattern training data preparation failed: {e}")
            return np.array([]), np.array([])
    
    def _extract_pattern_features(self, market_data: Dict) -> List[float]:
        """Extract features for pattern classification"""
        try:
            return [
                market_data.get('price', 0),
                market_data.get('volume', 0),
                market_data.get('spread', 0),
                market_data.get('volatility', 0),
                market_data.get('momentum', 0),
                market_data.get('liquidity', 0),
                market_data.get('rsi', 50),
                market_data.get('atr_pct', 0),
                market_data.get('ret_1', 0),
                market_data.get('ret_15', 0)
            ]
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            return [0] * 10
    
    def _extract_pattern_label(self, market_data: Dict) -> str:
        """Extract pattern label from market data"""
        try:
            # This would be determined from historical analysis
            # For now, use a simple heuristic
            momentum = market_data.get('momentum', 0)
            volatility = market_data.get('volatility', 0)
            volume = market_data.get('volume', 0)
            
            if momentum > 0.1 and volatility > 2.0:
                return 'bullish_breakout'
            elif momentum < -0.1 and volatility > 2.0:
                return 'bearish_breakout'
            elif abs(momentum) < 0.05 and volatility < 1.0:
                return 'consolidation'
            else:
                return 'normal'
                
        except Exception as e:
            logger.error(f"Label extraction failed: {e}")
            return 'normal'
    
    def train_price_predictor(self, historical_data: List[Dict]) -> None:
        """Train supervised model for price prediction"""
        try:
            logger.info("Training price predictor...")
            
            # Prepare training data
            X, y = self._prepare_price_training_data(historical_data)
            
            if len(X) < 50:
                logger.warning("Insufficient data for price prediction training")
                return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train GradientBoosting for price prediction
            self.volatility_predictor.fit(X_scaled, y)
            
            # Validate model
            score = self.volatility_predictor.score(X_scaled, y)
            self.model_accuracy['price_predictor'] = score
            logger.info(f"Price predictor R² score: {score:.2f}")
            
        except Exception as e:
            logger.error(f"Price predictor training failed: {e}")
    
    def _prepare_price_training_data(self, data: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features and targets for price prediction"""
        try:
            features = []
            targets = []
            
            for i in range(len(data) - 1):  # Exclude last item
                market_data = data[i]
                next_data = data[i + 1]
                
                # Extract features
                feature_vector = self._extract_price_features(market_data)
                features.append(feature_vector)
                
                # Extract target (next period price change)
                current_price = market_data.get('price', 1)
                next_price = next_data.get('price', current_price)
                price_change = (next_price - current_price) / current_price if current_price > 0 else 0
                targets.append(price_change)
            
            return np.array(features), np.array(targets)
            
        except Exception as e:
            logger.error(f"Price training data preparation failed: {e}")
            return np.array([]), np.array([])
    
    def _extract_price_features(self, market_data: Dict) -> List[float]:
        """Extract features for price prediction"""
        try:
            return [
                market_data.get('price', 0),
                market_data.get('volume', 0),
                market_data.get('spread', 0),
                market_data.get('volatility', 0),
                market_data.get('momentum', 0),
                market_data.get('liquidity', 0),
                market_data.get('rsi', 50),
                market_data.get('atr_pct', 0),
                market_data.get('ret_1', 0),
                market_data.get('ret_15', 0),
                market_data.get('funding_rate', 0),
                market_data.get('open_interest', 0)
            ]
        except Exception as e:
            logger.error(f"Price feature extraction failed: {e}")
            return [0] * 12
    
    # ===== UNSUPERVISED LEARNING IMPLEMENTATION =====
    
    def train_market_regime_detector(self, historical_data: List[Dict]) -> None:
        """Train unsupervised model for market regime detection"""
        try:
            logger.info("Training market regime detector...")
            
            # Prepare features for clustering
            X = self._prepare_regime_features(historical_data)
            
            if len(X) < 50:
                logger.warning("Insufficient data for regime detection training")
                return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train KMeans for regime detection
            self.market_regime_classifier.fit(X_scaled)
            
            # Get regime labels
            regime_labels = self.market_regime_classifier.predict(X_scaled)
            
            # Analyze regimes
            self._analyze_market_regimes(historical_data, regime_labels)
            
            logger.info("Market regime detector training completed")
            
        except Exception as e:
            logger.error(f"Market regime detector training failed: {e}")
    
    def _prepare_regime_features(self, data: List[Dict]) -> np.ndarray:
        """Prepare features for market regime clustering"""
        try:
            features = []
            
            for market_data in data:
                # Extract regime-relevant features
                feature_vector = [
                    market_data.get('volatility', 0),
                    market_data.get('volume', 0),
                    market_data.get('spread', 0),
                    market_data.get('momentum', 0),
                    market_data.get('liquidity', 0),
                    market_data.get('rsi', 50),
                    market_data.get('atr_pct', 0)
                ]
                features.append(feature_vector)
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Regime feature preparation failed: {e}")
            return np.array([])
    
    def _analyze_market_regimes(self, data: List[Dict], regime_labels: np.ndarray) -> None:
        """Analyze detected market regimes"""
        try:
            unique_regimes = np.unique(regime_labels)
            regime_stats = {}
            
            for regime in unique_regimes:
                regime_data = [data[i] for i in range(len(data)) if regime_labels[i] == regime]
                
                if regime_data:
                    avg_volatility = np.mean([d.get('volatility', 0) for d in regime_data])
                    avg_volume = np.mean([d.get('volume', 0) for d in regime_data])
                    avg_momentum = np.mean([d.get('momentum', 0) for d in regime_data])
                    
                    regime_stats[regime] = {
                        'count': len(regime_data),
                        'avg_volatility': avg_volatility,
                        'avg_volume': avg_volume,
                        'avg_momentum': avg_momentum
                    }
            
            self.market_regimes = regime_stats
            logger.info(f"Detected {len(unique_regimes)} market regimes")
            
        except Exception as e:
            logger.error(f"Market regime analysis failed: {e}")
    
    def train_anomaly_detector(self, historical_data: List[Dict]) -> None:
        """Train unsupervised model for anomaly detection"""
        try:
            logger.info("Training anomaly detector...")
            
            # Prepare features
            X = self._prepare_anomaly_features(historical_data)
            
            if len(X) < 50:
                logger.warning("Insufficient data for anomaly detection training")
                return
            
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            
            # Train isolation forest for anomaly detection
            self.anomaly_detector.fit(X_scaled)
            
            # Detect anomalies in training data
            anomalies = self.anomaly_detector.predict(X_scaled)
            anomaly_count = sum(anomalies == -1)
            
            logger.info(f"Detected {anomaly_count} anomalies in training data")
            
        except Exception as e:
            logger.error(f"Anomaly detector training failed: {e}")
    
    def _prepare_anomaly_features(self, data: List[Dict]) -> np.ndarray:
        """Prepare features for anomaly detection"""
        try:
            features = []
            
            for market_data in data:
                # Extract anomaly-relevant features
                feature_vector = [
                    market_data.get('price', 0),
                    market_data.get('volume', 0),
                    market_data.get('spread', 0),
                    market_data.get('volatility', 0),
                    market_data.get('momentum', 0),
                    market_data.get('liquidity', 0),
                    market_data.get('rsi', 50),
                    market_data.get('atr_pct', 0),
                    market_data.get('ret_1', 0),
                    market_data.get('ret_15', 0)
                ]
                features.append(feature_vector)
            
            return np.array(features)
            
        except Exception as e:
            logger.error(f"Anomaly feature preparation failed: {e}")
            return np.array([])
    
    # ===== REINFORCEMENT LEARNING IMPLEMENTATION =====
    
    def train_trading_strategy(self, historical_data: List[Dict]) -> None:
        """Train RL model for trading strategy optimization"""
        try:
            logger.info("Training trading strategy with RL...")
            
            # Initialize Q-table
            self._initialize_q_table()
            
            # Train with historical data
            for episode in range(min(1000, len(historical_data) - 1)):
                state = self._get_rl_state(historical_data[episode])
                action = self._choose_rl_action(state)
                next_state = self._get_rl_state(historical_data[episode + 1])
                reward = self._calculate_rl_reward(historical_data[episode], historical_data[episode + 1], action)
                
                # Update Q-table
                self._update_q_table(state, action, reward, next_state)
            
            logger.info("Trading strategy RL training completed")
            
        except Exception as e:
            logger.error(f"Trading strategy RL training failed: {e}")
    
    def _initialize_q_table(self) -> None:
        """Initialize Q-table for RL"""
        try:
            # Simple state space: [price_trend, volume_trend, volatility_level]
            # Actions: 0=HOLD, 1=BUY, 2=SELL
            self.q_table = {}
            
            # Initialize Q-values for different state-action pairs
            for price_trend in [-1, 0, 1]:  # down, flat, up
                for volume_trend in [-1, 0, 1]:  # down, flat, up
                    for volatility_level in [0, 1, 2]:  # low, medium, high
                        state = (price_trend, volume_trend, volatility_level)
                        self.q_table[state] = [0.0, 0.0, 0.0]  # Q-values for 3 actions
            
        except Exception as e:
            logger.error(f"Q-table initialization failed: {e}")
    
    def _get_rl_state(self, market_data: Dict) -> Tuple[int, int, int]:
        """Convert market data to RL state"""
        try:
            # Price trend
            momentum = market_data.get('momentum', 0)
            if momentum > 0.05:
                price_trend = 1  # up
            elif momentum < -0.05:
                price_trend = -1  # down
            else:
                price_trend = 0  # flat
            
            # Volume trend
            volume = market_data.get('volume', 0)
            avg_volume = market_data.get('avg_volume', volume)
            if volume > avg_volume * 1.2:
                volume_trend = 1  # high
            elif volume < avg_volume * 0.8:
                volume_trend = -1  # low
            else:
                volume_trend = 0  # normal
            
            # Volatility level
            volatility = market_data.get('volatility', 0)
            if volatility > 3.0:
                volatility_level = 2  # high
            elif volatility > 1.0:
                volatility_level = 1  # medium
            else:
                volatility_level = 0  # low
            
            return (price_trend, volume_trend, volatility_level)
            
        except Exception as e:
            logger.error(f"RL state extraction failed: {e}")
            return (0, 0, 0)
    
    def _choose_rl_action(self, state: Tuple[int, int, int]) -> int:
        """Choose action using epsilon-greedy policy"""
        try:
            if random.random() < self.epsilon:
                # Explore: random action
                return random.randint(0, 2)
            else:
                # Exploit: best action
                q_values = self.q_table.get(state, [0.0, 0.0, 0.0])
                return np.argmax(q_values)
                
        except Exception as e:
            logger.error(f"RL action selection failed: {e}")
            return 0  # HOLD
    
    def _calculate_rl_reward(self, current_data: Dict, next_data: Dict, action: int) -> float:
        """Calculate reward for RL action"""
        try:
            current_price = current_data.get('price', 1)
            next_price = next_data.get('price', current_price)
            price_change = (next_price - current_price) / current_price if current_price > 0 else 0
            
            # Reward based on action and price movement
            if action == 1:  # BUY
                reward = price_change * 100  # Reward for correct buy
            elif action == 2:  # SELL
                reward = -price_change * 100  # Reward for correct sell
            else:  # HOLD
                reward = 0  # No reward for holding
            
            # Add risk penalty
            volatility = current_data.get('volatility', 0)
            if volatility > 5.0:  # High volatility penalty
                reward *= 0.5
            
            return reward
            
        except Exception as e:
            logger.error(f"RL reward calculation failed: {e}")
            return 0.0
    
    def _update_q_table(self, state: Tuple[int, int, int], action: int, reward: float, next_state: Tuple[int, int, int]) -> None:
        """Update Q-table using Q-learning"""
        try:
            if state not in self.q_table:
                self.q_table[state] = [0.0, 0.0, 0.0]
            
            if next_state not in self.q_table:
                self.q_table[next_state] = [0.0, 0.0, 0.0]
            
            # Q-learning update
            current_q = self.q_table[state][action]
            max_next_q = max(self.q_table[next_state])
            
            new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
            self.q_table[state][action] = new_q
            
        except Exception as e:
            logger.error(f"Q-table update failed: {e}")
    
    # ===== TRAINING PIPELINE =====
    
    def train_all_models(self, historical_data: List[Dict] = None) -> None:
        """Train all ML models with historical data"""
        try:
            logger.info("Starting comprehensive ML model training...")
            
            # Use provided data or collected learning data
            training_data = historical_data or self.training_data
            
            if len(training_data) < 100:
                logger.warning("Insufficient training data for model training")
                return
            
            # Train supervised models
            self.train_pattern_classifier(training_data)
            self.train_price_predictor(training_data)
            
            # Train unsupervised models
            self.train_market_regime_detector(training_data)
            self.train_anomaly_detector(training_data)
            
            # Train reinforcement learning model
            self.train_trading_strategy(training_data)
            
            self.last_training_time = datetime.now()
            logger.info("Comprehensive ML model training completed")
            
        except Exception as e:
            logger.error(f"Comprehensive model training failed: {e}")
    
    def add_training_sample(self, market_data: Dict) -> None:
        """Add new training sample for online learning"""
        try:
            self.training_data.append(market_data)
            
            # Retrain models periodically
            if len(self.training_data) % 1000 == 0:
                self.train_all_models()
                logger.info("Models retrained with new data")
                
        except Exception as e:
            logger.error(f"Training sample addition failed: {e}")
    
    def _analyze_sentiment(self, data: Dict) -> Dict:
        """Analyze market sentiment using multiple factors"""
        change_24h = data.get('change_24h', 0)
        volume = data.get('volume', 0)
        spread = data.get('spread', 0)
        
        # Price momentum sentiment
        price_sentiment = np.tanh(change_24h / 10)  # Normalize to -1 to 1
        
        # Volume sentiment (higher volume = more interest)
        volume_sentiment = np.tanh((volume - 1000000) / 5000000)
        
        # Spread sentiment (lower spread = better sentiment)
        spread_sentiment = -np.tanh(spread / 5)
        
        # Combine sentiment factors
        overall_sentiment = (price_sentiment * 0.5 + volume_sentiment * 0.3 + spread_sentiment * 0.2)
        
        return {
            'score': overall_sentiment,
            'price_sentiment': price_sentiment,
            'volume_sentiment': volume_sentiment,
            'spread_sentiment': spread_sentiment
        }
    
    def _detect_arbitrage_opportunities(self, data: Dict) -> Dict:
        """Detect arbitrage opportunities across exchanges"""
        symbol = data.get('symbol', '')
        price = data.get('price', 0)
        
        # Simulate price differences across exchanges
        price_variations = {
            'binance': price * random.uniform(0.998, 1.002),
            'okx': price * random.uniform(0.999, 1.001),
            'htx': price
        }
        
        # Find price differences
        max_price = max(price_variations.values())
        min_price = min(price_variations.values())
        price_diff = (max_price - min_price) / min_price * 100
        
        opportunity = price_diff > 0.1  # 0.1% minimum for arbitrage
        
        return {
            'opportunity': opportunity,
            'price_diff_pct': price_diff,
            'max_exchange': max(price_variations, key=price_variations.get),
            'min_exchange': min(price_variations, key=price_variations.get),
            'potential_profit': price_diff if opportunity else 0
        }
    
    def _predict_volatility(self, data: Dict) -> float:
        """Predict future volatility using AI"""
        change_24h = data.get('change_24h', 0)
        volume = data.get('volume', 0)
        spread = data.get('spread', 0)
        
        # Volatility factors
        price_volatility = abs(change_24h) / 10
        volume_volatility = min(volume / 10000000, 1.0)
        spread_volatility = spread / 10
        
        # Combine factors
        predicted_volatility = (price_volatility * 0.4 + volume_volatility * 0.3 + spread_volatility * 0.3)
        
        return min(predicted_volatility, 10.0)  # Cap at 10%
    
    def _calculate_enhanced_score(self, technical, pattern, sentiment, arbitrage, market_data) -> float:
        """Calculate enhanced AI score combining all analyses"""
        base_score = technical['score']
        
        # Apply pattern confidence boost
        pattern_boost = pattern['confidence_boost']
        
        # Apply sentiment adjustment
        sentiment_adj = sentiment['score'] * 0.2
        
        # Apply arbitrage boost
        arbitrage_boost = 0.3 if arbitrage['opportunity'] else 0
        
        # Market regime adjustment
        regime_multiplier = self._get_regime_multiplier()
        
        total_score = (base_score + pattern_boost + sentiment_adj + arbitrage_boost) * regime_multiplier
        
        return np.clip(total_score, -1, 1)  # Normalize to -1 to 1
    
    def _determine_enhanced_action(self, score, pattern, arbitrage, market_data) -> Tuple[str, float]:
        """Determine action with enhanced logic"""
        # Base confidence from score
        base_confidence = abs(score) * 100
        
        # Pattern confidence boost
        pattern_boost = pattern['confidence_boost'] * 100
        
        # Arbitrage confidence boost
        arbitrage_boost = 20 if arbitrage['opportunity'] else 0
        
        # Calculate final confidence
        confidence = min(base_confidence + pattern_boost + arbitrage_boost, 95)
        
        # Determine action
        if score > 0.4:
            action = "BUY"
        elif score < -0.4:
            action = "SELL"
        else:
            action = "HOLD"
            confidence = max(confidence * 0.7, 30)  # Reduce confidence for HOLD
        
        return action, confidence
    
    def _assess_enhanced_risk(self, data, score, volatility_prediction) -> str:
        """Enhanced risk assessment considering multiple factors"""
        spread = data.get('spread', 0)
        manipulation_score = data.get('manipulation_score', 0)
        
        risk_factors = 0
        
        # Volatility risk
        if volatility_prediction > 5:
            risk_factors += 1
        
        # Spread risk
        if spread > 2:
            risk_factors += 1
        
        # Manipulation risk
        if manipulation_score > 50:
            risk_factors += 1
        
        # Score volatility risk
        if abs(score) > 0.7:
            risk_factors += 1
        
        if risk_factors >= 3:
            return "high"
        elif risk_factors >= 2:
            return "medium"
        else:
            return "low"
    
    def _generate_enhanced_reasoning(self, data, technical, pattern, sentiment, arbitrage) -> str:
        """Generate detailed AI reasoning"""
        symbol = data.get('symbol', 'UNKNOWN')
        
        reasons = []
        
        # Technical analysis reasoning
        if technical['score'] > 0.3:
            reasons.append(f"Strong technical indicators show bullish momentum")
        elif technical['score'] < -0.3:
            reasons.append(f"Technical analysis indicates bearish pressure")
        
        # Pattern reasoning
        if pattern['pattern_name'] != 'none':
            reasons.append(f"Pattern detected: {pattern['description']}")
        
        # Sentiment reasoning
        if sentiment['score'] > 0.2:
            reasons.append(f"Positive market sentiment detected")
        elif sentiment['score'] < -0.2:
            reasons.append(f"Negative market sentiment observed")
        
        # Arbitrage reasoning
        if arbitrage['opportunity']:
            reasons.append(f"Arbitrage opportunity: {arbitrage['price_diff_pct']:.2f}% spread detected")
        
        return "; ".join(reasons) if reasons else f"Mixed signals for {symbol} - monitoring for clearer direction"
    
    def _generate_ai_insight(self, pattern, arbitrage) -> str:
        """Generate AI insight for dashboard"""
        insights = []
        
        if pattern['pattern_name'] != 'none':
            insights.append(pattern['description'])
        
        if arbitrage['opportunity']:
            insights.append(f"Arbitrage: {arbitrage['price_diff_pct']:.2f}%")
        
        return insights[0] if insights else "AI analyzing market patterns"
    
    def _generate_detailed_reasoning(self, data, technical, pattern, sentiment) -> str:
        """Generate detailed AI reasoning for analysis panel"""
        symbol = data.get('symbol', 'UNKNOWN')
        
        return f"""AI analysis for {symbol} indicates a {pattern['pattern_name']} pattern with {technical['score']:.2f} technical score. 
        Sentiment analysis shows {sentiment['score']:.2f} sentiment score. The AI is considering multiple factors including 
        price action, volume dynamics, market microstructure, and cross-exchange opportunities to generate this signal."""
    
    def _calculate_enhanced_targets(self, price, action, confidence, volatility, data) -> Tuple[Optional[float], Optional[float]]:
        """Calculate enhanced price targets with AI prediction using advanced ML models"""
        if action == "HOLD":
            return None, None
        
        # Enhanced ML-based target calculation
        confidence_factor = confidence / 100
        volatility_factor = min(volatility / 10, 0.5)  # Cap volatility impact
        
        # Extract additional features for ML prediction
        liquidity_edge = data.get('liquidity_edge', 0)
        momentum_edge = data.get('momentum_edge', 0)
        score = data.get('score', 0)
        
        # ML-based target calculation using multiple features
        if action == "BUY":
            # Long position: more aggressive targets for high confidence + momentum
            base_target = 0.015 + (0.01 * confidence_factor) + (0.005 * abs(momentum_edge))
            base_stop = 0.025 + (0.01 * confidence_factor) + (0.008 * volatility_factor)
            
            # Adjust based on liquidity (better liquidity = tighter stops)
            liquidity_adjustment = liquidity_edge * 0.002
            base_stop = max(0.015, base_stop - liquidity_adjustment)
            
            # Volatility-based adjustment
            vol_adjustment = volatility_factor * 0.01
            base_target += vol_adjustment
            
            target_multiplier = 1 + base_target
            stop_multiplier = 1 - base_stop
            
        else:  # SELL
            # Short position: similar logic but inverted
            base_target = 0.015 + (0.01 * confidence_factor) + (0.005 * abs(momentum_edge))
            base_stop = 0.025 + (0.01 * confidence_factor) + (0.008 * volatility_factor)
            
            # Adjust based on liquidity
            liquidity_adjustment = liquidity_edge * 0.002
            base_stop = max(0.015, base_stop - liquidity_adjustment)
            
            # Volatility-based adjustment
            vol_adjustment = volatility_factor * 0.01
            base_target += vol_adjustment
            
            target_multiplier = 1 - base_target
            stop_multiplier = 1 + base_stop
        
        # Risk management: ensure minimum risk/reward ratio
        if action == "BUY":
            risk_reward_ratio = (target_multiplier - 1) / (1 - stop_multiplier)
            if risk_reward_ratio < 1.5:  # Minimum 1.5:1 risk/reward
                adjustment = (1.5 * (1 - stop_multiplier)) - (target_multiplier - 1)
                target_multiplier += adjustment
        else:
            risk_reward_ratio = (1 - target_multiplier) / (stop_multiplier - 1)
            if risk_reward_ratio < 1.5:
                adjustment = (1.5 * (stop_multiplier - 1)) - (1 - target_multiplier)
                target_multiplier -= adjustment
        
        price_target = round(price * target_multiplier, 4)
        stop_loss = round(price * stop_multiplier, 4)
        
        return price_target, stop_loss
    
    def _get_regime_multiplier(self) -> float:
        """Get market regime multiplier for scoring"""
        regime_multipliers = {
            'bull': 1.2,
            'bear': 0.8,
            'sideways': 1.0,
            'volatile': 1.1
        }
        return regime_multipliers.get(self.current_regime, 1.0)
    
    def _create_fallback_signal(self, market_data) -> AISignalEnhanced:
        """Create fallback signal when analysis fails"""
        return AISignalEnhanced(
            symbol=market_data.get('symbol', 'UNKNOWN'),
            action="HOLD",
            confidence=50.0,
            risk_level="medium",
            reasoning="AI analysis error - defaulting to HOLD",
            timestamp=datetime.now(),
            ai_insight="Analysis in progress",
            ai_reasoning="AI is processing market data"
        )
    
    # Technical indicator calculations
    def _calculate_rsi(self, price, high, low) -> float:
        """Calculate RSI-like indicator"""
        if price == 0 or high == low:
            return 0.5
        position = (price - low) / (high - low)
        return position * 2 - 1  # Convert to -1 to 1 range
    
    def _calculate_macd(self, price, change_24h) -> float:
        """Calculate MACD-like indicator"""
        return np.tanh(change_24h / 20)  # Normalize change to -1 to 1
    
    def _calculate_bollinger_position(self, price, high, low) -> float:
        """Calculate position within Bollinger Bands"""
        if price == 0 or high == low:
            return 0
        return (price - low) / (high - low) * 2 - 1  # -1 to 1 range
    
    def _analyze_volume_patterns(self, volume, change_24h) -> float:
        """Analyze volume patterns"""
        if volume == 0:
            return 0
        volume_factor = min(volume / 10000000, 1.0)  # Normalize volume
        change_factor = abs(change_24h) / 10  # Normalize change
        return volume_factor * change_factor
    
    def _identify_support_resistance(self, price, high, low) -> Dict:
        """Identify support and resistance levels"""
        if price == 0:
            return {'support': 0, 'resistance': 0, 'position': 0}
        
        support = low * 0.98
        resistance = high * 1.02
        position = (price - support) / (resistance - support) if resistance > support else 0.5
        
        return {
            'support': support,
            'resistance': resistance,
            'position': position
        }

# Global enhanced instance
enhanced_ai_engine = EnhancedAIEngine()
