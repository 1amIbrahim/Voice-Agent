import * as THREE from "three";
import { JARVIS_SCENE } from "./sceneConfig";

export type Point3 = [number, number, number];

export interface ShellNode {
  id: number;
  position: Point3;
  normal: Point3;
  intensity: number;
  fragments: Point3[][];
  panel?: Point3[];
}

export interface StructuralPath {
  id: number;
  nodeId: number;
  points: Point3[];
  branches: Point3[][];
}

export interface JarvisSceneModel {
  nodes: ShellNode[];
  paths: StructuralPath[];
}

export function createSeededRandom(seed: number) {
  let value = seed;
  return () => {
    value = (value * 16807) % 2147483647;
    return (value - 1) / 2147483646;
  };
}

function tuple(vector: THREE.Vector3): Point3 {
  return [vector.x, vector.y, vector.z];
}

function createPatch(position: THREE.Vector3, normal: THREE.Vector3, index: number, random: () => number) {
  const reference = Math.abs(normal.y) > 0.8 ? new THREE.Vector3(1, 0, 0) : new THREE.Vector3(0, 1, 0);
  const tangent = new THREE.Vector3().crossVectors(normal, reference).normalize();
  const bitangent = new THREE.Vector3().crossVectors(normal, tangent).normalize();
  const width = 0.3 + random() * 0.5;
  const height = 0.2 + random() * 0.38;
  const depth = 0.025 + random() * 0.065;
  const fragments: Point3[][] = [];

  const corner = (u: number, v: number, lift = 0) => tuple(
    position.clone()
      .addScaledVector(tangent, u * width)
      .addScaledVector(bitangent, v * height)
      .addScaledVector(normal, lift * depth),
  );

  fragments.push([corner(-0.5, -0.42), corner(-0.12, -0.55, 0.4), corner(0.48, -0.32)]);
  fragments.push([corner(-0.48, -0.32), corner(-0.36, 0.24), corner(0.02, 0.5, 0.65)]);
  if (index % 3 !== 1) fragments.push([corner(-0.18, 0.48), corner(0.28, 0.36, -0.25), corner(0.52, 0.05)]);
  if (index % 4 === 0) fragments.push([corner(-0.38, 0.05), corner(0.12, 0.02), corner(0.42, -0.16)]);
  if (index % 5 === 0) fragments.push([corner(0.08, -0.5), corner(0.04, 0.42)]);

  const panel = index % 6 === 0
    ? [corner(-0.35, -0.25), corner(0.28, -0.2), corner(0.22, 0.25), corner(-0.2, 0.34)]
    : undefined;

  return { fragments, panel };
}

export function createJarvisSceneModel(): JarvisSceneModel {
  const random = createSeededRandom(7411);
  const nodes: ShellNode[] = [];
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));

  for (let index = 0; index < JARVIS_SCENE.shell.nodeCount; index += 1) {
    if (index % 11 === 2 || index % 17 === 7) continue;
    const y = 1 - (index / (JARVIS_SCENE.shell.nodeCount - 1)) * 2;
    const radial = Math.sqrt(1 - y * y);
    const angle = index * goldenAngle + (random() - 0.5) * 0.28;
    const normal = new THREE.Vector3(Math.cos(angle) * radial, y, Math.sin(angle) * radial);
    const radius = JARVIS_SCENE.shell.radius * (0.88 + random() * 0.19);
    const position = normal.clone().multiplyScalar(radius);
    position.x *= 1.1;
    position.y *= 0.88;
    position.z *= 0.94;
    const patch = createPatch(position, normal, index, random);
    nodes.push({
      id: index,
      position: tuple(position),
      normal: tuple(normal),
      intensity: 0.28 + random() * 0.72,
      fragments: patch.fragments,
      panel: patch.panel,
    });
  }

  const pathNodes = nodes.filter((_, index) => index % 2 === 0 || index % 7 === 0).slice(0, 32);
  const paths = pathNodes.map((node, index) => {
    const target = new THREE.Vector3(...node.position);
    const direction = target.clone().normalize();
    const side = new THREE.Vector3(-direction.y, direction.x, direction.z * 0.12).normalize();
    const start = direction.clone().multiplyScalar(0.52 + (index % 4) * 0.04);
    start.z += 0.08 - (index % 3) * 0.05;
    const elbow = target.clone().multiplyScalar(0.45).addScaledVector(side, ((index % 5) - 2) * 0.09);
    const approach = target.clone().multiplyScalar(0.79);
    const branchAnchor = target.clone().multiplyScalar(0.63);
    const branchLength = 0.12 + (index % 4) * 0.045;
    const branches = index % 3 === 0 ? [
      [tuple(branchAnchor.clone().addScaledVector(side, -branchLength)), tuple(branchAnchor), tuple(branchAnchor.clone().addScaledVector(side, branchLength))],
    ] : [];

    return {
      id: index,
      nodeId: node.id,
      points: [tuple(start), tuple(elbow), tuple(approach), node.position],
      branches,
    };
  });

  return { nodes, paths };
}
