"use client";

import { useState, useEffect, useRef } from "react"; // <-- Import useRef
import DeploymentCard, { ModelData } from "./DeploymentCard";

export default function FleetBoard() {
  const [deployments, setDeployments] = useState<ModelData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  
  // The React-safe way to prevent overlapping fetches
  const isFetchingRef = useRef(false);

  useEffect(() => {
    const fetchFleet = async () => {
      // Check the ref current value
      if (isFetchingRef.current) return;
      isFetchingRef.current = true;

      try {
        const response = await fetch("http://localhost:8000/api/deployments");
        if (!response.ok) throw new Error("Failed to fetch cluster state.");
        
        const data = await response.json();
        
        const activeFleet: ModelData[] = data.deployments.map((dep: any) => ({
          id: dep.deployment_id,
          name: dep.name,
          port: dep.internal_port || "Pending",
          replicas: dep.replicas,
          status: dep.available > 0 ? "RUNNING" : "BOOTING"
        }));

        setDeployments(activeFleet);
        setError("");
      } catch (err: any) {
        setError("Cannot connect to Master API. Is FastAPI running?");
      } finally {
        // Reset the ref
        isFetchingRef.current = false;
        setIsLoading(false);
      }
    };

    fetchFleet();
    const intervalId = setInterval(fetchFleet, 10000);
    return () => clearInterval(intervalId);
  }, []);
  
  // ... rest of your return() code stays exactly the same

  return (
    <div className="rounded-lg border border-neutral-800 bg-neutral-900/50 p-5 min-h-[500px] flex flex-col">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-sm font-medium text-neutral-400 uppercase tracking-widest">
          Active Fleet
        </h2>
        <div className="flex items-center gap-2">
          {error ? (
            <>
              <span className="relative flex h-2 w-2"><span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span></span>
              <span className="text-xs text-red-500 font-medium tracking-wide">Cluster Offline</span>
            </>
          ) : (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-xs text-green-500 font-medium tracking-wide">Minikube Synchronized</span>
            </>
          )}
        </div>
      </div>
      
      <div className="flex flex-col gap-4">
        {isLoading ? (
          <div className="py-12 flex items-center justify-center text-neutral-500 text-sm animate-pulse">
            Scanning Kubernetes cluster...
          </div>
        ) : deployments.length > 0 ? (
          deployments.map((model) => (
            <DeploymentCard key={model.id} model={model} />
          ))
        ) : (
          <div className="py-12 flex flex-col items-center justify-center text-neutral-600 border border-dashed border-neutral-800 rounded">
            <span className="text-sm mb-1">No active deployments found.</span>
            <span className="text-xs">Upload a model above to ignite the cluster.</span>
          </div>
        )}
      </div>
    </div>
  );
}