import { MeshTransmissionMaterial } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";

interface EnergyNucleusProps { state: AIState; audioSignal: AudioReactiveSignal; }

const intensityFor = (state: AIState): number => ({ idle: 0.82, listening: 1.12, thinking: 1.42, executing: 1.32, speaking: 1.24, alert: 1.05, offline: 0.13 })[state];

export function EnergyNucleus({ state, audioSignal }: EnergyNucleusProps) {
  const root = useRef<THREE.Group>(null);
  const crystal = useRef<THREE.Mesh>(null);
  const membrane = useRef<THREE.Mesh>(null);
  const aura = useRef<THREE.MeshBasicMaterial>(null);
  const sparks = useRef<THREE.Points>(null);
  const light = useRef<THREE.PointLight>(null);
  const intensity = intensityFor(state);
  const sparkPositions = useMemo(() => {
    const values = new Float32Array(360 * 3);
    for (let index = 0; index < 360; index += 1) {
      const phi = Math.acos(2 * Math.random() - 1);
      const theta = Math.random() * Math.PI * 2;
      const radius = 0.14 + Math.pow(Math.random(), 0.7) * 0.48;
      values[index * 3] = radius * Math.sin(phi) * Math.cos(theta);
      values[index * 3 + 1] = radius * Math.cos(phi);
      values[index * 3 + 2] = radius * Math.sin(phi) * Math.sin(theta);
    }
    return values;
  }, []);

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    const { level, bass, mid, treble } = audioSignal.current;
    const irregular = Math.sin(time * 1.72) * 0.045 + Math.sin(time * 3.93 + 0.8) * 0.019;
    const pulse = 1 + irregular * intensity + bass * 0.22;
    if (root.current) root.current.scale.setScalar(pulse);
    if (crystal.current) {
      crystal.current.rotation.x = time * 0.38;
      crystal.current.rotation.y = -time * 0.52;
      crystal.current.rotation.z = time * 0.17;
    }
    if (membrane.current) {
      membrane.current.rotation.x = -time * 0.13;
      membrane.current.rotation.y = time * (0.2 + treble * 0.08);
      membrane.current.scale.setScalar(1 + Math.sin(time * 1.13) * 0.04 + mid * 0.12);
    }
    if (sparks.current) {
      sparks.current.rotation.y = time * (0.24 + treble * 0.2);
      const material = sparks.current.material as THREE.PointsMaterial;
      material.size = 0.027 + level * 0.025;
      material.opacity = Math.min(1, intensity * 0.7 + mid * 0.55);
    }
    if (light.current) light.current.intensity = intensity * 3.8 + bass * 5.5;
    if (aura.current) aura.current.opacity = 0.035 + intensity * 0.04 + Math.sin(time * 2.4) * 0.008 + level * 0.06;
  });

  return (
    <group ref={root}>
      <pointLight ref={light} color="#ffe7a1" intensity={intensity * 3.8} distance={6} decay={2} />
      <mesh ref={crystal} scale={[0.82, 1.15, 0.9]}>
        <octahedronGeometry args={[0.21, 2]} />
        <meshBasicMaterial color="#fffdf0" toneMapped={false} />
      </mesh>
      <mesh ref={membrane} scale={1.52}>
        <icosahedronGeometry args={[0.22, 3]} />
        <MeshTransmissionMaterial color="#ffd56d" transmission={0.78} thickness={0.25} roughness={0.16} chromaticAberration={0.02} anisotropicBlur={0.12} distortion={0.2} distortionScale={0.14} temporalDistortion={0.08} transparent opacity={0.4} />
      </mesh>
      <mesh scale={2.35}>
        <icosahedronGeometry args={[0.22, 2]} />
        <meshBasicMaterial ref={aura} color="#e9a928" wireframe transparent blending={THREE.AdditiveBlending} depthWrite={false} />
      </mesh>
      <points ref={sparks}>
        <bufferGeometry><bufferAttribute attach="attributes-position" args={[sparkPositions, 3]} /></bufferGeometry>
        <pointsMaterial color="#fff2b5" size={0.027} sizeAttenuation transparent opacity={Math.min(0.95, intensity)} blending={THREE.AdditiveBlending} depthWrite={false} />
      </points>
    </group>
  );
}
