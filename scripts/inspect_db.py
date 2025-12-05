import sqlite3
import pprint

def main():
    conn = sqlite3.connect('db.sqlite3')
    cur = conn.cursor()

    print('\n== pos_empleado schema ==')
    cur.execute("PRAGMA table_info('pos_empleado')")
    rows = cur.fetchall()
    pprint.pprint(rows)

    print('\n== django_migrations for pos ==')
    cur.execute("SELECT id, name, applied FROM django_migrations WHERE app='pos' ORDER BY id")
    rows = cur.fetchall()
    pprint.pprint(rows)

if __name__ == '__main__':
    main()
