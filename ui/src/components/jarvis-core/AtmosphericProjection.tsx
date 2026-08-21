import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";

interface AtmosphericProjectionProps { state: AIState; }

export function AtmosphericProjection({ state }: AtmosphericProjectionProps) {
  const scan = useRef<THREE.Group>(null);
  const markers = useMemo(() => Array.from({ length: 24 }, (_, index) => {
    const angle = index / 24 * Math.PI * 2;
    const radius = 2.35 + (index % 4) * 0.17;
    return [Math.cos(angle) * radius, Math.sin(angle) * radius * 0.55, -0.7 - (index % 3) * 0.2] as [number, number, number];
  }), []);
  useFrame(({ clock }) => {
    if (!scan.current) return;
    scan.current.rotation.z = clock.getElapsedTime() * (state === "offline" ? 0.004 : 0.06);
    scan.current.rotation.y = Math.sin(clock.getElapsedTime() * 0.12) * 0.16;
  });
  const opacity = state === "offline" ? 0.025 : 0.12;
  return <group><group ref={scan} rotation={[0.1, 0, 0.22]}><Line points={[[0, 0, -0.9], [2.85, 0, -0.9]]} color="#d79d2f" transparent opacity={state === "listening" ? 0.34 : opacity} lineWidth={0.5} /></group>{markers.map((position, index) => <mesh key={index} position={position} rotation={[0, 0, index * 0.22]}><planeGeometry args={[index % 5 === 0 ? 0.12 : 0.05, 0.008]} /><meshBasicMaterial color={index % 5 === 0 ? "#ffdf7a" : "#715115"} transparent opacity={opacity} side={THREE.DoubleSide} /></mesh>)}</group>;
}
