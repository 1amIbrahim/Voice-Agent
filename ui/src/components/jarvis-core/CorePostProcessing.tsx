import { EffectComposer, Bloom, Vignette, Noise } from "@react-three/postprocessing";

export function CorePostProcessing() {
  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={0.82} luminanceThreshold={0.62} luminanceSmoothing={0.18} mipmapBlur radius={0.58} />
      <Vignette offset={0.14} darkness={0.82} />
      <Noise opacity={0.018} />
    </EffectComposer>
  );
}
