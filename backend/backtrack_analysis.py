"""
Backtrack Analysis Tool
======================

Script per analizzare i dati storici del trading agent e fare backtrack
delle decisioni AI, correlandole con i risultati effettivi dei trade.

Funzionalità:
- Estrazione completa delle decisioni AI con contesto
- Analisi correlazione decisioni vs risultati
- Identificazione pattern di successo/fallimento
- Valutazione performance per modello/symbol/condizioni di mercato
- Report dettagliati per ottimizzazione strategia
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import statistics

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("backtrack_analysis")

# Import database utilities
import db_utils


class BacktrackAnalyzer:
    """Analyzer for trading decisions and outcomes"""

    def __init__(self):
        pass

    def connect_db(self):
        """Initialize database connection"""
        try:
            db_utils.init_db()
            logger.info("✅ Database initialized")
            return True
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False

    def extract_decisions_with_context(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """
        Extract all bot decisions with their full context

        Returns list of decisions with:
        - AI decision details
        - Market indicators at decision time
        - News sentiment at decision time
        - Forecasts at decision time
        - Linked executed trades (if any)
        """
        logger.info(f"📊 Extracting decisions from last {days_back} days...")

        query = """
        SELECT
            bo.id as decision_id,
            bo.created_at as decision_time,
            bo.operation,
            bo.symbol,
            bo.direction,
            bo.target_portion_of_balance,
            bo.leverage,
            bo.raw_payload as decision_payload,

            -- Context data
            ac.system_prompt,
            ic.ticker,
            ic.ts as indicators_timestamp,
            ic.price,
            ic.ema20, ic.macd, ic.rsi_7,
            ic.volume_bid, ic.volume_ask,
            ic.pp, ic.s1, ic.s2, ic.r1, ic.r2,
            ic.open_interest_latest, ic.open_interest_average,
            ic.funding_rate,
            ic.ema20_15m, ic.ema50_15m, ic.atr3_15m, ic.atr14_15m,
            ic.volume_15m_current, ic.volume_15m_average,
            ic.intraday_mid_prices,
            ic.intraday_ema20_series, ic.intraday_macd_series,
            ic.intraday_rsi7_series, ic.intraday_rsi14_series,
            ic.lt15m_macd_series, ic.lt15m_rsi14_series,

            nc.news_text,
            sc.value as sentiment_value,
            sc.classification as sentiment_classification,
            sc.sentiment_timestamp,
            fc.ticker as forecast_ticker,
            fc.timeframe,
            fc.last_price, fc.prediction, fc.lower_bound, fc.upper_bound,
            fc.change_pct, fc.forecast_timestamp,

            -- Linked executed trade
            et.id as trade_id,
            et.trade_type,
            et.entry_price, et.exit_price,
            et.size, et.size_usd,
            et.pnl_usd, et.pnl_pct,
            et.exit_reason, et.status,
            et.duration_minutes,
            et.created_at as trade_open_time,
            et.closed_at as trade_close_time

        FROM bot_operations bo
        LEFT JOIN ai_contexts ac ON bo.context_id = ac.id
        LEFT JOIN indicators_contexts ic ON ic.context_id = ac.id
        LEFT JOIN news_contexts nc ON nc.context_id = ac.id
        LEFT JOIN sentiment_contexts sc ON sc.context_id = ac.id
        LEFT JOIN forecasts_contexts fc ON fc.context_id = ac.id
        LEFT JOIN executed_trades et ON et.bot_operation_id = bo.id

        WHERE bo.created_at > NOW() - INTERVAL '%s days'
        ORDER BY bo.created_at DESC
        """

        try:
            with db_utils.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (days_back,))
                    columns = [desc[0] for desc in cur.description]
                    rows = cur.fetchall()

            # Group by decision_id (one decision can have multiple forecasts/indicators)
            decisions_dict = {}

            for row in rows:
                data = dict(zip(columns, row))
                decision_id = data['decision_id']

                if decision_id not in decisions_dict:
                    decisions_dict[decision_id] = {
                        'decision_id': decision_id,
                        'decision_time': data['decision_time'],
                        'operation': data['operation'],
                        'symbol': data['symbol'],
                        'direction': data['direction'],
                        'target_portion_of_balance': data['target_portion_of_balance'],
                        'leverage': data['leverage'],
                        'decision_payload': data['decision_payload'],
                        'system_prompt': data['system_prompt'],
                        'indicators': [],
                        'news_text': data['news_text'],
                        'sentiment': {
                            'value': data['sentiment_value'],
                            'classification': data['sentiment_classification'],
                            'timestamp': data['sentiment_timestamp']
                        } if data['sentiment_value'] else None,
                        'forecasts': [],
                        'executed_trade': None
                    }

                decision = decisions_dict[decision_id]

                # Add indicators if present
                if data['ticker'] and not any(ind.get('ticker') == data['ticker'] for ind in decision['indicators']):
                    indicators_data = {
                        'ticker': data['ticker'],
                        'timestamp': data['indicators_timestamp'],
                        'current': {
                            'price': data['price'],
                            'ema20': data['ema20'],
                            'macd': data['macd'],
                            'rsi_7': data['rsi_7']
                        },
                        'pivot_points': {
                            'pp': data['pp'], 's1': data['s1'], 's2': data['s2'],
                            'r1': data['r1'], 'r2': data['r2']
                        },
                        'derivatives': {
                            'open_interest_latest': data['open_interest_latest'],
                            'open_interest_average': data['open_interest_average'],
                            'funding_rate': data['funding_rate']
                        },
                        'longer_term_15m': {
                            'ema_20_current': data['ema20_15m'],
                            'ema_50_current': data['ema50_15m'],
                            'atr_3_current': data['atr3_15m'],
                            'atr_14_current': data['atr14_15m'],
                            'volume_current': data['volume_15m_current'],
                            'volume_average': data['volume_15m_average']
                        },
                        'intraday': {
                            'mid_prices': data['intraday_mid_prices'],
                            'ema_20': data['intraday_ema20_series'],
                            'macd': data['intraday_macd_series'],
                            'rsi_7': data['intraday_rsi7_series'],
                            'rsi_14': data['intraday_rsi14_series']
                        },
                        'volume': {
                            'bid': data['volume_bid'],
                            'ask': data['volume_ask']
                        },
                        'lt15m_macd_series': data['lt15m_macd_series'],
                        'lt15m_rsi14_series': data['lt15m_rsi14_series']
                    }
                    decision['indicators'].append(indicators_data)

                # Add forecasts if present
                if data['forecast_ticker']:
                    forecast_data = {
                        'ticker': data['forecast_ticker'],
                        'timeframe': data['timeframe'],
                        'last_price': data['last_price'],
                        'prediction': data['prediction'],
                        'lower_bound': data['lower_bound'],
                        'upper_bound': data['upper_bound'],
                        'change_pct': data['change_pct'],
                        'timestamp': data['forecast_timestamp']
                    }
                    decision['forecasts'].append(forecast_data)

                # Add executed trade if present
                if data['trade_id'] and not decision['executed_trade']:
                    decision['executed_trade'] = {
                        'trade_id': data['trade_id'],
                        'trade_type': data['trade_type'],
                        'entry_price': data['entry_price'],
                        'exit_price': data['exit_price'],
                        'size': data['size'],
                        'size_usd': data['size_usd'],
                        'pnl_usd': data['pnl_usd'],
                        'pnl_pct': data['pnl_pct'],
                        'exit_reason': data['exit_reason'],
                        'status': data['status'],
                        'duration_minutes': data['duration_minutes'],
                        'open_time': data['trade_open_time'],
                        'close_time': data['trade_close_time']
                    }

            decisions = list(decisions_dict.values())
            logger.info(f"✅ Extracted {len(decisions)} decisions with context")
            return decisions

        except Exception as e:
            logger.error(f"❌ Error extracting decisions: {e}")
            return []

    def analyze_decision_outcomes(self, decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze correlation between decisions and outcomes"""

        logger.info("🔍 Analyzing decision-outcome correlations...")

        analysis = {
            'total_decisions': len(decisions),
            'decisions_by_operation': defaultdict(int),
            'decisions_by_symbol': defaultdict(int),
            'decisions_by_direction': defaultdict(int),
            'confidence_distribution': [],
            'executed_vs_not': {'executed': 0, 'not_executed': 0},
            'outcome_analysis': {
                'profitable_trades': 0,
                'losing_trades': 0,
                'breakeven_trades': 0,
                'avg_pnl_profitable': 0,
                'avg_pnl_losing': 0,
                'win_rate_by_operation': {},
                'win_rate_by_symbol': {},
                'win_rate_by_direction': {},
                'exit_reason_distribution': defaultdict(int),
                'avg_duration_by_exit_reason': {}
            },
            'market_conditions_at_decision': {
                'avg_rsi_at_decision': [],
                'avg_macd_at_decision': [],
                'sentiment_distribution': defaultdict(int)
            }
        }

        profitable_trades = []
        losing_trades = []

        for decision in decisions:
            # Basic decision counts
            analysis['decisions_by_operation'][decision['operation']] += 1
            if decision['symbol']:
                analysis['decisions_by_symbol'][decision['symbol']] += 1
            if decision['direction']:
                analysis['decisions_by_direction'][decision['direction']] += 1

            # Confidence analysis
            payload = decision.get('decision_payload', {})
            if isinstance(payload, dict) and 'confidence' in payload:
                analysis['confidence_distribution'].append(payload['confidence'])

            # Execution analysis
            if decision['executed_trade']:
                analysis['executed_vs_not']['executed'] += 1
                trade = decision['executed_trade']

                # Outcome analysis
                if trade['pnl_usd'] is not None:
                    if trade['pnl_usd'] > 0:
                        analysis['outcome_analysis']['profitable_trades'] += 1
                        profitable_trades.append(trade['pnl_usd'])
                    elif trade['pnl_usd'] < 0:
                        analysis['outcome_analysis']['losing_trades'] += 1
                        losing_trades.append(trade['pnl_usd'])
                    else:
                        analysis['outcome_analysis']['breakeven_trades'] += 1

                # Exit reason distribution
                if trade['exit_reason']:
                    analysis['outcome_analysis']['exit_reason_distribution'][trade['exit_reason']] += 1

                # Win rate by categories
                operation = decision['operation']
                symbol = decision['symbol']
                direction = decision['direction']

                if operation not in analysis['outcome_analysis']['win_rate_by_operation']:
                    analysis['outcome_analysis']['win_rate_by_operation'][operation] = {'wins': 0, 'total': 0}
                if symbol and symbol not in analysis['outcome_analysis']['win_rate_by_symbol']:
                    analysis['outcome_analysis']['win_rate_by_symbol'][symbol] = {'wins': 0, 'total': 0}
                if direction and direction not in analysis['outcome_analysis']['win_rate_by_direction']:
                    analysis['outcome_analysis']['win_rate_by_direction'][direction] = {'wins': 0, 'total': 0}

                # Update win counts
                if trade['pnl_usd'] and trade['pnl_usd'] > 0:
                    analysis['outcome_analysis']['win_rate_by_operation'][operation]['wins'] += 1
                    if symbol:
                        analysis['outcome_analysis']['win_rate_by_symbol'][symbol]['wins'] += 1
                    if direction:
                        analysis['outcome_analysis']['win_rate_by_direction'][direction]['wins'] += 1

                # Update totals
                analysis['outcome_analysis']['win_rate_by_operation'][operation]['total'] += 1
                if symbol:
                    analysis['outcome_analysis']['win_rate_by_symbol'][symbol]['total'] += 1
                if direction:
                    analysis['outcome_analysis']['win_rate_by_direction'][direction]['total'] += 1

            else:
                analysis['executed_vs_not']['not_executed'] += 1

            # Market conditions at decision time
            if decision['indicators']:
                for indicator in decision['indicators']:
                    current = indicator.get('current', {})
                    if current.get('rsi_7'):
                        analysis['market_conditions_at_decision']['avg_rsi_at_decision'].append(current['rsi_7'])
                    if current.get('macd'):
                        analysis['market_conditions_at_decision']['avg_macd_at_decision'].append(current['macd'])

            # Sentiment analysis
            if decision['sentiment'] and decision['sentiment']['classification']:
                analysis['market_conditions_at_decision']['sentiment_distribution'][decision['sentiment']['classification']] += 1

        # Calculate averages
        if profitable_trades:
            analysis['outcome_analysis']['avg_pnl_profitable'] = statistics.mean(profitable_trades)
        if losing_trades:
            analysis['outcome_analysis']['avg_pnl_losing'] = statistics.mean(losing_trades)

        # Calculate win rates
        for op, stats in analysis['outcome_analysis']['win_rate_by_operation'].items():
            if stats['total'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total']) * 100

        for sym, stats in analysis['outcome_analysis']['win_rate_by_symbol'].items():
            if stats['total'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total']) * 100

        for dir, stats in analysis['outcome_analysis']['win_rate_by_direction'].items():
            if stats['total'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total']) * 100

        # Average market conditions
        if analysis['market_conditions_at_decision']['avg_rsi_at_decision']:
            analysis['market_conditions_at_decision']['avg_rsi_at_decision'] = statistics.mean(
                analysis['market_conditions_at_decision']['avg_rsi_at_decision']
            )

        if analysis['market_conditions_at_decision']['avg_macd_at_decision']:
            analysis['market_conditions_at_decision']['avg_macd_at_decision'] = statistics.mean(
                analysis['market_conditions_at_decision']['avg_macd_at_decision']
            )

        logger.info("✅ Decision-outcome analysis completed")
        return analysis

    def identify_improvement_areas(self, decisions: List[Dict[str, Any]], analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Identify areas for strategy improvement"""

        logger.info("🎯 Identifying improvement areas...")

        improvements = {
            'low_confidence_decisions': [],
            'high_risk_patterns': [],
            'market_condition_warnings': [],
            'exit_reason_issues': [],
            'symbol_performance_issues': [],
            'recommendations': []
        }

        # Low confidence decisions that were executed
        for decision in decisions:
            if decision['executed_trade']:
                payload = decision.get('decision_payload', {})
                confidence = payload.get('confidence', 0) if isinstance(payload, dict) else 0

                if confidence < 0.5:
                    trade = decision['executed_trade']
                    if trade['pnl_usd'] and trade['pnl_usd'] < 0:  # Losing trade with low confidence
                        improvements['low_confidence_decisions'].append({
                            'decision_id': decision['decision_id'],
                            'symbol': decision['symbol'],
                            'confidence': confidence,
                            'pnl_usd': trade['pnl_usd'],
                            'exit_reason': trade['exit_reason']
                        })

        # High risk patterns (high leverage + low confidence)
        for decision in decisions:
            if decision['executed_trade']:
                payload = decision.get('decision_payload', {})
                confidence = payload.get('confidence', 0) if isinstance(payload, dict) else 0
                leverage = decision.get('leverage', 1)

                if leverage >= 5 and confidence < 0.6:
                    improvements['high_risk_patterns'].append({
                        'decision_id': decision['decision_id'],
                        'symbol': decision['symbol'],
                        'leverage': leverage,
                        'confidence': confidence,
                        'outcome': decision['executed_trade']['pnl_usd']
                    })

        # Market condition warnings (extreme RSI)
        for decision in decisions:
            if decision['indicators']:
                for indicator in decision['indicators']:
                    current = indicator.get('current', {})
                    rsi = current.get('rsi_7')
                    if rsi and (rsi > 80 or rsi < 20):
                        improvements['market_condition_warnings'].append({
                            'decision_id': decision['decision_id'],
                            'symbol': decision['symbol'],
                            'rsi': rsi,
                            'operation': decision['operation'],
                            'outcome': decision['executed_trade']['pnl_usd'] if decision['executed_trade'] else None
                        })

        # Exit reason issues (high frequency of certain exit reasons)
        exit_reasons = analysis['outcome_analysis']['exit_reason_distribution']
        total_closed = sum(exit_reasons.values())

        for reason, count in exit_reasons.items():
            percentage = (count / total_closed) * 100 if total_closed > 0 else 0

            if reason == 'stop_loss' and percentage > 60:
                improvements['exit_reason_issues'].append({
                    'issue': 'High stop loss frequency',
                    'percentage': percentage,
                    'recommendation': 'Review stop loss placement or entry timing'
                })
            elif reason == 'circuit_breaker' and percentage > 20:
                improvements['exit_reason_issues'].append({
                    'issue': 'High circuit breaker exits',
                    'percentage': percentage,
                    'recommendation': 'Reduce position sizes or improve risk management'
                })

        # Symbol performance issues
        symbol_win_rates = analysis['outcome_analysis']['win_rate_by_symbol']
        for symbol, stats in symbol_win_rates.items():
            if stats['total'] >= 5 and stats['win_rate'] < 30:  # At least 5 trades, win rate < 30%
                improvements['symbol_performance_issues'].append({
                    'symbol': symbol,
                    'win_rate': stats['win_rate'],
                    'total_trades': stats['total'],
                    'recommendation': 'Consider avoiding this symbol or reviewing strategy'
                })

        # Generate recommendations
        if len(improvements['low_confidence_decisions']) > 0:
            improvements['recommendations'].append(
                f"Consider increasing minimum confidence threshold (currently allowing {len(improvements['low_confidence_decisions'])} low-confidence losing trades)"
            )

        if len(improvements['high_risk_patterns']) > 0:
            improvements['recommendations'].append(
                f"Review risk management for high-leverage trades (found {len(improvements['high_risk_patterns'])} high-risk patterns)"
            )

        execution_rate = (analysis['executed_vs_not']['executed'] / analysis['total_decisions']) * 100
        if execution_rate < 50:
            improvements['recommendations'].append(
                f"Low execution rate ({execution_rate:.1f}%). Consider relaxing filters or improving market timing"
            )

        logger.info("✅ Improvement areas identified")
        return improvements

    def generate_report(self, decisions: List[Dict[str, Any]], analysis: Dict[str, Any], improvements: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive backtrack report"""

        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'analysis_period_days': 30,
            'summary': {
                'total_decisions': analysis['total_decisions'],
                'execution_rate': (analysis['executed_vs_not']['executed'] / analysis['total_decisions']) * 100 if analysis['total_decisions'] > 0 else 0,
                'win_rate_overall': (analysis['outcome_analysis']['profitable_trades'] /
                                   (analysis['outcome_analysis']['profitable_trades'] + analysis['outcome_analysis']['losing_trades'])) * 100
                                   if (analysis['outcome_analysis']['profitable_trades'] + analysis['outcome_analysis']['losing_trades']) > 0 else 0,
                'avg_profit_per_trade': analysis['outcome_analysis']['avg_pnl_profitable'],
                'avg_loss_per_trade': analysis['outcome_analysis']['avg_pnl_losing']
            },
            'performance_by_category': {
                'by_operation': analysis['outcome_analysis']['win_rate_by_operation'],
                'by_symbol': analysis['outcome_analysis']['win_rate_by_symbol'],
                'by_direction': analysis['outcome_analysis']['win_rate_by_direction']
            },
            'market_conditions': analysis['market_conditions_at_decision'],
            'exit_reasons': dict(analysis['outcome_analysis']['exit_reason_distribution']),
            'improvement_areas': improvements,
            'raw_data': {
                'decisions_count': len(decisions),
                'decisions_sample': decisions[:5] if decisions else []  # First 5 decisions as sample
            }
        }

        return report

    def run_full_analysis(self, days_back: int = 30, save_to_file: bool = True) -> Dict[str, Any]:
        """Run complete backtrack analysis"""

        logger.info("🚀 Starting full backtrack analysis...")
        logger.info(f"📅 Analyzing last {days_back} days of trading data")

        if not self.connect_db():
            return {}

        # Extract data
        decisions = self.extract_decisions_with_context(days_back)

        if not decisions:
            logger.warning("⚠️ No decisions found in the specified period")
            return {}

        # Analyze outcomes
        analysis = self.analyze_decision_outcomes(decisions)

        # Identify improvements
        improvements = self.identify_improvement_areas(decisions, analysis)

        # Generate report
        report = self.generate_report(decisions, analysis, improvements)

        # Save to file
        if save_to_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'backtrack_report_{timestamp}.json'

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, default=str)

            logger.info(f"💾 Report saved to {filename}")

            # Also save raw decisions for detailed analysis
            decisions_filename = f'decisions_raw_{timestamp}.json'
            with open(decisions_filename, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, indent=2, default=str)

            logger.info(f"💾 Raw decisions saved to {decisions_filename}")

        logger.info("✅ Full backtrack analysis completed")
        return report

    def link_existing_trades_to_operations(self):
        """Link existing trades to operations based on timestamp and symbol matching"""
        logger.info("🔗 Linking existing trades to operations...")

        # Get all trades without bot_operation_id
        query_trades = """
            SELECT id, created_at, symbol, direction, entry_price, trade_type
            FROM executed_trades
            WHERE bot_operation_id IS NULL
            ORDER BY created_at ASC
        """

        # Get all operations
        query_operations = """
            SELECT id, created_at, symbol, direction, operation
            FROM bot_operations
            WHERE operation = 'open'
            ORDER BY created_at ASC
        """

        try:
            with db_utils.get_connection() as conn:
                with conn.cursor() as cur:
                    # Get trades
                    cur.execute(query_trades)
                    trades = cur.fetchall()

                    # Get operations
                    cur.execute(query_operations)
                    operations = cur.fetchall()

            linked_count = 0
            for trade in trades:
                trade_id, trade_time, trade_symbol, trade_direction, trade_price, trade_type = trade

                # Find matching operation within a reasonable time window (e.g., 5 minutes)
                matching_op = None
                for op in operations:
                    op_id, op_time, op_symbol, op_direction, op_operation = op

                    # Check if operation matches trade criteria
                    time_diff = abs((trade_time - op_time).total_seconds())
                    symbol_match = trade_symbol == op_symbol
                    direction_match = trade_direction == op_direction
                    operation_match = op_operation == 'open' and trade_type == 'open'

                    if (time_diff < 300 and  # Within 5 minutes
                        symbol_match and
                        direction_match and
                        operation_match):
                        matching_op = op_id
                        break

                # Link the trade to the operation
                if matching_op:
                    with db_utils.get_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                "UPDATE executed_trades SET bot_operation_id = %s WHERE id = %s",
                                (matching_op, trade_id)
                            )
                            conn.commit()
                    linked_count += 1
                    logger.info(f"✅ Linked trade {trade_id} to operation {matching_op}")

            logger.info(f"🔗 Linked {linked_count} trades to operations")
            return linked_count

        except Exception as e:
            logger.error(f"❌ Error linking trades to operations: {e}")
            return 0


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Trading Agent Backtrack Analysis')
    parser.add_argument('--days', type=int, default=30, help='Days to analyze (default: 30)')
    parser.add_argument('--no-save', action='store_true', help='Do not save results to file')
    parser.add_argument('--link-trades', action='store_true', help='Link existing trades to operations before analysis')

    args = parser.parse_args()

    analyzer = BacktrackAnalyzer()

    # Link existing trades if requested
    if args.link_trades:
        linked_count = analyzer.link_existing_trades_to_operations()
        print(f"Linked {linked_count} trades to operations")

    report = analyzer.run_full_analysis(
        days_back=args.days,
        save_to_file=not args.no_save
    )

    if report:
        print("\n" + "="*80)
        print("BACKTRACK ANALYSIS SUMMARY")
        print("="*80)
        print(f"Period: Last {args.days} days")
        print(f"Total Decisions: {report['summary']['total_decisions']}")
        print(f"Execution Rate: {report['summary']['execution_rate']:.1f}%")
        print(f"Win Rate: {report['summary']['win_rate_overall']:.1f}%")
        print(f"Avg Profit/Trade: ${report['summary']['avg_profit_per_trade']:.2f}")
        print(f"Avg Loss/Trade: ${report['summary']['avg_loss_per_trade']:.2f}")
        print(f"Improvement Areas: {len(report['improvement_areas']['recommendations'])} recommendations")
        print("="*80)

        if report['improvement_areas']['recommendations']:
            print("\nRECOMMENDATIONS:")
            for i, rec in enumerate(report['improvement_areas']['recommendations'], 1):
                print(f"{i}. {rec}")

        print("\nRaw data saved to JSON files for detailed analysis.")
    else:
        print("❌ Analysis failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
