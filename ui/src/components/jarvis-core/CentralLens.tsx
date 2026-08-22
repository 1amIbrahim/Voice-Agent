import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AudioReactiveSignal } from "../../audio/audioReactivity";
import type { AIState } from "../../types/ui";
import { JARVIS_COLORS, JARVIS_SCENE } from "./sceneConfig";
import type { Point3 } from "./sceneModel";

interface CentralLensProps { state: AIState; audioSignal: AudioReactiveSignal; }

const activityFor = (state: AIState) => ({ idle: 0.34, listening: 0.7, thinking: 1, executing: 0.9, speaking: 0.76, alert: 0.84, offline: 0.04 })[state];

function arcPoints(radius: number, start: number, length: number, z: number): Point3[] {
  return Array.from({ length: 28 }, (_, index) => {
    const angle = start + (index / 27) * length;
    return [Math.cos(angle) * radius, Math.sin(angle) * radius, z];
  });
}

function MechanicalRing({ radius, tube, depth, z, color, opacity, speed, state, phase }: { radius: number; tube: number; depth: number; z: number; color: string; opacity: number; speed: number; state: AIState; phase: number }) {
  const group = useRef<THREE.Group>(null);
  const segments = useMemo(() => Array.from({ length: 9 }, (_, index) => {
    if ((index + Math.round(phase * 10)) % 7 === 2) return null;
    const angle = (index / 9) * Math.PI * 2 + phase;
    const length = 0.42 + (index % 4) * 0.085;
    return { angle, length, points: arcPoints(radius, angle, length, z + depth * 0.52) };
  }).filter((item): item is NonNullable<typeof item> => item !== null), [depth, phase, radius, z]);

  useFrame(({ clock }) => {
    if (!group.current) return;
    const stateSpeed = state === "thinking" ? 1.5 : state === "offline" ? 0.08 : 1;
    group.current.rotation.z = clock.getElapsedTime() * speed * stateSpeed;
  });

  return (
    <group ref={group}>
      {segments.map((segment, index) => (
        <group key={index}>
          <mesh position={[0, 0, z]} rotation={[0, 0, segment.angle]}>
            <torusGeometry args={[radius, tube, 5, 24, segment.length]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.26} transparent opacity={state === "offline" ? 0.025 : opacity * (0.38 + (index % 3) * 0.1)} roughness={0.42} metalness={0.58} depthWrite={false} />
          </mesh>
          <Line points={segment.points} color={index % 3 === 0 ? JARVIS_COLORS.bright : color} transparent opacity={state === "offline" ? 0.03 : opacity * 0.82} lineWidth={index % 3 === 0 ? 0.82 : 0.38} depthWrite={false} />
          {index % 3 === 0 && <Line points={arcPoints(radius - depth * 0.32, segment.angle + 0.04, segment.length * 0.72, z - depth)} color={JARVIS_COLORS.dim} transparent opacity={state === "offline" ? 0.015 : opacity * 0.38} lineWidth={0.28} depthWrite={false} />}
        </group>
      ))}
    </group>
  );
}

function ApertureAssembly({ state, audioSignal }: CentralLensProps) {
  const blades = useRef<THREE.Group>(null);
  const iris = useMemo(() => Array.from({ length: 0 }, (_, index) => index), []);

  useFrame(({ clock }) => {
    if (!blades.current) return;
    const audio = audioSignal.current.level;
    blades.current.rotation.z = -clock.getElapsedTime() * (state === "thinking" ? 0.18 : 0.045);
    blades.current.scale.setScalar(1 + audio * 0.035);
  });

  return (
    <group ref={blades} position={[0, 0, 0.16]}>
      {iris.map((index) => {
        const angle = (index / iris.length) * Math.PI * 2;
        return (
          <mesh key={index} position={[Math.cos(angle) * 0.22, Math.sin(angle) * 0.22, -0.025]} rotation={[0.08 * Math.sin(angle), 0.08 * Math.cos(angle), angle - 0.48]}>
            <shapeGeometry args={[new THREE.Shape().moveTo(0.04, -0.018).lineTo(0.27, -0.008).lineTo(0.22, 0.038).lineTo(0.055, 0.026).closePath()]} />
            <meshStandardMaterial color={index % 4 === 0 ? JARVIS_COLORS.highlight : JARVIS_COLORS.secondary} emissive={JARVIS_COLORS.primary} emissiveIntensity={0.2} transparent opacity={state === "offline" ? 0.03 : 0.35} side={THREE.DoubleSide} roughness={0.45} metalness={0.5} depthWrite={false} />
          </mesh>
        );
      })}
    </group>
  );
}

function LensSpokes({ state }: { state: AIState }) {
  const spokes = useMemo(() => Array.from({ length: 18 }, (_, index) => {
    if (index % 8 === 3) return null;
    const angle = (index / 18) * Math.PI * 2;
    const inner = 0.49 + (index % 3) * 0.025;
    const outer = 0.88 + (index % 4) * 0.06;
    return [[Math.cos(angle) * inner, Math.sin(angle) * inner, 0.03], [Math.cos(angle) * outer, Math.sin(angle) * outer, -0.16]] as Point3[];
  }).filter((path): path is Point3[] => path !== null), []);

  return <group>{spokes.map((points, index) => <Line key={index} points={points} color={index % 5 === 0 ? JARVIS_COLORS.bright : JARVIS_COLORS.primary} transparent opacity={state === "offline" ? 0.025 : index % 5 === 0 ? 0.76 : 0.3} lineWidth={index % 5 === 0 ? 1.05 : 0.48} depthWrite={false} />)}</group>;
}

