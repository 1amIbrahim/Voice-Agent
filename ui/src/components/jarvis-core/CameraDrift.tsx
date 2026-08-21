import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { JARVIS_SCENE } from "./sceneConfig";

export function CameraDrift() {
  const camera = useThree((state) => state.camera);
  const target = useMemo(() => new THREE.Vector3(0, 0, -0.08), []);

  useFrame(({ clock, pointer }) => {
    const time = clock.getElapsedTime();
    camera.position.x = Math.sin(time * 0.075) * JARVIS_SCENE.camera.drift + pointer.x * 0.025;
    camera.position.y = Math.cos(time * 0.061) * JARVIS_SCENE.camera.drift + pointer.y * 0.018;
    camera.lookAt(target);
  });

  return null;
}
