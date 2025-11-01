FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY mysql-operator.py .
ENV NFS_SERVER="192.168.1.59"
ENV NFS_BASE_PATH="/data/mysql"
ENV STORAGE_CLASS_NAME="nfs-storage"
CMD ["kopf", "run", "mysql-operator.py", "--all-namespaces", "--verbose"]