import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { JARVIS_COLORS } from "./sceneConfig";
import type { Point3 } from "./sceneModel";

interface InnerStructuresProps { state: AIState; }

function PartialBand({ radius, tilt, speed, phase, state, index }: { radius: number; tilt: [number, number, number]; speed: number; phase: number; state: AIState; index: number }) {
  const group = useRef<THREE.Group>(null);
  const fragments = useMemo(() => Array.from({ length: 6 + index }, (_, fragmentIndex) => {
    const start = phase + fragmentIndex * (0.67 + index * 0.025);
    const length = 0.18 + ((fragmentIndex * 5 + index) % 4) * 0.095;
    return Array.from({ length: 16 }, (_, pointIndex) => {
      const angle = start + (pointIndex / 15) * length;
      const wobble = 1 + Math.sin(angle * (3 + index) + fragmentIndex) * 0.018;
      return [Math.cos(angle) * radius * wobble, Math.sin(angle) * radius * wobble, Math.sin(angle * 2 + index) * 0.055] as Point3;
    });
  }), [index, phase, radius]);

  useFrame(({ clock }) => {
    if (!group.current) return;
    const modifier = state === "thinking" ? 1.45 : state === "offline" ? 0.08 : 1;
    group.current.rotation.z = clock.getElapsedTime() * speed * modifier;
  });

  return <group ref={group} rotation={tilt}>{fragments.map((points, fragmentIndex) => <Line key={fragmentIndex} points={points} color={fragmentIndex % 4 === 0 ? JARVIS_COLORS.highlight : JARVIS_COLORS.secondary} transparent opacity={state === "offline" ? 0.025 : 0.16 + (fragmentIndex % 3) * 0.08} lineWidth={fragmentIndex % 4 === 0 ? 0.85 : 0.38} depthWrite={false} />)}</group>;
}

export function InnerStructures({ state }: InnerStructuresProps) {
  return <group><PartialBand radius={0.98} tilt={[0.25, -0.44, 0.16]} speed={0.08} phase={0.12} state={state} index={0} /><PartialBand radius={1.22} tilt={[0.82, 0.31, -0.38]} speed={-0.052} phase={0.73} state={state} index={1} /><PartialBand radius={1.48} tilt={[-0.47, 0.72, 0.49]} speed={0.031} phase={1.41} state={state} index={2} /></group>;
}
