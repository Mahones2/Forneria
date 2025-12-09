from django import template

register = template.Library()

@register.filter
def index(indexable, i):
    """Retorna el elemento en el índice i de una lista"""
    try:
        return indexable[int(i)]
    except (IndexError, TypeError, ValueError):
        return None
