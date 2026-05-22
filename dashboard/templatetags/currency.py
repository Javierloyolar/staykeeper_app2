from django import template

register = template.Library()

@register.filter(name='clp')
def clp(value):
    try:
        # Convertimos a entero para eliminar decimales (,0)
        valor_entero = int(float(value))
        # Formateamos con puntos usando la herramienta nativa de Python
        return f"{valor_entero:,}".replace(",", ".")
    except (ValueError, TypeError):
        return value
    
@register.filter(name='clp_short')
def clp_short(value):
    try:
        value = float(value)
        abs_value = abs(value)

        if abs_value >= 1_000_000_000:
            formatted = f"{value / 1_000_000_000:.2f} B"
        elif abs_value >= 1_000_000:
            formatted = f"{value / 1_000_000:.2f} M"
        elif abs_value >= 1_000:
            formatted = f"{value / 1_000:.0f} K"
        else:
            formatted = f"{value:,.0f}".replace(",", ".")

        return formatted

    except (ValueError, TypeError):
        return value