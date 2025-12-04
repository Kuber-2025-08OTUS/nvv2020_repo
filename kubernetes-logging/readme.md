kubectl label nodes kubemaster1 kubemaster2 kubemaster3 node-role=infra
kubectl taint nodes kubemaster1 kubemaster2 kubemaster3 node-role=infra:NoSchedule
kubectl apply -f 0_ns.yaml
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update


helm upgrade --install loki grafana/loki --namespace logging

cat > loki-stack-values.yaml << EOF
...
EOF
helm upgrade --install loki-stack grafana/loki-stack --namespace logging --values loki-stack-values.yaml




# helm upgrade --install loki grafana/loki --namespace logging
# helm upgrade --install promtail grafana/promtail --namespace logging --set "loki.serviceName=loki"
# helm upgrade --install grafana grafana/grafana --namespace logging