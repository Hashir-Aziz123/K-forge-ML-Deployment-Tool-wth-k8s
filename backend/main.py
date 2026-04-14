import shutil
import json
import subprocess
import time
import httpx
import asyncio  
import socket
from pathlib import Path
from typing import List, Annotated

from fastapi import FastAPI, File, UploadFile as DefaultUploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import WithJsonSchema
import uvicorn

from services.generator import create_api_script
from services.builder import build_docker_image, generate_dockerfile
from services.k8s_engine import deploy_model, get_all_deployments, delete_deployment


UploadFile = Annotated[
    DefaultUploadFile, 
    WithJsonSchema({"type": "string", "format": "binary"})
]

app = FastAPI(title="KUBE-AI Master API")

# --- CORS MIDDLEWARE ---
# This allows your localhost:3000 React app to talk to this localhost:8000 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "storage" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# def get_minikube_ip():
#     """Dynamically fetches the exact IP of the Minikube VM to bypass tunnels."""
#     try:
#         process = subprocess.run(["minikube", "ip"], capture_output=True, text=True, check=True)
#         return process.stdout.strip()
#     except Exception:
#         return "127.0.0.1" # Fallback if command fails

@app.post("/api/upload")
def deploy_ai_model(
    files: List[UploadFile] = File(...),
    schema: str = Form(...),
    replicas: int = Form(1),
    model_name: str = Form("Unnamed Model") # <-- NEW: Captures custom name
):
    """Ingests model files, generates the API, containerizes it, and orchestrates it."""
    
    # 1. Schema Validation
    try:
        parsed_schema = json.loads(schema)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON schema provided.")

    # 2. Setup Isolated Tenant Directory
    project_id = f"model-{int(time.time())}"
    image_tag = f"kube-ai-{project_id}:latest"
    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    
    primary_file_path = None

    try:
        print(f"\n[1/4] Saving files to isolated directory {project_id}...")
        
        # Save all uploaded files (handles detached ONNX weights)
        for file in files:
            file_path = project_dir / file.filename
            with file_path.open("wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Identify the core architecture file to pass to the generator
            if file.filename.endswith(".pkl") or (file.filename.endswith(".onnx") and not file.filename.endswith(".data")):
                primary_file_path = file_path

        if not primary_file_path:
            raise ValueError("No valid .pkl or core .onnx file found in payload.")

        # Generate the dynamic app.py inside the specific project directory
        create_api_script(model_path=primary_file_path, schema=parsed_schema, output_dir=project_dir)

        print(f"[2/4] Initiating Docker Build for {image_tag}...")
        generate_dockerfile(model_path=primary_file_path, output_dir=project_dir)
        
        build_result = build_docker_image(str(project_dir), image_tag)
        if build_result.get("status") != "success":
            raise RuntimeError("Docker build failed.")

        print(f"[3/4] Teleporting image to Minikube internal registry...")
        process = subprocess.run(["minikube", "image", "load", image_tag], capture_output=True, text=True)
        if process.returncode != 0:
            raise RuntimeError(f"Failed to load image into Minikube: {process.stderr}")

        print(f"[4/4] Orchestrating Deployment '{project_id}' with {replicas} replicas...")
        # Pass the human-readable name into the k8s engine
        k8s_result = deploy_model(
            image_tag=image_tag, 
            deployment_name=project_id, 
            replicas=replicas,
            model_name=model_name # <-- NEW: Handed off to cluster
        )

        # Cleanup the isolated directory after successful deployment
        shutil.rmtree(project_dir, ignore_errors=True)

        return JSONResponse(content={
            "status": "success",
            "deployment_id": project_id,
            "name": model_name, # <-- NEW: Returned to frontend
            "service_name": k8s_result["service_name"],
            "internal_port": k8s_result["node_port"],
            "replicas_running": k8s_result["replicas"],
        })

    except Exception as e:
        shutil.rmtree(project_dir, ignore_errors=True) # Emergency cleanup
        print(f"\n❌ Pipeline Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW: DISCOVERY ENDPOINT ---
@app.get("/api/deployments")
async def list_deployments():
    """Returns a list of all active models running in the cluster."""
    try:
        fleet = get_all_deployments()
        return {"status": "success", "deployments": fleet}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- NEW: TEARDOWN ENDPOINT ---
@app.delete("/api/deployments/{deployment_id}")
async def terminate_deployment(deployment_id: str):
    """Kills a specific model deployment in the cluster."""
    try:
        delete_deployment(deployment_id)
        return {"status": "success", "message": f"Deployment {deployment_id} terminated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# --- NEW: API GATEWAY (INFERENCE ROUTE) ---
@app.post("/api/predict/{deployment_id}")
async def proxy_inference(deployment_id: str, payload: dict):
    """Acts as a reverse proxy, bypassing Windows networking via dynamic ephemeral port-forwarding."""
    fleet = get_all_deployments()
    
    target_model = next((model for model in fleet if model["deployment_id"] == deployment_id), None)
    if not target_model:
        raise HTTPException(status_code=404, detail=f"Model {deployment_id} is not currently running.")

    # 1. Find an absolutely free, unused port on your Windows machine
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    free_port = s.getsockname()[1]
    s.close()

    # 2. Open a direct TCP socket to the pod (Bypassing the broken Minikube Bridge)
    print(f"\n🔒 Establishing direct K8s tunnel to {deployment_id} on port {free_port}...")
    pf_process = subprocess.Popen(
        ["kubectl", "port-forward", f"svc/{deployment_id}", f"{free_port}:8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    try:
        # Give the tunnel 1.5 seconds to establish the secure connection
        await asyncio.sleep(1.5)
        
        target_url = f"http://127.0.0.1:{free_port}/predict"
        
        # 3. Fire the payload down the tunnel
        async with httpx.AsyncClient() as client:
            response = await client.post(target_url, json=payload, timeout=30.0)
            response.raise_for_status()
            return response.json()
            
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"Tunnel collapsed: {str(e)}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=f"Model rejected payload: {e.response.text}")
    finally:
        # 4. Nuke the tunnel after the request finishes to free up system memory
        pf_process.terminate()
        print(f"🔓 Tunnel closed.")