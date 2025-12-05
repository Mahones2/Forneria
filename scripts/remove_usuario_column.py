import sqlite3

def main():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()
    cur.executescript('''
    PRAGMA foreign_keys=off;
    BEGIN TRANSACTION;
    CREATE TABLE pos_empleado_new (
        id INTEGER PRIMARY KEY,
        run varchar(45) NOT NULL,
        fono varchar(20) NOT NULL,
        direccion varchar(200) NOT NULL,
        cargo varchar(45) NOT NULL,
        nombres varchar(100) NOT NULL DEFAULT 'Sin_clave',
        apellido_paterno varchar(45) NOT NULL DEFAULT 'Desconocido',
        correo varchar(100) NOT NULL DEFAULT 'Desconocido',
        clave varchar(100) NOT NULL DEFAULT '0000'
    );
    INSERT INTO pos_empleado_new (id, run, fono, direccion, cargo, nombres, apellido_paterno, correo, clave)
        SELECT id, run, fono, direccion, cargo, nombres, apellido_paterno, correo, clave FROM pos_empleado;
    DROP TABLE pos_empleado;
    ALTER TABLE pos_empleado_new RENAME TO pos_empleado;
    COMMIT;
    PRAGMA foreign_keys=on;
    ''')
    conn.close()
    print('usuario column removed (pos_empleado rebuilt)')

if __name__ == '__main__':
    main()
