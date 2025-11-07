#!/bin/bash

for i in {0..4}; do
  kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-kafka-prod-controller-${i}
  namespace: prod
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 2Gi
  storageClassName: nfs-storage
  volumeName: nfs-kafka-pv-${i}
EOF
done