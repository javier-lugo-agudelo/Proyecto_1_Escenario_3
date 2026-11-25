# Entrega 2 — Semana 5: Integración Continua con Jenkins
## Sistema de Inventarios — Proyecto 1 Escenario 3

**Repositorio:** https://github.com/javier-lugo-agudelo/Proyecto_2_Semana_5  
**Integrantes:** Javier Lugo Agudelo  
**Fecha de entrega:** 24 de noviembre de 2026

---

## 1. Características Requeridas para Implementar Jenkins

### 1.1 Requisitos de Hardware

| Recurso | Mínimo recomendado | Configuración utilizada |
|---------|-------------------|------------------------|
| CPU | 2 núcleos | 2 núcleos (entorno Docker) |
| RAM | 2 GB para Jenkins + memoria adicional para los contenedores del proyecto | 4 GB recomendado |
| Disco | 10 GB libres | 10 GB (volumen Docker `jenkins_home`) |

> **Nota:** Jenkins en contenedor Docker consume aproximadamente 400–600 MB de RAM en reposo. Durante un build que levanta los dos servicios del proyecto (app + db), el consumo puede superar los 1.5 GB de RAM.

### 1.2 Requisitos de Software

| Componente | Versión | Rol |
|-----------|---------|-----|
| Docker Engine | >= 24.0 | Motor de contenedores |
| Docker Compose | >= 2.20 (plugin `docker compose`) | Orquestación de servicios |
| Jenkins | LTS (imagen `jenkins/jenkins:lts-jdk17`) | Servidor de CI/CD |
| JDK | 17 (incluido en la imagen base) | Entorno de ejecución de Jenkins |
| Git | >= 2.x (incluido en la imagen base) | Gestión de código fuente |

### 1.3 Decisión de Instalación: Contenedor Docker

Se eligió la imagen oficial `jenkins/jenkins:lts-jdk17` con un volumen Docker por las siguientes razones:

- **Portabilidad:** La configuración completa viaja dentro del repositorio (`jenkins/`).
- **Reproducibilidad:** Cualquier integrante puede levantar el entorno idéntico con un solo comando.
- **Persistencia selectiva:** El volumen `jenkins_home` conserva el historial de builds, configuración y credenciales entre reinicios, sin mezclar datos con el sistema operativo anfitrión.
- **Aislamiento:** No interfiere con otros servicios del host.
- **Facilidad de actualización:** Cambiar la versión de Jenkins implica modificar una sola línea en el `Dockerfile`.

**Alternativa descartada:** Instalación nativa (`.war` o paquete `apt`) requiere configurar Java, gestionar actualizaciones manualmente y no es portable entre equipos del equipo.

### 1.4 Puertos

| Puerto | Protocolo | Función |
|--------|----------|---------|
| 8080 | HTTP | Interfaz web de Jenkins (acceso desde navegador) |
| 50000 | TCP | Comunicación con agentes JNLP (escalabilidad futura) |

### 1.5 Plugins Instalados

Los plugins se declaran en `jenkins/plugins.txt` y se pre-instalan durante la construcción de la imagen Docker:

| Plugin | Función |
|--------|---------|
| `workflow-aggregator` | Soporte completo para Declarative y Scripted Pipeline |
| `git` | Integración con repositorios Git (clone, checkout) |
| `github` | Integración con GitHub (webhooks, estado de commits) |
| `docker-workflow` | Pasos `docker.build()`, `docker.image()` en Pipeline |
| `configuration-as-code` | Configuración de Jenkins como código (JCasC) |
| `job-dsl` | Creación automática de jobs desde `casc.yaml` |
| `pipeline-stage-view` | Vista visual de etapas del pipeline en la interfaz web |

### 1.6 Credenciales

Las credenciales se gestionan exclusivamente desde el **Jenkins Credentials Store** — nunca en texto plano en el código fuente.

| ID de credencial | Tipo | Contenido |
|-----------------|------|----------|
| `inventario-db-password` | Secret text | Contraseña de PostgreSQL |
| `inventario-secret-key` | Secret text | Secret key de Flask |

**Configuración automática:** El archivo `jenkins/casc.yaml` inyecta las credenciales al arrancar Jenkins, leyendo sus valores de variables de entorno definidas en `jenkins/.env` (excluido del repositorio por `.gitignore`).

---

## 2. Instalación y Configuración de Jenkins

### 2.1 Estructura de archivos Jenkins

