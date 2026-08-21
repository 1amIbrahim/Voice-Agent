import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import type { JarvisSceneModel, StructuralPath } from "./sceneModel";
import { JARVIS_COLORS } from "./sceneConfig";

interface StructuralConnectionsProps { state: AIState; model: JarvisSceneModel; }
interface ConnectionProps { state: AIState; path: StructuralPath; index: number; }

function Connection({ state, path, index }: ConnectionProps) {
  const pulse = useRef<THREE.Mesh>(null);
  const pulseMaterial = useRef<THREE.MeshBasicMaterial>(null);
  const curve = useMemo(() => new THREE.CatmullRomCurve3(path.points.map((point) => new THREE.Vector3(...point)), false, "catmullrom", 0.18), [path]);
  const sampled = useMemo(() => curve.getPoints(48).map((point) => [point.x, point.y, point.z] as [number, number, number]), [curve]);
  const isMajor = index % 4 === 0;

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    const activeState = state === "listening" || state === "thinking" || state === "executing" || state === "speaking" || state === "alert";
    const slotActive = ((Math.floor(time * 0.7) + index * 3) % 11) < (state === "thinking" ? 4 : state === "executing" ? 3 : 2);
    const active = activeState && slotActive;
    if (pulse.current) {
      pulse.current.visible = active;
      if (active) {
        let progress = (time * (state === "thinking" ? 0.34 : 0.23) + index * 0.137) % 1;
        if (state === "listening" || state === "thinking") progress = 1 - progress;
        pulse.current.position.copy(curve.getPoint(progress));
      }
    }
    if (pulseMaterial.current) pulseMaterial.current.opacity = active ? 0.95 : 0;
  });

  const stateOpacity = state === "offline" ? 0.012 : state === "executing" ? 0.36 : state === "thinking" ? 0.28 : state === "listening" ? 0.22 : 0.12;
  return (
    <group>
      <Line points={sampled} color={isMajor ? JARVIS_COLORS.highlight : JARVIS_COLORS.secondary} transparent opacity={stateOpacity * (isMajor ? 1 : 0.62)} lineWidth={isMajor ? 0.72 : 0.32} depthWrite={false} />
      {path.branches.map((branch, branchIndex) => <Line key={branchIndex} points={branch} color={JARVIS_COLORS.dim} transparent opacity={stateOpacity * 0.72} lineWidth={0.3} depthWrite={false} />)}
      <mesh ref={pulse} visible={false}>
        <sphereGeometry args={[isMajor ? 0.026 : 0.017, 8, 8]} />
        <meshBasicMaterial ref={pulseMaterial} color={JARVIS_COLORS.bright} transparent toneMapped={false} depthWrite={false} />
      </mesh>
    </group>
  );
}

export function StructuralConnections({ state, model }: StructuralConnectionsProps) {
  return <group>{model.paths.map((path, index) => <Connection key={path.id} state={state} path={path} index={index} />)}</group>;
}
