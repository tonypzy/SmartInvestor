# SmartInvestor

**SmartInvestor** is a comprehensive quantitative financial analysis platform designed to bridge the gap between institutional-grade tools and retail investors. It integrates rigorous fundamental analysis (SEC filings), advanced options screening, and automated valuation models into a unified ecosystem.

## 🚀 Core Components

### 1. Options Runner (`options_runner/`)
A modular framework for screening high-probability options strategies using professional Greeks and volatility data.

*   **10+ Models**: Iron Condor, ZEBRA, Bull/Bear Spreads, Strangles, LEAPS, etc.
*   **Institutional Metrics**: Uses Black-Scholes Greeks, IV Rank, and Expected Value (EV).
*   **CLI Usage**: `python options_runner/main.py <strategy> <symbol>`

### 2. Fundamental Alpha Engine (`engines/alpha_engine.py`)
A powerful financial statement analysis engine that processes SEC data to derive "True Alpha" metrics.

*   **Q4 Derivation**: Automatically calculates implied Q4 data when only Annual (10-K) and Cumulative Q3 data exist.
*   **Quality Metrics**: Computes ROIC (Return on Invested Capital), EVA Spread (Economic Value Added), and Margin Expansion.
*   **Valuation**: Reverse DCF (Implied Growth), FCF Yield, and "Alpha Gap" (Market Implied Growth vs. Actual Growth).
*   **Capital Allocation**: Tracks Buyback Yield, Dividend Yield, and Shareholder Yield.

### 3. Valuation Dashboard (`dashboards/`)
Visualizes financial health and valuation reality using `matplotlib`.

*   **Financial Funnel**: Visualizes the flow from Revenue -> Gross Profit -> Net Income -> FCF.
*   **Trend Analysis**: Sparklines for Gross Margin trends and FCF Yield history.
*   **Valuation Reality**: Compares P/E and EV/EBIT multiples.
*   **Institutional Signal**: A clear "Scorecard" summarizing FCF Yield and Growth.

### 4. SEC Data Pipeline (`pipelines/`, `data/`)
Automated extraction and parsing of EDGAR filings.

*   **SEC_Loader**: Fetches 10-K and 10-Q filings directly from the SEC.
*   **SEC_Parser**: Extracts standardized financial tables (Income Statement, Balance Sheet, Cash Flow).

## 🛠️ Installation

```bash
# Clone the repository
git clone https://github.com/tonypzy/SmartInvestor.git
cd SmartInvestor

# Install dependencies
pip install -r requirements.txt
```

## 📖 Usage Guide

### A. Running Options Strategies
To find trading setups:
```bash
python options_runner/main.py iron_condor NVDA
python options_runner/main.py leaps PLTR
```
*(See `options_runner/README.md` or source code for full list of strategies)*

### B. Running Fundamental Analysis
To perform a deep dive valuation on a stock:
```bash
python pipelines/analysis_pipeline.py
```
*(Note: Edit the `run_pipeline(['AAPL'], mode="DEEP_DIVE")` line in `pipelines/analysis_pipeline.py` to change targets)*

### C. Running Smoke Tests
To verify all options strategies are working:
```bash
python verify_all.py SPY
```

## 🏗️ Project Architecture & File Map

### 1. Core Frameworks
| Path | Component | Description |
| :--- | :--- | :--- |
| **`options_runner/`** | **Options Strategy Engine** | The modern, object-oriented framework for running 10+ options strategies. |
| `options_runner/main.py` | CLI Entry Point | Central dispatcher for all strategies (Iron Condor, ZEBRA, etc.). |
| `options_runner/screeners/` | Strategy Library | Contains `BaseScreener` and all strategy classes (e.g., `bull_put.py`, `bear_call.py`). |
| `options_runner/utils/` | Shared Utilities | `market_data.py` (IV/HV), `option_math.py` (Greeks), `display.py`. |
| **`engines/`** | **Financial Logic** | Core calculation engines for fundamental analysis. |
| `engines/alpha_engine.py` | Alpha Engine | Derives Q4 data, calculates ROIC, Valuation, and Quality metrics. |
| `engines/sentiment_engine.py` | Sentiment Engine | (Experimental) NLP analysis for market sentiment. |
| **`pipelines/`** | **Orchestration** | Scripts to run end-to-end analysis workflows. |
| `pipelines/analysis_pipeline.py` | Analysis Pipeline | Main script for Fundamental Deep Dives (`run_pipeline`). |
| `pipelines/data_pipeline.py` | Data Pipeline | Manages large-scale data ingestion. |

### 2. Visualization & Reporting
| Path | Component | Description |
| :--- | :--- | :--- |
| **`dashboards/`** | **Visualizations** | Matplotlib-based dashboards. |
| `dashboards/valuation_dashboard.py` | Valuation Viz | Draws Financial Funnels, Trend Lines, and Valuation cards. |
| `dashboards/peer_dashboard.py` | Peer Viz | Sector comparison charts. |
| **`reporting/`** | **Output Formatting** | Console output formatting. |
| `reporting/reporting.py` | Reporting | Formats the "Institutional Deck" console output. |

### 3. Data Layer
| Path | Component | Description |
| :--- | :--- | :--- |
| **`data/`** | **Data Access** | Data fetchers and parsers. |
| `data/market_data.py` | Market Data | Wrapper for real-time price fetching. |
| `data/sec_core/` | SEC Data | `SEC_Loader` (Downloader) and `SEC_Parser` (Html parsing). |

### 4. Standalone & Legacy Tools
| File | Status | Description |
| :--- | :--- | :--- |
| `verify_all.py` | **Active** | Smoke test script to verify all `options_runner` strategies. |
| `InstitutionalEngine.py` | Legacy | Older engine containing "Seagull" strategy logic (Safe/Pro modes). |
| `volativity_smile.py` | Standalone | Tool to plot Volatility Smile curves for a ticker. |
| `Newton_raphson_method.py` | Utility | Solver for calculating IV using Newton-Raphson method. |
| `get_options_by_yfinance.py` | Utility | Simple script to fetch raw option chains. |
| `get-pip.py` | Utility | Python pip installer script. |

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice.
