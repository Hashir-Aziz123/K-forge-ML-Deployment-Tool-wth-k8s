from pathlib import Path
from services.builder import generate_dockerfile, build_docker_image

# Resolve the absolute path to the uploads directory
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
model_path = UPLOAD_DIR / "dummy_model.pkl"

def run_test():
    print(f"Targeting model: {model_path}")
    
    # Step 1: Generate Dockerfile
    print("1. Generating Dockerfile...")
    df_path = generate_dockerfile(model_path, UPLOAD_DIR)
    print(f"   ✅ Created at: {df_path}")

    # Step 2: Build Image
    print("\n2. Compiling Docker Image 'kube-ai-dummy:latest'...")
    print("   (This might take a minute if it needs to pull the python:3.10-slim base image)")
    
    try:
        result = build_docker_image(UPLOAD_DIR, "kube-ai-dummy:latest")
        print(f"\n   ✅ Build Successful!")
        print(f"   Image ID: {result['tag']}")
    except Exception as e:
        print(f"\n   ❌ Build Failed:\n{e}")

if __name__ == "__main__":
    run_test()