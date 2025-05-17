from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='mul')
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return value * arg
    except (TypeError, ValueError):
        try:
            return Decimal(str(value)) * Decimal(str(arg))
        except:
            return 0 