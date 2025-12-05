"""
Script rápido para crear grupos y usuarios de desarrollo:
- Administrador / contraseña: inacap123 (superuser + staff)
- Vendedor / contraseña: vendedor123 (grupo Vendedor)
- Cliente / contraseña: cliente123 (grupo Cliente)

Ejecutar en la raíz del proyecto:
py -3 -c "import os; os.environ['DJANGO_SETTINGS_MODULE']='forneria.settings_dev'; from django import setup; setup(); exec(open('scripts/create_roles_and_users.py').read())"
"""
from django.contrib.auth.models import User, Group

# Crear grupos
for g in ['Administrador', 'Vendedor', 'Cliente']:
    Group.objects.get_or_create(name=g)

# Administrador (superuser)
admin_username = 'administrador'
admin_pw = 'inacap123'
if not User.objects.filter(username=admin_username).exists():
    u = User.objects.create_superuser(admin_username, 'admin@example.com', admin_pw)
    u.is_staff = True
    u.save()
    print('Creado superusuario:', admin_username)
else:
    print('Superusuario ya existe:', admin_username)

# Vendedor
vendedor_username = 'vendedor'
vendedor_pw = 'vendedor123'
if not User.objects.filter(username=vendedor_username).exists():
    v = User.objects.create_user(vendedor_username, 'vendedor@example.com', vendedor_pw)
    grp = Group.objects.get(name='Vendedor')
    v.groups.add(grp)
    v.is_staff = True
    v.save()
    print('Creado vendedor:', vendedor_username)
else:
    print('Vendedor ya existe:', vendedor_username)

# Cliente
cliente_username = 'cliente_demo'
cliente_pw = 'cliente123'
if not User.objects.filter(username=cliente_username).exists():
    c = User.objects.create_user(cliente_username, 'cliente@example.com', cliente_pw)
    grp = Group.objects.get(name='Cliente')
    c.groups.add(grp)
    c.save()
    print('Creado cliente:', cliente_username)
else:
    print('Cliente ya existe:', cliente_username)

print('Script finalizado.')

# Opcional: crear registro en modelo Cliente (si existe) y enlazar por correo
try:
    from pos.models import Cliente
    cliente_rut = '00000000-0'
    if not Cliente.objects.filter(rut=cliente_rut).exists():
        Cliente.objects.create(rut=cliente_rut, nombre='Cliente Demo', correo='cliente@example.com')
        print('Cliente demo creado en pos.Cliente:', cliente_rut)
    else:
        print('Cliente demo ya existe en pos.Cliente:', cliente_rut)
except Exception as e:
    print('No se pudo crear registro en pos.Cliente (pos app quizá no instalada):', str(e))
