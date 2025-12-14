"""
Pruebas para validators.py
Testing de todas las funciones de validación centralizadas
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError as DjangoValidationError

from pos.validators import (
    validate_rut_format,
    validate_username_format,
    validate_username_unique,
    validate_positive_decimal,
    validate_non_negative_decimal,
    validate_stock_range,
    validate_password_strength,
    validate_email_unique,
    validate_chilean_phone,
    validate_codigo_barra,
    validate_future_date,
    validate_date_after,
    validate_positive_price_model,
    validate_stock_range_model
)
from pos.models import Cliente, Empleado
from decimal import Decimal
from datetime import date, timedelta


class ValidateRutFormatTest(TestCase):
    """Pruebas para validación de formato RUT chileno"""

    def test_rut_valido_con_puntos_y_guion(self):
        """RUT válido: 12.345.678-9"""
        self.assertEqual(validate_rut_format("12.345.678-9"), "12.345.678-9")

    def test_rut_valido_sin_puntos_con_guion(self):
        """RUT válido: 12345678-9"""
        self.assertEqual(validate_rut_format("12345678-9"), "12345678-9")

    def test_rut_valido_con_k_mayuscula(self):
        """RUT válido con K mayúscula"""
        self.assertEqual(validate_rut_format("12.345.678-K"), "12.345.678-K")

    def test_rut_valido_con_k_minuscula(self):
        """RUT válido con k minúscula"""
        self.assertEqual(validate_rut_format("12.345.678-k"), "12.345.678-k")

    def test_rut_invalido_sin_guion(self):
        """RUT inválido: sin guión"""
        with self.assertRaises(DRFValidationError):
            validate_rut_format("123456789")

    def test_rut_invalido_formato_incorrecto(self):
        """RUT inválido: formato incorrecto"""
        with self.assertRaises(DRFValidationError):
            validate_rut_format("12-345-678-9")

    def test_rut_vacio_retorna_valor(self):
        """RUT vacío debe retornar el valor sin error"""
        self.assertEqual(validate_rut_format(""), "")
        self.assertIsNone(validate_rut_format(None))


class ValidateUsernameTest(TestCase):
    """Pruebas para validación de username"""

    def test_username_valido(self):
        """Username válido: solo letras, números, guiones bajos"""
        self.assertEqual(validate_username_format("usuario123"), "usuario123")
        self.assertEqual(validate_username_format("user_name"), "user_name")

    def test_username_minimo_3_caracteres(self):
        """Username debe tener mínimo 3 caracteres"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_username_format("ab")
        self.assertIn("mínimo 3", str(cm.exception))

    def test_username_sin_espacios(self):
        """Username no debe contener espacios"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_username_format("user name")
        self.assertIn("espacios", str(cm.exception))

    def test_username_solo_alfanumerico(self):
        """Username solo permite alfanuméricos y guiones bajos"""
        with self.assertRaises(DRFValidationError):
            validate_username_format("user@name")
        with self.assertRaises(DRFValidationError):
            validate_username_format("user-name")

    def test_username_unique_sin_duplicados(self):
        """Username único cuando no existe otro usuario"""
        resultado = validate_username_unique("nuevo_usuario")
        self.assertEqual(resultado, "nuevo_usuario")

    def test_username_unique_con_duplicado(self):
        """Username duplicado debe lanzar error"""
        User.objects.create_user(username="existente", password="pass123")
        with self.assertRaises(DRFValidationError) as cm:
            validate_username_unique("existente")
        self.assertIn("en uso", str(cm.exception))


class ValidatePositiveDecimalTest(TestCase):
    """Pruebas para validación de decimales positivos"""

    def test_decimal_positivo_valido(self):
        """Decimal positivo válido"""
        self.assertEqual(validate_positive_decimal(Decimal('100.50')), Decimal('100.50'))
        self.assertEqual(validate_positive_decimal(0.01, "Precio"), 0.01)

    def test_decimal_cero_invalido(self):
        """Decimal cero debe ser inválido"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_positive_decimal(0, "Precio")
        self.assertIn("mayor a 0", str(cm.exception))

    def test_decimal_negativo_invalido(self):
        """Decimal negativo debe ser inválido"""
        with self.assertRaises(DRFValidationError):
            validate_positive_decimal(-10.5, "Monto")

    def test_decimal_none_retorna_none(self):
        """None debe retornar None sin error"""
        self.assertIsNone(validate_positive_decimal(None))


