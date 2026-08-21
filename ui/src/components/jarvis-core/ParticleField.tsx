import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";
import type { AIState } from "../../types/ui";
import { createSeededRandom } from "./sceneModel";
import { JARVIS_COLORS, JARVIS_SCENE } from "./sceneConfig";

interface ParticleFieldProps { state: AIState; audioSignal: AudioReactiveSignal; }
interface LayerProps { count: number; inner: number; outer: number; scale: [number, number, number]; color: string; size: number; opacity: number; speed: number; seed: number; audioSignal: AudioReactiveSignal; audioWeight: number; state: AIState; }

const particleActivity = (state: AIState) => ({ idle: 0.3, listening: 0.64, thinking: 1, executing: 0.86, speaking: 0.7, alert: 0.76, offline: 0.04 })[state];

function ParticleLayer({ count, inner, outer, scale, color, size, opacity, speed, seed, audioSignal, audioWeight, state }: LayerProps) {
  const points = useRef<THREE.Points>(null);
  const material = useRef<THREE.PointsMaterial>(null);
  const activity = particleActivity(state);
  const positions = useMemo(() => {
    const random = createSeededRandom(seed);
    const values = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = random() * Math.PI * 2;
      const elevation = Math.asin(random() * 2 - 1);
      const cluster = index % 5 === 0 ? 0.28 + random() * 0.26 : Math.pow(random(), 1.35);
      const gap = Math.sin(angle * 2.3) + Math.cos(elevation * 3.8);
      const radius = inner + cluster * (outer - inner) * (gap < -1.15 ? 0.72 : 1);
      const asymmetry = 0.86 + Math.sin(angle * 3.2 + elevation) * 0.12;
      values[index * 3] = Math.cos(angle) * Math.cos(elevation) * radius * asymmetry * scale[0];
      values[index * 3 + 1] = Math.sin(elevation) * radius * scale[1];
      values[index * 3 + 2] = Math.sin(angle) * Math.cos(elevation) * radius * scale[2];
    }
    return values;
  }, [count, inner, outer, scale, seed]);

  useFrame(({ clock }) => {
    if (!points.current) return;
    const time = clock.getElapsedTime();
    points.current.rotation.y = time * speed * (0.7 + activity * 0.45);
    points.current.rotation.x = Math.sin(time * speed * 0.6 + seed) * 0.025;
    const audio = audioSignal.current.mid * audioWeight;
    points.current.scale.setScalar(1 - activity * 0.012 + Math.sin(time * 0.31 + seed) * 0.006 + audio * 0.025);
    if (material.current) {
      material.current.opacity = Math.min(0.9, opacity * (0.42 + activity * 0.58) + audio * 0.13);
      material.current.size = size + audioSignal.current.treble * audioWeight * 0.004;
    }
  });

  return <points ref={points}><bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry><pointsMaterial ref={material} color={color} size={size} sizeAttenuation transparent opacity={opacity} blending={THREE.AdditiveBlending} depthWrite={false} /></points>;
}

export function ParticleField({ state, audioSignal }: ParticleFieldProps) {
  return <group><ParticleLayer count={JARVIS_SCENE.particles.inner} inner={0.35} outer={1.18} scale={[1.18, 0.86, 0.92]} color={JARVIS_COLORS.bright} size={0.009} opacity={0.75} speed={0.052} seed={103} state={state} audioSignal={audioSignal} audioWeight={1} /><ParticleLayer count={JARVIS_SCENE.particles.middle} inner={0.9} outer={2.08} scale={[1.08, 0.82, 0.92]} color={JARVIS_COLORS.primary} size={0.012} opacity={0.46} speed={-0.021} seed={307} state={state} audioSignal={audioSignal} audioWeight={0.42} /><ParticleLayer count={JARVIS_SCENE.particles.atmospheric} inner={1.8} outer={3.15} scale={[1.16, 0.78, 1]} color={JARVIS_COLORS.secondary} size={0.014} opacity={0.22} speed={0.009} seed={701} state={state} audioSignal={audioSignal} audioWeight={0.12} /></group>;
}
