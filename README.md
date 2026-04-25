# Financial Analyst Agent

An agentic financial analysis system built with Python, LangChain agents,
Gemini, yfinance, Alpha Vantage, Pandas, NumPy, Matplotlib, and Plotly.

## Features

- Fetches historical and latest stock data from yfinance.
- Fetches company overview and fundamental context from Alpha Vantage when configured.
- Calculates SMA, EMA, RSI, volatility, trend, momentum, and recommendation.
- Uses LangChain agents and tools, not a simple chain.
- Uses Gemini through `langchain-google-genai`.
- Maintains short-term conversational memory in interactive mode.
- Handles placeholder or invalid Gemini API keys with clear errors.
- Handles data/API failures gracefully with structured tool responses.
- Generates interactive Plotly HTML price charts.
- Includes TTL caching for yfinance and Alpha Vantage calls.

## Files

- `agent.py` - Gemini model setup, LangChain `create_agent`, memory, and system prompt.
- `tools.py` - yfinance, Alpha Vantage, analysis, comparison, chart, and report tools.
- `analysis.py` - Pandas/NumPy technical analysis and report logic.
- `main.py` - CLI entry point with single-shot and interactive modes.
- `.env.example` - Environment variable template.
- `requirements.txt` - Python dependencies.

## Setup In VS Code

1. Open VS Code.
2. Click `File > Open Folder`.
3. Select:

   ```text
   D:\ALL PROJECTS\New folder
   ```

4. Open the terminal in VS Code:

   ```text
   Terminal > New Terminal
   ```

5. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

6. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell blocks it, run this once:

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

   Then activate again:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

7. Install packages:

   ```powershell
   pip install -r requirements.txt
   ```

8. Create your `.env` file:

   ```powershell
   Copy-Item .env.example .env
   ```

9. Open `.env` and replace this:

   ```env
   GEMINI_API_KEY=your_gemini_api_key
   ```

   with your real key:

   ```env
   GEMINI_API_KEY=AIzaSyYourRealKeyHere
   ```

   Get your Gemini key here:

   ```text
   https://aistudio.google.com/app/apikey
   ```

   Important: edit `.env`, not `.env.example`. Do not use quotes around the key.

## Run

Single stock report:

```powershell
python main.py --ticker AAPL
```

Free-form question:

```powershell
python main.py --question "Analyze TSLA and compare it with last week"
```

Interactive memory mode:

```powershell
python main.py --interactive
```

Example interactive questions:

```text
Generate a financial report for MSFT
Compare it with last week
Create a chart for it
What about NVDA?
```

Type this to stop:

```text
exit
```

## Example Output

```text
Financial Report for MSFT

* Current Price: USD 421.50 (latest close: 2026-04-24)
* Trend: Bullish
* RSI: 58.21 (Positive)
* Moving Averages: SMA 20: USD 414.18, SMA 50: USD 405.44, EMA 20: USD 415.03
* Volatility: 24.84% annualized

Analysis: MSFT is trading at USD 421.50, with price action above or improving
against the 20-day and 50-day moving averages.

Recommendation: Buy - Price is above key moving averages, trend is bullish, and
RSI does not show an overbought extreme.

Risk Note: This is an analytical signal summary, not personalized financial advice.
```

The numbers above are examples. Live output depends on current market data.

## Agent Reasoning Flow

1. You ask a stock-market question.
2. LangChain sends your message and the system prompt to Gemini.
3. Gemini chooses a tool:
   - `fetch_stock_data` for prices.
   - `fetch_alpha_vantage_overview` for company fundamentals.
   - `run_technical_analysis` for SMA, EMA, RSI, trend, volatility.
   - `generate_financial_report` for a full report.
   - `compare_recent_performance` for follow-up comparisons.
   - `create_price_chart` for Plotly charts.
4. The tool result goes back to Gemini.
5. Gemini decides whether more tools are needed.
6. Gemini writes the final answer.
7. LangGraph memory keeps context inside the same running interactive session.

## Multi-Agent Extension Idea

- Research Agent: news, filings, earnings calls, macro data.
- Analyst Agent: technical indicators, fundamentals, risk.
- Portfolio Agent: position sizing, exposure, constraints.
- Report Agent: investor-facing summaries and dashboard output.

## Scaling Into A Product

- Replace `InMemorySaver` with Postgres or Redis memory.
- Add scheduled watchlist monitoring.
- Add FastAPI or Streamlit UI.
- Store reports and charts in cloud storage.
- Add LangSmith tracing and data-quality alerts.
- Add compliance checks before showing trade recommendations.

## Common Errors

If you see:

```text
Configuration error: GEMINI_API_KEY is still set to the placeholder value.
```

open `.env` and replace:

```env
GEMINI_API_KEY=your_gemini_api_key
```

with your real Gemini key.

If you see:

```text
Gemini rejected your API key.
```

make a new key from Google AI Studio and paste it into `.env`.