```
jenkins/
├── Dockerfile          # Imagen Jenkins LTS + Docker CLI + plugins
├── docker-compose.yml  # Servicio Jenkins con volumen y socket Docker
├── plugins.txt         # Lista de plugins a pre-instalar
├── casc.yaml           # JCasC: seguridad, credenciales, job pipeline
└── .env.example        # Plantilla de variables de entorno (copiar a .env)
```

### 2.2 Pasos de instalación

```bash
# 1. Ir al directorio jenkins/
cd jenkins/

# 2. Crear archivo de variables de entorno
cp .env.example .env
# Editar .env con los valores reales

# 3. Construir la imagen Jenkins (instala plugins automáticamente)
docker compose build

# 4. Levantar Jenkins
docker compose up -d

# 5. Esperar a que Jenkins esté listo (~60-90 segundos)
docker compose logs -f jenkins
# Esperar a ver: "Jenkins is fully up and running"

# 6. Acceder en el navegador
# http://localhost:8080
# Usuario: admin  |  Contraseña: la definida en .env
```

> **¿Por qué no hay contraseña inicial?** La imagen está configurada con `JAVA_OPTS="-Djenkins.install.runSetupWizard=false"` y JCasC configura el usuario admin automáticamente desde las variables de entorno. No se genera `initialAdminPassword`.

### 2.3 Verificación de plugins

Después de iniciar sesión en Jenkins:

1. Ir a **Manage Jenkins → Plugins → Installed plugins**
2. Verificar que aparecen: Pipeline, Git, GitHub, Docker Pipeline, Configuration as Code

### 2.4 Verificación de credenciales

1. Ir a **Manage Jenkins → Credentials → System → Global credentials**
2. Deben aparecer las dos credenciales: `inventario-db-password` e `inventario-secret-key`
3. Los valores aparecen ocultos (****) — correcto comportamiento de seguridad

---

## 3. Pipeline como Código (Jenkinsfile)

El archivo `Jenkinsfile` en la raíz del repositorio define el pipeline completo en sintaxis Declarative.

### 3.1 Estructura del pipeline

```
Jenkinsfile
├── agent any
├── triggers { pollSCM('H/5 * * * *') }
├── environment { variables no-sensibles }
├── stages
│   ├── Checkout
│   ├── Build
│   └── Test
└── post
    ├── always  → logs + cleanup
    ├── success → mensaje confirmación
    └── failure → mensaje diagnóstico
```

### 3.2 Descripción de cada etapa

**Stage: Checkout**
```groovy
stage('Checkout') {
    steps {
        checkout scm                        // Clona el repo desde GitHub
        sh 'echo "Branch  : ${GIT_BRANCH}"' // Muestra rama activa
        sh 'echo "Commit  : ${GIT_COMMIT}"' // SHA del commit
        sh 'echo "Repo    : ${GIT_URL}"'    // URL del repositorio
    }
}
```

**Stage: Build**
```groovy
stage('Build') {
    steps {
        withCredentials([
            string(credentialsId: 'inventario-db-password', variable: 'DB_PASS'),
            string(credentialsId: 'inventario-secret-key',  variable: 'APP_SECRET')
        ]) {
            sh '...' // Crea .env con credenciales inyectadas desde Jenkins
        }
        sh 'docker compose build --no-cache' // Construye imagen app (Flask)
        // docker-compose también construye el servicio db (PostgreSQL)
    }
}
```

**Stage: Test**
```groovy
stage('Test') {
    steps {
        sh 'docker compose up -d --wait'  // Levanta app + db, espera healthchecks
        // Pruebas unitarias (DB mockeada, 6 casos)
        sh 'docker compose exec -T app python -m pytest tests/ -v --tb=short'
        // Pruebas de integración: verifica comunicación entre contenedores
        sh 'curl -f http://localhost:5000/health'
        sh 'curl -f -X POST http://localhost:5000/mensajes ...'
        sh 'curl -f http://localhost:5000/mensajes | grep jenkins-integration-test'
    }
}
```

**Bloque post**
```groovy
post {
    always  { sh 'docker compose logs > build-logs.txt'; archiveArtifacts ...; docker compose down -v; rm -f .env }
    success { echo "Pipeline exitoso — branch: ${env.GIT_BRANCH}" }
    failure { echo "Pipeline fallido. Revisar build-logs.txt" }
}
```

---

## 4. Integración con GitHub

### 4.1 Poll SCM (configurado)