export function CentralLens({ state, audioSignal }: CentralLensProps) {
  const root = useRef<THREE.Group>(null);
  const energy = useRef<THREE.MeshBasicMaterial>(null);
  const coreSphereMesh = useRef<THREE.Mesh>(null);
  const coreSphereMaterial = useRef<THREE.MeshStandardMaterial>(null);
  const rear = useRef<THREE.Group>(null);
  const light = useRef<THREE.PointLight>(null);
  const activity = activityFor(state);

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    const { level, bass, mid } = audioSignal.current;
    
    if (root.current) {
      root.current.rotation.x = -0.16 + Math.sin(time * 0.12) * 0.018;
      root.current.rotation.y = 0.38 + Math.sin(time * 0.09) * 0.032;
      root.current.scale.setScalar(JARVIS_SCENE.lens.scale * (1 + bass * 0.12));
    }
    
    if (rear.current) rear.current.rotation.z = time * 0.024;
    if (energy.current) energy.current.opacity = Math.min(0.92, (state === "offline" ? 0.018 : 0.18 + activity * 0.13) + level * 0.32);
    if (light.current) light.current.intensity = (state === "offline" ? 0.08 : 1.7 + activity * 1.1) + mid * 3.2;

    // Reactively drive the Core 3D Sphere scaling and glow intensity using voice frequencies
    if (state !== "offline") {
      if (coreSphereMesh.current) {
        // High frequency scale vibrations matching the bass beats
        coreSphereMesh.current.scale.setScalar(1 + bass * 0.28);
      }
      if (coreSphereMaterial.current) {
        // Unclamped radiant emissions spike past the Bloom barrier based on volume thresholds
        coreSphereMaterial.current.emissiveIntensity = 2.0 + activity * 1.5 + level * 4.0;
      }
    } else {
      if (coreSphereMesh.current) coreSphereMesh.current.scale.setScalar(1);
      if (coreSphereMaterial.current) coreSphereMaterial.current.emissiveIntensity = 0.05;
    }
  });

  return (
    <group ref={root}>
      <pointLight ref={light} color={JARVIS_COLORS.primary} intensity={2.4} distance={3.2} decay={2} />
      
      <group ref={rear} position={[0, 0, -0.5]}>
        <mesh position={[0, 0, -0.18]}><ringGeometry args={[0.72, 0.82, 72]} /><meshBasicMaterial color={JARVIS_COLORS.dim} transparent opacity={state === "offline" ? 0.02 : 0.2} side={THREE.DoubleSide} /></mesh>
        <mesh position={[0, 0, -0.28]}><torusGeometry args={[0.54, 0.022, 6, 72]} /><meshBasicMaterial color={JARVIS_COLORS.secondary} transparent opacity={state === "offline" ? 0.02 : 0.26} /></mesh>
      </group>
      
      <MechanicalRing radius={0.94} tube={0.024} depth={0.16} z={-0.3} color={JARVIS_COLORS.dim} opacity={0.46} speed={0.035} state={state} phase={0.16} />
      <LensSpokes state={state} />
      <MechanicalRing radius={0.68} tube={0.03} depth={0.13} z={-0.06} color={JARVIS_COLORS.secondary} opacity={0.20} speed={-0.07} state={state} phase={0.42} />
      <ApertureAssembly state={state} audioSignal={audioSignal} />
      <MechanicalRing radius={0.44} tube={0.018} depth={0.08} z={0.2} color={JARVIS_COLORS.highlight} opacity={0.30} speed={0.12} state={state} phase={0.05} />
      
      <mesh position={[0, 0, 0.235]}><torusGeometry args={[0.25, 0.02, 8, 72]} /><meshBasicMaterial color={JARVIS_COLORS.bright} transparent opacity={state === "offline" ? 0.04 : 0.7} toneMapped={false} /></mesh>
      <mesh position={[0, 0, 0.22]}><circleGeometry args={[0.215, 64]} /><meshBasicMaterial color={JARVIS_COLORS.void} /></mesh>
      
      {/* Upgraded 3D Core Glowing Sphere */}
      <mesh ref={coreSphereMesh} position={[0, 0, -0.55]}>
        <sphereGeometry args={[0.075, 64, 64]} />
        <meshStandardMaterial 
          ref={coreSphereMaterial}
          color={JARVIS_COLORS.bright} 
          emissive={JARVIS_COLORS.bright}
          emissiveIntensity={2.5}
          toneMapped={false}
          roughness={0.1}
          metalness={0.1}
        />
      </mesh>

      <mesh position={[0, 0, 0.228]}><ringGeometry args={[0.106, 0.132, 64]} /><meshBasicMaterial ref={energy} color={JARVIS_COLORS.bright} transparent side={THREE.DoubleSide} depthWrite={false} /></mesh>
    </group>
  );
}
