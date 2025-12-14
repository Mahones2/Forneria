"""
Validadores centralizados para el sistema POS
Validaciones reutilizables para serializers y modelos
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError as DjangoValidationError
import re


def validate_rut_format(value):
    """
    Valida formato RUT chileno XX.XXX.XXX-X o XXXXXXXX-X
    Acepta con o sin puntos, pero requiere guión antes del dígito verificador
    """
    if not value:
        return value

    # Patrón: acepta con o sin puntos, pero REQUIERE guión antes del dígito verificador
    rut_pattern = r'^(\d{1,2}\.?\d{3}\.?\d{3})-[\dkK]$'

    if not re.match(rut_pattern, value):
        raise serializers.ValidationError(
            "Formato RUT inválido. Use XX.XXX.XXX-X o XXXXXXXX-X (el guión es obligatorio)"
        )

    return value


def validate_username_format(value):
    """
    Username sin espacios, mínimo 3 caracteres
    Solo permite letras, números y guiones bajos
    """
    if not value:
        raise serializers.ValidationError("El username es requerido")

    if ' ' in value:
        raise serializers.ValidationError("El username no debe contener espacios")

    if len(value) < 3:
        raise serializers.ValidationError("El username debe tener mínimo 3 caracteres")

    # Validar solo caracteres alfanuméricos y guiones bajos
    if not re.match(r'^[a-zA-Z0-9_]+$', value):
        raise serializers.ValidationError(
            "El username solo puede contener letras, números y guiones bajos"
        )

    return value


def validate_username_unique(value, instance=None):
    """
    Verifica que el username no esté en uso
    instance: objeto User existente (para ediciones)
    """
    if not value:
        return value

    qs = User.objects.filter(username=value)

    # Si estamos editando, excluir el usuario actual
    if instance:
        if hasattr(instance, 'usuario'):  # Para Empleado
            qs = qs.exclude(pk=instance.usuario_id)
        elif hasattr(instance, 'pk'):  # Para User directo
            qs = qs.exclude(pk=instance.pk)

    if qs.exists():
        raise serializers.ValidationError("El username ya está en uso")

    return value


def validate_positive_decimal(value, field_name="Campo"):
    """
    Valida que un decimal/float sea mayor a 0
    """
    if value is None:
        return value

    if value <= 0:
        raise serializers.ValidationError(
            f"{field_name} debe ser mayor a 0"
        )

    return value


def validate_non_negative_decimal(value, field_name="Campo"):
    """
    Valida que un decimal/float sea mayor o igual a 0
    """
    if value is None:
        return value

    if value < 0:
        raise serializers.ValidationError(
            f"{field_name} no puede ser negativo"
        )

    return value


def validate_stock_range(value):
    """
    Stock debe estar entre 0 y 9999
    """
    if value is None:
        return value

    if value < 0:
        raise serializers.ValidationError("El stock no puede ser negativo")

    if value > 9999:
        raise serializers.ValidationError("Stock máximo permitido: 9999")

    return value


def validate_password_strength(value):
    """
    Contraseña mínimo 6 caracteres
    Puede extenderse con más reglas (mayúsculas, números, etc.)
    """
    if not value:
        raise serializers.ValidationError("La contraseña es requerida")

    if len(value) < 6:
        raise serializers.ValidationError(
            "La contraseña debe tener al menos 6 caracteres"
        )

    return value


def validate_email_unique(value, model_class, instance=None):
    """
    Valida que el email sea único en el modelo especificado

    Args:
        value: email a validar
        model_class: Clase del modelo (ej: Cliente)
        instance: Instancia actual (para ediciones)
    """
    if not value:
        return value

    qs = model_class.objects.filter(correo=value)

    # Si estamos editando, excluir la instancia actual
    if instance:
        qs = qs.exclude(pk=instance.pk)

    if qs.exists():
        raise serializers.ValidationError("Este email ya está registrado")

    return value


def validate_chilean_phone(value):
    """
    Valida formato de teléfono chileno
    Acepta: +56912345678, 912345678, 223456789 (fijo)
    """
    if not value:
        return value

    # Limpiar espacios y guiones
    clean_phone = value.replace(' ', '').replace('-', '')

    # Patrón: opcional +56, luego 9 dígitos (celular) o 2 + 8 dígitos (fijo)
    phone_pattern = r'^(\+?56)?([2-9]\d{8})$'

    if not re.match(phone_pattern, clean_phone):
        raise serializers.ValidationError(
            "Formato de teléfono inválido. Use formato chileno: +56912345678 o 912345678"
        )

    return value


def validate_codigo_barra(value):
    """
    Valida que el código de barras tenga formato correcto
    Generalmente 8, 12 o 13 dígitos
    """
    if not value:
        return value

    # Limpiar espacios
    clean_code = value.replace(' ', '').replace('-', '')

    # Debe ser solo números
    if not clean_code.isdigit():
        raise serializers.ValidationError(
            "El código de barras debe contener solo números"
        )

    # Validar longitud común (EAN-8, UPC-A, EAN-13)
    valid_lengths = [8, 12, 13]
    if len(clean_code) not in valid_lengths:
        raise serializers.ValidationError(
            f"El código de barras debe tener 8, 12 o 13 dígitos. Recibido: {len(clean_code)}"
        )

    return value


def validate_future_date(value):
    """
    Valida que una fecha sea futura (para fechas de caducidad)
    """
    from datetime import date

    if not value:
        return value

    if value <= date.today():
        raise serializers.ValidationError(
            "La fecha debe ser futura"
        )

    return value


def validate_date_after(value, reference_date, field_name="fecha"):
    """
    Valida que una fecha sea posterior a otra fecha de referencia

    Args:
        value: fecha a validar
        reference_date: fecha de referencia
        field_name: nombre del campo para el mensaje de error
    """
    if not value or not reference_date:
        return value

    if value <= reference_date:
        raise serializers.ValidationError(
            f"La {field_name} debe ser posterior a la fecha de referencia"
        )

    return value


# Validadores para modelos (Django ValidationError)
def validate_positive_price_model(value):
    """
    Validador para modelos Django - precio positivo
    """
    if value is not None and value < 0:
        raise DjangoValidationError("El precio no puede ser negativo")


def validate_stock_range_model(value):
    """
    Validador para modelos Django - rango de stock
    """
    if value is not None:
        if value < 0:
            raise DjangoValidationError("El stock no puede ser negativo")
        if value > 9999:
            raise DjangoValidationError("Stock máximo permitido: 9999")
