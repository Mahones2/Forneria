import os
import os
import sys
import re

# Asegurarse de que el repo root esté en sys.path para que se pueda importar el paquete 'forneria'
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'forneria.settings')
import django
from pos.views import landing

def main():
    r = RequestFactory().get('/')
    resp = landing(r)
    html = resp.content.decode('utf-8')
    imgs = re.findall(r'src="([^"]+)"', html)
    print('--- Image src in rendered HTML ---')
    for s in imgs:
        if '/static/' in s:
            print(s)

if __name__ == '__main__':
    main()
