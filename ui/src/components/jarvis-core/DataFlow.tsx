import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import { GlowLine } from "./GlowLine";

interface DataFlowProps { state: AIState; }
interface FlowPathProps { state: AIState; index: number; }

function FlowPath({ state, index }: FlowPathProps) {
  const pulse = useRef<THREE.Mesh>(null);
  const curve = useMemo(() => {
    const angle = (index / 7) * Math.PI * 2 + 0.25;
    const start = new THREE.Vector3(Math.cos(angle) * 2.45, Math.sin(angle) * 1.25, Math.sin(angle * 2) * 0.7);
    const middle = new THREE.Vector3(Math.cos(angle + 0.4) * 1.05, Math.sin(angle - 0.24) * 0.65, Math.cos(angle) * 0.42);
    return new THREE.CatmullRomCurve3([start, middle, new THREE.Vector3(0, 0, 0)]);
  }, [index]);
  const path = useMemo(() => curve.getPoints(48).map((point) => [point.x, point.y, point.z] as [number, number, number]), [curve]);
  useFrame(({ clock }) => {
    if (!pulse.current) return;
    const inward = state === "listening" || state === "thinking";
    const active = inward || state === "executing" || state === "speaking";
    pulse.current.visible = active;
    if (!active) return;
    const speed = state === "thinking" ? 0.35 : state === "executing" ? 0.27 : 0.18;
    let progress = (clock.getElapsedTime() * speed + index / 7) % 1;
    if (state === "executing") progress = 1 - progress;
    pulse.current.position.copy(curve.getPoint(progress));
    const scale = state === "speaking" ? 0.8 + Math.sin(clock.getElapsedTime() * 4 + index) * 0.25 : 1;
    pulse.current.scale.setScalar(scale);
  });
  const active = state === "listening" || state === "thinking" || state === "executing" || state === "speaking";
  return <group><GlowLine points={path} color="#ffe59a" haloColor="#b87518" opacity={active ? 0.13 : 0.035} lineWidth={0.35} /><mesh ref={pulse}><sphereGeometry args={[0.035, 10, 10]} /><meshBasicMaterial color="#fff4bd" toneMapped={false} transparent opacity={0.95} /></mesh></group>;
}

export function DataFlow({ state }: DataFlowProps) {
  return <group>{Array.from({ length: 7 }, (_, index) => <FlowPath key={index} state={state} index={index} />)}</group>;
}
