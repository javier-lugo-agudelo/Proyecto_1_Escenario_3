import os
from flask import Flask, request, jsonify
from models.db import init_db, get_connection
from controllers.inventario import bp as inventario_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")

app.register_blueprint(inventario_bp)


@app.route("/health")
def health():
    return {"status": "ok", "servicio": "inventario-app"}


@app.route("/mensajes", methods=["POST"])
def guardar_mensaje():
    data = request.get_json()
    contenido = data.get("contenido", "").strip()
    if not contenido:
        return jsonify({"error": "contenido requerido"}), 400
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO mensajes (contenido) VALUES (%s) RETURNING id, contenido, creado_en", (contenido,))
    mensaje = dict(cur.fetchone())
    conn.commit()
    cur.close()
    conn.close()
    return jsonify(mensaje), 201


@app.route("/mensajes", methods=["GET"])
def listar_mensajes():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, contenido, creado_en FROM mensajes ORDER BY creado_en DESC")
    mensajes = [dict(r) for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(mensajes)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG", "0") == "1")
