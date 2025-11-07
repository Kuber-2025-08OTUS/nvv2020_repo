#!/bin/bash

for i in {0..0}; do
  kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-kafka-dev-controller-${i}
  namespace: dev
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 2Gi
  storageClassName: nfs-storage
  volumeName: nfs-kafka-dev-pv-${i}
EOF
done