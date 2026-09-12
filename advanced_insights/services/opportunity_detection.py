
import numpy as np
import pandas as pd


# ============================================================
# COLUMN DETECTION
# ============================================================

def detect_column(df, candidates):

    normalized = {
        str(column).strip().lower(): column
        for column in df.columns
    }

    # Exact match
    for candidate in candidates:

        candidate = candidate.lower().strip()

        if candidate in normalized:
            return normalized[candidate]

    # Partial match
    for column in df.columns:

        column_name = str(column).strip().lower()

        for candidate in candidates:

            candidate = candidate.lower().strip()

            if candidate in column_name:
                return column

    return None


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_data(
    df,
    date_column=None,
    sales_column=None,
    quantity_column=None,
):

    data = df.copy()

    # --------------------------------------------------------
    # Date
    # --------------------------------------------------------

    if (
        date_column
        and date_column in data.columns
    ):

        data[date_column] = pd.to_datetime(
            data[date_column],
            errors="coerce",
        )

    # --------------------------------------------------------
    # Sales / Revenue
    # --------------------------------------------------------

    if (
        sales_column
        and sales_column in data.columns
    ):

        data[sales_column] = pd.to_numeric(
            data[sales_column],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if (
        quantity_column
        and quantity_column in data.columns
    ):

        data[quantity_column] = pd.to_numeric(
            data[quantity_column],
            errors="coerce",
        ).fillna(0)

    # --------------------------------------------------------
    # Remove invalid dates
    # --------------------------------------------------------

    if (
        date_column
        and date_column in data.columns
    ):

        data = data.dropna(
            subset=[date_column]
        )

    return data


# ============================================================
# PERCENTAGE CHANGE
# ============================================================

def calculate_percentage_change(
    current,
    previous,
):

    try:

        current = float(current)
        previous = float(previous)

    except (
        ValueError,
        TypeError,
    ):

        return 0

    # --------------------------------------------------------
    # Both zero
    # --------------------------------------------------------

    if previous == 0:

        if current == 0:
            return 0

        # New activity where previous period had none
        return 100

    return (
        (
            current - previous
        )
        / abs(previous)
    ) * 100


# ============================================================
# CREATE TIME PERIODS
# ============================================================

def create_periods(
    data,
    date_column,
    days=30,
):

    if (
        data.empty
        or not date_column
        or date_column not in data.columns
    ):

        return (
            data.iloc[0:0].copy(),
            data.iloc[0:0].copy(),
            None,
            None,
        )

    valid_dates = (
        data[date_column]
        .dropna()
    )

    if valid_dates.empty:

        return (
            data.iloc[0:0].copy(),
            data.iloc[0:0].copy(),
            None,
            None,
        )

    max_date = (
        valid_dates
        .max()
        .normalize()
    )

    current_start = (
        max_date
        - pd.Timedelta(
            days=days - 1
        )
    )

    previous_end = (
        current_start
        - pd.Timedelta(
            days=1
        )
    )

    previous_start = (
        previous_end
        - pd.Timedelta(
            days=days - 1
        )
    )

    current = data[
        (
            data[date_column]
            >= current_start
        )
        &
        (
            data[date_column]
            <= max_date
        )
    ].copy()

    previous = data[
        (
            data[date_column]
            >= previous_start
        )
        &
        (
            data[date_column]
            <= previous_end
        )
    ].copy()

    return (
        current,
        previous,
        current_start,
        max_date,
    )


# ============================================================
# ANALYZE BUSINESS DIMENSION
# ============================================================

def analyze_dimension(
    current,
    previous,
    dimension_column,
    sales_column,
    quantity_column=None,
):

    if (
        not dimension_column
        or dimension_column not in current.columns
    ):

        return pd.DataFrame()

    current_data = current.copy()
    previous_data = previous.copy()

    # --------------------------------------------------------
    # Normalize dimension
    # --------------------------------------------------------

    current_data[dimension_column] = (
        current_data[
            dimension_column
        ]
        .astype(str)
        .str.strip()
    )

    previous_data[dimension_column] = (
        previous_data[
            dimension_column
        ]
        .astype(str)
        .str.strip()
    )

    # --------------------------------------------------------
    # Remove invalid dimension values
    # --------------------------------------------------------

    invalid_values = [
        "",
        "nan",
        "none",
        "null",
        "n/a",
        "na",
    ]

    current_data = current_data[
        ~current_data[
            dimension_column
        ]
        .str.lower()
        .isin(invalid_values)
    ]

    previous_data = previous_data[
        ~previous_data[
            dimension_column
        ]
        .str.lower()
        .isin(invalid_values)
    ]

    if current_data.empty:

        return pd.DataFrame()

    # --------------------------------------------------------
    # Current period
    # --------------------------------------------------------

    current_group = (
        current_data
        .groupby(
            dimension_column
        )
        .agg(
            current_revenue=(
                sales_column,
                "sum",
            ),
            current_transactions=(
                sales_column,
                "count",
            ),
        )
    )

    # --------------------------------------------------------
    # Previous period
    # --------------------------------------------------------

    if previous_data.empty:

        previous_group = pd.DataFrame(
            columns=[
                "previous_revenue",
                "previous_transactions",
            ]
        )

    else:

        previous_group = (
            previous_data
            .groupby(
                dimension_column
            )
            .agg(
                previous_revenue=(
                    sales_column,
                    "sum",
                ),
                previous_transactions=(
                    sales_column,
                    "count",
                ),
            )
        )

    # --------------------------------------------------------
    # Quantity
    # --------------------------------------------------------

    if (
        quantity_column
        and quantity_column
        in current_data.columns
    ):

        current_quantity = (
            current_data
            .groupby(
                dimension_column
            )[quantity_column]
            .sum()
            .rename(
                "current_quantity"
            )
        )

    else:

        current_quantity = pd.Series(
            0.0,
            index=current_group.index,
            name="current_quantity",
        )

    if (
        quantity_column
        and quantity_column
        in previous_data.columns
        and not previous_data.empty
    ):

        previous_quantity = (
            previous_data
            .groupby(
                dimension_column
            )[quantity_column]
            .sum()
            .rename(
                "previous_quantity"
            )
        )

    else:

        previous_quantity = pd.Series(
            0.0,
            index=previous_group.index,
            name="previous_quantity",
        )

    # --------------------------------------------------------
    # Combine
    # --------------------------------------------------------

    result = pd.concat(
        [
            current_group,
            previous_group,
            current_quantity,
            previous_quantity,
        ],
        axis=1,
    ).fillna(0)

    # --------------------------------------------------------
    # Revenue change
    # --------------------------------------------------------

    result["revenue_change"] = (
        result["current_revenue"]
        -
        result["previous_revenue"]
    )

    # --------------------------------------------------------
    # Revenue growth
    # --------------------------------------------------------

    result["growth_percent"] = result.apply(
        lambda row:
        calculate_percentage_change(
            row["current_revenue"],
            row["previous_revenue"],
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # Quantity change
    # --------------------------------------------------------

    result["quantity_change"] = (
        result["current_quantity"]
        -
        result["previous_quantity"]
    )

    # --------------------------------------------------------
    # Quantity growth
    # --------------------------------------------------------

    result["quantity_growth_percent"] = result.apply(
        lambda row:
        calculate_percentage_change(
            row["current_quantity"],
            row["previous_quantity"],
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # Transaction change
    # --------------------------------------------------------

    result["transaction_change"] = (
        result["current_transactions"]
        -
        result["previous_transactions"]
    )

    # --------------------------------------------------------
    # Transaction growth
    # --------------------------------------------------------

    result["transaction_growth_percent"] = result.apply(
        lambda row:
        calculate_percentage_change(
            row["current_transactions"],
            row["previous_transactions"],
        ),
        axis=1,
    )

    return result


# ============================================================
# NORMALIZE SCORE
# ============================================================

def normalize_score(
    series,
    minimum=0,
    maximum=100,
):

    if series is None:

        return pd.Series(
            dtype=float
        )

    values = pd.to_numeric(
        series,
        errors="coerce",
    ).fillna(0)

    if values.empty:

        return values

    values = values.clip(
        minimum,
        maximum,
    )

    return values


# ============================================================
# CALCULATE OPPORTUNITY SCORES
# ============================================================

def calculate_opportunity_scores(
    data,
    category_type=None,
):

    if data.empty:

        return data

    result = data.copy()

    category = (
        str(
            category_type
            or ""
        )
        .strip()
        .lower()
    )

    # ========================================================
    # REVENUE GROWTH SCORE
    # ========================================================

    growth_score = (
        result[
            "growth_percent"
        ]
        .clip(
            -100,
            100,
        )
        + 100
    ) / 2

    # ========================================================
    # REVENUE SCALE SCORE
    # ========================================================

    revenue_max = (
        result[
            "current_revenue"
        ]
        .max()
    )

    if revenue_max > 0:

        revenue_score = (
            result[
                "current_revenue"
            ]
            / revenue_max
        ) * 100

    else:

        revenue_score = pd.Series(
            0.0,
            index=result.index,
        )

    # ========================================================
    # QUANTITY GROWTH SCORE
    # ========================================================

    if (
        "quantity_growth_percent"
        in result.columns
    ):

        quantity_score = (
            result[
                "quantity_growth_percent"
            ]
            .clip(
                -100,
                100,
            )
            + 100
        ) / 2

    else:

        quantity_score = pd.Series(
            50.0,
            index=result.index,
        )

    # ========================================================
    # TRANSACTION GROWTH SCORE
    # ========================================================

    if (
        "transaction_growth_percent"
        in result.columns
    ):

        transaction_score = (
            result[
                "transaction_growth_percent"
            ]
            .clip(
                -100,
                100,
            )
            + 100
        ) / 2

    else:

        transaction_score = pd.Series(
            50.0,
            index=result.index,
        )

    # ========================================================
    # CATEGORY-SPECIFIC WEIGHTS
    # ========================================================

    if category == "products":

        # Products:
        # Revenue + demand + transactions

        result["opportunity_score"] = (
            growth_score * 0.45
            + revenue_score * 0.25
            + quantity_score * 0.20
            + transaction_score * 0.10
        )

    elif category == "customers":

        # Customers:
        # Revenue + transaction engagement + frequency

        result["opportunity_score"] = (
            growth_score * 0.45
            + revenue_score * 0.30
            + transaction_score * 0.25
        )

    elif category == "regional":

        # Regional:
        # Growth is especially important for market expansion.

        result["opportunity_score"] = (
            growth_score * 0.55
            + revenue_score * 0.30
            + quantity_score * 0.15
        )

    elif category == "marketing":

        # Marketing:
        # Revenue momentum + campaign activity.

        result["opportunity_score"] = (
            growth_score * 0.50
            + revenue_score * 0.25
            + transaction_score * 0.25
        )

    else:

        # Generic fallback

        result["opportunity_score"] = (
            growth_score * 0.50
            + revenue_score * 0.30
            + quantity_score * 0.20
        )

    # ========================================================
    # NEW GROWTH BONUS
    # ========================================================
    #
    # If the dimension had no previous revenue but now has
    # meaningful revenue, it represents a newly emerging
    # opportunity.
    # ========================================================

    new_activity = (
        (
            result[
                "previous_revenue"
            ]
            <= 0
        )
        &
        (
            result[
                "current_revenue"
            ]
            > 0
        )
    )

    result.loc[
        new_activity,
        "opportunity_score"
    ] = (
        result.loc[
            new_activity,
            "opportunity_score"
        ]
        + 8
    )

    # ========================================================
    # STRONG GROWTH BONUS
    # ========================================================

    strong_growth = (
        result[
            "growth_percent"
        ] >= 25
    )

    result.loc[
        strong_growth,
        "opportunity_score"
    ] = (
        result.loc[
            strong_growth,
            "opportunity_score"
        ]
        + 5
    )

    # ========================================================
    # CLIP FINAL SCORE
    # ========================================================

    result[
        "opportunity_score"
    ] = (
        result[
            "opportunity_score"
        ]
        .clip(
            0,
            100,
        )
        .round(1)
    )

    return result


# ============================================================
# CLASSIFY OPPORTUNITY
# ============================================================

def classify_opportunity(
    row,
):

    growth = float(
        row.get(
            "growth_percent",
            0,
        )
    )

    revenue = float(
        row.get(
            "current_revenue",
            0,
        )
    )

    score = float(
        row.get(
            "opportunity_score",
            0,
        )
    )

    quantity_growth = float(
        row.get(
            "quantity_growth_percent",
            0,
        )
    )

    transaction_growth = float(
        row.get(
            "transaction_growth_percent",
            0,
        )
    )

    # ========================================================
    # HIGH OPPORTUNITY
    # ========================================================

    if (
        score >= 75
        and growth >= 20
        and revenue > 0
    ):

        return "High Opportunity"

    # ========================================================
    # STRONG OPPORTUNITY
    # ========================================================

    if (
        score >= 60
        and growth >= 10
        and revenue > 0
    ):

        return "Strong Opportunity"

    # ========================================================
    # EMERGING OPPORTUNITY
    # ========================================================

    if (
        score >= 50
        and (
            growth >= 5
            or quantity_growth >= 5
            or transaction_growth >= 5
        )
        and revenue > 0
    ):

        return "Emerging Opportunity"

    # ========================================================
    # NEEDS ATTENTION
    # ========================================================

    if (
        growth < 0
        and revenue > 0
    ):

        return "Needs Attention"

    # ========================================================
    # STABLE
    # ========================================================

    return "Stable"


# ============================================================
# CATEGORY-SPECIFIC RECOMMENDED ACTION
# ============================================================

def recommended_action(
    row,
    category_type=None,
):

    level = row.get(
        "opportunity_level",
        "Stable",
    )

    category = (
        str(
            category_type
            or ""
        )
        .strip()
        .lower()
    )

    dimension = str(
        row.get(
            "dimension",
            "business area",
        )
    )

    # ========================================================
    # HIGH OPPORTUNITY
    # ========================================================

    if level == "High Opportunity":

        if category == "products":

            return (
                "Increase inventory availability, "
                "promotion, and marketing support "
                "for this high-growth product."
            )

        if category == "customers":

            return (
                "Prioritize this customer or segment "
                "with personalized offers and "
                "retention-focused engagement."
            )

        if category == "regional":

            return (
                "Consider increasing regional "
                "investment, distribution, and "
                "market coverage."
            )

        if category == "marketing":

            return (
                "Scale this campaign or channel "
                "while monitoring ROI and "
                "conversion efficiency."
            )

        return (
            "Increase investment and scale "
            "this opportunity aggressively."
        )

    # ========================================================
    # STRONG OPPORTUNITY
    # ========================================================

    if level == "Strong Opportunity":

        if category == "products":

            return (
                "Increase product visibility and "
                "monitor inventory to support "
                "continued demand."
            )

        if category == "customers":

            return (
                "Increase engagement through "
                "targeted offers and personalized "
                "customer communication."
            )

        if category == "regional":

            return (
                "Strengthen regional marketing and "
                "distribution to capture additional demand."
            )

        if category == "marketing":

            return (
                "Increase campaign visibility and "
                "test a controlled increase in spend."
            )

        return (
            "Increase visibility, inventory, "
            "and business support."
        )

    # ========================================================
    # EMERGING OPPORTUNITY
    # ========================================================

    if level == "Emerging Opportunity":

        if category == "products":

            return (
                "Monitor demand closely and test "
                "targeted promotions before scaling."
            )

        if category == "customers":

            return (
                "Encourage repeat purchases through "
                "targeted engagement and offers."
            )

        if category == "regional":

            return (
                "Test localized campaigns and "
                "monitor demand before expanding."
            )

        if category == "marketing":

            return (
                "Run controlled campaign experiments "
                "and monitor performance before scaling."
            )

        return (
            "Monitor growth and test targeted "
            "promotions."
        )

    # ========================================================
    # NEEDS ATTENTION
    # ========================================================

    if level == "Needs Attention":

        if category == "products":

            return (
                "Investigate declining demand, "
                "pricing, competition, or inventory issues."
            )

        if category == "customers":

            return (
                "Investigate declining engagement and "
                "consider a reactivation strategy."
            )

        if category == "regional":

            return (
                "Investigate regional performance "
                "decline before increasing investment."
            )

        if category == "marketing":

            return (
                "Review campaign efficiency, targeting, "
                "and spend before further investment."
            )

        return (
            "Investigate performance decline "
            "before increasing investment."
        )

    # ========================================================
    # STABLE
    # ========================================================

    return (
        "Maintain the current strategy and "
        "continue monitoring performance."
    )


# ============================================================
# BUILD OPPORTUNITY RESULTS
# ============================================================

def build_opportunities(
    comparison,
    dimension_name,
    category_type=None,
):

    if comparison.empty:

        return []

    comparison = (
        calculate_opportunity_scores(
            comparison,
            category_type=category_type,
        )
    )

    comparison[
        "opportunity_level"
    ] = comparison.apply(
        classify_opportunity,
        axis=1,
    )

    # --------------------------------------------------------
    # Add dimension
    # --------------------------------------------------------

    comparison[
        "dimension"
    ] = dimension_name

    # --------------------------------------------------------
    # Category-specific action
    # --------------------------------------------------------

    comparison[
        "recommended_action"
    ] = comparison.apply(
        lambda row:
        recommended_action(
            {
                **row.to_dict(),
                "dimension": dimension_name,
            },
            category_type=category_type,
        ),
        axis=1,
    )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    comparison = (
        comparison
        .sort_values(
            [
                "opportunity_score",
                "growth_percent",
            ],
            ascending=False,
        )
    )

    opportunities = []

    # --------------------------------------------------------
    # Return top 20 per dimension
    # --------------------------------------------------------

    for category, row in (
        comparison
        .head(20)
        .iterrows()
    ):

        opportunities.append(
            {

                # --------------------------------------------
                # Dimension
                # --------------------------------------------

                "dimension": (
                    dimension_name
                ),

                # --------------------------------------------
                # Category
                # --------------------------------------------

                "category": str(
                    category
                ),

                # --------------------------------------------
                # Current revenue
                # --------------------------------------------

                "current_revenue": round(
                    float(
                        row.get(
                            "current_revenue",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Previous revenue
                # --------------------------------------------

                "previous_revenue": round(
                    float(
                        row.get(
                            "previous_revenue",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Revenue change
                # --------------------------------------------

                "revenue_change": round(
                    float(
                        row.get(
                            "revenue_change",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Growth
                # --------------------------------------------

                "growth_percent": round(
                    float(
                        row.get(
                            "growth_percent",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Current quantity
                # --------------------------------------------

                "current_quantity": round(
                    float(
                        row.get(
                            "current_quantity",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Quantity change
                # --------------------------------------------

                "quantity_change": round(
                    float(
                        row.get(
                            "quantity_change",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Quantity growth
                # --------------------------------------------

                "quantity_growth_percent": round(
                    float(
                        row.get(
                            "quantity_growth_percent",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Transactions
                # --------------------------------------------

                "current_transactions": int(
                    row.get(
                        "current_transactions",
                        0,
                    )
                ),

                "previous_transactions": int(
                    row.get(
                        "previous_transactions",
                        0,
                    )
                ),

                "transaction_change": int(
                    row.get(
                        "transaction_change",
                        0,
                    )
                ),

                "transaction_growth_percent": round(
                    float(
                        row.get(
                            "transaction_growth_percent",
                            0,
                        )
                    ),
                    2,
                ),

                # --------------------------------------------
                # Score
                # --------------------------------------------

                "opportunity_score": round(
                    float(
                        row.get(
                            "opportunity_score",
                            0,
                        )
                    ),
                    1,
                ),

                # --------------------------------------------
                # Level
                # --------------------------------------------

                "opportunity_level": (
                    row[
                        "opportunity_level"
                    ]
                ),

                # --------------------------------------------
                # Recommended action
                # --------------------------------------------

                "recommended_action": (
                    row[
                        "recommended_action"
                    ]
                ),
            }
        )

    return opportunities


# ============================================================
# SUMMARY
# ============================================================

def calculate_opportunity_summary(
    opportunities,
):

    if not opportunities:

        return {
            "total_opportunities": 0,
            "high_opportunities": 0,
            "strong_opportunities": 0,
            "emerging_opportunities": 0,
            "average_score": 0,
        }

    high = sum(
        item[
            "opportunity_level"
        ]
        == "High Opportunity"
        for item in opportunities
    )

    strong = sum(
        item[
            "opportunity_level"
        ]
        == "Strong Opportunity"
        for item in opportunities
    )

    emerging = sum(
        item[
            "opportunity_level"
        ]
        == "Emerging Opportunity"
        for item in opportunities
    )

    scores = [
        item[
            "opportunity_score"
        ]
        for item in opportunities
    ]

    return {

        "total_opportunities": len(
            opportunities
        ),

        "high_opportunities": int(
            high
        ),

        "strong_opportunities": int(
            strong
        ),

        "emerging_opportunities": int(
            emerging
        ),

        "average_score": round(
            float(
                np.mean(scores)
            ),
            1,
        ),
    }


# ============================================================
# INSIGHTS
# ============================================================

def generate_opportunity_insights(
    opportunities,
    summary,
    category_type=None,
):

    insights = []

    if not opportunities:

        return [
            "No significant business opportunities "
            "were identified from the selected dataset."
        ]

    category = (
        str(
            category_type
            or ""
        )
        .strip()
        .lower()
    )

    high = summary[
        "high_opportunities"
    ]

    strong = summary[
        "strong_opportunities"
    ]

    emerging = summary[
        "emerging_opportunities"
    ]

    # ========================================================
    # HIGH OPPORTUNITIES
    # ========================================================

    if high > 0:

        insights.append(
            f"{high} high-priority opportunities "
            "were identified and should receive "
            "immediate management attention."
        )

    # ========================================================
    # STRONG OPPORTUNITIES
    # ========================================================

    if strong > 0:

        insights.append(
            f"{strong} strong opportunities show "
            "positive momentum and may benefit "
            "from additional investment."
        )

    # ========================================================
    # EMERGING
    # ========================================================

    if emerging > 0:

        insights.append(
            f"{emerging} emerging opportunities "
            "show early positive signals and "
            "should be monitored for further growth."
        )

    # ========================================================
    # BEST OPPORTUNITY
    # ========================================================

    best = max(
        opportunities,
        key=lambda item:
        item[
            "opportunity_score"
        ],
    )

    if category == "products":

        insights.append(
            f"{best['category']} is the strongest "
            f"product opportunity with a score of "
            f"{best['opportunity_score']:.1f} and "
            f"revenue growth of "
            f"{best['growth_percent']:.1f}%."
        )

    elif category == "customers":

        insights.append(
            f"{best['category']} is the strongest "
            f"customer opportunity with a score of "
            f"{best['opportunity_score']:.1f} and "
            f"revenue growth of "
            f"{best['growth_percent']:.1f}%."
        )

    elif category == "regional":

        insights.append(
            f"{best['category']} is the strongest "
            f"regional opportunity with a score of "
            f"{best['opportunity_score']:.1f} and "
            f"revenue growth of "
            f"{best['growth_percent']:.1f}%."
        )

    elif category == "marketing":

        insights.append(
            f"{best['category']} is the strongest "
            f"marketing opportunity with a score of "
            f"{best['opportunity_score']:.1f} and "
            f"revenue growth of "
            f"{best['growth_percent']:.1f}%."
        )

    else:

        insights.append(
            f"{best['category']} is currently the "
            f"strongest opportunity with an "
            f"opportunity score of "
            f"{best['opportunity_score']:.1f}."
        )

    # ========================================================
    # HIGHEST GROWTH
    # ========================================================

    highest_growth = max(
        opportunities,
        key=lambda item:
        item[
            "growth_percent"
        ],
    )

    insights.append(
        f"{highest_growth['category']} recorded "
        f"the highest recent growth of "
        f"{highest_growth['growth_percent']:.1f}%."
    )

    # ========================================================
    # NEW OPPORTUNITIES
    # ========================================================

    new_opportunities = [
        item
        for item in opportunities
        if (
            item[
                "previous_revenue"
            ] <= 0
            and
            item[
                "current_revenue"
            ] > 0
        )
    ]

    if new_opportunities:

        insights.append(
            f"{len(new_opportunities)} areas "
            "showed new measurable activity "
            "after having no recorded revenue "
            "in the previous comparison period."
        )

    return insights


# ============================================================
# MAIN OPPORTUNITY DETECTION ENGINE
# ============================================================

def run_opportunity_detection(
    df,
    date_column,
    sales_column,
    quantity_column=None,
    dimension_columns=None,
    category_type=None,
):

    # ========================================================
    # EMPTY DATA
    # ========================================================

    if df.empty:

        return {

            "opportunities": [],

            "summary": (
                calculate_opportunity_summary(
                    []
                )
            ),

            "insights": [],

            "current_start": None,

            "current_end": None,
        }

    # ========================================================
    # PREPARE DATA
    # ========================================================

    data = prepare_data(
        df=df,
        date_column=date_column,
        sales_column=sales_column,
        quantity_column=quantity_column,
    )

    if data.empty:

        return {

            "opportunities": [],

            "summary": (
                calculate_opportunity_summary(
                    []
                )
            ),

            "insights": [
                "No valid dated transaction "
                "records were available for "
                "opportunity detection."
            ],

            "current_start": None,

            "current_end": None,
        }

    # ========================================================
    # CREATE PERIODS
    # ========================================================

    (
        current,
        previous,
        current_start,
        current_end,
    ) = create_periods(
        data,
        date_column,
        days=30,
    )

    # ========================================================
    # CURRENT PERIOD EMPTY
    # ========================================================

    if current.empty:

        return {

            "opportunities": [],

            "summary": (
                calculate_opportunity_summary(
                    []
                )
            ),

            "insights": [
                "There is not enough recent "
                "transaction data for opportunity "
                "detection."
            ],

            "current_start": current_start,

            "current_end": current_end,
        }

    # ========================================================
    # DIMENSIONS
    # ========================================================

    if dimension_columns is None:

        dimension_columns = []

    # Remove duplicates while preserving order

    dimension_columns = list(
        dict.fromkeys(
            dimension_columns
        )
    )

    # ========================================================
    # NO DIMENSIONS
    # ========================================================

    if not dimension_columns:

        return {

            "opportunities": [],

            "summary": (
                calculate_opportunity_summary(
                    []
                )
            ),

            "insights": [
                "No suitable business dimension "
                "was available for opportunity detection."
            ],

            "current_start": current_start,

            "current_end": current_end,
        }

    # ========================================================
    # ANALYZE EACH DIMENSION
    # ========================================================

    all_opportunities = []

    for dimension in dimension_columns:

        if (
            not dimension
            or dimension not in current.columns
        ):

            continue

        comparison = analyze_dimension(
            current=current,
            previous=previous,
            dimension_column=dimension,
            sales_column=sales_column,
            quantity_column=quantity_column,
        )

        if comparison.empty:

            continue

        opportunities = build_opportunities(
            comparison=comparison,
            dimension_name=dimension,
            category_type=category_type,
        )

        all_opportunities.extend(
            opportunities
        )

    # ========================================================
    # GLOBAL SORT
    # ========================================================

    all_opportunities.sort(
        key=lambda item: (
            item[
                "opportunity_score"
            ],
            item[
                "growth_percent"
            ],
        ),
        reverse=True,
    )

    # ========================================================
    # KEEP TOP 30
    # ========================================================

    all_opportunities = (
        all_opportunities[:30]
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = (
        calculate_opportunity_summary(
            all_opportunities
        )
    )

    # ========================================================
    # INSIGHTS
    # ========================================================

    insights = (
        generate_opportunity_insights(
            all_opportunities,
            summary,
            category_type=category_type,
        )
    )

    # ========================================================
    # RETURN
    # ========================================================

    return {

        "opportunities": (
            all_opportunities
        ),

        "summary": summary,

        "insights": insights,

        "current_start": (
            current_start
        ),

        "current_end": (
            current_end
        ),
    }
