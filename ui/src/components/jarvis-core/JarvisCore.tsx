import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import type { AIState } from "../../types/ui";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";
import { AtmosphericProjection } from "./AtmosphericProjection";
import { CorePostProcessing } from "./CorePostProcessing";
import { DataFlow } from "./DataFlow";
import { EventPulseSystem } from "./EventPulseSystem";
import { EnergyNucleus } from "./EnergyNucleus";
import { HolographicGeometry } from "./HolographicGeometry";
import { NeuralConnections } from "./NeuralConnections";
import { OrbitalSystem } from "./OrbitalSystem";
import { ParticleField } from "./ParticleField";

interface JarvisCoreProps { state: AIState; audioSignal: AudioReactiveSignal; }

function CoreScene({ state, audioSignal }: JarvisCoreProps) {
  return (
    <>
      <color attach="background" args={["#070704"]} />
      <fog attach="fog" args={["#070704", 4.3, 9]} />
      <ambientLight intensity={0.1} color="#ffe5a0" />
      <group>
        <AtmosphericProjection state={state} />
        <HolographicGeometry state={state} />
        <EventPulseSystem state={state} />
        <OrbitalSystem state={state} />
        <ParticleField state={state} audioSignal={audioSignal} />
        <NeuralConnections state={state} />
        <DataFlow state={state} />
        <EnergyNucleus state={state} audioSignal={audioSignal} />
      </group>
      <CorePostProcessing />
    </>
  );
}

export function JarvisCore({ state, audioSignal }: JarvisCoreProps) {
  return (
    <div className="jarvis-core" aria-label={`Central intelligence visualization: ${state}`}>
      <Canvas camera={{ position: [0, 0, 4.8], fov: 40 }} dpr={[1, 1.75]} gl={{ antialias: true, alpha: false, powerPreference: "high-performance" }}>
        <Suspense fallback={null}><CoreScene state={state} audioSignal={audioSignal} /></Suspense>
      </Canvas>
    </div>
  );
}
