import textwrap
from pathlib import Path

def create_api_script(model_path: Path, schema: dict, output_dir: Path) -> Path:
    """
    Generates a universal FastAPI app.py that dynamically handles both .pkl and .onnx models
    using the Matrix (2D Array) payload standard.
    """
    file_ext = model_path.suffix.lower()
    model_filename = model_path.name
    
    app_code = textwrap.dedent(f"""\
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel
        from typing import List
        import numpy as np

        app = FastAPI(title="KUBE-AI Inference Engine")

        # The strict Matrix requirement we established
        class InferencePayload(BaseModel):
            features: List[List[float]]

        MODEL_PATH = "{model_filename}"
        FILE_EXT = "{file_ext}"

        model = None
        onnx_session = None
        onnx_input_name = None

        @app.on_event("startup")
        def load_model():
            global model, onnx_session, onnx_input_name
            try:
                if FILE_EXT == ".pkl":
                    import pickle
                    with open(MODEL_PATH, "rb") as f:
                        model = pickle.load(f)
                elif FILE_EXT == ".onnx":
                    import onnxruntime as rt
                    # Load the C++ engine
                    onnx_session = rt.InferenceSession(MODEL_PATH)
                    # Dynamically grab whatever the input node was named during export
                    onnx_input_name = onnx_session.get_inputs()[0].name
            except Exception as e:
                print(f"Failed to load model into memory: {{e}}")

        @app.post("/predict")
        def predict(payload: InferencePayload):
            try:
                # ONNX strictly requires float32. scikit-learn accepts it.
                input_matrix = np.array(payload.features, dtype=np.float32)
                
                if FILE_EXT == ".pkl":
                    if model is None:
                        raise HTTPException(status_code=500, detail="Model artifact missing.")
                    preds = model.predict(input_matrix)
                    return {{"prediction": preds.tolist()}}
                    
                elif FILE_EXT == ".onnx":
                    if onnx_session is None:
                        raise HTTPException(status_code=500, detail="ONNX engine failed to start.")
                    
                    # Feed the matrix into the dynamic input node
                    preds = onnx_session.run(None, {{onnx_input_name: input_matrix}})
                    return {{"prediction": preds[0].tolist()}}
                    
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
    """)
    
    app_path = output_dir / "app.py"
    with app_path.open("w") as f:
        f.write(app_code)
        
    return app_path