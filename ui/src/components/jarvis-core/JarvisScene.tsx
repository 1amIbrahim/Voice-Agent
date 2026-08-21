import { useMemo } from "react";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";
import type { AIState } from "../../types/ui";
import { CameraDrift } from "./CameraDrift";
import { CentralLens } from "./CentralLens";
import { CorePostProcessing } from "./CorePostProcessing";
import { ForegroundFragments } from "./ForegroundFragments";
import { InnerStructures } from "./InnerStructures";
import { OuterShellFragments } from "./OuterShellFragments";
import { ParticleField } from "./ParticleField";
import { StructuralConnections } from "./StructuralConnections";
import { createJarvisSceneModel } from "./sceneModel";
import { JARVIS_COLORS } from "./sceneConfig";

interface JarvisSceneProps { state: AIState; audioSignal: AudioReactiveSignal; }

export function JarvisScene({ state, audioSignal }: JarvisSceneProps) {
  const model = useMemo(createJarvisSceneModel, []);

  return (
    <>
      <color attach="background" args={[JARVIS_COLORS.background]} />
      <fog attach="fog" args={[JARVIS_COLORS.background, 4.8, 9.5]} />
      <ambientLight intensity={0.035} color={JARVIS_COLORS.highlight} />
      <CameraDrift />
      <group rotation={[-0.035, 0.08, -0.015]}>
        <OuterShellFragments state={state} model={model} />
        <StructuralConnections state={state} model={model} />
        <ParticleField state={state} audioSignal={audioSignal} />
        <InnerStructures state={state} />
        <CentralLens state={state} audioSignal={audioSignal} />
        <ForegroundFragments state={state} />
      </group>
      <CorePostProcessing />
    </>
  );
}
