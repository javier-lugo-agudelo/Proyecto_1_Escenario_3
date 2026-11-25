pipeline {
    agent any

    // Disparo automático: revisa GitHub cada 5 minutos.
    // También se puede usar webhook desde GitHub → Jenkins (puerto 8080).
    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        COMPOSE_PROJECT_NAME = 'inventario-jenkins'
        DB_NAME        = 'inventario_db'
        DB_USER        = 'inventario_user'
        DB_PORT        = '5432'
        POSTGRES_DB    = 'inventario_db'
        POSTGRES_USER  = 'inventario_user'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                sh 'echo "Branch  : ${GIT_BRANCH}"'
                sh 'echo "Commit  : ${GIT_COMMIT}"'
                sh 'echo "Repo    : ${GIT_URL}"'
            }
        }

        stage('Build') {
            steps {
                // Las credenciales se inyectan desde Jenkins Credentials Store.
                // Nunca se escriben directamente en el Jenkinsfile.
                withCredentials([
                    string(credentialsId: 'inventario-db-password', variable: 'DB_PASS'),
                    string(credentialsId: 'inventario-secret-key',  variable: 'APP_SECRET')
                ]) {
                    sh '''
                        echo "DB_NAME=${DB_NAME}"              > .env
                        echo "DB_USER=${DB_USER}"             >> .env
                        echo "DB_PASSWORD=${DB_PASS}"         >> .env
                        echo "DB_PORT=${DB_PORT}"             >> .env
                        echo "POSTGRES_DB=${POSTGRES_DB}"     >> .env
                        echo "POSTGRES_USER=${POSTGRES_USER}" >> .env
                        echo "POSTGRES_PASSWORD=${DB_PASS}"   >> .env
                        echo "SECRET_KEY=${APP_SECRET}"       >> .env
                    '''
                }
                sh 'docker compose build --no-cache'
            }
        }

        stage('Test') {
            steps {
                // Limpiar entorno previo antes de levantar servicios
                sh 'docker compose down -v --remove-orphans || true'
                // Levantar ambos contenedores y esperar healthchecks
                sh 'docker compose up -d --wait'

                echo '--- Pruebas unitarias (DB mockeada) ---'
                sh 'docker compose exec -T app python -m pytest tests/ -v --tb=short'

                echo '--- Pruebas de integración: comunicación entre contenedores ---'
                // Los curls corren DENTRO del contenedor app (misma red Docker)
                sh '''
                    echo "=== Health check ==="
                    docker compose exec -T app curl -sf http://localhost:5000/health

                    echo "=== POST /mensajes: app escribe en db ==="
                    docker compose exec -T app curl -sf -X POST http://localhost:5000/mensajes \
                        -H "Content-Type: application/json" \
                        -d '{"contenido": "jenkins-integration-test"}'

                    echo "=== GET /mensajes: app lee desde db ==="
                    RESPONSE=$(docker compose exec -T app curl -sf http://localhost:5000/mensajes)
                    echo "${RESPONSE}"
                    echo "${RESPONSE}" | grep -q "jenkins-integration-test" \
                        && echo "Comunicacion app -> db -> app: OK" \
                        || (echo "ERROR: mensaje no encontrado en la respuesta" && exit 1)
                '''
            }
        }
    }

    post {
        always {
            sh 'docker compose logs --no-color > build-logs.txt 2>&1 || true'
            archiveArtifacts artifacts: 'build-logs.txt', allowEmptyArchive: true
            sh 'docker compose down -v || true'
            sh 'rm -f .env || true'
        }
        success {
            echo "Pipeline exitoso — branch: ${env.GIT_BRANCH} | commit: ${env.GIT_COMMIT}"
        }
        failure {
            echo "Pipeline fallido. Revisar build-logs.txt o la vista de etapas en Jenkins."
        }
    }
}
