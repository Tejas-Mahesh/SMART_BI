# ============================================================
# OPPORTUNITY DETECTION ENGINE
# ============================================================

import numpy as np
import pandas as pd


# ============================================================
# HELPERS
# ============================================================

def safe_float(value, default=0.0):
    """
    Safely convert a value to float.
    """

    try:
        if value is None:
            return default

        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def normalize_column_name(column):
    """
    Normalize a dataframe column name for comparison.
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
    )


def json_safe(value):
    """
    Convert pandas / numpy values into JSON-safe values.
    """

    if value is None:
        return None

    if isinstance(value, (np.integer,)):
        return int(value)

    if isinstance(value, (np.floating,)):
        if np.isnan(value) or np.isinf(value):
            return 0.0
        return float(value)

    if isinstance(value, (np.bool_,)):
        return bool(value)

    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")

    if pd.isna(value):
        return None

    return value


# ============================================================
# OPPORTUNITY LEVEL
# ============================================================

def get_opportunity_level(score):
    """
    Convert opportunity score into a business-friendly level.
    """

    score = safe_float(score)

    if score >= 70:
        return "High"

    if score >= 40:
        return "Medium"

    return "Low"


# ============================================================
# DATE PREPARATION
# ============================================================

def prepare_date_column(dataframe, date_column):
    """
    Convert the selected date column into datetime values.
    """

    if not date_column:
        return dataframe, None

    if date_column not in dataframe.columns:
        return dataframe, None

    dataframe = dataframe.copy()

    dataframe["_opportunity_date"] = pd.to_datetime(
        dataframe[date_column],
        errors="coerce",
    )

    dataframe = dataframe[
        dataframe["_opportunity_date"].notna()
    ].copy()

    return dataframe, "_opportunity_date"


# ============================================================
# MAIN ANALYSIS
# ============================================================

def analyze_opportunity_detection(
    dataframe,
    dimension_column,
    value_column,
    date_column=None,
):
    """
    Analyze business opportunities from a selected dataset.

    Parameters
    ----------
    dataframe : pandas.DataFrame
        Cleaned dataset version.

    dimension_column : str
        Column used to identify the business area/entity.

    value_column : str
        Numeric column used to measure business value.

    date_column : str, optional
        Date column used to calculate growth.

    Returns
    -------
    dict
        Complete Opportunity Detection result.
    """

    # ========================================================
    # VALIDATE DATAFRAME
    # ========================================================

    if dataframe is None:
        raise ValueError(
            "No dataset was provided for Opportunity Detection."
        )

    if dataframe.empty:
        raise ValueError(
            "The selected dataset contains no usable records."
        )

    dataframe = dataframe.copy()

    # ========================================================
    # VALIDATE DIMENSION
    # ========================================================

    if not dimension_column:
        raise ValueError(
            "A dimension column is required for Opportunity Detection."
        )

    if dimension_column not in dataframe.columns:
        raise ValueError(
            f"The selected dimension column "
            f"'{dimension_column}' is not available."
        )

    # ========================================================
    # VALIDATE VALUE COLUMN
    # ========================================================

    if not value_column:
        raise ValueError(
            "A value metric is required for Opportunity Detection."
        )

    if value_column not in dataframe.columns:
        raise ValueError(
            f"The selected value column "
            f"'{value_column}' is not available."
        )

    # ========================================================
    # PREPARE VALUE COLUMN
    # ========================================================

    dataframe["_opportunity_value"] = pd.to_numeric(
        dataframe[value_column],
        errors="coerce",
    )

    dataframe = dataframe[
        dataframe["_opportunity_value"].notna()
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "The selected value metric does not contain usable numeric values."
        )

    # ========================================================
    # PREPARE DIMENSION
    # ========================================================

    dataframe["_opportunity_dimension"] = (
        dataframe[dimension_column]
        .astype(str)
        .str.strip()
    )

    dataframe = dataframe[
        dataframe["_opportunity_dimension"].ne("")
        & dataframe["_opportunity_dimension"].ne("nan")
    ].copy()

    if dataframe.empty:
        raise ValueError(
            "The selected dimension column does not contain usable values."
        )

    # ========================================================
    # PREPARE DATE
    # ========================================================

    dataframe, prepared_date_column = prepare_date_column(
        dataframe,
        date_column,
    )

    # ========================================================
    # AGGREGATE CURRENT VALUE
    # ========================================================

    grouped = (
        dataframe
        .groupby(
            "_opportunity_dimension",
            dropna=False,
        )
        .agg(
            current_value=(
                "_opportunity_value",
                "sum",
            ),
            record_count=(
                "_opportunity_value",
                "count",
            ),
        )
        .reset_index()
    )

    if grouped.empty:
        raise ValueError(
            "Unable to calculate opportunity values."
        )

    # ========================================================
    # CALCULATE GROWTH
    # ========================================================

    grouped["previous_value"] = 0.0
    grouped["growth_percentage"] = 0.0

    if prepared_date_column:

        valid_dates = dataframe[
            dataframe[prepared_date_column].notna()
        ].copy()

        if not valid_dates.empty:

            max_date = valid_dates[
                prepared_date_column
            ].max()

            min_date = valid_dates[
                prepared_date_column
            ].min()

            date_span = (
                max_date - min_date
            ).days

            # If there is enough historical data,
            # compare the latest period with the previous
            # period of the same approximate length.

            if date_span >= 1:

                midpoint = (
                    min_date
                    + (
                        max_date - min_date
                    ) / 2
                )

                previous_data = valid_dates[
                    valid_dates[
                        prepared_date_column
                    ] < midpoint
                ]

                current_data = valid_dates[
                    valid_dates[
                        prepared_date_column
                    ] >= midpoint
                ]

                previous_grouped = (
                    previous_data
                    .groupby(
                        "_opportunity_dimension"
                    )[
                        "_opportunity_value"
                    ]
                    .sum()
                )

                current_grouped = (
                    current_data
                    .groupby(
                        "_opportunity_dimension"
                    )[
                        "_opportunity_value"
                    ]
                    .sum()
                )

                for index, row in grouped.iterrows():

                    dimension = (
                        row[
                            "_opportunity_dimension"
                        ]
                    )

                    current_value = safe_float(
                        current_grouped.get(
                            dimension,
                            0,
                        )
                    )

                    previous_value = safe_float(
                        previous_grouped.get(
                            dimension,
                            0,
                        )
                    )

                    grouped.at[
                        index,
                        "current_value"
                    ] = current_value

                    grouped.at[
                        index,
                        "previous_value"
                    ] = previous_value

                    if previous_value != 0:

                        growth = (
                            (
                                current_value
                                - previous_value
                            )
                            / abs(previous_value)
                        ) * 100

                    elif current_value > 0:

                        growth = 100.0

                    else:

                        growth = 0.0

                    grouped.at[
                        index,
                        "growth_percentage"
                    ] = growth

    # ========================================================
    # FALLBACK GROWTH
    # ========================================================

    # When no usable date information exists, opportunity
    # scoring will rely primarily on relative business value.

    if not prepared_date_column:

        grouped["current_value"] = pd.to_numeric(
            grouped["current_value"],
            errors="coerce",
        ).fillna(0)

    # ========================================================
    # VALUE SHARE
    # ========================================================

    total_value = safe_float(
        grouped["current_value"].sum()
    )

    if total_value > 0:

        grouped["value_share_percentage"] = (
            grouped["current_value"]
            / total_value
            * 100
        )

    else:

        grouped["value_share_percentage"] = 0.0

    # ========================================================
    # NORMALIZED VALUE SCORE
    # ========================================================

    max_value = safe_float(
        grouped["current_value"].max()
    )

    if max_value > 0:

        grouped["value_score"] = (
            grouped["current_value"]
            / max_value
            * 100
        )

    else:

        grouped["value_score"] = 0.0

    # ========================================================
    # NORMALIZED GROWTH SCORE
    # ========================================================

    growth_values = pd.to_numeric(
        grouped["growth_percentage"],
        errors="coerce",
    ).fillna(0)

    # We focus on positive growth for opportunity detection.
    positive_growth = growth_values.clip(
        lower=0
    )

    max_growth = safe_float(
        positive_growth.max()
    )

    if max_growth > 0:

        grouped["growth_score"] = (
            positive_growth
            / max_growth
            * 100
        )

    else:

        grouped["growth_score"] = 0.0

    # ========================================================
    # OPPORTUNITY SCORE
    # ========================================================

    # Method:
    #
    # 60% = current business value
    # 40% = positive growth
    #
    # This keeps the score focused on areas that already
    # generate meaningful value while recognizing areas
    # showing positive momentum.

    grouped["opportunity_score"] = (
        grouped["value_score"] * 0.60
        + grouped["growth_score"] * 0.40
    )

    # ========================================================
    # OPPORTUNITY LEVEL
    # ========================================================

    grouped["opportunity_level"] = (
        grouped["opportunity_score"]
        .apply(get_opportunity_level)
    )

    # ========================================================
    # OPPORTUNITY RANK
    # ========================================================

    grouped = grouped.sort_values(
        by=[
            "opportunity_score",
            "current_value",
        ],
        ascending=[
            False,
            False,
        ],
    ).reset_index(drop=True)

    grouped["opportunity_rank"] = (
        grouped.index + 1
    )

    # ========================================================
    # TOTAL OPPORTUNITIES
    # ========================================================

    total_opportunities = len(grouped)

    high_opportunities = int(
        (
            grouped["opportunity_level"]
            == "High"
        ).sum()
    )

    medium_opportunities = int(
        (
            grouped["opportunity_level"]
            == "Medium"
        ).sum()
    )

    low_opportunities = int(
        (
            grouped["opportunity_level"]
            == "Low"
        ).sum()
    )

    # ========================================================
    # OPPORTUNITY PERCENTAGE
    # ========================================================

    if total_opportunities > 0:

        opportunity_percentage = (
            high_opportunities
            / total_opportunities
            * 100
        )

    else:

        opportunity_percentage = 0.0

    # ========================================================
    # AVERAGE OPPORTUNITY SCORE
    # ========================================================

    average_opportunity_score = safe_float(
        grouped["opportunity_score"].mean()
    )

    # ========================================================
    # HIGHEST OPPORTUNITY
    # ========================================================

    if not grouped.empty:

        highest_row = grouped.iloc[0]

        highest_opportunity = str(
            highest_row[
                "_opportunity_dimension"
            ]
        )

        highest_opportunity_score = safe_float(
            highest_row[
                "opportunity_score"
            ]
        )

    else:

        highest_opportunity = ""
        highest_opportunity_score = 0.0

    # ========================================================
    # OPPORTUNITY DATA
    # ========================================================

    opportunity_data = []

    for _, row in grouped.iterrows():

        opportunity_data.append(
            {
                "dimension": json_safe(
                    row[
                        "_opportunity_dimension"
                    ]
                ),
                "current_value": round(
                    safe_float(
                        row["current_value"]
                    ),
                    2,
                ),
                "previous_value": round(
                    safe_float(
                        row["previous_value"]
                    ),
                    2,
                ),
                "growth_percentage": round(
                    safe_float(
                        row[
                            "growth_percentage"
                        ]
                    ),
                    2,
                ),
                "value_share_percentage": round(
                    safe_float(
                        row[
                            "value_share_percentage"
                        ]
                    ),
                    2,
                ),
                "opportunity_score": round(
                    safe_float(
                        row[
                            "opportunity_score"
                        ]
                    ),
                    2,
                ),
                "opportunity_level": (
                    row[
                        "opportunity_level"
                    ]
                ),
                "opportunity_rank": int(
                    row[
                        "opportunity_rank"
                    ]
                ),
                "record_count": int(
                    row[
                        "record_count"
                    ]
                ),
            }
        )

    # ========================================================
    # TOP OPPORTUNITIES
    # ========================================================

    opportunity_details = opportunity_data[
        :20
    ]

    # ========================================================
    # CHART DATA
    # ========================================================

    level_counts = {
        "High": high_opportunities,
        "Medium": medium_opportunities,
        "Low": low_opportunities,
    }

    chart_data = {
        "distribution": {
            "labels": [
                "High",
                "Medium",
                "Low",
            ],
            "values": [
                high_opportunities,
                medium_opportunities,
                low_opportunities,
            ],
        },

        "top_opportunities": {
            "labels": [
                item["dimension"]
                for item in opportunity_data[:10]
            ],
            "values": [
                item["opportunity_score"]
                for item in opportunity_data[:10]
            ],
        },

        "value_comparison": {
            "labels": [
                item["dimension"]
                for item in opportunity_data[:10]
            ],
            "values": [
                item["current_value"]
                for item in opportunity_data[:10]
            ],
        },
    }

    # ========================================================
    # SUMMARY
    # ========================================================

    if highest_opportunity:

        if prepared_date_column:

            summary = (
                f"{highest_opportunity} has the highest "
                f"opportunity score of "
                f"{highest_opportunity_score:.2f}. "
                f"The analysis considers current business "
                f"value and positive growth using the selected "
                f"value and date metrics."
            )

        else:

            summary = (
                f"{highest_opportunity} has the highest "
                f"opportunity score of "
                f"{highest_opportunity_score:.2f}. "
                f"Because no date-based comparison was used, "
                f"the opportunity assessment is primarily "
                f"based on relative business value."
            )

    else:

        summary = (
            "No measurable business opportunities were "
            "identified from the selected columns."
        )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {
        "dimension_column": dimension_column,

        "value_column": value_column,

        "date_column": (
            date_column
            if date_column
            else ""
        ),

        "opportunity_method": (
            "Opportunity Score: "
            "60% current business value + "
            "40% positive growth"
        ),

        "total_records": int(
            len(dataframe)
        ),

        "total_opportunities": int(
            total_opportunities
        ),

        "high_opportunities": int(
            high_opportunities
        ),

        "medium_opportunities": int(
            medium_opportunities
        ),

        "low_opportunities": int(
            low_opportunities
        ),

        "opportunity_percentage": round(
            safe_float(
                opportunity_percentage
            ),
            2,
        ),

        "average_opportunity_score": round(
            safe_float(
                average_opportunity_score
            ),
            2,
        ),

        "highest_opportunity": (
            highest_opportunity
        ),

        "highest_opportunity_score": round(
            safe_float(
                highest_opportunity_score
            ),
            2,
        ),

        "summary": summary,

        "opportunity_data": opportunity_data,

        "opportunity_details": opportunity_details,

        "chart_data": chart_data,
    }