import DeploymentForm from "@/components/DeploymentForm";
import FleetBoard from "@/components/FleetBoard";

export default function Home() {
  return (
    <main className="min-h-screen p-6">
      {/* max-w-5xl keeps the UI from stretching infinitely on ultrawide monitors */}
      <div className="w-full max-w-[1800px] mx-auto flex flex-col gap-8 px-8 lg:px-16 py-10">
        
        <header className="border-b border-neutral-800 pb-4 mt-4">
          <h1 className="text-2xl font-semibold tracking-tight text-white">
            KUBE-AI <span className="text-neutral-500 font-normal">Command Center</span>
          </h1>
        </header>

        {/* Top: The Ingestion Zone */}
        <section>
          <DeploymentForm />
        </section>

        {/* Bottom: The Active Fleet */}
        <section>
          <FleetBoard />
        </section>

      </div>
    </main>
  );
}