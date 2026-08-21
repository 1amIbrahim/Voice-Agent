import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { GlowLine } from "./GlowLine";

interface OrbitalSystemProps { state: AIState; }
interface OrbitProps { radiusX: number; radiusY: number; rotation: [number, number, number]; speed: number; phase: number; opacity: number; state: AIState; seed: number; fragmentCount: number; }

function randomFor(seed: number) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function BrokenOrbit({ radiusX, radiusY, rotation, speed, phase, opacity, state, seed, fragmentCount }: OrbitProps) {
  const group = useRef<THREE.Group>(null);
  const nodes = useRef<THREE.Group>(null);
  const fragments = useMemo(() => {
    const random = randomFor(seed);
    let cursor = phase;
    return Array.from({ length: fragmentCount }, (_, fragmentIndex) => {
      cursor += 0.14 + random() * 0.28;
      const length = 0.12 + random() * (fragmentIndex % 3 === 0 ? 0.5 : 0.3);
      const samples = 8 + Math.floor(length * 28);
      const wobble = (random() - 0.5) * 0.08;
      const points: [number, number, number][] = [];
      for (let index = 0; index < samples; index += 1) {
        const angle = cursor + (index / (samples - 1)) * length;
        const radiusNoise = 1 + Math.sin(angle * (2.4 + seed % 3) + seed) * wobble;
        points.push([Math.cos(angle) * radiusX * radiusNoise, Math.sin(angle) * radiusY * radiusNoise, Math.sin(angle * 2.7 + seed) * 0.035]);
      }
      cursor += length;
      return { points, opacity: 0.35 + random() * 0.65, width: 0.3 + random() * 0.75 };
    });
  }, [fragmentCount, phase, radiusX, radiusY, seed]);

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    const factor = state === "offline" ? 0.08 : state === "thinking" ? 1.38 : 1;
    if (group.current) {
      group.current.rotation.z = time * speed * factor;
      group.current.rotation.x = Math.sin(time * 0.11 + seed) * 0.055;
    }
    if (nodes.current) nodes.current.rotation.z = -time * speed * factor * 1.8;
  });

  const alpha = opacity * (state === "offline" ? 0.14 : 1);
  return (
    <group ref={group} rotation={rotation}>
      {fragments.map((fragment, index) => <GlowLine key={index} points={fragment.points} color={index % 4 === 0 ? "#fff7cc" : "#ffd86d"} haloColor="#cf8a1f" opacity={alpha * fragment.opacity} lineWidth={fragment.width} />)}
      <group ref={nodes}>{fragments.filter((_, index) => index % 3 === 0).map((fragment, index) => { const point = fragment.points[fragment.points.length - 1]; return <mesh key={index} position={point}><sphereGeometry args={[index % 2 === 0 ? 0.025 : 0.015, 8, 8]} /><meshBasicMaterial color="#fff5c7" transparent opacity={alpha + 0.16} toneMapped={false} /></mesh>; })}</group>
    </group>
  );
}

function BrokenTickBand({ state }: OrbitalSystemProps) {
  const group = useRef<THREE.Group>(null);
  const ticks = useMemo(() => Array.from({ length: 88 }, (_, index) => {
    if (index % 11 === 3 || index % 13 === 7 || (index > 51 && index < 60)) return null;
    const angle = (index / 88) * Math.PI * 2 + Math.sin(index * 3.7) * 0.008;
    const major = index % 7 === 0;
    const inner = major ? 1.72 : 1.81 + (index % 4) * 0.012;
    const outer = major ? 1.9 : 1.86;
    return { major, points: [[Math.cos(angle) * inner, Math.sin(angle) * inner, 0], [Math.cos(angle) * outer, Math.sin(angle) * outer, 0]] as [number, number, number][] };
  }).filter((tick): tick is NonNullable<typeof tick> => tick !== null), []);
  useFrame(({ clock }) => { if (group.current) group.current.rotation.z = -clock.getElapsedTime() * (state === "offline" ? 0.004 : 0.033); });
  return <group ref={group} rotation={[1.06, 0.12, 0.4]}>{ticks.map((tick, index) => <Line key={index} points={tick.points} color={tick.major ? "#ffe99a" : "#916713"} transparent opacity={state === "offline" ? 0.025 : tick.major ? 0.36 : 0.15} lineWidth={tick.major ? 0.78 : 0.34} />)}</group>;
}

export function OrbitalSystem({ state }: OrbitalSystemProps) {
  return <group><BrokenTickBand state={state} /><BrokenOrbit radiusX={1.65} radiusY={0.62} rotation={[0.71, -0.34, 0.14]} speed={0.1} phase={0.2} opacity={0.48} state={state} seed={17} fragmentCount={11} /><BrokenOrbit radiusX={1.38} radiusY={0.89} rotation={[-0.48, 0.74, -0.36]} speed={-0.17} phase={1.1} opacity={0.31} state={state} seed={29} fragmentCount={9} /><BrokenOrbit radiusX={0.92} radiusY={0.5} rotation={[1.12, 0.24, 0.62]} speed={0.31} phase={2.25} opacity={0.64} state={state} seed={43} fragmentCount={8} /><BrokenOrbit radiusX={2.18} radiusY={1.14} rotation={[0.25, -0.56, -0.7]} speed={-0.045} phase={-0.8} opacity={0.19} state={state} seed={61} fragmentCount={13} /><BrokenOrbit radiusX={2.65} radiusY={0.78} rotation={[-0.84, 0.22, 0.85]} speed={0.026} phase={0.5} opacity={0.13} state={state} seed={79} fragmentCount={15} /></group>;
}
