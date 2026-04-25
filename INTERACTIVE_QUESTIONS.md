To run the agent:

For Apple stock:        

"python main.py --ticker AAPL"

For Tesla:

"python main.py --ticker TSLA"

For any custom question:

"python main.py --question "Analyze NVDA and give me a buy hold or sell recommendation"

# Questions You Can Ask In Interactive Mode

Use interactive mode when you want to ask follow-up questions and let the agent
remember the previous stock.

Start it with:

```
python main.py --interactive
```

Then ask questions like the examples below.

## Full Financial Reports

```text
Generate a financial report for MSFT
```

```text
Analyze AAPL and give me a recommendation
```

```text
Create a complete financial report for TSLA
```

```text
Give me a Buy, Hold, or Sell recommendation for NVDA
```

```text
Prepare a stock analysis report for AMZN
```

## Current Price And Historical Data

```text
What is the latest price of MSFT?
```

```text
Fetch recent stock data for AAPL
```

```text
Show me the last 6 months of TSLA price data
```

```text
Get historical price data for NVDA
```

```text
What was the recent closing price for AMZN?
```

## Technical Indicator Questions

```text
Run technical analysis for MSFT
```

```text
What is the RSI for AAPL?
```

```text
Calculate the moving averages for TSLA
```

```text
Is NVDA bullish or bearish right now?
```

```text
Analyze the trend and momentum for AMZN
```

```text
Calculate SMA, EMA, RSI, and volatility for META
```

## Trend And Recommendation Questions

```text
Should I buy, hold, or sell MSFT?
```

```text
Is AAPL showing bullish momentum?
```

```text
Does TSLA look overbought or oversold?
```

```text
Is NVDA in an uptrend?
```

```text
Give me the trading signal for AMZN
```

## Comparison Questions

```text
Compare MSFT with last week
```

```text
Compare AAPL performance with 7 trading days ago
```

```text
How has TSLA moved over the last week?
```

```text
Compare NVDA with 10 days ago
```

```text
Did AMZN go up or down recently?
```

## Follow-Up Questions

After asking:

```text
Generate a financial report for MSFT
```

You can ask:

```text
Compare it with last week
```

```text
Create a chart for it
```

```text
What is its RSI?
```

```text
Is it bullish or bearish?
```

```text
What is your final recommendation?
```

The word `it` refers to the previous stock because interactive mode keeps memory.

## Chart And Visualization Questions

```text
Create a chart for MSFT
```

```text
Generate a price chart for AAPL
```

```text
Plot TSLA with moving averages
```

```text
Create a 6-month chart for NVDA
```

```text
Show me a technical chart for AMZN
```

Charts are saved as HTML files inside:

```text
outputs/charts
```

## Fundamentals And Company Overview

These questions use Alpha Vantage if you added an Alpha Vantage API key.

```text
Get company fundamentals for MSFT
```

```text
Show Alpha Vantage overview for AAPL
```

```text
What sector is TSLA in?
```

```text
Get company overview for NVDA
```

```text
Show fundamentals for AMZN
```

If you did not add an Alpha Vantage key, the agent will still work with
yfinance and technical analysis.

## Different Time Periods

```text
Analyze MSFT over the last 1 month
```

```text
Generate a 1-year report for AAPL
```

```text
Run technical analysis for TSLA using 6 months of data
```

```text
Create a chart for NVDA over 1 year
```

```text
Compare AMZN over the last 30 days
```

## Multi-Step Requests

```text
Analyze MSFT, create a report, and tell me if it is a buy or hold
```

```text
Fetch AAPL data, run RSI and moving averages, then give me a recommendation
```

```text
Generate a report for TSLA and create a chart
```

```text
Analyze NVDA and compare it with last week
```

```text
Give me a full technical analysis of AMZN with trend, RSI, volatility, and recommendation
```

## Switching Stocks

```text
Generate a report for MSFT
```

Then:

```text
What about AAPL?
```

Then:

```text
Compare it with last week
```

In this example, `it` now refers to AAPL because AAPL was the latest stock.

## Example Interactive Session

```text
You: Generate a financial report for MSFT
Agent: Financial Report for MSFT ...

You: Compare it with last week
Agent: MSFT moved ... over the comparison window.

You: Create a chart for it
Agent: Chart saved at outputs/charts/...

You: What about NVDA?
Agent: Financial Report for NVDA ...
```

## How To Exit

Type:

```text
exit
```

or:

```text
quit
```
