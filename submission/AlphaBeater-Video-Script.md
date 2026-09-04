# AlphaBeater — Video Script v3
**Runtime:** ~4:50  
**Base:** v2 with slide-accuracy fixes  
**Deck:** AlphaBeater-Final.pptx (13 slides) or the Google Slides

---

## [SLIDE 1: Title — AlphaBeater]
**(0:00 – 0:20)**

> "Good morning. This is AlphaBeater — an autonomous, risk-gated options trading agent built for the Alpaca AI Trading Agents Hackathon.
>
> Our core philosophy is simple: an AI trading agent must earn every single trade. We do not let a language model trade on intuition, hallucinate code, or gamble account equity. Here is how AlphaBeater works from signal to execution."

---

## [SLIDE 2: The Big Picture]
**(0:20 – 0:45)**

> "At a high level, AlphaBeater operates across six connected stages: it reads real market data, uses a large language model to form a hypothesis, deterministically backtests that hypothesis, selects an optimal defined-risk option, tests the trade against 16 safety checks, and routes the approved order to Alpaca paper trading.
>
> In one sentence: AlphaBeater is an AI agent that researches market signals, backtests them mathematically, converts trusted signals into defined-risk options, and executes only when hard risk gates allow it."

---

## [SLIDE 3: How It Works]
**(0:45 – 1:15)**

> "To understand why this architecture is safe, look at the split on this slide.
>
> Stages 1 and 2 — Observe and Hypothesize — rely on the LLM's reasoning engine. The model analyzes price action, volatility, and volume across SPY, QQQ, and IWM.
>
> But stages 3 through 6 are 100% deterministic Python. The model outputs formulas into our custom Factor DSL. There is no eval() and no arbitrary code execution. We split the data chronologically into 50% training, 20% validation, and a locked 30% holdout. The LLM dreams up the ideas; strict math decides if they survive."

---

## [SLIDE 4: What Powers It]
**(1:15 – 1:40)**

> "Four distinct engines power the stack.
>
> First, our large language model proposes factors across five precommitted quantitative themes — trend, mean reversion, volatility, volume divergence, and breakouts. AlphaBeater is model-agnostic: the LLM endpoint can be swapped without touching a single line of risk logic.
>
> Second, Alpaca Market Data provides historical bars and live options chains.
>
> Third, our Deterministic Backtester scores factors on out-of-sample data.
>
> And fourth, the official Alpaca MCP server, launched via uvx, acts as our broker interface. The AI never talks directly to the broker — it only ever reaches Alpaca through our risk firewall."

---

## [SLIDE 5: Worked Example — Factor Selection]
**(1:40 – 2:05)**

> "Here is an example of factor discovery in action.
>
> In this run, the LLM proposed multiple candidate factors. The backtester evaluated them and selected Momentum Volume Divergence — which divides 5-day returns by 20-day relative volume.
>
> On the out-of-sample holdout, this factor produced an 8.35% return against a benchmark of 0.65%, an annualized Sharpe of 1.29, and a controlled drawdown of negative 6.66%. It outperformed the runner-up and earned promotion to trade planning."

---

## [SLIDE 6: Worked Example — Trade Plan & Risk Gate]
**(2:05 – 2:35)**

> "The agent converted that signal into a defined-risk trade: buying one contract of the IWM 296 Call, targeting 21 to 45 DTE and a 0.35 to 0.60 delta. Maximum loss was strictly capped at the $414 premium.
>
> But notice what happened in this dashboard demonstration: AlphaBeater did NOT place this order.
>
> 15 of our 16 risk checks passed — but the quote was older than our strict 15-minute freshness threshold. The order was instantly withheld.
>
> This is the central thesis of our project: an AI recommendation is not an entitlement to trade. The firewall catches problems the model would never self-report."

---

## [SLIDE 7: The Risk System]
**(2:35 – 3:05)**

> "Here is that firewall in full. Every trade must satisfy 16 deterministic checks — and as you can see, in our September 3rd live paper-trading run, all 16 passed.
>
> We verify account state, enforce a strict one-contract limit, cap single-trade loss at 0.5% of equity, and enforce a 2% daily loss circuit breaker.
>
> On the execution side, we check bid-ask spread and quote freshness — a check that blocked the dashboard demo but cleared on the real run with a zero-second quote age.
>
> And on the quantitative side, the factor must prove a Sharpe above 0.50 and positive excess return. The LLM has zero authority to bypass any of these rules."

