"""
Compatibilidad: reexporta el filtro `clp` desde `pos.templatetags.currency`.

Este archivo existe para mantener compatibilidad con plantillas que
importaban `currency_extras`. La implementación canonical está en
`pos.templatetags.currency` y además se registra como builtin.
"""
from django import template
from .currency import clp as _clp

register = template.Library()
register.filter('clp', _clp)
