from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import time

def get_k8s_client():
    """Authenticates with your local Minikube cluster."""
    try:
        config.load_kube_config() 
        return client.AppsV1Api(), client.CoreV1Api()
    except Exception as e:
        raise RuntimeError(f"Could not connect to Kubernetes cluster: {e}")

# UPDATE 1: Add the replicas parameter
def create_deployment(apps_api, name, image_tag, replicas):
    """Generates and applies the Kubernetes Deployment manifest (Upsert)."""
    container = client.V1Container(
        name=name,
        image=image_tag,
        image_pull_policy="Never", 
        ports=[client.V1ContainerPort(container_port=8000)]
    )

    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": name}),
        spec=client.V1PodSpec(containers=[container])
    )

    spec = client.V1DeploymentSpec(
        replicas=replicas, # <-- INJECTED HERE
        template=template,
        selector=client.V1LabelSelector(match_labels={"app": name})
    )

    deployment = client.V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec
    )

    try:
        apps_api.read_namespaced_deployment(name=name, namespace="default")
        apps_api.patch_namespaced_deployment(name=name, namespace="default", body=deployment)
        print(f"✅ Deployment '{name}' found. Initiating rolling update with {replicas} replicas...")
    except ApiException as e:
        if e.status == 404:
            apps_api.create_namespaced_deployment(namespace="default", body=deployment)
            print(f"✅ Deployment '{name}' created with {replicas} replicas.")
        else:
            raise RuntimeError(f"Kubernetes API Error: {e}")

def create_service(core_api, name):
    """Creates or retrieves the NodePort service."""
    spec = client.V1ServiceSpec(
        type="NodePort", 
        selector={"app": name},
        ports=[client.V1ServicePort(port=8000, target_port=8000)]
    )

    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=client.V1ObjectMeta(name=name),
        spec=spec
    )

    try:
        existing_service = core_api.read_namespaced_service(name=name, namespace="default")
        node_port = existing_service.spec.ports[0].node_port
        print(f"✅ Service '{name}' already exists. Reusing NodePort: {node_port}.")
        return node_port
    except ApiException as e:
        if e.status == 404:
            created_service = core_api.create_namespaced_service(namespace="default", body=service)
            node_port = created_service.spec.ports[0].node_port
            print(f"✅ Service '{name}' exposed on NodePort: {node_port}.")
            return node_port
        else:
            raise RuntimeError(f"Kubernetes API Error: {e}")

def wait_for_deployment(apps_api, name, timeout=120):
    """Polls the cluster until the container is fully booted and ready."""
    print(f"⏳ Waiting for pod to reach 'Running' state...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        deployment = apps_api.read_namespaced_deployment(name=name, namespace="default")
        # Check if the replica is actually available to take traffic
        if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
            print(f"\n✅ Pod is running and ready to serve predictions!")
            return True
        time.sleep(2)
        print(".", end="", flush=True)
    
    raise TimeoutError("Deployment timed out. Check `kubectl get pods` for errors.")

def deploy_model(image_tag: str, deployment_name: str, replicas: int = 1):
    """The main orchestrator function."""
    
    apps_api, core_api = get_k8s_client()
    
    try:
        create_deployment(apps_api, deployment_name, image_tag, replicas)
        node_port = create_service(core_api, deployment_name)
        wait_for_deployment(apps_api, deployment_name)
        
        return {
            "status": "success",
            "service_name": deployment_name,
            "node_port": node_port,
            "replicas": replicas
        }
    except Exception as e:
        raise RuntimeError(f"Kubernetes deployment failed: {e}")