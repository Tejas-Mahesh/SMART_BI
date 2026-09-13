"""
Smart BI - What-If Scenario Simulator
"""


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.replace("%", "").replace(",", "").strip()

        return float(value)

    except (ValueError, TypeError):
        return default


def calculate_scenario(
    base_revenue,
    base_profit,
    base_units,
    price_change=0,
    discount_change=0,
    marketing_change=0,
    demand_change=0,
):
    """
    Calculate the estimated impact of a business scenario.

    All changes are percentages relative to the current baseline.
    """

    # ---------------------------------------------------------
    # BASE VALUES
    # ---------------------------------------------------------

    base_revenue = max(
        0,
        safe_float(base_revenue)
    )

    base_profit = max(
        0,
        safe_float(base_profit)
    )

    base_units = max(
        0,
        safe_float(base_units)
    )

    price_change = safe_float(price_change)
    discount_change = safe_float(discount_change)
    marketing_change = safe_float(marketing_change)
    demand_change = safe_float(demand_change)

    # ---------------------------------------------------------
    # DEMAND CALCULATION
    # ---------------------------------------------------------

    demand_factor = (
        1 + demand_change / 100
    )

    # Price elasticity assumption.
    # A 1% price increase reduces demand by
    # approximately 0.4%.

    price_demand_effect = (
        1 - (price_change / 100 * 0.40)
    )

    # Discount stimulates demand.
    # A 1% discount increase produces approximately
    # 0.25% additional demand.

    discount_demand_effect = (
        1 + (discount_change / 100 * 0.25)
    )

    adjusted_units = (
        base_units
        * demand_factor
        * price_demand_effect
        * discount_demand_effect
    )

    adjusted_units = max(
        0,
        adjusted_units
    )

    # ---------------------------------------------------------
    # REVENUE
    # ---------------------------------------------------------

    price_factor = (
        1 + price_change / 100
    )

    if base_units > 0:

        adjusted_revenue = (
            base_revenue
            * price_factor
            * (adjusted_units / base_units)
        )

    else:

        adjusted_revenue = (
            base_revenue
            * price_factor
            * demand_factor
        )

    # ---------------------------------------------------------
    # MARKETING IMPACT
    # ---------------------------------------------------------

    if marketing_change != 0:

        marketing_effect = (
            1
            + (
                marketing_change ** 0.5
                * 0.03
            )
            if marketing_change > 0
            else
            1
            - (
                abs(marketing_change) ** 0.5
                * 0.03
            )
        )

    else:

        marketing_effect = 1

    adjusted_revenue *= marketing_effect

    adjusted_revenue = max(
        0,
        adjusted_revenue
    )

    # ---------------------------------------------------------
    # PROFIT
    # ---------------------------------------------------------

    if base_revenue > 0:

        baseline_margin = (
            base_profit / base_revenue
        )

    else:

        baseline_margin = 0.20

    # Discount reduces margin.

    discount_penalty = (
        discount_change / 100
    )

    # Marketing investment has an estimated cost effect.

    marketing_penalty = (
        abs(marketing_change)
        / 100
        * 0.05
    )

    adjusted_margin = (
        baseline_margin
        - discount_penalty
        - marketing_penalty
    )

    # Prevent unrealistic margins.

    adjusted_margin = max(
        -0.50,
        min(
            0.80,
            adjusted_margin
        )
    )

    adjusted_profit = (
        adjusted_revenue
        * adjusted_margin
    )

    # ---------------------------------------------------------
    # PERCENTAGE CHANGES
    # ---------------------------------------------------------

    if base_revenue > 0:

        revenue_change = (
            (
                adjusted_revenue
                - base_revenue
            )
            / base_revenue
        ) * 100

    else:

        revenue_change = 0

    if base_profit > 0:

        profit_change = (
            (
                adjusted_profit
                - base_profit
            )
            / base_profit
        ) * 100

    else:

        profit_change = 0

    if base_units > 0:

        units_change = (
            (
                adjusted_units
                - base_units
            )
            / base_units
        ) * 100

    else:

        units_change = 0

    # ---------------------------------------------------------
    # BUSINESS SCORE
    # ---------------------------------------------------------

    score = 50

    if revenue_change >= 0:

        score += min(
            20,
            revenue_change * 0.5
        )

    else:

        score += max(
            -20,
            revenue_change * 0.5
        )

    if profit_change >= 0:

        score += min(
            25,
            profit_change * 0.5
        )

    else:

        score += max(
            -25,
            profit_change * 0.5
        )

    score = max(
        0,
        min(
            100,
            score
        )
    )

    # ---------------------------------------------------------
    # DECISION
    # ---------------------------------------------------------

    if (
        adjusted_profit > base_profit
        and adjusted_revenue >= base_revenue
    ):

        decision = "Recommended"

    elif (
        adjusted_revenue > base_revenue
        and adjusted_profit < base_profit
    ):

        decision = "High Revenue / Lower Profit"

    elif (
        adjusted_revenue < base_revenue
        and adjusted_profit < base_profit
    ):

        decision = "Not Recommended"

    else:

        decision = "Review"

    # ---------------------------------------------------------
    # BUSINESS INSIGHTS
    # ---------------------------------------------------------

    insights = []

    if price_change > 0:

        insights.append(
            f"Price increased by "
            f"{price_change:.1f}%."
        )

    elif price_change < 0:

        insights.append(
            f"Price decreased by "
            f"{abs(price_change):.1f}% "
            f"to potentially stimulate demand."
        )

    if discount_change > 0:

        insights.append(
            "Higher discounts may increase demand "
            "but can reduce profit margin."
        )

    elif discount_change < 0:

        insights.append(
            "Lower discounts can improve margin "
            "but may reduce demand."
        )

    if marketing_change > 0:

        insights.append(
            "Additional marketing investment is "
            "expected to increase revenue with "
            "diminishing returns."
        )

    elif marketing_change < 0:

        insights.append(
            "Reduced marketing investment may "
            "decrease future revenue potential."
        )

    if demand_change != 0:

        insights.append(
            f"Manual demand assumption changed by "
            f"{demand_change:.1f}%."
        )

    if adjusted_profit > base_profit:

        insights.append(
            "The scenario improves estimated "
            "profit compared with the baseline."
        )

    elif adjusted_profit < base_profit:

        insights.append(
            "The scenario reduces estimated "
            "profit compared with the baseline."
        )

    else:

        insights.append(
            "Estimated profit remains approximately "
            "unchanged."
        )

    # ---------------------------------------------------------
    # RETURN RESULT
    # ---------------------------------------------------------

    return {

        "baseline": {

            "revenue": round(
                base_revenue,
                2
            ),

            "profit": round(
                base_profit,
                2
            ),

            "units": round(
                base_units,
                2
            ),
        },

        "scenario": {

            "revenue": round(
                adjusted_revenue,
                2
            ),

            "profit": round(
                adjusted_profit,
                2
            ),

            "units": round(
                adjusted_units,
                2
            ),

            "margin": round(
                adjusted_margin * 100,
                2
            ),
        },

        "changes": {

            "revenue": round(
                revenue_change,
                2
            ),

            "profit": round(
                profit_change,
                2
            ),

            "units": round(
                units_change,
                2
            ),
        },

        "score": round(
            score,
            1
        ),

        "decision": decision,

        "insights": insights,
    }


