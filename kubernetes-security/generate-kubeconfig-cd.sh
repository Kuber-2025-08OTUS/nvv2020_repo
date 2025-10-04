#!/bin/bash

set -x

NAMESPACE="homework"
SERVICE_ACCOUNT="cd"
TOKEN_FILE="token"
KUBECONFIG_FILE="cd-kubeconfig"
TOKEN_DURATION="24h"

echo "🔧 Setting up ServiceAccount $SERVICE_ACCOUNT in namespace $NAMESPACE"

# Проверяем, существует ли namespace
if ! kubectl get namespace $NAMESPACE > /dev/null 2>&1; then
    echo "❌ Namespace $NAMESPACE does not exist. Please create it first."
    exit 1
fi

# Проверяем, существует ли ServiceAccount
if ! kubectl get serviceaccount $SERVICE_ACCOUNT -n $NAMESPACE > /dev/null 2>&1; then
    echo "❌ ServiceAccount $SERVICE_ACCOUNT does not exist in namespace $NAMESPACE. Please create it first."
    exit 1
fi

echo "✅ Namespace and ServiceAccount exist"

# Получаем текущий контекст кластера
CLUSTER_NAME=$(kubectl config view --minify -o jsonpath='{.clusters[0].name}')
APISERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')

if [ -z "$CLUSTER_NAME" ] || [ -z "$APISERVER" ]; then
    echo "❌ Cannot determine cluster name or API server"
    exit 1
fi

echo "📝 Cluster: $CLUSTER_NAME"
echo "🌐 API Server: $APISERVER"

# Извлекаем CA сертификат
echo "📄 Extracting CA certificate..."
kubectl get secret $SERVICE_ACCOUNT-token -n $NAMESPACE -o jsonpath='{.data.ca\.crt}' | base64 --decode > ca.crt

# Получаем токен
echo "🔑 Extracting token..."
TOKEN=$(kubectl get secret $SERVICE_ACCOUNT-token -n $NAMESPACE -o jsonpath='{.data.token}' | base64 --decode)

# Сохраняем токен в файл
echo "$TOKEN" > $TOKEN_FILE
echo "✅ Token saved to $TOKEN_FILE"

# Создаем kubeconfig
echo "🛠️ Creating kubeconfig..."
kubectl config set-cluster $CLUSTER_NAME \
  --certificate-authority=ca.crt \
  --server=$APISERVER \
  --kubeconfig=$KUBECONFIG_FILE

kubectl config set-credentials $SERVICE_ACCOUNT \
  --token=$TOKEN \
  --kubeconfig=$KUBECONFIG_FILE

kubectl config set-context $SERVICE_ACCOUNT-context \
  --cluster=$CLUSTER_NAME \
  --user=$SERVICE_ACCOUNT \
  --namespace=$NAMESPACE \
  --kubeconfig=$KUBECONFIG_FILE

kubectl config use-context $SERVICE_ACCOUNT-context \
  --kubeconfig=$KUBECONFIG_FILE

echo "✅ Kubeconfig saved to $KUBECONFIG_FILE"
echo "📋 Verification commands:"
echo "  kubectl --kubeconfig=$KUBECONFIG_FILE get pods"
echo "  kubectl --kubeconfig=$KUBECONFIG_FILE auth can-i '*' '*'"