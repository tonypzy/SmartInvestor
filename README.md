# Institutional Options Runner

A modular, institutional-grade options screening framework designed to systematically identify high-probability trading setups using Python. This project processes market data, calculates Greeks, and scans for 10+ professional options strategies including Iron Condors, ZEBRA, and Strangles.

## 🚀 Key Features

*   **Modular Architecture**: Easily extensible `BaseScreener` class for adding new strategies.
*   **Institutional Data**: Uses standard industry models for Greeks (Black-Scholes), IV Rank, and Historical Volatility via `yfinance` and `py_vollib_vectorized`.
*   **10 Pre-Built Strategies**:
    *   **Iron Condor**: Neutral range trading (Short Volatility).
    *   **ZEBRA**: Zero Extrinsic Bullish Risk Adjustment (Stock Replacement).
    *   **Bull Put Spread**: Credit spreads for bullish setups.
    *   **Bull Call Spread**: Debit spreads for directional plays.
    *   **Bear Call Spread**: Credit spreads for bearish setups.
    *   **Double Bull**: Combination of credit put and debit call spreads.
    *   **Short Strangle**: Premium selling for neutral/wide market.
    *   **Long Strangle**: Volatility buying for event-driven moves.
    *   **LEAPS**: Deep value, long-term equity anticipation securities.
    *   **Deep ITM**: Safe stock substitution with minimal extrinsic value.

## 🛠️ Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/options-runner.git
    cd options-runner
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Requires `yfinance`, `pandas`, `numpy`, `py_vollib_vectorized`, `scipy`)*

## 📖 Usage

Run any strategy directly from the command line using the central dispatcher:

```bash
python options_runner/main.py <strategy_name> <symbol>
```

### Supported Strategy Commands

| Strategy | Command | Description |
| :--- | :--- | :--- |
| **Iron Condor** | `iron_condor` | Neutral strategy seeking range-bound price action. |
| **ZEBRA** | `zebra` | Bullish strategy removing extrinsic value risk. |
| **Bull Put** | `bull_put` | Bullish credit spread (selling puts). |
| **Bull Call** | `bull_call` | Bullish debit spread (buying calls). |
| **Bear Call** | `bear_call` | Bearish credit spread (selling calls). |
| **Double Bull** | `double_bull` | Aggressive bullish financing with credit spreads. |
| **Short Strangle** | `strangle_short` | Selling OTM Call and Put (High IV Rank). |
| **Long Strangle** | `strangle_long` | Buying OTM Call and Put (Low IV, Expecting Move). |
| **LEAPS** | `leaps` | Long-term investment substitution. |
| **Deep ITM** | `deep_itm` | High delta stock replacement. |

### Examples

**Run an Iron Condor scan on NVIDIA:**
```bash
python options_runner/main.py iron_condor NVDA
```

**Find LEAPS for Palantir:**
```bash
python options_runner/main.py leaps PLTR
```

**Run a Smoke Test** (Verify all strategies):
```bash
python verify_all.py SPY
```

## 🏗️ Project Structure

```text
options_runner/
├── main.py                 # Central CLI Entry Point
├── screeners/              # Strategy Implementations
│   ├── base_screener.py    # Abstract Base Class
│   ├── iron_condor.py
│   ├── bear_call.py
│   └── ... (other strategies)
└── utils/                  # Shared Utilities
    ├── market_data.py      # Data fetching (IV, HV, Chains)
    ├── option_math.py      # Greeks Calculation
    └── display.py          # Pandas formatting
```

## ⚠️ Disclaimer

This software is for educational and research purposes only. It is not financial advice. Options trading involves significant risk and is not suitable for all investors.
