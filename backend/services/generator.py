import textwrap
from pathlib import Path

def generate_sklearn_wrapper(model_filename: str) -> str:
    """Generates a FastAPI wrapper for scikit-learn .pkl models."""
    return textwrap.dedent(f"""\
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import pickle
        import numpy as np
        import warnings
        
        # Suppress sklearn version warnings for cleaner logs
        warnings.filterwarnings("ignore")

        app = FastAPI(title="KUBE-AI Sklearn Inference API")

        # Load the model at startup
        try:
            with open("{model_filename}", "rb") as f:
                model = pickle.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to load model: {{e}}")

        class InferenceRequest(BaseModel):
            # Expecting a list of features, e.g., [[0.0, 0.0]]
            features: list
            
        @app.post("/predict")
        async def predict(request: InferenceRequest):
            try:
                # Convert input to numpy array and predict
                input_data = np.array(request.features)
                prediction = model.predict(input_data)
                
                # Convert numpy types to native Python types for JSON serialization
                return {{"prediction": prediction.tolist()}}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    """)

def generate_onnx_wrapper(model_filename: str, schema: dict) -> str:
    """Generates a FastAPI wrapper for ONNX models."""
    # We extract the input name from the schema to dynamically map it in onnxruntime
    input_name = schema["inputs"][0]["name"]
    
    return textwrap.dedent(f"""\
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        import onnxruntime as ort
        import numpy as np

        app = FastAPI(title="KUBE-AI ONNX Inference API")

        # Initialize ONNX session
        try:
            session = ort.InferenceSession("{model_filename}")
        except Exception as e:
            raise RuntimeError(f"Failed to load ONNX model: {{e}}")

        class InferenceRequest(BaseModel):
            {input_name}: list

        @app.post("/predict")
        async def predict(request: InferenceRequest):
            try:
                # Prepare inputs dynamically based on the schema
                input_data = np.array(request.{input_name}, dtype=np.float32)
                
                # Run inference
                outputs = session.run(None, {{"{input_name}": input_data}})
                
                return {{"prediction": outputs[0].tolist()}}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    """)

def create_api_script(model_path: Path, schema: dict, output_dir: Path) -> Path:
    """Routes to the correct template and writes the final app.py to disk."""
    file_ext = model_path.suffix.lower()
    
    if file_ext == ".pkl":
        code = generate_sklearn_wrapper(model_path.name)
    elif file_ext == ".onnx":
        code = generate_onnx_wrapper(model_path.name, schema)
    else:
        raise ValueError("Unsupported model type for generation.")

    # Write the generated code to app.py in the same directory as the model
    app_path = output_dir / "app.py"
    with app_path.open("w") as f:
        f.write(code)
        
    return app_path