
pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                echo 'Repository checkout completed.'
            }
        }

        stage('Build') {
            steps {
                bat '''
                    @echo off
                    if not exist server.py exit /b 1
                    if not exist test.py exit /b 1
                    if not exist public\\index.html exit /b 1
                    if not exist public\\style.css exit /b 1
                    if not exist public\\script.js exit /b 1
                    if not exist public\\registrations.html exit /b 1
                    if not exist public\\registrations.js exit /b 1

                    echo Found: server.py
                    echo Found: test.py
                    echo Found: public\\index.html
                    echo Found: public\\style.css
                    echo Found: public\\script.js
                    echo Found: public\\registrations.html
                    echo Found: public\\registrations.js
                '''
            }
        }

        stage('Test') {
            steps {
                bat 'python test.py'
            }
        }
    }

    post {
        success {
            echo 'College Registration CI: SUCCESS'
        }
        failure {
            echo 'College Registration CI: FAILED'
        }
    }
}
