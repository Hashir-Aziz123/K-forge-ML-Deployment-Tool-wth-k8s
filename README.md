# K-Forge: Automated Kubernetes MLOps & Model Orchestration Platform

Kube-AI is an end-to-end MLOps platform designed to automate the lifecycle of machine learning models from raw artifact ingestion to scalable, containerized orchestration within a Kubernetes cluster. The system features a headless code-generation engine, an automated containerization pipeline, and a dynamic reverse-proxy mechanism to handle inference workloads without manual network provisioning.

---

## High-Level System Architecture

The platform is structured as a decoupled, full-stack application consisting of three core tiers:

1. **Control Panel (Frontend):** A React/Next.js interface that provides deep visibility into cluster health, deployment states, and replica counts, alongside an interactive workbench for inference testing.
2. **Master API (Control Plane):** A FastAPI gateway acting as the central orchestrator. It executes code generation, drives local Docker builds, interfaces directly with the Kubernetes API via `kubectl`, and tracks deployment metadata.
3. **Data Plane (Inference Pods):** Isolated, horizontally autoscaled child FastAPI services encapsulated inside Kubernetes pods, executing optimized model inference workloads via ONNX or Pickle.

---

## Core Execution Pipeline

### 1. Ingestion and Headless Code Generation

When a model binary (`.onnx` or `.pkl`) is uploaded along with a strict feature schema, the Master API isolates the deployment payload. It invokes an internal script generation service that dynamically compiles a custom Python microservice specifically tailored to the uploaded model's inputs. This generated script enforces structural type-checking and exposes a dedicated `/predict` endpoint.

### 2. Automated Containerization

Once the application script is generated, the pipeline automates the filesystem construction:

* **Dockerfile Synthesis:** A standard base image is selected, and a custom Dockerfile is compiled to handle dependencies, install runtime utilities, copy the model binaries, and configure the Uvicorn ASGI server.
* **Image Compilation:** The control plane invokes the host Docker daemon to execute an isolated image build, tagging the artifact with a distinct temporal identifier (e.g., `kube-ai-model-1776180572:latest`).
* **Cluster Loading:** To circumvent air-gapped network restrictions inside local Kubernetes environments, the compiled image is directly injected into the internal Minikube registry using low-level image loading protocols.

### 3. Kubernetes Orchestration

The control plane generates standard declarative Kubernetes manifests on the fly:

* **Deployment Resource:** Defines the target replica state, image pull policies, rolling update strategies, and health probes for the model pods.
* **Service Resource:** Provisions a stable internal cluster IP and exposes a target NodePort, load-balancing traffic across all active model replicas.
* **Metadata Registry:** The model's entry schema is written to a localized state file (`registry.json`) on the host filesystem to preserve metadata independent of the volatile cluster state.

### 4. Dynamic Reverse-Proxy Inference Loop

Due to the isolated network topologies of local container runtimes, external clients cannot natively route traffic to internal cluster IPs. Kube-AI implements a temporary tunnel proxy mechanism to address this:

1. The client sends a standard HTTP payload to the Master API's proxy endpoint.
2. The Master API intercepts the request, dynamically binds to a free ephemeral port on the host machine, and spawns an asynchronous background port-forwarding tunnel directly to the respective Kubernetes Service.
3. The incoming payload is proxied down the tunnel, processed by the model container, and the prediction is sent back up to the client.
4. Upon resolution, the tunnel process is immediately terminated to clear system resources.

---

## Technical Stack

* **Control Plane & Services:** Python, FastAPI, Uvicorn, SQLAlchemy
* **Frontend Dashboard:** React, Next.js, TypeScript, Tailwind CSS
* **Container Layer:** Docker Engine, Docker API
* **Orchestration Layer:** Kubernetes, Minikube, Kubectl CLI
* **Runtime Storage:** Local Filesystem Registry

---
