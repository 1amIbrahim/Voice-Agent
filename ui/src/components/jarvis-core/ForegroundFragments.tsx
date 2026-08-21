import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { JARVIS_COLORS } from "./sceneConfig";
import type { Point3 } from "./sceneModel";

interface ForegroundFragmentsProps { state: AIState; }

export function ForegroundFragments({ state }: ForegroundFragmentsProps) {
  const root = useRef<THREE.Group>(null);
  const fragments = useMemo(() => [
    [[-3.25, 1.58, 1.55], [-2.78, 1.36, 1.42], [-2.5, 0.98, 1.28], [-2.18, 0.8, 1.18]],
    [[2.68, 1.76, 1.22], [2.31, 1.39, 1.12], [2.14, 1.04, 1.02], [1.78, 0.87, 0.94]],
    [[-2.98, -1.62, 1.35], [-2.42, -1.38, 1.21], [-2.14, -1.05, 1.06]],
    [[2.91, -1.45, 1.48], [2.52, -1.24, 1.28], [2.26, -0.88, 1.08]],
  ] as Point3[][], []);

  useFrame(({ clock }) => {
    if (!root.current) return;
    const time = clock.getElapsedTime();
    root.current.position.x = Math.sin(time * 0.08) * 0.035;
    root.current.position.y = Math.cos(time * 0.065) * 0.025;
  });

  return <group ref={root}>{fragments.map((points, index) => <group key={index}><Line points={points} color={index % 2 === 0 ? JARVIS_COLORS.secondary : JARVIS_COLORS.primary} transparent opacity={state === "offline" ? 0.015 : 0.18} lineWidth={1.35} depthWrite={false} /><mesh position={points[1]} rotation={[0.2, 0.5, index * 0.7]}><boxGeometry args={[0.18, 0.06, 0.035]} /><meshBasicMaterial color={JARVIS_COLORS.secondary} transparent opacity={state === "offline" ? 0.02 : 0.16} depthWrite={false} /></mesh></group>)}</group>;
}
