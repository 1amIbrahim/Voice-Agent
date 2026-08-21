export interface AudioBands {
  level: number;
  bass: number;
  mid: number;
  treble: number;
}

export interface AudioReactiveSignal {
  current: AudioBands;
}

export interface AudioAnalyserConnection {
  context: AudioContext;
  analyser: AnalyserNode;
  disconnect(): void;
}

export function createAudioSignal(): AudioReactiveSignal {
  return { current: { level: 0, bass: 0, mid: 0, treble: 0 } };
}

export function connectMediaElement(element: HTMLMediaElement): AudioAnalyserConnection {
  const context = new AudioContext();
  const analyser = context.createAnalyser();
  analyser.fftSize = 512;
  analyser.smoothingTimeConstant = 0.72;
  const source = context.createMediaElementSource(element);
  source.connect(analyser);
  analyser.connect(context.destination);
  return {
    context,
    analyser,
    disconnect() {
      source.disconnect();
      analyser.disconnect();
      void context.close();
    },
  };
}
