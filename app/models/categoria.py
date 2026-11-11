from .db import get_connection


class Categoria:
    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM categorias ORDER BY nombre")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
