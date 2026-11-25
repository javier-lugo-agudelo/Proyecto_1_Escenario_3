"""
Pruebas unitarias para el sistema de inventarios.
La conexion a PostgreSQL se mockea; no se requiere DB real.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

def test_health_retorna_ok(client):
    """GET /health responde 200 con status ok sin necesitar DB."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["servicio"] == "inventario-app"
    # ERROR INTENCIONAL: esta linea falla para generar evidencia de build fallido
    assert data["version"] == "2.0"


# ---------------------------------------------------------------------------
# POST /mensajes
# ---------------------------------------------------------------------------

def test_guardar_mensaje_exitoso(client):
    """POST /mensajes con contenido valido retorna 201 y el mensaje creado."""
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_cur.fetchone.return_value = {
        "id":         1,
        "contenido":  "jenkins-test",
        "creado_en":  "2024-01-01T00:00:00",
    }
    mock_conn.cursor.return_value = mock_cur

    with patch("app.get_connection", return_value=mock_conn):
        resp = client.post(
            "/mensajes",
            data=json.dumps({"contenido": "jenkins-test"}),
            content_type="application/json",
        )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == 1
    assert data["contenido"] == "jenkins-test"


def test_guardar_mensaje_sin_contenido_retorna_400(client):
    """POST /mensajes con body vacio retorna 400."""
    resp = client.post(
        "/mensajes",
        data=json.dumps({}),
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_guardar_mensaje_contenido_vacio_retorna_400(client):
    """POST /mensajes con contenido de espacios retorna 400."""
    resp = client.post(
        "/mensajes",
        data=json.dumps({"contenido": "   "}),
        content_type="application/json",
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /mensajes
# ---------------------------------------------------------------------------

def test_listar_mensajes_retorna_lista(client):
    """GET /mensajes retorna lista JSON con los mensajes de la DB."""
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_cur.fetchall.return_value = [
        {"id": 1, "contenido": "mensaje uno", "creado_en": "2024-01-01T00:00:00"},
        {"id": 2, "contenido": "mensaje dos", "creado_en": "2024-01-02T00:00:00"},
    ]
    mock_conn.cursor.return_value = mock_cur

    with patch("app.get_connection", return_value=mock_conn):
        resp = client.get("/mensajes")

    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["contenido"] == "mensaje uno"
    assert data[1]["contenido"] == "mensaje dos"


def test_listar_mensajes_db_vacia(client):
    """GET /mensajes retorna lista vacia si la DB no tiene registros."""
    mock_conn = MagicMock()
    mock_cur  = MagicMock()
    mock_cur.fetchall.return_value = []
    mock_conn.cursor.return_value = mock_cur

    with patch("app.get_connection", return_value=mock_conn):
        resp = client.get("/mensajes")

    assert resp.status_code == 200
    data = resp.get_json()
    assert data == []
