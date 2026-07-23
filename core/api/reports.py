from core.dashboard.service import get_dashboard
from core.reports.service import generate_report as _generate_report


def report():

    dashboard = get_dashboard()

    result = _generate_report(
        dashboard
    )

    return result


get_report = report