El Jenkinsfile incluye un bloque `triggers` que activa el pipeline automáticamente:

```groovy
triggers {
    pollSCM('H/5 * * * *')  // Revisa el repo cada ~5 minutos
}
```

Formato cron: `H/5 * * * *` — el `H` distribuye la carga entre jobs para evitar picos simultáneos.

**Cómo funciona:**
1. Jenkins consulta `https://github.com/javier-lugo-agudelo/Proyecto_2_Semana_5` cada 5 minutos
2. Si detecta nuevos commits desde la última revisión, lanza un nuevo build
3. No se requiere configuración adicional en GitHub (no necesita acceso inbound al servidor)

### 4.2 Webhook (alternativa)

Para respuesta inmediata en lugar de polling:

1. En GitHub: **Settings → Webhooks → Add webhook**
   - Payload URL: `http://<IP-del-servidor>:8080/github-webhook/`
   - Content type: `application/json`
   - Events: `Just the push event`

2. En el job de Jenkins: el plugin GitHub detecta el webhook automáticamente si el pipeline usa `triggers { githubPush() }`.

> Ambas opciones (Poll SCM y webhook) tienen la misma calificación según las indicaciones del curso.

---

## 5. Construcción de los Contenedores

El pipeline construye **ambas imágenes** definidas en `docker-compose.yml`:

| Servicio | Imagen base | Construcción |
|---------|------------|-------------|
| `app` | `python:3.11-slim` | `docker compose build` → lee `app/Dockerfile` |
| `db` | `postgres:15` | Imagen oficial, descargada en `docker compose up` |

**Stage Build — detalle de la construcción:**

```bash
# El comando construye todos los servicios con Dockerfile
docker compose build --no-cache

# Resultado: imagen lista para el servicio app
# docker.io/library/python:3.11-slim → instalación de dependencias → copia código

# El servicio db usa imagen oficial postgres:15 (pulled en docker compose up)
```

El flag `--no-cache` garantiza que cada build en Jenkins sea limpio, evitando artefactos de builds anteriores.

---

## 6. Pruebas y Verificación Automática

### 6.1 Pruebas Unitarias (`app/tests/test_unit.py`)

Ejecutadas dentro del contenedor `app` con la base de datos **mockeada**:

```bash
docker compose exec -T app python -m pytest tests/ -v --tb=short
```

| Prueba | Ruta | Descripción |
|--------|------|-------------|
| `test_health_retorna_ok` | `GET /health` | Verifica respuesta 200 sin DB |
| `test_guardar_mensaje_exitoso` | `POST /mensajes` | Verifica 201 con mensaje creado |
| `test_guardar_mensaje_sin_contenido_retorna_400` | `POST /mensajes` | Verifica validación de entrada |
| `test_guardar_mensaje_contenido_vacio_retorna_400` | `POST /mensajes` | Verifica strip de espacios |
| `test_listar_mensajes_retorna_lista` | `GET /mensajes` | Verifica lista con 2 elementos |
| `test_listar_mensajes_db_vacia` | `GET /mensajes` | Verifica lista vacía |

Si alguna prueba falla, `pytest` retorna código de salida distinto de 0 → el stage falla → el build falla.

### 6.2 Pruebas de Integración

Verifican la **comunicación real entre los dos contenedores** (`app` ↔ `db`) por nombre de servicio Docker:

```bash
# 1. Health check del servicio app
curl -f http://localhost:5000/health
# Respuesta esperada: {"status": "ok", "servicio": "inventario-app"}

# 2. Escritura: app recibe mensaje y lo persiste en db
curl -f -X POST http://localhost:5000/mensajes \
    -H "Content-Type: application/json" \
    -d '{"contenido": "jenkins-integration-test"}'
# Respuesta esperada: {"id": 1, "contenido": "jenkins-integration-test", ...}

# 3. Lectura: app consulta db y retorna el mensaje guardado
RESPONSE=$(curl -f http://localhost:5000/mensajes)
echo "${RESPONSE}" | grep -q "jenkins-integration-test"
# Si grep no encuentra el texto → exit 1 → build falla
```

La prueba 3 confirma el flujo completo: `app → db (INSERT) → db (SELECT) → app`.

---

## 7. Evidencias de Ejecución

Jenkins corrió exitosamente con 5 builds ejecutados. A continuación la evidencia real capturada de la consola.

### 7.1 Historial de builds ejecutados

