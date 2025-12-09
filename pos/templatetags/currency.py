from django import template

register = template.Library()


def clp(value):
    """Formatea un número como peso chileno sin decimales y con separador de miles '.'

    Ejemplo: 1200.0 -> "$1.200"
    """
    try:
        val = float(value)
    except Exception:
        return value
    try:
        # redondear al entero más cercano
        entero = int(round(val))
        # usar separador de miles como punto
        formatted = f"{entero:,}".replace(",", ".")
        return f"${formatted}"
    except Exception:
        return value


def as_number(value):
    """Devuelve el valor sin formato, como entero (string), útil para atributos data- en HTML."""
    try:
        return str(int(round(float(value))))
    except Exception:
        return value


register.filter('clp', clp)
register.filter('as_number', as_number)
