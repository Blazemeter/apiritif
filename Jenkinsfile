@Library('jenkins_library') _
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
                sh "pip install -r requirements.txt"
                sh "pip install codecov nose-exclude nose-timer \"pluggy>=1.0\""
            }
        }
        stage('Code coverage') {
            steps {
                sh "coverage run --source=apiritif -m nose2 -s tests/unit -v"
            }
        }
        post {
            success {
                sh "codecov"
            }
        }
    }
}