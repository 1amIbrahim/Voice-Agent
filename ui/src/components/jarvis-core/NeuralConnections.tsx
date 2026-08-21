import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { GlowLine } from "./GlowLine";

interface NeuralConnectionsProps { state: AIState; }
interface NeuralPathProps { points: [number, number, number][]; index: number; state: AIState; }

function NeuralPath({ points, index, state }: NeuralPathProps) {
  const pulse = useRef<THREE.Mesh>(null);
  const material = useRef<THREE.MeshBasicMaterial>(null);
  const curve = useMemo(() => new THREE.CatmullRomCurve3(points.map(([x, y, z]) => new THREE.Vector3(x, y, z))), [points]);
  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    const activity = state === "thinking" ? 1 : state === "executing" ? 0.72 : 0.22;
    const cycle = (Math.sin(time * (0.7 + index * 0.03) + index * 2.4) + 1) / 2;
    const active = cycle > 0.78 - activity * 0.28 && state !== "offline";
    if (pulse.current) {
      pulse.current.visible = active;
      pulse.current.position.copy(curve.getPoint((time * 0.24 + index * 0.13) % 1));
    }
    if (material.current) material.current.opacity = active ? 0.95 : 0;
  });
  const baseOpacity = state === "offline" ? 0.015 : state === "thinking" ? 0.24 : 0.08;
  return <group><GlowLine points={points} color="#ffeaa0" haloColor="#bd7f19" opacity={baseOpacity} lineWidth={0.42} /><mesh ref={pulse}><sphereGeometry args={[0.023, 8, 8]} /><meshBasicMaterial ref={material} color="#fff5c5" transparent toneMapped={false} /></mesh></group>;
}

export function NeuralConnections({ state }: NeuralConnectionsProps) {
  const paths = useMemo(() => {
    const values: [number, number, number][][] = [];
    for (let index = 0; index < 18; index += 1) {
      const a = index * 2.399;
      const b = a + 0.7 + (index % 4) * 0.21;
      const radius = 0.45 + (index % 5) * 0.11;
      values.push([
        [Math.cos(a) * radius, Math.sin(a * 1.3) * radius * 0.75, Math.sin(a) * radius * 0.68],
        [Math.cos((a + b) / 2) * radius * 0.55, Math.sin(a + 0.4) * radius * 0.5, Math.cos(b) * radius * 0.35],
        [Math.cos(b) * (radius + 0.18), Math.sin(b * 1.1) * radius * 0.72, Math.sin(b) * radius * 0.62],
      ]);
    }
    return values;
  }, []);
  return <group>{paths.map((path, index) => <NeuralPath key={index} points={path} index={index} state={state} />)}</group>;
}
