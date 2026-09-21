
from django import template


register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Safely retrieve a value from a dictionary using a template key.

    Usage:
        {% with source=dataset_status|get_item:dataset_type %}
    """

    if dictionary is None:
        return None

    if not isinstance(dictionary, dict):
        return None

    return dictionary.get(key)
