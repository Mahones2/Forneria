"""
Extrae nombres y precios de imágenes usando Tesseract OCR y genera un CSV
Uso:
  py tools\extract_products_ocr.py --dir path/to/images --out pos/fixtures/forneria_products_extracted.csv
Requisitos:
  - Tesseract OCR instalado y en PATH
  - pip install pytesseract pillow opencv-python

Este script aplica preprocesado simple para mejorar OCR y heurísticas para localizar precios.
"""
import os
import re
import csv
import argparse
from PIL import Image, ImageOps, ImageFilter
import pytesseract

PRICE_RE = re.compile(r"\$?\s*([0-9]{1,3}(?:[.,][0-9]{3})*(?:[.,][0-9]{1,2})?)")

# Heurística para caducidad por categoría/key words
DEFAULT_CAD_DAYS = 7
CAD_KEYWORDS = {
    'Empanadas': 3,
    'Panaderia': 7,
    'Pasteleria': 5,
    'Cafe': 1,
    'Congelados': 90,
    'Pasta': 180,
}

def normalize_price(raw):
    if not raw:
        return '0'
    s = raw.strip()
    # eliminar $ y espacios
    s = s.replace('$','').replace(' ','')
    # si usa comas como separador decimal (ej 1.234,56) -> cambiar a 1234.56
    if s.count(',') == 1 and s.count('.') >= 1:
        # casos ambiguos como 1.234,56 -> remove dots, comma->dot
        s = s.replace('.','').replace(',','.')
    else:
        # remover separadores de miles (puntos) y cambiar comas decimales
        s = s.replace('.', '')
        s = s.replace(',', '.')
    try:
        # formatear con 2 decimales
        v = float(s)
        return f"{v:.2f}"
    except Exception:
        return '0'


def preprocess_image(path):
    img = Image.open(path).convert('RGB')
    # convertir a escala de grises, aumentar contraste
    gray = ImageOps.grayscale(img)
    # redimensionar si imagen pequeña
    w,h = gray.size
    if w < 1200:
        scale = int(1200 / w)
        gray = gray.resize((w*scale, h*scale), Image.LANCZOS)
    # aplicar filtro suave y luego aumentar nitidez
    gray = gray.filter(ImageFilter.MedianFilter(size=3))
    return gray


def extract_text_from_image(path):
    img = preprocess_image(path)
    # intentar OCR en español, si no está instalado usará eng
    try:
        text = pytesseract.image_to_string(img, lang='spa')
    except Exception:
        text = pytesseract.image_to_string(img)
    return text


def guess_rows_from_text(text):
    # dividir en líneas y extraer líneas con números (posible precio)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    results = []
    for ln in lines:
        # buscar precio en la línea
        m = PRICE_RE.search(ln)
        if m:
            price_raw = m.group(1)
            price = normalize_price(price_raw)
            # eliminar el fragmento del precio del nombre
            name = PRICE_RE.sub('', ln).strip(' -–:')
            # si name vacío y línea anterior existe, usar la anterior como nombre
            results.append((name, price, ln))
    # fallback: si no se encontraron precios, intentar líneas que parezcan "Nombre - Precio"
    if not results and lines:
        for i, ln in enumerate(lines):
            # si la línea siguiente tiene un número, combinar
            if i+1 < len(lines):
                m = PRICE_RE.search(lines[i+1])
                if m:
                    price = normalize_price(m.group(1))
                    results.append((lines[i], price, lines[i+1]))
    return results


def choose_category_from_name(name):
    # heurística simple por palabras clave
    n = name.lower()
    if any(x in n for x in ['empanad', 'pino', 'queso']):
        return 'Empanadas', CAD_KEYWORDS.get('Empanadas', DEFAULT_CAD_DAYS)
    if any(x in n for x in ['pan', 'rollo', 'galleta', 'pastel']):
        return 'Panaderia y Pasteleria', CAD_KEYWORDS.get('Panaderia', DEFAULT_CAD_DAYS)
    if any(x in n for x in ['cafe', 'lavazza', 'bebida']):
        return 'Cafe y Bebidas', CAD_KEYWORDS.get('Cafe', DEFAULT_CAD_DAYS)
    if any(x in n for x in ['pasta', 'pizza', 'congelada', 'congelados']):
        return 'Gourmet y Congelados', CAD_KEYWORDS.get('Congelados', DEFAULT_CAD_DAYS)
    return 'Sin categoría', DEFAULT_CAD_DAYS


def process_directory(img_dir, out_csv):
    rows_out = []
    files = [os.path.join(img_dir,f) for f in os.listdir(img_dir) if f.lower().endswith(('.png','.jpg','.jpeg','.tiff'))]
    files.sort()
    for fpath in files:
        print(f"Procesando {fpath}...")
        text = extract_text_from_image(fpath)
        candidates = guess_rows_from_text(text)
        if not candidates:
            print('  No se encontraron líneas con precio. Guardando líneas candidatas para revisión...')
            # intentar extraer líneas que contengan números al final
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            for ln in lines:
                m = PRICE_RE.search(ln)
                if m:
                    candidates.append((PRICE_RE.sub('', ln).strip(' -–:'), normalize_price(m.group(1)), ln))
        for name, price, raw in candidates:
            if not name:
                # buscar en líneas previas del texto
                # usar raw si no hay nombre claro
                name = raw
            # limpiar caracteres extraños
            name = re.sub(r'[^\w\-\.,()áéíóúÁÉÍÓÚñÑ ]+', '', name).strip()
            if not name:
                continue
            cat, cad = choose_category_from_name(name)
            row = {
                'nombre': name,
                'descripcion': '',
                'categoria': cat,
                'precio': price,
                'stock': '10',
                'costo_unitario': '0',
                'tipo': '',
                'presentacion': '',
                'caducidad_days': str(cad),
            }
            rows_out.append(row)
    # Escribir CSV
    if not rows_out:
        print('No se extrajeron productos.')
        return
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, 'w', newline='', encoding='utf-8') as csvf:
        fieldnames = ['nombre','descripcion','categoria','precio','stock','costo_unitario','tipo','presentacion','caducidad_days']
        writer = csv.DictWriter(csvf, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)
    print(f"CSV generado en {out_csv} con {len(rows_out)} filas.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dir', required=True, help='Carpeta donde están las imágenes')
    parser.add_argument('--out', default='pos/fixtures/forneria_products_extracted.csv', help='Ruta CSV de salida')
    args = parser.parse_args()
    process_directory(args.dir, args.out)
