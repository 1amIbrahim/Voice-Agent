import { EffectComposer, Bloom, Vignette, Noise } from "@react-three/postprocessing";

export function CorePostProcessing() {
  return (
    <EffectComposer multisampling={0}>
      <Bloom intensity={0.48} luminanceThreshold={0.76} luminanceSmoothing={0.12} mipmapBlur radius={0.34} />
      <Vignette offset={0.16} darkness={0.72} />
      <Noise opacity={0.012} />
    </EffectComposer>
  );
}
