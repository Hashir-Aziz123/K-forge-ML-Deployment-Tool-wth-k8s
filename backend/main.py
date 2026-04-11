import shutil
import json
import subprocess
import time
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Import your pipeline services
from services.generator import create_api_script
from services.builder import build_docker_image, generate_dockerfile
from services.k8s_engine import deploy_model

app = FastAPI(title="KUBE-AI Master API")

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/api/upload")
async def deploy_ai_model(
    model_file: UploadFile = File(...),
    schema: str = Form(...),
    replicas: int = Form(1) # <-- NEW: User can request manual scaling
):
    """
    The Zero-Touch MLOps Pipeline.
    Ingests a model & schema, generates the API, containerizes it, and orchestrates it on Kubernetes.
    """
    # 1. Format Validation
    allowed_extensions = {".pkl", ".onnx"}
    file_ext = Path(model_file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported format {file_ext}. Must be .pkl or .onnx"
        )

    # 2. Schema Validation
    try:
        parsed_schema = json.loads(schema)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON schema provided.")

    # 3. Generate Unique Tags
    # We use a timestamp so Kubernetes doesn't get confused by overlapping image names
    project_id = f"model-{int(time.time())}"
    image_tag = f"kube-ai-{project_id}:latest"
    file_path = UPLOAD_DIR / model_file.filename
    
    try:
        # --- PHASE 1: INGESTION & CODE GENERATION ---
        print(f"\n[1/4] Saving model and generating API script...")
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(model_file.file, buffer)

        # Generate the dynamic app.py in the UPLOAD_DIR
        app_script_path = create_api_script(
            model_path=file_path, 
            schema=parsed_schema, 
            output_dir=UPLOAD_DIR
        )

        # --- PHASE 2: CONTAINERIZATION ---
        print(f"[2/4] Initiating Docker Build for {image_tag}...")

        # Write the Dockerfile tailored to this specific upload
        generate_dockerfile(model_path=file_path, output_dir=UPLOAD_DIR)
        
        # Pass the directory where both the model and the generated app.py live
        build_result = build_docker_image(str(UPLOAD_DIR), image_tag)
        if build_result.get("status") != "success":
            raise RuntimeError("Docker build failed.")

        # --- THE BRIDGE: AUTOMATING THE LOCAL REGISTRY PUSH ---
        print(f"[3/4] Teleporting image to Minikube internal registry...")
        process = subprocess.run(
            ["minikube", "image", "load", image_tag],
            capture_output=True,
            text=True
        )
        if process.returncode != 0:
            raise RuntimeError(f"Failed to load image into Minikube: {process.stderr}")

        # --- PHASE 3: ORCHESTRATION ---
        print(f"[4/4] Orchestrating Deployment '{project_id}' with {replicas} replicas...")
        
        # We now pass the dynamic project_id and the user's replica count into K8s
        k8s_result = deploy_model(
            image_tag=image_tag, 
            deployment_name=project_id, 
            replicas=replicas
        )

        # --- CLEANUP ---
        # Wipe the local storage so your disk doesn't fill up with stale models. 
        # The true artifact now lives inside the Minikube registry.
        file_path.unlink(missing_ok=True)
        if Path(app_script_path).exists():
            Path(app_script_path).unlink()

        # Return the final orchestration data
        return JSONResponse(content={
            "status": "success",
            "message": "Model successfully compiled, containerized, and deployed to cluster.",
            "deployment_id": project_id,
            "service_name": k8s_result["service_name"],
            "internal_port": k8s_result["node_port"],
            "replicas_running": k8s_result["replicas"],
            "instruction": f"Run `kubectl port-forward service/{k8s_result['service_name']} 8080:8000` to access your live API."
        })

    except Exception as e:
        # Emergency cleanup on pipeline failure
        file_path.unlink(missing_ok=True)
        print(f"\n❌ Pipeline Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)