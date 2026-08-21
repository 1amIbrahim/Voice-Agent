import { Line } from "@react-three/drei";

type Point = [number, number, number];
interface GlowLineProps { points: Point[]; opacity: number; lineWidth?: number; color?: string; haloColor?: string; }

export function GlowLine({ points, opacity, lineWidth = 0.55, color = "#fff1ad", haloColor = "#d69a28" }: GlowLineProps) {
  return <group><Line points={points} color={haloColor} transparent opacity={opacity * 0.22} lineWidth={lineWidth * 5.5} depthWrite={false} /><Line points={points} color={haloColor} transparent opacity={opacity * 0.42} lineWidth={lineWidth * 2.4} depthWrite={false} /><Line points={points} color={color} transparent opacity={opacity} lineWidth={lineWidth} depthWrite={false} /></group>;
}
