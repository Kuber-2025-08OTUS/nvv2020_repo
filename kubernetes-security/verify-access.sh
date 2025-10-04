#!/bin/bash

set -x

KUBECONFIG_FILE="cd-kubeconfig"
NAMESPACE="homework"
OTHER_NAMESPACE="default"

echo "🔍 Verifying access for ServiceAccount cd"

echo ""
echo "1. Testing access in namespace $NAMESPACE (should have admin access):"
echo "=========================================="

# Проверяем различные права в homework namespace
COMMANDS=(
    "get pods"
    "create pods"
    "delete pods"
    "get secrets"
    "create secrets"
    "get deployments"
    "create deployments"
    "delete deployments"
    "get services"
    "create services"
)

for cmd in "${COMMANDS[@]}"; do
    if kubectl --kubeconfig=$KUBECONFIG_FILE auth can-i $cmd --namespace=$NAMESPACE > /dev/null 2>&1; then
        echo "✅ Can $cmd in $NAMESPACE"
    else
        echo "❌ Cannot $cmd in $NAMESPACE"
    fi
done

echo ""
echo "2. Testing access in other namespace $OTHER_NAMESPACE (should have NO access):"
echo "=========================================="

for cmd in "${COMMANDS[@]}"; do
    if kubectl --kubeconfig=$KUBECONFIG_FILE auth can-i $cmd --namespace=$OTHER_NAMESPACE > /dev/null 2>&1; then
        echo "❌ CAN $cmd in $OTHER_NAMESPACE (this should not happen!)"
    else
        echo "✅ Cannot $cmd in $OTHER_NAMESPACE (expected)"
    fi
done

echo ""
echo "3. Testing actual resource operations:"
echo "=========================================="

# Пробуем создать простой ресурс в homework
echo "📝 Creating test configmap in $NAMESPACE..."
kubectl --kubeconfig=$KUBECONFIG_FILE create configmap test-cm --from-literal=test=value -n $NAMESPACE

if [ $? -eq 0 ]; then
    echo "✅ Successfully created configmap in $NAMESPACE"
    # Удаляем тестовый ресурс
    kubectl --kubeconfig=$KUBECONFIG_FILE delete configmap test-cm -n $NAMESPACE
    echo "✅ Successfully deleted configmap from $NAMESPACE"
else
    echo "❌ Failed to create configmap in $NAMESPACE"
fi

echo ""
echo "4. Testing access denial in other namespaces:"
echo "=========================================="

# Пробуем создать ресурс в другом namespace
echo "📝 Trying to create configmap in $OTHER_NAMESPACE (should fail)..."
kubectl --kubeconfig=$KUBECONFIG_FILE create configmap test-cm --from-literal=test=value -n $OTHER_NAMESPACE 2>/dev/null

if [ $? -eq 0 ]; then
    echo "❌ UNEXPECTED: Created configmap in $OTHER_NAMESPACE"
    # Очищаем если создалось (хотя не должно)
    kubectl --kubeconfig=$KUBECONFIG_FILE delete configmap test-cm -n $OTHER_NAMESPACE 2>/dev/null
else
    echo "✅ Correctly denied creating configmap in $OTHER_NAMESPACE"
fi

echo ""
echo "🎉 Verification complete!"