| Build | Resultado | Duración | Causa |
|-------|----------|----------|-------|
| #1 | FAILURE | 37 s | Contenedores huérfanos con `container_name` fijo |
| #2 | FAILURE | 40 s | Mismo conflicto en segunda rama de commits |
| #3 | **FAILURE** | 42 s | **Fallo intencional**: aserción `assert data["version"] == "2.0"` |
| #4 | FAILURE | 72 s | `curl` ejecutado en host Jenkins, fuera de la red Docker |
| #5 | **SUCCESS** | 40 s | **Build exitoso**: todos los fixes aplicados |

---

### 7.2 Consola — Build #3 (FALLO INTENCIONAL)

```
Started by user Administrador
Obtained Jenkinsfile from git https://github.com/javier-lugo-agudelo/Proyecto_2_Semana_5
[Pipeline] Start of Pipeline
[Pipeline] node
Running on Jenkins in /var/jenkins_home/workspace/inventario-pipeline
...
[Pipeline] stage
[Pipeline] { (Checkout)
Branch  : origin/master
Commit  : 7c8e851...
...
[Pipeline] stage
[Pipeline] { (Build)
Masking supported pattern matches of $DB_PASS or $APP_SECRET
+ echo DB_PASSWORD=****
+ echo SECRET_KEY=****
 Image inventario-jenkins-app Built
...
[Pipeline] stage
[Pipeline] { (Test)
 Container inventario-jenkins-db-1 Healthy
 Container inventario-jenkins-app-1 Healthy

--- Pruebas unitarias (DB mockeada) ---
+ docker compose exec -T app python -m pytest tests/ -v --tb=short

============================= test session starts ==============================
platform linux -- Python 3.11.18, pytest-8.3.4

tests/test_unit.py::test_health_retorna_ok FAILED                        [ 16%]
tests/test_unit.py::test_guardar_mensaje_exitoso PASSED                  [ 33%]
tests/test_unit.py::test_guardar_mensaje_sin_contenido_retorna_400 PASSED [ 50%]
tests/test_unit.py::test_guardar_mensaje_contenido_vacio_retorna_400 PASSED [ 66%]
tests/test_unit.py::test_listar_mensajes_retorna_lista PASSED            [ 83%]
tests/test_unit.py::test_listar_mensajes_db_vacia PASSED                 [100%]

=================================== FAILURES ===================================
____________________________ test_health_retorna_ok ____________________________

    assert data["version"] == "2.0"
E   KeyError: 'version'

FAILED tests/test_unit.py::test_health_retorna_ok - KeyError: 'version'
========================= 1 failed, 5 passed in 0.17s ==========================

ERROR: script returned exit code 1
Finished: FAILURE
```

**Análisis:** La prueba `test_health_retorna_ok` falló porque el endpoint `/health` no retorna un campo `version`. El pipeline detectó el fallo y abortó correctamente el build.

---

### 7.3 Consola — Build #5 (SUCCESS)

