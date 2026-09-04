"""The tradable universe the agent researches over.

Breadth is not cosmetic here. Two DSL operators — `rank` and `zscore` — are *cross-sectional*:
they compare symbols against each other on the same day. With three symbols, `rank` can only
return 0.33, 0.67 or 1.0, and `zscore` estimates a standard deviation from three points. Both are
statistically meaningless at that width.

The daily strategy also holds the single strongest signal in the universe, so three symbols means
choosing one of three and paying the spread every time that choice flips.

Every symbol below is a large, liquid, optionable US ETF, chosen to span different risk drivers so
that a cross-sectional comparison carries information: broad market, size, geography, sectors, and
the classic diversifiers (gold, treasuries, credit).
"""

#: Broad market and size.
_CORE = ["SPY", "QQQ", "IWM", "DIA", "MDY"]

#: Geography.
_INTERNATIONAL = ["EFA", "EEM"]

#: Sectors, so a cross-sectional rank can express rotation.
_SECTORS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLI", "XLP", "SMH"]

#: Diversifiers that behave differently from equities.
_DIVERSIFIERS = ["GLD", "TLT", "HYG"]

RESEARCH_UNIVERSE: list[str] = [*_CORE, *_INTERNATIONAL, *_SECTORS, *_DIVERSIFIERS]

#: Trading days of history requested for research.
LOOKBACK_DAYS = 760
