import textwrap
import docker
from pathlib import Path

def generate_dockerfile(model_path: Path, output_dir: Path) -> Path:
    """
    Writes a lean Dockerfile based on the model type.
    """
    file_ext = model_path.suffix.lower()
    
    # Base requirements needed for both types to run the web server
    base_packages = "fastapi uvicorn pydantic gunicorn numpy"
    
    # Conditionally add the heavy ML runtimes
    if file_ext == ".pkl":
        ml_package = "scikit-learn"
    elif file_ext == ".onnx":
        ml_package = "onnxruntime"
    else:
        raise ValueError("Unsupported model type for Dockerfile generation.")

    # We use a slim Python 3.10 image to minimize bloat
    dockerfile_content = textwrap.dedent(f"""\
        FROM python:3.10-slim
        
        # Prevent Python from writing pyc files and buffering stdout
        ENV PYTHONDONTWRITEBYTECODE=1
        ENV PYTHONUNBUFFERED=
                                         
        ENV PIP_DEFAULT_TIMEOUT=1000 
        ENV PIP_NO_CACHE_DIR=1

        WORKDIR /app

        # Install exact dependencies needed for this specific model
        RUN pip install --no-cache-dir \\
            --timeout=1000 \\
            --trusted-host pypi.org \\
            --trusted-host files.pythonhosted.org \\
            fastapi uvicorn pydantic gunicorn numpy {ml_package}

        # Copy the dynamically generated API script and the model artifact
        COPY app.py /app/app.py
        COPY {model_path.name} /app/{model_path.name}

        EXPOSE 8000

        # Run Gunicorn as the process manager with 2 Uvicorn workers
        CMD ["gunicorn", "app:app", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
    """)

    dockerfile_path = output_dir / "Dockerfile"
    with dockerfile_path.open("w") as f:
        f.write(dockerfile_content)
        
    return dockerfile_path

def build_docker_image(build_context_dir: Path, image_tag: str) -> dict:
    try:
        client = docker.from_env()
    except Exception as e:
        raise RuntimeError(f"Could not connect to Docker: {e}")

    try:
        # We'll use the generator to print logs in real-time
        print("--- Docker Build Logs Start ---")
        build_logs = client.api.build(
            path=str(build_context_dir),
            tag=image_tag,
            rm=True,
            decode=True
        )
        
        for line in build_logs:
            if 'stream' in line:
                print(line['stream'].strip())
            elif 'error' in line:
                raise RuntimeError(line['error'])
        
        print("--- Docker Build Logs End ---")
        return {"status": "success", "tag": image_tag}
    except Exception as e:
        raise RuntimeError(str(e))