```
Started by user Administrador
Obtained Jenkinsfile from git https://github.com/javier-lugo-agudelo/Proyecto_2_Semana_5
[Pipeline] Start of Pipeline
[Pipeline] node
Running on Jenkins in /var/jenkins_home/workspace/inventario-pipeline

[Pipeline] stage (Checkout)
Branch  : origin/master
Commit  : c2692f0e0d07e605ebb400fa197162f28b42f7dc
Repo    : https://github.com/javier-lugo-agudelo/Proyecto_2_Semana_5

[Pipeline] stage (Build)
Masking supported pattern matches of $DB_PASS or $APP_SECRET
+ echo DB_NAME=inventario_db
+ echo DB_USER=inventario_user
+ echo DB_PASSWORD=****
+ echo DB_PORT=5432
+ echo POSTGRES_DB=inventario_db
+ echo POSTGRES_USER=inventario_user
+ echo POSTGRES_PASSWORD=****
+ echo SECRET_KEY=****

+ docker compose build --no-cache
 Image inventario-jenkins-app Building
[...]
Successfully installed Jinja2-3.1.6 MarkupSafe-3.0.4 Werkzeug-3.1.9 blinker-1.9.0
click-8.5.1 flask-3.0.3 iniconfig-2.3.1 itsdangerous-2.2.0 pluggy-1.7.0
psycopg2-binary-2.9.9 pytest-8.3.4
 Image inventario-jenkins-app Built

[Pipeline] stage (Test)
+ docker compose down -v --remove-orphans
+ docker compose up -d --wait
 Network inventario-jenkins_proyecto_net Created
 Container inventario-jenkins-db-1 Created
 Container inventario-jenkins-app-1 Created
 Container inventario-jenkins-db-1 Healthy
 Container inventario-jenkins-app-1 Healthy

--- Pruebas unitarias (DB mockeada) ---
+ docker compose exec -T app python -m pytest tests/ -v --tb=short

============================= test session starts ==============================
platform linux -- Python 3.11.18, pytest-8.3.4, pluggy-1.7.0
rootdir: /app
collected 6 items

tests/test_unit.py::test_health_retorna_ok PASSED                        [ 16%]
tests/test_unit.py::test_guardar_mensaje_exitoso PASSED                  [ 33%]
tests/test_unit.py::test_guardar_mensaje_sin_contenido_retorna_400 PASSED [ 50%]
tests/test_unit.py::test_guardar_mensaje_contenido_vacio_retorna_400 PASSED [ 66%]
tests/test_unit.py::test_listar_mensajes_retorna_lista PASSED            [ 83%]
tests/test_unit.py::test_listar_mensajes_db_vacia PASSED                 [100%]

============================== 6 passed in 0.13s ===============================

--- Pruebas de integración: comunicación entre contenedores ---
=== Health check ===
+ docker compose exec -T app curl -sf http://localhost:5000/health
{"servicio":"inventario-app","status":"ok"}

=== POST /mensajes: app escribe en db ===
+ docker compose exec -T app curl -sf -X POST http://localhost:5000/mensajes \
    -H "Content-Type: application/json" \
    -d '{"contenido": "jenkins-integration-test"}'
{"contenido":"jenkins-integration-test","creado_en":"Wed, 25 Nov 2026 01:43:18 GMT","id":1}

=== GET /mensajes: app lee desde db ===
+ RESPONSE=[{"contenido":"jenkins-integration-test","creado_en":"Wed, 25 Nov 2026 01:43:18 GMT","id":1}]
+ grep -q jenkins-integration-test
+ echo Comunicacion app -> db -> app: OK
Comunicacion app -> db -> app: OK

[Pipeline] post { always }
+ docker compose logs --no-color   [archivado en build-logs.txt]
+ docker compose down -v
 Container inventario-jenkins-app-1 Removed
 Container inventario-jenkins-db-1 Removed
 Volume inventario-jenkins_postgres_data Removed
 Network inventario-jenkins_proyecto_net Removed
+ rm -f .env

Pipeline exitoso — branch: origin/master | commit: c2692f0e0d07e605ebb400fa197162f28b42f7dc

Finished: SUCCESS
```

### 7.4 Verificación de credenciales (Jenkins Credentials Store)

Las credenciales se crearon automáticamente vía JCasC al iniciar Jenkins:
- `inventario-db-password` — Secret text (valor oculto ***)
- `inventario-secret-key` — Secret text (valor oculto ***)

En la consola del build se confirma el enmascaramiento:
```
Masking supported pattern matches of $DB_PASS or $APP_SECRET
+ echo DB_PASSWORD=****
+ echo POSTGRES_PASSWORD=****
+ echo SECRET_KEY=****
```

### 7.5 Verificación de plugins instalados

Plugins pre-instalados en la imagen (`jenkins/plugins.txt`):
```
workflow-aggregator   ← Pipeline Declarativo
git                   ← Integración Git
github                ← Integración GitHub
docker-workflow       ← Docker Pipeline steps
configuration-as-code ← JCasC
job-dsl               ← Creación automática de jobs
pipeline-stage-view   ← Vista de etapas
```

> **Nota para capturas adicionales:** Acceder a `http://localhost:8080` con usuario `admin` para tomar capturas de pantalla de la interfaz Stage View, Build History y Credentials Manager.

---

