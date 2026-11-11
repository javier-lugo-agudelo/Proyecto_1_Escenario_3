import os
import psycopg2
from psycopg2.extras import RealDictCursor


def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 5432)),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        cursor_factory=RealDictCursor,
    )


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL UNIQUE
        );

        INSERT INTO categorias (nombre)
        VALUES ('Electrónica'), ('Ropa'), ('Alimentos'), ('Herramientas'), ('Otros')
        ON CONFLICT (nombre) DO NOTHING;

        CREATE TABLE IF NOT EXISTS productos (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(200) NOT NULL,
            descripcion TEXT,
            categoria_id INTEGER REFERENCES categorias(id),
            precio NUMERIC(10, 2) NOT NULL DEFAULT 0,
            stock INTEGER NOT NULL DEFAULT 0,
            stock_minimo INTEGER NOT NULL DEFAULT 5,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS movimientos (
            id SERIAL PRIMARY KEY,
            producto_id INTEGER REFERENCES productos(id) ON DELETE CASCADE,
            tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('entrada', 'salida')),
            cantidad INTEGER NOT NULL,
            observacion TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS mensajes (
            id SERIAL PRIMARY KEY,
            contenido TEXT NOT NULL,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    cur.close()
    conn.close()
