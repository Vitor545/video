pipeline {
  agent {
    kubernetes {
      yaml """
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins
  containers:
  - name: docker
    image: docker:24.0.5-dind
    securityContext:
      privileged: true
    args: ["--mtu=1400"]
  - name: helm-kubectl
    image: dtzar/helm-kubectl:3
    command: ['sleep']
    args: ['99d']
"""
    }
  }

  environment {
    REGISTRY            = "docker.vitorsouzadasilva.tech"
    BACKEND_IMAGE       = "vitorsouzadasilva/video-backend"
    FRONTEND_IMAGE      = "vitorsouzadasilva/video-frontend"
    IMAGE_TAG           = "${env.BUILD_NUMBER}"
    KUBE_NAMESPACE      = "video"
    HELM_RELEASE        = "video-app"
    HELM_CHART_DIR      = "deploy/helm/video-app"
    APP_DOMAIN          = "video.vitorsouzadasilva.tech"
  }

  stages {
    stage("Checkout") {
      steps {
        checkout scm
      }
    }

    stage("Build imagens") {
      steps {
        container('docker') {
          sh '''
            docker build -t $REGISTRY/$BACKEND_IMAGE:$IMAGE_TAG -t $REGISTRY/$BACKEND_IMAGE:latest ./backend
            docker build -t $REGISTRY/$FRONTEND_IMAGE:$IMAGE_TAG -t $REGISTRY/$FRONTEND_IMAGE:latest ./frontend
          '''
        }
      }
    }

    stage("Push imagens") {
      steps {
        withCredentials([usernamePassword(credentialsId: "docker-registry", usernameVariable: "REGISTRY_USER", passwordVariable: "REGISTRY_PASSWORD")]) {
          container('docker') {
            sh '''
              echo $REGISTRY_PASSWORD | docker login -u $REGISTRY_USER --password-stdin $REGISTRY
              docker push $REGISTRY/$BACKEND_IMAGE:$IMAGE_TAG
              docker push $REGISTRY/$BACKEND_IMAGE:latest
              docker push $REGISTRY/$FRONTEND_IMAGE:$IMAGE_TAG
              docker push $REGISTRY/$FRONTEND_IMAGE:latest
            '''
          }
        }
      }
    }

    stage("Deploy via Helm") {
      steps {
        withCredentials([file(credentialsId: "video-app-values", variable: "SECRET_VALUES")]) {
          container('helm-kubectl') {
            sh '''
              helm upgrade --install $HELM_RELEASE $HELM_CHART_DIR \
                --namespace $KUBE_NAMESPACE \
                --create-namespace \
                --values $HELM_CHART_DIR/values.yaml \
                --values $SECRET_VALUES \
                --set image.tag=$IMAGE_TAG \
                --set ingress.host=$APP_DOMAIN \
                --wait --timeout 10m

              kubectl rollout status deployment/video-backend -n $KUBE_NAMESPACE --timeout=5m
              kubectl rollout status deployment/video-frontend -n $KUBE_NAMESPACE --timeout=3m
            '''
          }
        }
      }
    }
  }

  post {
    failure {
      container('helm-kubectl') {
        sh '''
          echo "=== Pods ==="
          kubectl get pods -n $KUBE_NAMESPACE -o wide || true
          echo "=== Eventos ==="
          kubectl get events -n $KUBE_NAMESPACE --sort-by=.lastTimestamp | tail -50 || true
          echo "=== Logs backend ==="
          kubectl logs -n $KUBE_NAMESPACE deployment/video-backend --tail=200 || true
          echo "=== Logs frontend ==="
          kubectl logs -n $KUBE_NAMESPACE deployment/video-frontend --tail=100 || true
        '''
      }
    }
  }
}
