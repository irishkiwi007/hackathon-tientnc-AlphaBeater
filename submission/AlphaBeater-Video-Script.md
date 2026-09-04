# AlphaBeater — Video Script (Compact ~2:30 - 3:00 Min)

**Target Runtime:** ~2:30 – 3:00  
**Word Count:** ~380 words (~135–140 words/min speaking pace)  
**Deck Reference:** 12 slides (AlphaBeater presentation)

---

### [SLIDE 1: Title — AlphaBeater]
**(0:00 – 0:12)**

> "This is AlphaBeater — an autonomous, risk-gated options trading agent built for the Alpaca AI Trading Agents Hackathon. Our core principle is simple: an AI trading agent must earn every trade with deterministic math, zero hallucinations, and zero naked risk."

---

### [SLIDE 2: The Big Picture]
**(0:12 – 0:25)**

> "AlphaBeater operates across six connected stages: from market observation and LLM hypothesis generation, to deterministic backtesting, defined-risk option selection, a 16-point risk firewall, and Alpaca paper execution. The AI does the research; strict Python controls the money."

---

### [SLIDE 3: How It Works]
**(0:25 – 0:40)**

> "Our architecture separates creative AI from financial execution. The LLM reasons over price, volume, and volatility, outputting candidate formulas into a sandboxed Factor DSL — no arbitrary code execution. Then, strict math backtests every signal across an untouched 50/20/30 chronological split."

---

### [SLIDE 4: What Powers It]
**(0:40 – 0:55)**

> "Four engines power the stack: a model-agnostic LLM factor generator, Alpaca Market Data for historical and real-time options chains, our custom deterministic backtester, and the official Alpaca MCP broker integration. The model never touches the broker directly."

---

### [SLIDE 5: Worked Example — Factor Selection]
**(0:55 – 1:10)**

> "Here is factor discovery in action. On IWM, the system evaluated candidate hypotheses and promoted a Momentum-Volume Divergence factor. On the untouched out-of-sample holdout, it delivered an 8.35% return, a 1.29 Sharpe ratio, and a tightly controlled drawdown."

---

### [SLIDE 6: Worked Example — Trade Plan & Risk Gate]
**(1:10 – 1:28)**

> "The agent translated that signal into a defined-risk IWM Call with max loss capped at the $414 premium. But in this dashboard demo, notice that AlphaBeater withheld the order: 15 checks passed, but stale quote data triggered an instant block. An AI suggestion is never an entitlement to trade."

---

### [SLIDE 7: The Risk System]
**(1:28 – 1:45)**

> "Here is our 16-point deterministic firewall. In our live paper-trading run, all 16 checks passed — including live quote freshness with zero seconds latency. We enforce strict sizing, a 2% daily loss circuit breaker, and required factor performance before any dollar is committed."

---

### [SLIDE 8: Execution Policies]
**(1:45 – 2:00)**

> "We practice strict intellectual honesty with two operating modes. In Validated Mode, all 16 checks are strictly blocking — if factors don't clear holdout gates, the agent abstains. In Paper Mode, backtest gates act as advisories for testing, but capital protection and liquidity rules remain 100% blocking."

---

### [SLIDE 9: Autonomous Monitoring]
**(2:00 – 2:15)**

> "Once placed, our autonomous monitoring daemon polls Alpaca every 30 seconds to manage the full lifecycle: enforcing a 25% stop loss, a 40% take profit, an exit at 7 days to expiration to avoid gamma crush, and a 15-minute cancel for stale limit orders."

---

### [SLIDE 10: Verified Paper-Trading Proof of Concept]
**(2:15 – 2:32)**

> "Here is our verified paper execution proof of concept. The agent routed the IWM 296 Call order via Alpaca MCP, filled at a $4.14 limit, and actively tracked the live position as it ticked to $4.17 — a logged, fully audited pipeline from raw market data to open position."

---

### [SLIDE 11: In One Sentence]
**(2:32 – 2:45)**

> "In summary: AlphaBeater researches market signals with an LLM, mathematically backtests them, maps them to defined-risk options, enforces strict risk gates, and autonomously executes via Alpaca. Research, backtest, defined risk, deterministic gating."

---

### [SLIDE 12: The Team]
**(2:45 – 2:55)**

> "AlphaBeater was built for the Alpaca AI Trading Agents Hackathon by Team Still Cookin': Tien Nguyen, Tabinda Noor, Muhammad Nameer Shah, and Hamza Atiq. Thank you!"

---

## Speaker Timing Guide
- **Slide 1-3 (Intro & Architecture):** ~40 seconds
- **Slide 4-7 (Engines, Demo & 16-Point Risk Gate):** ~65 seconds
- **Slide 8-10 (Policies, Monitoring & Paper Proof):** ~47 seconds
- **Slide 11-12 (Summary & Wrap up):** ~23 seconds
- **Total:** ~2:55 (~380 words)
