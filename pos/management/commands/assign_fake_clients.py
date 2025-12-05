from django.core.management.base import BaseCommand
from django.utils import timezone
import random
from pos.models import Cliente, Venta

FIRST_NAMES = ['Alex', 'María', 'Carlos', 'Laura', 'Jorge', 'Ana', 'Andrés', 'Beatriz', 'Diego', 'Camila', 'Santiago', 'Valentina', 'Pablo', 'Isabel', 'Fernando', 'Monica']
LAST_NAMES = ['Pérez', 'Gómez', 'Díaz', 'López', 'Rodríguez', 'Martínez', 'Fernández', 'Rojas', 'Soto', 'Vargas', 'Muñoz', 'Silva', 'Navarro', 'Molina']


def rut_with_dv(number: int) -> str:
    """Genera un RUT con dígito verificador válido (algoritmo módulo 11).

    number: entero sin puntos ni DV, por ejemplo 12345678
    retorna: "12345678-K" o con DV numérico
    """
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


def gen_unique_rut():
    """Genera un RUT único para la base de datos probando hasta encontrar uno no existente."""
    attempt = 0
    while True:
        attempt += 1
        num = random.randint(10000000, 24999999)
        rut = rut_with_dv(num)
        if not Cliente.objects.filter(rut=rut).exists():
            return rut
        if attempt > 200:
            # fallback: usar un rango más alto
            num = random.randint(25000000, 99999999)
            rut = rut_with_dv(num)
            if not Cliente.objects.filter(rut=rut).exists():
                return rut


class Command(BaseCommand):
    help = 'Crear clientes ficticios y asignar ventas a ellos (útil para poblar histórico).'

    def add_arguments(self, parser):
        parser.add_argument('--create', type=int, default=5, help='Número de clientes ficticios a crear')
        parser.add_argument('--assign-all', action='store_true', help='Asignar clientes a todas las ventas (si no tienen o incluso si ya tienen)')
        parser.add_argument('--only-empty', action='store_true', help='Solo asignar ventas que no tengan cliente')

    def handle(self, *args, **options):
        create_n = options['create']
        assign_all = options['assign_all']
        only_empty = options['only_empty']

        self.stdout.write(f'Creando {create_n} clientes ficticios...')
        created_clients = []
        for i in range(create_n):
            nombre = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            rut = gen_unique_rut()
            correo = f"{nombre.replace(' ','.').lower()}@demo.local"
            cliente, c = Cliente.objects.get_or_create(rut=rut, defaults={'nombre': nombre, 'correo': correo})
            created_clients.append(cliente)

        ventas_qs = Venta.objects.all().order_by('-fecha')
        assigned = 0
        for v in ventas_qs:
            if only_empty and v.cliente is not None:
                continue
            if (not assign_all) and v.cliente is not None and v.cliente.nombre and v.cliente.nombre != 'Cliente Demo':
                # mantener si ya tiene nombre distinto al genérico
                continue
            # asignar aleatoriamente
            new_cli = random.choice(created_clients)
            v.cliente = new_cli
            v.save(update_fields=['cliente'])
            assigned += 1

        self.stdout.write(self.style.SUCCESS(f'Clientes creados: {len(created_clients)}. Ventas reasignadas: {assigned}.'))
