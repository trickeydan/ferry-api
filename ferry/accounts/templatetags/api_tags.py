from django import template

register = template.Library()


@register.filter
def redact(token: str) -> str:
    length = len(token)
    return "*" * (length - 5) + token[-5:]
