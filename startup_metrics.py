from database_manager import MetricsDB

def main():
    st.set_page_config(page_title="Startup Metrics Dashboard", layout="wide")

    db = MetricsDB()
    saved_metrics = db.get_latest_metrics()

    if saved_metrics:
        cash_balance = saved_metrics['cash_balance']
        monthly_revenue = saved_metrics['monthly_revenue']
        monthly_expenses = saved_metrics['monthly_expenses']
        b2b_total = saved_metrics['b2b_total']
        b2b_new = saved_metrics['b2b_new']
        b2b_cac = saved_metrics['b2b_cac']
        b2b_churn_rate = saved_metrics['b2b_churn_rate']
        b2c_total = saved_metrics['b2c_total']
        b2c_new = saved_metrics['b2c_new']
        b2c_cac = saved_metrics['b2c_cac']
        b2c_churn_rate = saved_metrics['b2c_churn_rate']