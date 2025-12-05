import os
import sys
import django

# Preparar entorno Django
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings_dev')
django.setup()

from pos.models import Cliente


def rut_with_dv(number: int) -> str:
    s = str(number)
    reversed_digits = list(map(int, reversed(s)))
    factors = [2, 3, 4, 5, 6, 7]
    total = 0
    factor_index = 0
    for d in reversed_digits:
        total += d * factors[factor_index]
        factor_index = (factor_index + 1) % len(factors)
    remainder = 11 - (total % 11)
    if remainder == 11:
        dv = '0'
    elif remainder == 10:
        dv = 'K'
    else:
        dv = str(remainder)
    return f"{number}-{dv}"


def main():
    # Lista determinística de clientes que queremos crear (numero_base, nombre)
    demo = [
        (11111111, 'Juan Pérez'),
        (12345678, 'María González'),
        (20123456, 'Carlos Ramírez'),
        (18345672, 'Ana Torres'),
        (22334455, 'Sofía Martínez'),
    ]

    created = []
    for num, nombre in demo:
        rut = rut_with_dv(num)
        correo = f"{nombre.replace(' ','.').lower()}@demo.local"
        cliente, created_flag = Cliente.objects.update_or_create(
            rut=rut,
            defaults={'nombre': nombre, 'correo': correo}
        )
        created.append((cliente, created_flag))

    print('\nClientes procesados:')
    for c, created_flag in created:
        print(f"  - {c.rut} | {c.nombre} | correo={c.correo} | creado_nuevo={created_flag}")


if __name__ == '__main__':
    main()
