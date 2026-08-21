import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";

interface ParticleFieldProps { state: AIState; audioSignal: AudioReactiveSignal; }
interface LayerProps { count: number; inner: number; outer: number; scale: [number, number, number]; color: string; size: number; opacity: number; speed: number; activity: number; seed: number; audioSignal: AudioReactiveSignal; audioWeight: number; }

const particleActivity = (state: AIState): number => ({ idle: 0.34, listening: 0.58, thinking: 1, executing: 0.88, speaking: 0.7, alert: 0.66, offline: 0.06 })[state];

function seeded(seed: number) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function ParticleLayer({ count, inner, outer, scale, color, size, opacity, speed, activity, seed, audioSignal, audioWeight }: LayerProps) {
  const points = useRef<THREE.Points>(null);
  const material = useRef<THREE.PointsMaterial>(null);
  const positions = useMemo(() => {
    const random = seeded(seed);
    const values = new Float32Array(count * 3);
    for (let index = 0; index < count; index += 1) {
      const angle = random() * Math.PI * 2;
      const elevation = Math.asin(random() * 2 - 1);
      const distribution = random() < 0.7 ? Math.pow(random(), 1.7) : random();
      const radius = inner + distribution * (outer - inner);
      const asymmetry = 0.85 + Math.sin(angle * 3.2 + elevation) * 0.13 + Math.cos(elevation * 5) * 0.08;
      values[index * 3] = Math.cos(angle) * Math.cos(elevation) * radius * asymmetry * scale[0];
      values[index * 3 + 1] = Math.sin(elevation) * radius * scale[1];
      values[index * 3 + 2] = Math.sin(angle) * Math.cos(elevation) * radius * scale[2];
    }
    return values;
  }, [count, inner, outer, scale, seed]);

  useFrame(({ clock }) => {
    if (!points.current) return;
    const time = clock.getElapsedTime();
    points.current.rotation.y = time * speed * (0.7 + activity);
    points.current.rotation.x = Math.sin(time * speed * 0.7 + seed) * 0.06;
    points.current.rotation.z = Math.cos(time * 0.08 + seed) * 0.09;
    const audio = audioSignal.current.mid * audioWeight;
    const convergence = 1 - activity * 0.035 + Math.sin(time * (0.37 + speed)) * 0.012 + audio * 0.1;
    points.current.scale.setScalar(convergence);
    if (material.current) {
      material.current.opacity = Math.min(1, opacity * (0.45 + activity * 0.55) + audio * 0.35);
      material.current.size = size + audioSignal.current.treble * audioWeight * 0.012;
    }
  });

  return (
    <points ref={points}>
      <bufferGeometry><bufferAttribute attach="attributes-position" args={[positions, 3]} /></bufferGeometry>
      <pointsMaterial ref={material} color={color} size={size} sizeAttenuation transparent opacity={opacity} blending={THREE.AdditiveBlending} depthWrite={false} />
    </points>
  );
}

export function ParticleField({ state, audioSignal }: ParticleFieldProps) {
  const activity = particleActivity(state);
  return (
    <group>
      <ParticleLayer count={1450} inner={0.18} outer={0.95} scale={[1.25, 0.9, 0.78]} color="#fff4bd" size={0.012} opacity={0.72} speed={0.082} activity={activity} seed={103} audioSignal={audioSignal} audioWeight={1} />
      <ParticleLayer count={920} inner={0.7} outer={1.68} scale={[1.1, 0.78, 0.88]} color="#e7b13f" size={0.016} opacity={0.46} speed={-0.038} activity={activity} seed={307} audioSignal={audioSignal} audioWeight={0.62} />
      <ParticleLayer count={380} inner={1.45} outer={2.65} scale={[1.1, 0.72, 0.92]} color="#7d5b1a" size={0.019} opacity={0.2} speed={0.018} activity={activity} seed={701} audioSignal={audioSignal} audioWeight={0.25} />
    </group>
  );
}
