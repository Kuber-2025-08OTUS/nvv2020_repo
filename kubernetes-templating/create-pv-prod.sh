#!/bin/bash

for i in {0..4}; do
  kubectl apply -f - <<EOF
apiVersion: v1
kind: PersistentVolume
metadata:
  name: nfs-kafka-pv-${i}
  namespace: prod
spec:
  capacity:
    storage: 3Gi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteMany
  persistentVolumeReclaimPolicy: Retain
  storageClassName: nfs-storage
  nfs:
    server: 192.168.1.59
    path: "/data/kafka/broker-${i}"
    readOnly: false
EOF
done