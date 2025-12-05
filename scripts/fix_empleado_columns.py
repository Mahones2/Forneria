import sqlite3
import sys

def main():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    statements = [
        "ALTER TABLE pos_empleado ADD COLUMN nombres varchar(100) NOT NULL DEFAULT 'Sin_clave'",
        "ALTER TABLE pos_empleado ADD COLUMN apellido_paterno varchar(45) NOT NULL DEFAULT 'Desconocido'",
        "ALTER TABLE pos_empleado ADD COLUMN correo varchar(100) NOT NULL DEFAULT 'Desconocido'",
        "ALTER TABLE pos_empleado ADD COLUMN clave varchar(100) NOT NULL DEFAULT '0000'",
    ]

    for s in statements:
        try:
            cur.execute(s)
            print('executed:', s)
        except Exception as e:
            print('skipped/err for:', s)
            print('  ', e)

    conn.commit()
    print('done')

if __name__ == '__main__':
    main()
