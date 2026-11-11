# Sistema de Inventarios - Proyecto 1 Escenario 3

Sistema web de gestión de inventarios construido con arquitectura **MVC**, Flask y PostgreSQL, orquestado con Docker Compose.

## Arquitectura MVC

```
┌──────────────────────────────────────────────┐
│              Red Docker: proyecto_net         │
│                                              │
│  ┌─────────────────────┐  ┌───────────────┐  │
│  │  Contenedor: app    │  │ Contenedor:db │  │
│  │  python:3.11-slim   │──▶  postgres:15  │  │
│  │  Flask + Jinja2     │  │               │  │
│  │  puerto 5000        │  │  puerto 5432  │  │
│  │                     │  │  volumen:     │  │
│  │  MVC:               │  │  postgres_data│  │
│  │  models/            │  └───────────────┘  │
│  │  controllers/       │                     │
│  │  templates/ (views) │                     │
│  └─────────────────────┘                     │
└──────────────────────────────────────────────┘
```

**Comunicación:** `app` → `db` por nombre de servicio Docker (`DB_HOST=db`), no por localhost ni IP fija.

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Frontend (View) | HTML5 + Bootstrap 5.3 + Jinja2 |
| Backend (Controller) | Flask 3.0 + Blueprints |
| Datos (Model) | PostgreSQL 15 + psycopg2 |
| Contenedores | Docker + Docker Compose |
| CI | GitHub Actions |

## Estructura MVC

```
app/
├── models/
│   ├── db.py           # Conexión y init de base de datos
│   ├── producto.py     # Modelo Producto (CRUD + movimientos)
│   └── categoria.py    # Modelo Categoria
├── controllers/
│   └── inventario.py   # Controlador (rutas Flask Blueprint)
├── templates/          # Vistas (Jinja2)
│   ├── base.html
│   └── productos/
│       ├── lista.html
│       ├── crear.html
│       ├── editar.html
│       └── detalle.html
├── static/
│   ├── css/style.css
│   └── js/main.js
├── app.py              # Punto de entrada
├── Dockerfile
└── requirements.txt
```

## Requisitos

- Docker >= 24
- Docker Compose >= 2.20

## Configuración

```bash
cp .env.example .env
# Editar .env con tus credenciales (nunca subir .env al repo)
```

## Levantar los contenedores

```bash
docker compose up -d
```

Abrir en el navegador: **http://localhost:5000**

## Comandos útiles

```bash
# Ver estado de contenedores
docker compose ps
docker ps

# Ver logs en tiempo real
docker compose logs -f

# Inspeccionar la red Docker
docker network inspect proyecto1escenario3_proyecto_net

# Detener
docker compose down

# Detener y borrar datos
docker compose down -v
```

## Prueba de comunicación entre contenedores

```bash
# Guardar dato en DB (app → db)
curl -X POST http://localhost:5000/mensajes \
  -H "Content-Type: application/json" \
  -d '{"contenido": "prueba"}'

# Leer dato desde DB (app ← db)
curl http://localhost:5000/mensajes

# Health check
curl http://localhost:5000/health
```

## Funcionalidades del sistema

- **Listar productos** con buscador en tiempo real
- **Crear producto** con nombre, descripción, categoría, precio, stock y stock mínimo
- **Editar producto** (datos generales, sin modificar stock directamente)
- **Eliminar producto** con confirmación
- **Registrar movimientos** de entrada y salida de stock
- **Historial de movimientos** por producto
- **Alertas de stock bajo** en el panel principal