"""
What-If Scenario Analysis Service

Uses real business baseline values supplied by the view and calculates
the projected impact of:
    - Price change
    - Discount change
    - Marketing change
    - Demand change
"""


# ============================================================
# SAFE CONVERSION HELPERS
# ============================================================

def safe_float(value, default=0.0):
    try:
        if value is None:
            return float(default)

        if isinstance(value, str):
            value = value.replace(",", "").replace("₹", "").strip()

        return float(value)

    except (ValueError, TypeError):
        return float(default)


# ============================================================
# SCENARIO CALCULATION
# ============================================================

def calculate_scenario(
    base_revenue,
    base_profit,
    base_units,
    price_change=0,
    discount_change=0,
    marketing_change=0,
    demand_change=0,
):
    """
    Calculate a business scenario using the supplied real baseline.

    Parameters
    ----------
    base_revenue : float
        Current revenue from the selected dataset.

    base_profit : float
        Current profit from the selected dataset.

    base_units : float
        Current units / quantity from the selected dataset.

    price_change : float
        Percentage price change.

    discount_change : float
        Percentage discount change.

    marketing_change : float
        Percentage marketing spend change.

    demand_change : float
        Percentage demand change.
    """

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    base_revenue = max(
        safe_float(base_revenue),
        0
    )

    base_profit = safe_float(
        base_profit
    )

    base_units = max(
        safe_float(base_units),
        0
    )

    price_change = safe_float(
        price_change
    )

    discount_change = safe_float(
        discount_change
    )

    marketing_change = safe_float(
        marketing_change
    )

    demand_change = safe_float(
        demand_change
    )

    # --------------------------------------------------------
    # DEMAND EFFECT
    # --------------------------------------------------------

    demand_factor = (
        1
        + demand_change / 100
    )

    # --------------------------------------------------------
    # PRICE ELASTICITY
    #
    # A price increase normally reduces demand.
    # A price decrease normally increases demand.
    #
    # Elasticity assumption:
    # 40% of price movement affects unit demand.
    # --------------------------------------------------------

    price_elasticity = (
        1
        - (
            price_change / 100
            * 0.40
        )
    )

    # --------------------------------------------------------
    # DISCOUNT EFFECT
    #
    # More discount can increase demand.
    # We use a conservative 25% demand response.
    # --------------------------------------------------------

    discount_demand_factor = (
        1
        + (
            discount_change / 100
            * 0.25
        )
    )

    # --------------------------------------------------------
    # PROJECTED UNITS
    # --------------------------------------------------------

    adjusted_units = (
        base_units
        * demand_factor
        * price_elasticity
        * discount_demand_factor
    )

    adjusted_units = max(
        adjusted_units,
        0
    )

    # --------------------------------------------------------
    # PRICE EFFECT ON REVENUE
    # --------------------------------------------------------

    price_factor = (
        1
        + price_change / 100
    )

    adjusted_revenue = (
        adjusted_units
        / base_units
        * base_revenue
        * price_factor
        if base_units > 0
        else base_revenue * price_factor
    )

    adjusted_revenue = max(
        adjusted_revenue,
        0
    )

    # --------------------------------------------------------
    # MARKETING EFFECT
    #
    # Marketing has diminishing returns.
    # Square-root response prevents unrealistic growth.
    # --------------------------------------------------------

    if marketing_change >= 0:
        marketing_effect = (
            (1 + marketing_change / 100) ** 0.5
        )
    else:
        marketing_effect = (
            (1 + marketing_change / 100)
            ** 0.5
            if marketing_change > -100
            else 0
        )

    adjusted_revenue *= marketing_effect

    # --------------------------------------------------------
    # PROFIT MARGIN
    # --------------------------------------------------------

    if base_revenue > 0:
        baseline_margin = (
            base_profit
            / base_revenue
        )
    else:
        baseline_margin = 0

    # --------------------------------------------------------
    # DISCOUNT PENALTY
    #
    # Increased discounts reduce margin.
    # Reduced discounts improve margin.
    # --------------------------------------------------------

    discount_penalty = (
        discount_change / 100
        * 0.50
    )

    # --------------------------------------------------------
    # MARKETING PENALTY
    #
    # Increased marketing spend consumes part of the
    # additional revenue.
    # --------------------------------------------------------

    marketing_penalty = (
        marketing_change / 100
        * 0.08
    )

    adjusted_margin = (
        baseline_margin
        - discount_penalty
        - marketing_penalty
    )

    # Keep the margin within a realistic safety range.
    adjusted_margin = max(
        -0.50,
        min(
            adjusted_margin,
            0.80
        )
    )

    adjusted_profit = (
        adjusted_revenue
        * adjusted_margin
    )

    # --------------------------------------------------------
    # CHANGE CALCULATIONS
    # --------------------------------------------------------

    if base_revenue != 0:
        revenue_change = (
            (
                adjusted_revenue
                - base_revenue
            )
            / abs(base_revenue)
            * 100
        )
    else:
        revenue_change = (
            100
            if adjusted_revenue > 0
            else 0
        )

    if base_profit != 0:
        profit_change = (
            (
                adjusted_profit
                - base_profit
            )
            / abs(base_profit)
            * 100
        )
    else:
        profit_change = (
            100
            if adjusted_profit > 0
            else 0
        )

    if base_units != 0:
        units_change = (
            (
                adjusted_units
                - base_units
            )
            / abs(base_units)
            * 100
        )
    else:
        units_change = (
            100
            if adjusted_units > 0
            else 0
        )

    # --------------------------------------------------------
    # BUSINESS SCORE
    # --------------------------------------------------------

    score = 50

    # Revenue contribution
    if revenue_change > 0:
        score += min(
            revenue_change * 0.50,
            20
        )
    else:
        score += max(
            revenue_change * 0.40,
            -20
        )

    # Profit contribution
    if profit_change > 0:
        score += min(
            profit_change * 0.35,
            20
        )
    else:
        score += max(
            profit_change * 0.30,
            -25
        )

    # Units contribution
    if units_change > 0:
        score += min(
            units_change * 0.10,
            10
        )
    else:
        score += max(
            units_change * 0.08,
            -10
        )

    score = max(
        0,
        min(
            round(score),
            100
        )
    )

    # --------------------------------------------------------
    # DECISION
    # --------------------------------------------------------

    if (
        profit_change >= 10
        and revenue_change >= 5
        and score >= 65
    ):
        decision = "Recommended"

    elif (
        revenue_change >= 10
        and profit_change < 0
    ):
        decision = "High Revenue"

    elif (
        profit_change <= -10
    ):
        decision = "Lower Profit"

    elif score < 40:
        decision = "Not Recommended"

    else:
        decision = "Review"

    # --------------------------------------------------------
    # INSIGHTS
    # --------------------------------------------------------

    insights = []

    if revenue_change > 0:
        insights.append(
            f"Projected revenue increases by "
            f"{revenue_change:.1f}%."
        )
    elif revenue_change < 0:
        insights.append(
            f"Projected revenue decreases by "
            f"{abs(revenue_change):.1f}%."
        )
    else:
        insights.append(
            "Projected revenue remains approximately unchanged."
        )

    if profit_change > 0:
        insights.append(
            f"Projected profit improves by "
            f"{profit_change:.1f}%."
        )
    elif profit_change < 0:
        insights.append(
            f"Projected profit declines by "
            f"{abs(profit_change):.1f}%."
        )
    else:
        insights.append(
            "Projected profit remains approximately unchanged."
        )

    if units_change > 0:
        insights.append(
            f"Projected unit demand increases by "
            f"{units_change:.1f}%."
        )
    elif units_change < 0:
        insights.append(
            f"Projected unit demand decreases by "
            f"{abs(units_change):.1f}%."
        )

    if discount_change > 0:
        insights.append(
            "Higher discounting increases expected demand "
            "but places pressure on profit margin."
        )

    if price_change > 0:
        insights.append(
            "The higher price improves revenue per unit, "
            "but the model applies a demand reduction "
            "through price elasticity."
        )

    if marketing_change > 0:
        insights.append(
            "Additional marketing spend increases projected "
            "revenue with diminishing returns."
        )

    if profit_change < 0 and revenue_change > 0:
        insights.append(
            "Revenue grows while profit declines, indicating "
            "that the scenario may be too expensive to execute."
        )

    if score >= 75:
        insights.append(
            "Overall scenario assessment is strong."
        )
    elif score >= 60:
        insights.append(
            "The scenario appears viable but should be monitored."
        )
    else:
        insights.append(
            "The scenario requires further review before execution."
        )

    # --------------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------------

    return {
        "baseline": {
            "revenue": round(
                base_revenue,
                2
            ),
            "profit": round(
                base_profit,
                2
            ),
            "units": round(
                base_units,
                2
            ),
        },

        "scenario": {
            "revenue": round(
                adjusted_revenue,
                2
            ),
            "profit": round(
                adjusted_profit,
                2
            ),
            "units": round(
                adjusted_units,
                2
            ),
        },

        "changes": {
            "revenue": round(
                revenue_change,
                2
            ),
            "profit": round(
                profit_change,
                2
            ),
            "units": round(
                units_change,
                2
            ),
        },

        "score": score,

        "decision": decision,

        "insights": insights,
    }
