import kopf
import kubernetes.client
from kubernetes.client import V1Deployment, V1Service, V1PersistentVolumeClaim, V1PersistentVolume
from kubernetes.client import V1ObjectMeta, V1DeploymentSpec, V1PodTemplateSpec
from kubernetes.client import V1PodSpec, V1Container, V1EnvVar, V1Volume, V1PersistentVolumeClaimVolumeSource
from kubernetes.client import V1VolumeMount, V1ContainerPort, V1ServiceSpec, V1ServicePort
from kubernetes.client import V1DeploymentStrategy, V1RollingUpdateDeployment
from kubernetes.client import V1NFSVolumeSource
from kubernetes.config import load_incluster_config, load_kube_config
from kubernetes.client.rest import ApiException
import os

# Инициализация Kubernetes клиента
try:
    load_incluster_config()
except:
    load_kube_config()

api = kubernetes.client.AppsV1Api()
core_api = kubernetes.client.CoreV1Api()

# Получаем настройки NFS из environment variables
NFS_SERVER = os.getenv('NFS_SERVER', '192.168.1.59')  # default значение
NFS_BASE_PATH = os.getenv('NFS_BASE_PATH', '/data/mysql')
STORAGE_CLASS_NAME = os.getenv('STORAGE_CLASS_NAME', 'nfs-storage')

@kopf.on.create('otus.homework', 'v1', 'mysqls')
async def create_mysql_instance(body, spec, name, namespace, logger, **kwargs):
    """Создание инстанса MySQL при создании кастомного ресурса"""

    # Получаем параметры из spec
    image = spec.get('image', 'mysql:8.0')
    database = spec.get('database')
    password = spec.get('password')
    storage_size = spec.get('storage_size', '1Gi')

    if not database or not password:
        raise kopf.PermanentError("Database name and password are required")

    # Логируем используемые настройки NFS
    logger.info(f"Using NFS server: {NFS_SERVER}, base path: {NFS_BASE_PATH}")

    # Создаем PersistentVolume
    pv_manifest = V1PersistentVolume(
        metadata=V1ObjectMeta(
            name=f"mysql-pv-{name}",
            labels={"app": "mysql", "instance": name}
        ),
        spec={
            "capacity": {
                "storage": storage_size
            },
            "volumeMode": "Filesystem",
            "accessModes": ["ReadWriteOnce"],
            "persistentVolumeReclaimPolicy": "Retain",
            "storageClassName": STORAGE_CLASS_NAME,
            "nfs": {
                "server": NFS_SERVER,
                "path": f"{NFS_BASE_PATH}/{name}",  # Создаем отдельную папку для каждого инстанса
                "readOnly": False
            }
        }
    )

    # Создаем PersistentVolumeClaim
    pvc_manifest = V1PersistentVolumeClaim(
        metadata=V1ObjectMeta(
            name=f"mysql-pvc-{name}",
            namespace=namespace,
            labels={"app": "mysql", "instance": name}
        ),
        spec={
            "accessModes": ["ReadWriteOnce"],
            "resources": {
                "requests": {
                    "storage": storage_size
                }
            },
            "storageClassName": STORAGE_CLASS_NAME,
            "volumeName": f"mysql-pv-{name}"  # Явно привязываем к PV
        }
    )

    # Создаем Deployment для MySQL
    deployment_manifest = V1Deployment(
        metadata=V1ObjectMeta(
            name=f"mysql-{name}",
            namespace=namespace,
            labels={"app": "mysql", "instance": name}
        ),
        spec=V1DeploymentSpec(
            replicas=1,
            selector={
                "matchLabels": {"app": "mysql", "instance": name}
            },
            strategy=V1DeploymentStrategy(
                type="RollingUpdate",
                rolling_update=V1RollingUpdateDeployment(
                    max_unavailable=0,
                    max_surge=1
                )
            ),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(
                    labels={"app": "mysql", "instance": name}
                ),
                spec=V1PodSpec(
                    containers=[
                        V1Container(
                            name="mysql",
                            image=image,
                            env=[
                                V1EnvVar(name="MYSQL_ROOT_PASSWORD", value=password),
                                V1EnvVar(name="MYSQL_DATABASE", value=database),
                                V1EnvVar(name="MYSQL_USER", value="admin"),
                                V1EnvVar(name="MYSQL_PASSWORD", value=password),
                            ],
                            ports=[V1ContainerPort(container_port=3306)],
                            volume_mounts=[V1VolumeMount(
                                name="mysql-storage",
                                mount_path="/var/lib/mysql"
                            )],
                            readiness_probe={
                                "exec": {
                                    "command": ["mysqladmin", "ping", "-h", "localhost"]
                                },
                                "initialDelaySeconds": 30,
                                "periodSeconds": 10
                            },
                            liveness_probe={
                                "exec": {
                                    "command": ["mysqladmin", "ping", "-h", "localhost"]
                                },
                                "initialDelaySeconds": 300,
                                "periodSeconds": 30
                            }
                        )
                    ],
                    volumes=[
                        V1Volume(
                            name="mysql-storage",
                            persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                claim_name=f"mysql-pvc-{name}"
                            )
                        )
                    ]
                )
            )
        )
    )

    # Создаем Service для доступа к MySQL
    service_manifest = V1Service(
        metadata=V1ObjectMeta(
            name=f"mysql-service-{name}",
            namespace=namespace,
            labels={"app": "mysql", "instance": name}
        ),
        spec=V1ServiceSpec(
            selector={"app": "mysql", "instance": name},
            ports=[V1ServicePort(port=3306, target_port=3306)],
            type="ClusterIP"
        )
    )

    try:
        # Создаем ресурсы в Kubernetes
        logger.info(f"Creating MySQL instance {name} in namespace {namespace}")

        # PV (cluster-wide ресурс, без namespace)
        core_api.create_persistent_volume(body=pv_manifest)
        logger.info(f"Created PV: mysql-pv-{name}")

        # PVC
        core_api.create_namespaced_persistent_volume_claim(
            namespace=namespace,
            body=pvc_manifest
        )
        logger.info(f"Created PVC: mysql-pvc-{name}")

        # Deployment
        api.create_namespaced_deployment(
            namespace=namespace,
            body=deployment_manifest
        )
        logger.info(f"Created Deployment: mysql-{name}")

        # Service
        core_api.create_namespaced_service(
            namespace=namespace,
            body=service_manifest
        )
        logger.info(f"Created Service: mysql-service-{name}")

        # Обновляем статус
        return {
            'phase': 'Creating',
            'message': f'MySQL instance {name} is being created',
            'ready': False
        }

    except Exception as e:
        logger.error(f"Failed to create MySQL instance: {e}")
        # Пытаемся удалить созданные ресурсы при ошибке
        try:
            core_api.delete_persistent_volume(name=f"mysql-pv-{name}")
        except:
            pass
        raise kopf.PermanentError(f"Creation failed: {e}")

