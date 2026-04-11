import requests
import json

# The URL of your Kubernetes tunnel
url = "http://127.0.0.1:8080/predict"

# The Iris dataset features (Setosa)
# A 2D array: [ [feature1, feature2, feature3, feature4] ]
payload = {
    "features": [
        [5.1, 3.5, 1.4, 0.2]
    ]
}

print(f"Sending live inference request to {url}...")

try:
    response = requests.post(url, json=payload)
    response.raise_for_status() # Raise an exception for bad status codes
    
    prediction = response.json()
    print("\n✅ Inference Successful!")
    print(f"Model Prediction: {prediction}")

except requests.exceptions.HTTPError as err:
    print(f"\n❌ FastAPI Rejected the Payload (422):")
    # This is the magic line. It prints exactly what FastAPI is complaining about.
    print(err.response.json())
    
except requests.exceptions.ConnectionError:
    print("\n❌ Connection Failed. Is the kubectl port-forward tunnel running?")
except Exception as e:
    print(f"\n❌ Request Failed: {e}")