import { Line } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import * as THREE from "three";
import type { AIState } from "../../types/ui";
import type { JarvisSceneModel } from "./sceneModel";
import { JARVIS_COLORS } from "./sceneConfig";

interface OuterShellFragmentsProps { state: AIState; model: JarvisSceneModel; }

function ShellLayer({ state, model, scale, opacity, speed, rotation }: OuterShellFragmentsProps & { scale: number; opacity: number; speed: number; rotation: [number, number, number] }) {
  const root = useRef<THREE.Group>(null);
  const fragmentGroups = useRef<Array<THREE.Group | null>>([]);
  const nodeGeometry = useMemo(() => new THREE.OctahedronGeometry(0.018, 0), []);
  const panelGeometry = useMemo(() => {
    const vertices = model.nodes.flatMap((node) => node.panel ? [
      ...node.panel[0], ...node.panel[1], ...node.panel[2],
      ...node.panel[0], ...node.panel[2], ...node.panel[3],
    ] : []);
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
    return geometry;
  }, [model]);
  const offline = state === "offline";

  useFrame(({ clock }) => {
    const time = clock.getElapsedTime();
    if (root.current) root.current.rotation.y = time * speed + Math.sin(time * 0.047) * 0.025;
    fragmentGroups.current.forEach((fragment, index) => {
      if (!fragment) return;
      const visibility = 0.55 + Math.sin(time * (0.15 + (index % 7) * 0.009) + index * 1.31) * 0.38;
      fragment.visible = offline || visibility > 0.12;
    });
  });

  return (
    <group ref={root} scale={scale} rotation={rotation}>
      <mesh geometry={panelGeometry}>
        <meshBasicMaterial color={JARVIS_COLORS.secondary} transparent opacity={offline ? 0.01 : opacity * 0.12} side={THREE.DoubleSide} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
      {model.nodes.map((node, index) => (
        <group key={node.id} ref={(value) => { fragmentGroups.current[index] = value; }}>
          {node.fragments.map((fragment, fragmentIndex) => <Line key={fragmentIndex} points={fragment} color={(index + fragmentIndex) % 9 === 0 ? JARVIS_COLORS.highlight : JARVIS_COLORS.secondary} transparent opacity={offline ? 0.018 : opacity * (0.42 + node.intensity * 0.58)} lineWidth={(index + fragmentIndex) % 8 === 0 ? 0.92 : 0.42} depthWrite={false} />)}
          {index % 3 === 0 && <mesh position={node.position} geometry={nodeGeometry} scale={index % 9 === 0 ? 1.9 : 1}><meshBasicMaterial color={index % 9 === 0 ? JARVIS_COLORS.bright : JARVIS_COLORS.primary} transparent opacity={offline ? 0.025 : opacity * (0.7 + node.intensity * 0.45)} toneMapped={false} /></mesh>}
        </group>
      ))}
    </group>
  );
}

export function OuterShellFragments({ state, model }: OuterShellFragmentsProps) {
  return <group><ShellLayer state={state} model={model} scale={0.86} opacity={0.2} speed={-0.003} rotation={[-0.12, -0.26, 0.08]} /><ShellLayer state={state} model={model} scale={1} opacity={0.56} speed={0.006} rotation={[0.04, 0, -0.02]} /><ShellLayer state={state} model={model} scale={1.14} opacity={0.16} speed={-0.004} rotation={[0.22, 0.3, 0.11]} /></group>;
}
