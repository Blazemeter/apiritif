@Library('jenkins_library@virtualenv') _
pipeline {
    agent {
        docker {
            label 'generalNodes'
            image 'us.gcr.io/verdant-bulwark-278/jenkins-docker-agent:master.latest'
        }
    }
    stages {
        stage('Install') {
            steps {
                venv "pip install -r requirements.txt"
                venv "pip install codecov nose-exclude nose-timer \"pluggy>=1.0\""
            }
        }
        stage('Code coverage') {
            steps {
                venv "coverage run --source=apiritif -m nose2 -s tests/unit -v"
            }
        }
    }
    post {
        success {
            venv "codecov"
        }
        always {
            cleanWs()
        }
    }
}