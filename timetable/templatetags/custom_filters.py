from django import template
from datetime import datetime

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary is None:
        return None  
    return dictionary.get(key, None)

@register.filter
def format_time(value):
    try:
        if isinstance(value, str):
            value = datetime.strptime(value, "%H:%M").time()
        return value.strftime("%I:%M %p")  # Safe across Windows, Linux, macOS
    except:
        return value