class ValidateStockRangeTest(TestCase):
    """Pruebas para validación de rango de stock"""

    def test_stock_valido_en_rango(self):
        """Stock válido entre 0 y 9999"""
        self.assertEqual(validate_stock_range(0), 0)
        self.assertEqual(validate_stock_range(100), 100)
        self.assertEqual(validate_stock_range(9999), 9999)

    def test_stock_negativo_invalido(self):
        """Stock negativo debe ser inválido"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_stock_range(-1)
        self.assertIn("negativo", str(cm.exception))

    def test_stock_mayor_9999_invalido(self):
        """Stock mayor a 9999 debe ser inválido"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_stock_range(10000)
        self.assertIn("9999", str(cm.exception))

    def test_stock_none_retorna_none(self):
        """None debe retornar None sin error"""
        self.assertIsNone(validate_stock_range(None))


class ValidatePasswordStrengthTest(TestCase):
    """Pruebas para validación de fortaleza de contraseña"""

    def test_password_valido_6_caracteres(self):
        """Contraseña válida con 6+ caracteres"""
        self.assertEqual(validate_password_strength("123456"), "123456")
        self.assertEqual(validate_password_strength("password123"), "password123")

    def test_password_corto_invalido(self):
        """Contraseña menor a 6 caracteres debe ser inválida"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_password_strength("12345")
        self.assertIn("6 caracteres", str(cm.exception))

    def test_password_vacio_invalido(self):
        """Contraseña vacía debe ser inválida"""
        with self.assertRaises(DRFValidationError):
            validate_password_strength("")


class ValidateEmailUniqueTest(TestCase):
    """Pruebas para validación de email único"""

    def test_email_unico_valido(self):
        """Email único cuando no existe otro cliente"""
        resultado = validate_email_unique("nuevo@correo.com", Cliente)
        self.assertEqual(resultado, "nuevo@correo.com")

    def test_email_duplicado_invalido(self):
        """Email duplicado debe lanzar error"""
        Cliente.objects.create(
            nombre="Cliente 1",
            correo="existente@correo.com",
            rut="12.345.678-9"
        )
        with self.assertRaises(DRFValidationError) as cm:
            validate_email_unique("existente@correo.com", Cliente)
        self.assertIn("ya está registrado", str(cm.exception))

    def test_email_vacio_retorna_valor(self):
        """Email vacío debe retornar sin error"""
        self.assertEqual(validate_email_unique("", Cliente), "")
        self.assertIsNone(validate_email_unique(None, Cliente))


class ValidateChileanPhoneTest(TestCase):
    """Pruebas para validación de teléfono chileno"""

    def test_telefono_celular_valido(self):
        """Teléfono celular válido: 9 dígitos"""
        self.assertEqual(validate_chilean_phone("912345678"), "912345678")
        self.assertEqual(validate_chilean_phone("+56912345678"), "+56912345678")

    def test_telefono_fijo_valido(self):
        """Teléfono fijo válido: 2 + 8 dígitos"""
        self.assertEqual(validate_chilean_phone("223456789"), "223456789")

    def test_telefono_con_espacios_valido(self):
        """Teléfono con espacios debe validarse correctamente"""
        self.assertEqual(validate_chilean_phone("9 1234 5678"), "9 1234 5678")

    def test_telefono_invalido_pocos_digitos(self):
        """Teléfono con menos de 9 dígitos debe ser inválido"""
        with self.assertRaises(DRFValidationError):
            validate_chilean_phone("12345")

    def test_telefono_vacio_retorna_valor(self):
        """Teléfono vacío debe retornar sin error"""
        self.assertEqual(validate_chilean_phone(""), "")
        self.assertIsNone(validate_chilean_phone(None))


class ValidateCodigoBarraTest(TestCase):
    """Pruebas para validación de código de barras"""

    def test_codigo_barra_8_digitos_valido(self):
        """Código de barras EAN-8 válido"""
        self.assertEqual(validate_codigo_barra("12345678"), "12345678")

    def test_codigo_barra_12_digitos_valido(self):
        """Código de barras UPC-A válido"""
        self.assertEqual(validate_codigo_barra("123456789012"), "123456789012")

    def test_codigo_barra_13_digitos_valido(self):
        """Código de barras EAN-13 válido"""
        self.assertEqual(validate_codigo_barra("1234567890123"), "1234567890123")

    def test_codigo_barra_longitud_invalida(self):
        """Código de barras con longitud inválida"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_codigo_barra("123456")
        self.assertIn("8, 12 o 13", str(cm.exception))

    def test_codigo_barra_con_letras_invalido(self):
        """Código de barras con letras debe ser inválido"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_codigo_barra("1234ABCD")
        self.assertIn("solo números", str(cm.exception))

    def test_codigo_barra_vacio_retorna_valor(self):
        """Código de barras vacío debe retornar sin error"""
        self.assertEqual(validate_codigo_barra(""), "")


class ValidateDateTest(TestCase):
    """Pruebas para validación de fechas"""

    def test_fecha_futura_valida(self):
        """Fecha futura debe ser válida"""
        fecha_futura = date.today() + timedelta(days=30)
        self.assertEqual(validate_future_date(fecha_futura), fecha_futura)

    def test_fecha_hoy_invalida(self):
        """Fecha de hoy debe ser inválida para fecha futura"""
        with self.assertRaises(DRFValidationError) as cm:
            validate_future_date(date.today())
        self.assertIn("futura", str(cm.exception))

    def test_fecha_pasada_invalida(self):
        """Fecha pasada debe ser inválida"""
        fecha_pasada = date.today() - timedelta(days=1)
        with self.assertRaises(DRFValidationError):
            validate_future_date(fecha_pasada)

    def test_fecha_posterior_valida(self):
        """Fecha posterior a referencia debe ser válida"""
        referencia = date(2025, 1, 1)
        posterior = date(2025, 1, 15)
        self.assertEqual(validate_date_after(posterior, referencia), posterior)

    def test_fecha_anterior_invalida(self):
        """Fecha anterior a referencia debe ser inválida"""
        referencia = date(2025, 1, 15)
        anterior = date(2025, 1, 1)
        with self.assertRaises(DRFValidationError) as cm:
            validate_date_after(anterior, referencia)
        self.assertIn("posterior", str(cm.exception))


class ValidateModelValidatorsTest(TestCase):
    """Pruebas para validadores de modelos Django"""

    def test_precio_positivo_modelo_valido(self):
        """Precio positivo válido para modelo"""
        # No debe lanzar excepción
        validate_positive_price_model(100.50)
        validate_positive_price_model(Decimal('50.00'))

    def test_precio_negativo_modelo_invalido(self):
        """Precio negativo debe lanzar DjangoValidationError"""
        with self.assertRaises(DjangoValidationError):
            validate_positive_price_model(-10)

    def test_stock_range_modelo_valido(self):
        """Stock en rango válido para modelo"""
        validate_stock_range_model(0)
        validate_stock_range_model(5000)
        validate_stock_range_model(9999)

    def test_stock_negativo_modelo_invalido(self):
        """Stock negativo debe lanzar DjangoValidationError"""
        with self.assertRaises(DjangoValidationError):
            validate_stock_range_model(-1)

    def test_stock_mayor_9999_modelo_invalido(self):
        """Stock mayor a 9999 debe lanzar DjangoValidationError"""
        with self.assertRaises(DjangoValidationError):
            validate_stock_range_model(10000)
