// Jenkins pipeline for the CampusConnect registration site.
// Needs a Linux agent with python3 (3.8+) and curl. Node.js is optional: if it is
// installed, the browser scripts are syntax-checked too. Nothing else to install.
//
// To run in a container instead of on the agent (needs the Docker Pipeline plugin),
// replace `agent any` with:
//   agent { docker { image 'python:3.12-slim' } }
// and drop the curl-dependent smoke test or use an image that includes curl.

pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 15, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '5'))
    }

    environment {
        PYTHONDONTWRITEBYTECODE = '1'
        PYTHONUNBUFFERED        = '1'
        SMOKE_PORT              = '8765'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Check tools') {
            steps {
                sh '''
                    python3 --version
                    curl --version | head -n 1
                    if command -v node >/dev/null 2>&1; then node --version; else echo "node not installed: skipping JavaScript syntax checks"; fi
                '''
            }
        }

        stage('Syntax check') {
            parallel {
                stage('Python') {
                    steps {
                        sh 'python3 -m py_compile server.py test.py'
                    }
                }
                stage('JavaScript') {
                    steps {
                        sh '''
                            if command -v node >/dev/null 2>&1; then
                                for f in public/*.js; do
                                    echo "checking $f"
                                    node --check "$f"
                                done
                            else
                                echo "node not installed: skipped"
                            fi
                        '''
                    }
                }
            }
        }

        stage('Test') {
            steps {
                // test.py starts the real server on a free port with a temporary database.
                sh 'python3 test.py'
            }
        }

        stage('Smoke test') {
            steps {
                // Start the server the way a person would, and check the main pages answer.
                sh '''
                    set -eu
                    export REG_DB="$WORKSPACE/.smoke-test.db"
                    rm -f "$REG_DB"
                    python3 server.py --port "$SMOKE_PORT" > smoke-server.log 2>&1 &
                    SERVER_PID=$!
                    trap 'kill $SERVER_PID 2>/dev/null || true; rm -f "$REG_DB"' EXIT

                    base="http://127.0.0.1:$SMOKE_PORT"
                    for i in $(seq 1 20); do
                        if curl -fsS "$base/api/health" >/dev/null 2>&1; then break; fi
                        sleep 0.5
                    done

                    curl -fsS "$base/api/health"; echo
                    curl -fsS "$base/" | grep -q "Student registration"
                    curl -fsS "$base/registrations" | grep -q "<title>Registrations</title>"
                    curl -fsS "$base/style.css" >/dev/null
                    curl -fsS "$base/script.js" >/dev/null
                    echo "smoke test passed"
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'smoke-server.log', allowEmptyArchive: true
                }
            }
        }

        stage('Package') {
            steps {
                sh '''
                    set -eu
                    mkdir -p dist
                    out="dist/campus-registration-${BUILD_NUMBER}.zip"
                    rm -f "$out"
                    python3 -m zipfile -c "$out" server.py test.py README.md Jenkinsfile public
                    python3 -m zipfile -l "$out"
                '''
            }
        }
    }

    post {
        success {
            archiveArtifacts artifacts: 'dist/*.zip', fingerprint: true
            echo 'Build passed. The packaged site is in the build artifacts.'
        }
        failure {
            echo 'Build failed. Check the stage logs above.'
        }
        cleanup {
            cleanWs()
        }
    }
}
