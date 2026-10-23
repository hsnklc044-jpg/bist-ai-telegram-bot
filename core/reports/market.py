"""
QuantBIST RC7
Market Intelligence Report
"""

from __future__ import annotations

from core.models.dashboard import DashboardModel


def generate_market_report(
    dashboard: DashboardModel,
) -> str:
    """
    Generate market intelligence report.

    Source:

        DashboardModel.market

    """



    market = dashboard.market



    if market is None:

        return """
📈 QUANTBIST MARKET REPORT

No market data available.
"""





    indicators = market.indicators





    technical_trend = "-"

    rsi = 0

    macd = "-"



    if indicators is not None:

        technical_trend = (

            indicators.trend.value

            if hasattr(
                indicators.trend,
                "value",
            )

            else str(
                indicators.trend
            )

        )


        rsi = indicators.rsi


        macd = indicators.macd_signal





    return f"""
📈 QUANTBIST MARKET REPORT


════════════════════

🌍 MARKET STATUS


Symbol:

{market.index}



Trend:

{market.trend.value}



Regime:

{market.regime.status.value}



════════════════════

📊 MARKET SCORES


Market Score:

{market.market_score}



Regime Score:

{market.regime.score}



Breadth Score:

{market.breadth.score}



Sentiment Score:

{market.sentiment.score}



════════════════════

⚡ VOLATILITY


Level:

{market.volatility.value}



════════════════════

📉 TECHNICAL


Technical Trend:

{technical_trend}



RSI:

{rsi}



MACD:

{macd}



════════════════════

"""
