import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { GlowLine } from "./GlowLine";

interface HolographicGeometryProps { state: AIState; }

export function HolographicGeometry({ state }: HolographicGeometryProps) {
  const group = useRef<THREE.Group>(null);
  const rays = useMemo(() => Array.from({ length: 21 }, (_, index) => {
    if (index % 6 === 2 || index % 9 === 5) return null;
    const angle = (index / 21) * Math.PI * 2 + Math.sin(index * 4.1) * 0.055;
    const inner = 0.82 + (index % 4) * 0.13;
    const outer = 1.28 + (index % 5) * 0.31;
    return {
      opacity: 0.4 + (index % 4) * 0.16,
      points: [[Math.cos(angle) * inner, Math.sin(angle) * inner * 0.7, -0.3], [Math.cos(angle) * outer, Math.sin(angle) * outer * 0.64, -0.62]] as [number, number, number][],
    };
  }).filter((ray): ray is NonNullable<typeof ray> => ray !== null), []);
  useFrame(({ clock }) => {
    if (!group.current) return;
    group.current.rotation.z = clock.getElapsedTime() * 0.022;
    group.current.rotation.y = Math.sin(clock.getElapsedTime() * 0.13) * 0.15;
  });
  const opacity = state === "offline" ? 0.035 : state === "listening" ? 0.3 : 0.14;
  return <group ref={group}>{rays.map((ray, index) => <GlowLine key={index} points={ray.points} color={index % 5 === 0 ? "#ffe9a0" : "#c79435"} haloColor="#78500d" opacity={opacity * ray.opacity} lineWidth={index % 4 === 0 ? 0.62 : 0.28} />)}</group>;
}