@kopf.on.delete('otus.homework', 'v1', 'mysqls')
async def delete_mysql_instance(name, namespace, logger, **kwargs):
    """Удаление инстанса MySQL при удалении кастомного ресурса"""

    try:
        # Удаляем связанные ресурсы
        logger.info(f"Deleting MySQL instance {name} from namespace {namespace}")

        # Удаляем Deployment
        api.delete_namespaced_deployment(
            name=f"mysql-{name}",
            namespace=namespace,
            propagation_policy='Foreground'
        )

        # Удаляем Service
        core_api.delete_namespaced_service(
            name=f"mysql-service-{name}",
            namespace=namespace
        )

        # Удаляем PVC
        core_api.delete_namespaced_persistent_volume_claim(
            name=f"mysql-pvc-{name}",
            namespace=namespace
        )

        # Удаляем PV
        core_api.delete_persistent_volume(
            name=f"mysql-pv-{name}"
        )

    except Exception as e:
        logger.error(f"Error during deletion: {e}")

@kopf.on.update('otus.homework', 'v1', 'mysqls')
async def update_mysql_instance(spec, name, namespace, logger, **kwargs):
    """Обновление инстанса MySQL при изменении кастомного ресурса"""

    image = spec.get('image', 'mysql:8.0')

    try:
        # Обновляем образ в Deployment
        deployment = api.read_namespaced_deployment(
            name=f"mysql-{name}",
            namespace=namespace
        )

        deployment.spec.template.spec.containers[0].image = image

        api.patch_namespaced_deployment(
            name=f"mysql-{name}",
            namespace=namespace,
            body=deployment
        )

        logger.info(f"Updated MySQL instance {name}")

        return {
            'phase': 'Updating',
            'message': f'MySQL instance {name} is being updated',
            'ready': True
        }

    except Exception as e:
        logger.error(f"Failed to update MySQL instance: {e}")
        raise kopf.TemporaryError(f"Update failed: {e}", delay=60)

@kopf.timer('otus.homework', 'v1', 'mysqls', interval=30.0)
async def monitor_mysql_status(body, name, namespace, logger, **kwargs):
    """Периодическая проверка статуса MySQL инстанса"""

    try:
        # Проверяем статус Deployment
        deployment = api.read_namespaced_deployment(
            name=f"mysql-{name}",
            namespace=namespace
        )

        ready_replicas = deployment.status.ready_replicas or 0
        desired_replicas = deployment.spec.replicas or 0

        if ready_replicas == desired_replicas and ready_replicas > 0:
            return {
                'phase': 'Running',
                'message': f'MySQL instance {name} is ready',
                'ready': True
            }
        else:
            return {
                'phase': 'NotReady',
                'message': f'MySQL instance {name} is not ready yet',
                'ready': False
            }

    except Exception as e:
        logger.error(f"Error monitoring MySQL instance {name}: {e}")
        return {
            'phase': 'Error',
            'message': f'Error monitoring instance: {e}',
            'ready': False
        }

if __name__ == '__main__':
    kopf.run()