## 8. Diagrama del Flujo CI/CD

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO CI/CD COMPLETO                         │
└─────────────────────────────────────────────────────────────────┘

  Desarrollador
       │
       │  git commit + git push
       ▼
  ┌─────────────┐
  │   GitHub    │  https://github.com/javier-lugo-agudelo/
  │ repositorio │  Proyecto_1_Escenario_3
  └──────┬──────┘
         │
         │  Poll SCM cada 5 min (o webhook)
         │  Jenkins detecta nuevo commit
         ▼
  ┌─────────────────────────────────────────────┐
  │            JENKINS  :8080                   │
  │                                             │
  │  ┌─────────────────────────────────────┐    │
  │  │  Stage 1: Checkout                  │    │
  │  │  • checkout scm (git clone/pull)    │    │
  │  │  • muestra branch, commit, repo URL │    │
  │  └──────────────┬──────────────────────┘    │
  │                 │                           │
  │  ┌──────────────▼──────────────────────┐    │
  │  │  Stage 2: Build                     │    │
  │  │  • inyecta credenciales desde Store │    │
  │  │  • crea .env (sin secrets en código)│    │
  │  │  • docker compose build --no-cache  │    │
  │  │    ├── imagen app (python:3.11-slim)│    │
  │  │    └── imagen db (postgres:15)      │    │
  │  └──────────────┬──────────────────────┘    │
  │                 │                           │
  │  ┌──────────────▼──────────────────────┐    │
  │  │  Stage 3: Test                      │    │
  │  │  • docker compose up -d --wait      │    │
  │  │    ├── contenedor db (PostgreSQL)   │    │
  │  │    └── contenedor app (Flask)       │    │
  │  │  • pytest (6 pruebas unitarias)     │    │
  │  │  • curl /health ✓                   │    │
  │  │  • curl POST /mensajes ✓            │    │
  │  │  • curl GET /mensajes → grep ✓      │    │
  │  └──────────────┬──────────────────────┘    │
  │                 │                           │
  │  ┌──────────────▼──────────────────────┐    │
  │  │  post { always }                    │    │
  │  │  • guarda build-logs.txt            │    │
  │  │  • docker compose down -v           │    │
  │  │  • elimina .env del workspace       │    │
  │  └─────────────────────────────────────┘    │
  └─────────────────────────────────────────────┘
         │                   │
         ▼                   ▼
    BUILD SUCCESS       BUILD FAILURE
    (stage view verde)  (stage view rojo)
```

---

## 9. Conclusiones

La implementación de Jenkins como herramienta de CI/CD sobre el sistema de inventarios existente permitió validar en la práctica los principios de integración continua estudiados en clase.

**Hallazgos principales:**

1. **Configuración como código (JCasC):** Declarar la configuración de Jenkins en `casc.yaml` eliminó la dependencia de pasos manuales en la interfaz web. Cualquier reinstalación del servidor reproduce exactamente el mismo estado, lo cual es esencial para equipos que trabajan en paralelo.

2. **Separación de secretos:** La combinación de `withCredentials` en el Jenkinsfile y el Credentials Store de Jenkins garantiza que las contraseñas nunca aparezcan en logs ni en el repositorio. Este patrón es directamente aplicable en entornos de producción.

3. **Estrategia de pruebas en dos niveles:** Las pruebas unitarias con mocking confirman la lógica de negocio independientemente de la infraestructura; las pruebas de integración con `curl` verifican que los contenedores se comunican correctamente por nombre de servicio Docker, que es el comportamiento crítico del sistema.

4. **Poll SCM vs. Webhook:** Poll SCM fue suficiente para este proyecto y no requiere que el servidor Jenkins sea accesible desde internet. En proyectos con repositorios privados en redes corporativas, esta es frecuentemente la única opción viable.

5. **Docker-out-of-Docker (DooD):** Montar el socket `/var/run/docker.sock` permite que el pipeline controle el Docker daemon del host. Esto es más eficiente que Docker-in-Docker (DinD) y evita problemas de privilegios anidados, aunque requiere otorgar permisos de socket al contenedor Jenkins.

---

## 10. Referencias

American Psychological Association (APA, 7.ª edición):

Jenkins. (2024). *Jenkins documentation: Pipeline*. https://www.jenkins.io/doc/book/pipeline/

Jenkins. (2024). *Configuration as Code plugin*. https://www.jenkins.io/projects/jcasc/

Docker Inc. (2024). *Docker Compose overview*. https://docs.docker.com/compose/

Python Software Foundation. (2024). *pytest documentation*. https://docs.pytest.org/en/stable/

Pallets Projects. (2024). *Flask documentation*. https://flask.palletsprojects.com/

The PostgreSQL Global Development Group. (2024). *PostgreSQL 15 documentation*. https://www.postgresql.org/docs/15/

Fowler, M. (2006). *Continuous integration*. https://martinfowler.com/articles/continuousIntegration.html

GitHub Inc. (2024). *About webhooks*. https://docs.github.com/en/webhooks/about-webhooks
