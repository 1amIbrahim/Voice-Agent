import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { GlowLine } from "./GlowLine";

interface EventPulseSystemProps { state: AIState; }
interface PulseProps { state: AIState; offset: number; rotation: [number, number, number]; }

function BrokenPulse({ state, offset, rotation }: PulseProps) {
  const group = useRef<THREE.Group>(null);
  const fragments = useMemo(() => [
    { start: 0.12, length: 0.65 },
    { start: 1.15, length: 0.31 },
    { start: 1.82, length: 0.9 },
    { start: 3.28, length: 0.45 },
    { start: 4.2, length: 1.08 },
    { start: 5.72, length: 0.2 },
  ].map(({ start, length }, fragmentIndex) => ({
    opacity: 0.32 + (fragmentIndex % 3) * 0.22,
    points: Array.from({ length: 18 }, (_, index) => {
      const angle = start + index / 17 * length;
      const radius = 0.48 + Math.sin(angle * 4 + fragmentIndex) * 0.012;
      return [Math.cos(angle) * radius, Math.sin(angle) * radius, 0] as [number, number, number];
    }),
  })), []);
  useFrame(({ clock }) => {
    if (!group.current) return;
    const active = state === "executing" || state === "alert" || state === "listening";
    const progress = active ? (clock.getElapsedTime() * 0.2 + offset) % 1 : 0;
    group.current.visible = active;
    group.current.scale.setScalar(0.4 + progress * 2.65);
    group.current.rotation.z = clock.getElapsedTime() * (offset === 0 ? 0.09 : -0.06);
    group.current.children.forEach((child, index) => {
      child.traverse((object) => {
        const line = object as THREE.Line;
        if (!line.material) return;
        const material = line.material as THREE.LineBasicMaterial;
        material.opacity = (1 - progress) * fragments[index].opacity * (state === "alert" ? 0.42 : 0.28);
      });
    });
  });
  const color = state === "alert" ? "#ff7a36" : "#e6ad35";
  return <group ref={group} rotation={rotation}>{fragments.map((fragment, index) => <GlowLine key={index} points={fragment.points} color={color} haloColor="#a86617" opacity={0} lineWidth={index % 2 === 0 ? 0.7 : 0.38} />)}</group>;
}

export function EventPulseSystem({ state }: EventPulseSystemProps) {
  return <group><BrokenPulse state={state} offset={0} rotation={[1.1, 0.12, -0.2]} /><BrokenPulse state={state} offset={0.5} rotation={[0.7, -0.45, 0.3]} /></group>;
}
