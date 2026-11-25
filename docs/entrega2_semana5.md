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

> Las siguientes capturas deben tomarse durante la ejecución real de Jenkins.

### 7.1 Jenkins funcionando con plugins instalados

**[Captura: Manage Jenkins → Plugins → Installed plugins]**
- Mostrar: Pipeline, Git, GitHub, Docker Pipeline, Configuration as Code, Job DSL, Pipeline Stage View

### 7.2 Credenciales guardadas en Jenkins

**[Captura: Manage Jenkins → Credentials → System → Global credentials]**
- Mostrar: `inventario-db-password` y `inventario-secret-key` con tipo "Secret text"
- Los valores deben aparecer ocultos (***)

### 7.3 Vista de etapas — Build exitoso

**[Captura: inventario-pipeline → Build #N → Stage View]**
- Mostrar las 3 etapas: Checkout ✓ | Build ✓ | Test ✓
- Tiempo de ejecución de cada etapa

### 7.4 Salida de consola — Build exitoso

**[Captura: inventario-pipeline → Build #N → Console Output]**
- Mostrar líneas clave:
  ```
  Branch  : origin/master
  Commit  : <SHA>
  ...
  docker compose build --no-cache
  ...
  PASSED tests/test_unit.py::test_health_retorna_ok
  PASSED tests/test_unit.py::test_guardar_mensaje_exitoso
  ...
  6 passed in X.XXs
  ...
  Comunicacion app -> db -> app: OK
  ...
  Finished: SUCCESS
  ```

### 7.5 Build fallido (ejemplo con error intencional)

**[Captura: Console Output de un build fallido]**
- Ejemplo: modificar una prueba para que falle, hacer push, ver el build rojo
- Stage View mostrando la etapa roja: Test ✗

### 7.6 Build que corrige el fallo

**[Captura: Console Output del build corregido]**
- Revertir el cambio, hacer push, ver el build verde nuevamente
- Historial mostrando: Build #N (rojo) → Build #N+1 (verde)

### 7.7 Historial de builds

**[Captura: inventario-pipeline → Build History]**
- Mostrar al menos 3 builds con íconos de estado (verde/rojo/verde)
- Timestamps y duraciones

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
