from decimal import Decimal, InvalidOperation

from django import template


register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Safely return dictionary[key] for Django templates.

    Usage:
        {{ my_dictionary|get_item:key }}
    """

    if dictionary is None:
        return None

    if not isinstance(dictionary, dict):
        return None

    return dictionary.get(key)


@register.filter
def smart_number(value):
    """
    Format business intelligence numbers cleanly.

    Examples:
        1000        -> 1,000
        12500.5     -> 12,500.5
        12500.00    -> 12,500
        None        -> —
        ""          -> —
    """

    if value is None:
        return "—"

    if value == "":
        return "—"

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    if number == number.to_integral_value():
        return f"{int(number):,}"

    formatted = f"{number:,.2f}"
    formatted = formatted.rstrip("0").rstrip(".")

    return formatted


@register.filter
def smart_percent(value):
    """
    Format percentage values cleanly.

    Examples:
        25        -> 25%
        25.5      -> 25.5%
        25.00     -> 25%
        None      -> —
        ""        -> —
    """

    if value is None:
        return "—"

    if value == "":
        return "—"

    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value

    if number == number.to_integral_value():
        return f"{int(number):,}%"

    formatted = f"{number:,.2f}"
    formatted = formatted.rstrip("0").rstrip(".")

    return f"{formatted}%"