---

## [SLIDE 8: Execution Policies]
**(3:05 – 3:30)**

> "We also practice extreme intellectual honesty in how we evaluate results. We separate our runtime into two distinct policies.
>
> In Validated Mode, all 16 checks are blocking. In our latest strict benchmark run, the LLM generated 15 factors; none passed both train and validation gates, so the agent abstained. That is correct risk-averse behavior.
>
> In Experimental Paper Mode, used for pipeline testing, historical backtest failures act as non-blocking advisories — but all operational, liquidity, and loss limits remain strictly blocking. Every action is logged in an immutable audit trail."

---

## [SLIDE 9: Autonomous Monitoring]
**(3:30 – 3:55)**

> "Once an order enters the paper market, AlphaBeater's job is not done. Our autonomous monitoring daemon polls Alpaca every 30 seconds to enforce four rules:
>
> A 25% stop loss, a 40% take profit, an expiry exit at 7 DTE to avoid unpredictable gamma decay in the final week, and an automatic 15-minute cancel for stale, unfilled entry limit orders.
>
> The system manages the entire trade lifecycle from entry to exit."

---

## [SLIDE 10: Verified Paper-Trading Proof of Concept]
**(3:55 – 4:15)**

> "Here is our verified paper execution proof of concept — the same run where all 16 checks passed.
>
> The agent identified a trend divergence factor on IWM, planned the September 25th $296 Call, routed the order through Alpaca MCP's place_option_order endpoint, and entered at a limit price of $4.14.
>
> The monitoring daemon tracked the position in real time as market price ticked to $4.17 — a live, logged, fully audited paper-trading lifecycle from raw data to open position."

---

## [SLIDE 11: In One Sentence]
**(4:15 – 4:35)**

> "To bring it all together:
>
> AlphaBeater is an AI trading agent that researches market signals, mathematically backtests them, converts a trusted signal into a defined-risk options strategy, validates it through strict risk gates, and executes and monitors the trade through Alpaca paper trading.
>
> Research. Backtest. Defined risk. Deterministic gating. Autonomous execution."

---

## [SLIDE 12: The Team]
**(4:35 – 4:50)**

> "This project was built for the lablab.ai Alpaca Hackathon by Team Still Cookin': Tien Nguyen, Tabinda Noor, Muhammad Nameer Shah, and Hamza Atiq.
>
> Thank you — we look forward to your questions."

---

## Change Log vs v2

| Slide | What changed | Why |
|-------|-------------|-----|
| **S2** | "uses Gemma to form a hypothesis" → "uses a large language model to form a hypothesis" | LLM-agnostic |
| **S3** | "Gemma analyzes price action" → "The model analyzes price action" | LLM-agnostic |
| **S3** | "The model dreams up the ideas" (was "Gemma dreams") | LLM-agnostic |
| **S4** | "Gemma 4 31B proposes factors" → "our large language model proposes factors" + added model-agnostic note | Slide badge now says "Large Language Model" |
| **S5** | "Gemma proposed multiple candidate factors" → "the LLM proposed..." | LLM-agnostic |
| **S6** | Added "in this dashboard demonstration" to clarify this run ≠ the Sep 3 run | Slide 7 now shows all 16 green (Sep 3 run passed) |
| **S7** | Added "in our September 3rd live paper-trading run, all 16 passed" | Slide 7 now shows all green; needs explanation |
| **S7** | Added "a check that blocked the dashboard demo but cleared on the real run with a zero-second quote age" | Ties S6 and S7 together cleanly |
| **S8** | "Gemma generated 15 factors" → "the LLM generated 15 factors" | LLM-agnostic |
| **S10** | Added "the same run where all 16 checks passed" | Connects back to the S7 explanation |

## Changes vs v1

v1 is 3 minutes (shorter). If you want a v1-length version, the same fixes apply — just drop the expanded paragraphs.
The critical lines in v1 that need the same fixes:
- S3: "use Gemma to reason" + "Gemma outputs to a sandboxed Factor DSL" → replace with LLM
- S4: "Gemma 4 31B for quantitative factor generation" → "our large language model"
- S7 narration is already describing the system in general (no specific run result), so no change needed there for v1
