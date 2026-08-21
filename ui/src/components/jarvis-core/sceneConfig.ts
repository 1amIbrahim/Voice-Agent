export const JARVIS_COLORS = {
  bright: "#fff3b0",
  highlight: "#ffd36a",
  primary: "#ffb000",
  secondary: "#d97706",
  dim: "#6b3a05",
  deep: "#2c1a05",
  void: "#010203",
  background: "#020508",
} as const;

export const JARVIS_SCENE = {
  camera: {
    position: [0, 0, 5.15] as [number, number, number],
    fov: 39,
    drift: 0.045,
  },
  lens: {
    radius: 0.52,
    scale: 1.08,
  },
  shell: {
    radius: 2.35,
    nodeCount: 64,
  },
  particles: {
    inner: 0,
    middle: 0,
    atmospheric: 750,
  },
} as const;
