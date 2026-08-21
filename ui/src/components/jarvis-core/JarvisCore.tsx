import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";
import { JarvisScene } from "./JarvisScene";
import { JARVIS_SCENE } from "./sceneConfig";

interface JarvisCoreProps { state: AIState; audioSignal: AudioReactiveSignal; }

export function JarvisCore({ state, audioSignal }: JarvisCoreProps) {
  return (
    <div className="jarvis-core" aria-label={`Central intelligence visualization: ${state}`}>
      <Canvas
        camera={{ position: JARVIS_SCENE.camera.position, fov: JARVIS_SCENE.camera.fov, near: 0.1, far: 30 }}
        dpr={[1, 1.65]}
        gl={{ antialias: true, alpha: false, powerPreference: "high-performance", toneMapping: THREE.ACESFilmicToneMapping }}
      >
        <Suspense fallback={null}><JarvisScene state={state} audioSignal={audioSignal} /></Suspense>
      </Canvas>
    </div>
  );
}
