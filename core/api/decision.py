from core.dashboard.service import get_dashboard
from core.decision.service import get_decision as _get_decision


def decision():

    dashboard = get_dashboard()

    result = _get_decision(
        portfolio_stats=dashboard.portfolio.stats,
        portfolio=dashboard.portfolio,
        market=dashboard.market
    )

    return result


get_decision = decision