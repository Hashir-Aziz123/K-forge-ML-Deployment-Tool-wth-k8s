"use client";

import { useState, useRef } from "react";

export default function DeploymentForm() {
  // --- STATE MACHINE ---
  const [files, setFiles] = useState<File[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [replicas, setReplicas] = useState(1);
  const [schema, setSchema] = useState('{\n  "feature_1": "float"\n}');
  
  // UI States
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState<"idle" | "deploying" | "success" | "error">("idle");
  const [errorMessage, setErrorMessage] = useState("");

  // Hidden file input reference for the "click to browse" fallback
  const fileInputRef = useRef<HTMLInputElement>(null);

  // --- DRAG AND DROP HANDLERS ---
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      // Convert FileList to Array and update state
      setFiles(Array.from(e.dataTransfer.files));
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setFiles(Array.from(e.target.files));
    }
  };

  // --- SUBMISSION LOGIC ---
  const handleSubmit = async () => {
    // Basic validation
    if (files.length === 0) {
      setErrorMessage("Please select at least one .onnx or .pkl file.");
      setStatus("error");
      return;
    }
    
    setStatus("deploying");
    setErrorMessage("");

    // Construct the payload exactly how FastAPI expects it
    const formData = new FormData();
    files.forEach((file) => formData.append("files", file));
    formData.append("schema", schema);
    formData.append("replicas", replicas.toString());
    formData.append("model_name", displayName || "Unnamed Model");

    try {
      const response = await fetch("http://localhost:8000/api/upload", {
        method: "POST",
        body: formData,
        // Notice: We DO NOT set the Content-Type header. 
        // The browser automatically sets it to 'multipart/form-data' with the correct boundary boundary limits.
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Deployment failed.");
      }

      setStatus("success");
      // Reset form after successful deployment
      setTimeout(() => {
        setFiles([]);
        setDisplayName("");
        setReplicas(1);
        setStatus("idle");
      }, 3000);

    } catch (error: any) {
      setErrorMessage(error.message);
      setStatus("error");
    }
  };

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-5">
      <div className="flex justify-between items-center mb-5">
        <h2 className="text-sm font-medium text-neutral-400 uppercase tracking-widest">
          Deploy New Model
        </h2>
        {/* Status Indicators */}
        {status === "success" && <span className="text-xs text-green-500 font-bold tracking-wide animate-pulse">DEPLOYMENT SUCCESSFUL</span>}
        {status === "error" && <span className="text-xs text-red-500 font-bold tracking-wide">{errorMessage}</span>}
      </div>

      <form className="space-y-6">
        <div className="grid grid-cols-2 gap-6">
          
          {/* File Dropzone */}
          <div>
            <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">
              Artifacts (.onnx, .pkl)
            </label>
            <div 
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`h-28 rounded border-2 border-dashed flex flex-col items-center justify-center transition-colors cursor-pointer group ${
                isDragging ? "border-neutral-300 bg-neutral-800/50" : "border-neutral-700 bg-neutral-950 hover:border-neutral-500"
              }`}
            >
              {/* Show selected files, or the upload prompt */}
              {files.length > 0 ? (
                <div className="text-center px-2">
                  <span className="text-green-400 text-sm font-medium block">
                    {files.length} file{files.length > 1 ? 's' : ''} staged
                  </span>
                  <span className="text-neutral-500 text-xs truncate block max-w-[200px]">
                    {files[0].name}
                  </span>
                </div>
              ) : (
                <span className="text-neutral-500 group-hover:text-neutral-300 text-sm transition-colors">
                  Drag & Drop or Click
                </span>
              )}
            </div>
            {/* Hidden native input */}
            <input 
              type="file" 
              multiple 
              className="hidden" 
              ref={fileInputRef} 
              onChange={handleFileSelect}
              accept=".onnx,.pkl,.data"
            />
          </div>

          {/* Setup Settings */}
          <div className="flex flex-col justify-between">
            <div>
              <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">
                Display Name
              </label>
              <input 
                type="text" 
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="e.g., Heat-Risk-V1"
                className="w-full bg-neutral-950 border border-neutral-800 rounded p-2.5 text-sm text-neutral-200 focus:outline-none focus:border-neutral-500 transition-colors"
                disabled={status === "deploying"}
              />
            </div>
            
            <div>
              <div className="flex justify-between text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">
                <label>Kubernetes Replicas</label>
                <span className="text-neutral-300">{replicas}</span>
              </div>
              <input 
                type="range" 
                min="1" 
                max="5" 
                value={replicas}
                onChange={(e) => setReplicas(parseInt(e.target.value))}
                className="w-full accent-neutral-400 cursor-pointer" 
                disabled={status === "deploying"}
              />
            </div>
          </div>
        </div>

        {/* JSON Schema Input */}
        <div>
          <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">
            Input Schema (JSON)
          </label>
          <textarea
            value={schema}
            onChange={(e) => setSchema(e.target.value)}
            className="w-full h-36 bg-neutral-950 border border-neutral-800 rounded p-3 text-sm text-neutral-300 font-mono focus:outline-none focus:border-neutral-500 resize-none transition-colors"
            spellCheck="false"
            disabled={status === "deploying"}
          />
        </div>

        <button 
          type="button" 
          onClick={handleSubmit}
          disabled={status === "deploying"}
          className={`w-full font-semibold py-2.5 rounded transition-all ${
            status === "deploying" 
              ? "bg-neutral-800 text-neutral-500 cursor-not-allowed" 
              : "bg-neutral-200 text-neutral-950 hover:bg-white"
          }`}
        >
          {status === "deploying" ? "Orchestrating Container..." : "Initialize Deployment"}
        </button>
      </form>
    </div>
  );
}