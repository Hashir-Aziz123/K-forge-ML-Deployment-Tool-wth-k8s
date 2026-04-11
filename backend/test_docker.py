import docker

def verify_docker_connection():
    try:
        # from_env() automatically looks for the local Docker socket/pipe
        client = docker.from_env()
        
        # Ping the daemon
        client.ping()
        print("✅ Successfully connected to Docker Desktop daemon.")
        
        # Fetch some basic telemetry to prove it's reading actual data
        info = client.info()
        print(f"Docker Version: {info.get('ServerVersion')}")
        print(f"Operating System: {info.get('OperatingSystem')}")
        print(f"Total Containers: {info.get('Containers')}")
        print(f"Images Available: {info.get('Images')}")
        
    except docker.errors.DockerException as e:
        print("❌ Failed to connect to Docker. Is Docker Desktop actually running?")
        print(f"Error details: {e}")

if __name__ == "__main__":
    verify_docker_connection()