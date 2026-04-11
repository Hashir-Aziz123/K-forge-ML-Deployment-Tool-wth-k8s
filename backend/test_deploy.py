from services.k8s_engine import deploy_model

def run_deployment_test():
    print("Initiating Kubernetes deployment sequence...")
    try:
        # We use the exact image tag we loaded into the Minikube registry
        result = deploy_model("kube-ai-dummy:latest")
        
        print("\n🎉 Orchestration Complete!")
        print(f"Service Name: {result['service_name']}")
        print(f"NodePort Mapping: 8000 -> {result['node_port']}")
        
        print("\n--- Next Steps ---")
        print("Because Minikube runs inside a Docker container on Windows,")
        print("localhost won't map directly to the NodePort. Run this command")
        print("in your terminal to get the actual accessible URL:")
        print(f"minikube service {result['service_name']} --url")
        
    except Exception as e:
        print(f"\n❌ Deployment Failed:\n{e}")

if __name__ == "__main__":
    run_deployment_test()