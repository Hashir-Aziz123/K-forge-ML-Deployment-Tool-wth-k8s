"use client";
import { useState } from "react";

export interface ModelData {
  id: string;
  name: string;
  port: number | string;
  replicas: number;
  status: string;
}

export default function DeploymentCard({ model }: { model: ModelData }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"workbench" | "api" | "danger">("workbench");

  // Workbench State
  const [payloadInput, setPayloadInput] = useState('{\n  "feature_1": 0.0\n}');
  const [outputLog, setOutputLog] = useState("Awaiting execution...");
  const [isInferencing, setIsInferencing] = useState(false);
  const [isTerminating, setIsTerminating] = useState(false);

  // --- THE PAYLOAD TRANSFORMER & INFERENCE ENGINE ---
  const handleInference = async () => {
    try {
      setIsInferencing(true);
      setOutputLog("Routing payload to Minikube pod...");
      
      // 1. Parse the user's flat JSON
      const parsedUserJson = JSON.parse(payloadInput);
      
      // 2. Transform: Extract values and wrap in 2D array for ONNX/Scikit
      const matrixPayload = {
        features: [Object.values(parsedUserJson).map(Number)]
      };

      // 3. Fire at the proxy
      const response = await fetch(`http://localhost:8000/api/predict/${model.id}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(matrixPayload)
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.detail || "Inference failed");

      // 4. Print beautiful JSON to the output box
      setOutputLog(JSON.stringify(data, null, 2));

    } catch (error: any) {
      setOutputLog(`[ERROR]\n${error.message || "Invalid JSON payload."}`);
    } finally {
      setIsInferencing(false);
    }
  };

  // --- THE CLUSTER CLEANUP ACTION ---
  const handleTerminate = async () => {
    const confirmNuke = window.confirm(`Are you sure you want to permanently delete ${model.name}?`);
    if (!confirmNuke) return;

    try {
      setIsTerminating(true);
      await fetch(`http://localhost:8000/api/deployments/${model.id}`, {
        method: "DELETE"
      });
      // The FleetBoard will automatically pick up the deletion on its next 5-second poll!
    } catch (error) {
      alert("Failed to delete deployment.");
      setIsTerminating(false);
    }
  };

  return (
    <div className="flex flex-col rounded border border-neutral-800 bg-neutral-950 overflow-hidden transition-colors hover:border-neutral-700">
      
      {/* Top Banner */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer bg-neutral-900/30 hover:bg-neutral-900/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-8">
           <div>
             <div className="text-[10px] text-neutral-500 uppercase tracking-widest mb-0.5">Name</div>
             <div className="text-sm text-neutral-200 font-medium">{model.name}</div>
           </div>
           <div>
             <div className="text-[10px] text-neutral-500 uppercase tracking-widest mb-0.5">ID</div>
             <div className="text-sm text-neutral-400 font-mono">{model.id}</div>
           </div>
           <div>
             <div className="text-[10px] text-neutral-500 uppercase tracking-widest mb-0.5">Port</div>
             <div className="text-sm text-neutral-400 font-mono">{model.port}</div>
           </div>
           <div>
             <div className="text-[10px] text-neutral-500 uppercase tracking-widest mb-0.5">Replicas</div>
             <div className="text-sm text-neutral-400 font-mono">{model.replicas}</div>
           </div>
        </div>
        
        <div className="flex items-center gap-4">
          <span className={`text-[10px] uppercase tracking-wider font-bold px-2 py-1 rounded border ${
            model.status === 'RUNNING' ? 'text-green-400 bg-green-950/30 border-green-900/50' : 'text-yellow-400 bg-yellow-950/30 border-yellow-900/50'
          }`}>
            {model.status}
          </span>
          <span className="text-neutral-500 text-xs w-4 text-center">
            {isExpanded ? "▲" : "▼"}
          </span>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-neutral-800 bg-neutral-950 p-5">
          
          <div className="flex gap-6 border-b border-neutral-800 mb-5 pb-2">
            <button className={`text-xs font-bold uppercase tracking-wider ${activeTab === 'workbench' ? 'text-neutral-200' : 'text-neutral-600 hover:text-neutral-400'}`} onClick={() => setActiveTab('workbench')}>Workbench</button>
            <button className={`text-xs font-bold uppercase tracking-wider ${activeTab === 'api' ? 'text-neutral-200' : 'text-neutral-600 hover:text-neutral-400'}`} onClick={() => setActiveTab('api')}>API Integration</button>
            <button className={`text-xs font-bold uppercase tracking-wider ${activeTab === 'danger' ? 'text-red-400' : 'text-neutral-600 hover:text-red-400/70'}`} onClick={() => setActiveTab('danger')}>Settings</button>
          </div>

          {activeTab === 'workbench' && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">Payload Matrix (JSON)</label>
                <textarea 
                  value={payloadInput}
                  onChange={(e) => setPayloadInput(e.target.value)}
                  className="w-full h-32 bg-neutral-900/50 border border-neutral-800 rounded p-3 text-sm text-neutral-300 font-mono focus:outline-none focus:border-neutral-500 resize-none" 
                  spellCheck="false"
                />
                <button 
                  onClick={handleInference}
                  disabled={isInferencing || model.status !== 'RUNNING'}
                  className={`mt-3 w-full font-semibold py-2 rounded transition-colors text-sm ${
                    isInferencing || model.status !== 'RUNNING' ? 'bg-neutral-800 text-neutral-500 cursor-not-allowed' : 'bg-neutral-200 text-neutral-950 hover:bg-white'
                  }`}
                >
                  {isInferencing ? "Executing..." : "Execute Inference"}
                </button>
              </div>
              <div>
                <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">Output Logs</label>
                <textarea 
                  readOnly
                  value={outputLog}
                  className={`w-full h-32 bg-neutral-900/50 border border-neutral-800 rounded p-3 text-sm font-mono resize-none ${
                    outputLog.includes('[ERROR]') ? 'text-red-400' : 'text-green-400'
                  }`}
                />
              </div>
            </div>
          )}

          {activeTab === 'api' && (
            <div>
               <label className="block text-xs font-semibold text-neutral-500 mb-2 uppercase tracking-wide">cURL Endpoint</label>
               <code className="block w-full bg-neutral-900/50 border border-neutral-800 rounded p-4 text-sm text-neutral-400 font-mono leading-relaxed select-all">
                 curl -X POST http://localhost:8000/api/predict/{model.id} \<br/>
                 &nbsp;&nbsp;&nbsp;&nbsp;-H "Content-Type: application/json" \<br/>
                 &nbsp;&nbsp;&nbsp;&nbsp;-d '&#123;"features": [[0.0]]&#125;'
               </code>
            </div>
          )}

          {activeTab === 'danger' && (
            <div className="p-4 border border-red-900/30 rounded bg-red-950/20">
               <h3 className="text-red-400 font-semibold text-sm mb-1">Terminate Deployment</h3>
               <p className="text-neutral-400 text-xs mb-4 leading-relaxed max-w-xl">
                 This will permanently destroy the active pods, unbind the NodePort, and remove the service from the Minikube cluster.
               </p>
               <button 
                 onClick={handleTerminate}
                 disabled={isTerminating}
                 className="text-xs font-bold py-2.5 px-6 bg-red-950/50 text-red-400 rounded hover:bg-red-900/80 transition-colors border border-red-900/50 hover:border-red-800"
                >
                 {isTerminating ? "Terminating..." : `Nuke "${model.name}"`}
               </button>
            </div>
          )}

        </div>
      )}
    </div>
  );
}