from .db import get_connection


class Producto:
    @staticmethod
    def get_all():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, c.nombre AS categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            ORDER BY p.id DESC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_id(producto_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, c.nombre AS categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.id = %s
            """,
            (producto_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row

    @staticmethod
    def create(nombre, descripcion, categoria_id, precio, stock, stock_minimo):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO productos (nombre, descripcion, categoria_id, precio, stock, stock_minimo)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nombre, descripcion, categoria_id, precio, stock, stock_minimo),
        )
        new_id = cur.fetchone()["id"]
        if int(stock) > 0:
            cur.execute(
                """
                INSERT INTO movimientos (producto_id, tipo, cantidad, observacion)
                VALUES (%s, 'entrada', %s, 'Stock inicial')
                """,
                (new_id, stock),
            )
        conn.commit()
        cur.close()
        conn.close()
        return new_id

    @staticmethod
    def update(producto_id, nombre, descripcion, categoria_id, precio, stock_minimo):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE productos
            SET nombre = %s,
                descripcion = %s,
                categoria_id = %s,
                precio = %s,
                stock_minimo = %s,
                actualizado_en = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (nombre, descripcion, categoria_id, precio, stock_minimo, producto_id),
        )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def delete(producto_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM productos WHERE id = %s", (producto_id,))
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def buscar(termino):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, c.nombre AS categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.nombre ILIKE %s OR p.descripcion ILIKE %s
            ORDER BY p.nombre
            """,
            (f"%{termino}%", f"%{termino}%"),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def stock_bajo():
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.*, c.nombre AS categoria_nombre
            FROM productos p
            LEFT JOIN categorias c ON p.categoria_id = c.id
            WHERE p.stock <= p.stock_minimo
            ORDER BY p.stock ASC
            """
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows

    @staticmethod
    def registrar_movimiento(producto_id, tipo, cantidad, observacion=""):
        conn = get_connection()
        cur = conn.cursor()
        if tipo == "entrada":
            cur.execute(
                "UPDATE productos SET stock = stock + %s, actualizado_en = CURRENT_TIMESTAMP WHERE id = %s",
                (cantidad, producto_id),
            )
        else:
            cur.execute(
                "UPDATE productos SET stock = GREATEST(stock - %s, 0), actualizado_en = CURRENT_TIMESTAMP WHERE id = %s",
                (cantidad, producto_id),
            )
        cur.execute(
            "INSERT INTO movimientos (producto_id, tipo, cantidad, observacion) VALUES (%s, %s, %s, %s)",
            (producto_id, tipo, cantidad, observacion),
        )
        conn.commit()
        cur.close()
        conn.close()

    @staticmethod
    def get_movimientos(producto_id):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM movimientos WHERE producto_id = %s ORDER BY fecha DESC LIMIT 50",
            (producto_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
