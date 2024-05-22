# filename: stock_info.py
import yfinance as yf
from datetime import datetime, timedelta

# Function to calculate percentage change
def percentage_change(current, previous):
    try:
        return ((current - previous) / previous) * 100
    except ZeroDivisionError:
        return 0

# Get today's date and the date of one month ago
today = datetime.today().strftime('%Y-%m-%d')
one_month_ago = (datetime.today() - timedelta(days=30)).strftime('%Y-%m-%d')

# Fetch data for NVDA and TSLA
nvda = yf.Ticker("NVDA")
tsla = yf.Ticker("TSLA")

# Get historical market data
nvda_hist = nvda.history(start=one_month_ago, end=today)
tsla_hist = tsla.history(start=one_month_ago, end=today)

# Calculate percentage change over the past month
nvda_percent_change = percentage_change(nvda_hist['Close'].iloc[-1], nvda_hist['Close'].iloc[0])
tsla_percent_change = percentage_change(tsla_hist['Close'].iloc[-1], tsla_hist['Close'].iloc[0])

# Print current prices and percentage changes
print(f"NVDA: Current Price = ${nvda_hist['Close'].iloc[-1]:.2f}, Percentage Change Over Past Month = {nvda_percent_change:.2f}%")
print(f"TESLA: Current Price = ${tsla_hist['Close'].iloc[-1]:.2f}, Percentage Change Over Past Month = {tsla_percent_change:.2f}%")