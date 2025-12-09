import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
django.setup()

from pos.models import Cliente

clientes_data = [
    {"rut": "12345678-9", "nombre": "Juan Pérez", "correo": "juan@example.com"},
    {"rut": "23456789-0", "nombre": "María García", "correo": "maria@example.com"},
    {"rut": "34567890-1", "nombre": "Carlos López", "correo": "carlos@example.com"},
    {"rut": "45678901-2", "nombre": "Ana Martínez", "correo": "ana@example.com"},
    {"rut": "56789012-3", "nombre": "Roberto Sánchez", "correo": "roberto@example.com"},
    {"rut": "67890123-4", "nombre": "Laura Rodríguez", "correo": "laura@example.com"},
    {"rut": "78901234-5", "nombre": "Francisco Torres", "correo": "francisco@example.com"},
    {"rut": "89012345-6", "nombre": "Isabel Flores", "correo": "isabel@example.com"},
    {"rut": "90123456-7", "nombre": "Diego Morales", "correo": "diego@example.com"},
    {"rut": "01234567-8", "nombre": "Patricia Jiménez", "correo": "patricia@example.com"},
]

for data in clientes_data:
    cliente, created = Cliente.objects.get_or_create(
        rut=data["rut"],
        defaults={"nombre": data["nombre"], "correo": data["correo"]}
    )
    status = "creado" if created else "ya existía"
    print(f"{data['nombre']} - {status}")

print(f"\nTotal de clientes: {Cliente.objects.count()}")
