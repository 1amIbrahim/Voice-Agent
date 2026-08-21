import { useEffect, useRef } from "react";
import type { AIState } from "../types/ui";
import type { AudioAnalyserConnection, AudioReactiveSignal } from "../audio/audioReactivity";
import { createAudioSignal } from "../audio/audioReactivity";

function average(data: Uint8Array, from: number, to: number): number {
  let total = 0;
  for (let index = from; index < to; index += 1) total += data[index];
  return total / Math.max(1, to - from) / 255;
}

export function useAudioReactivity(state: AIState, connection?: AudioAnalyserConnection): AudioReactiveSignal {
  const signal = useRef<AudioReactiveSignal>(createAudioSignal()).current;

  useEffect(() => {
    let frame = 0;
    const frequencyData = connection ? new Uint8Array(connection.analyser.frequencyBinCount) : undefined;
    const update = (time: number) => {
      let targetLevel = 0;
      let targetBass = 0;
      let targetMid = 0;
      let targetTreble = 0;
      if (connection && frequencyData) {
        connection.analyser.getByteFrequencyData(frequencyData);
        targetBass = average(frequencyData, 1, 14);
        targetMid = average(frequencyData, 14, 58);
        targetTreble = average(frequencyData, 58, frequencyData.length);
        targetLevel = targetBass * 0.42 + targetMid * 0.42 + targetTreble * 0.16;
      } else if (state === "speaking") {
        const seconds = time / 1000;
        const syllable = Math.max(0, Math.sin(seconds * 10.8) * 0.48 + Math.sin(seconds * 17.2 + 1.4) * 0.3);
        const phrase = 0.45 + Math.sin(seconds * 2.1) * 0.2 + Math.sin(seconds * 0.67 + 0.8) * 0.12;
        targetLevel = Math.max(0.08, phrase + syllable) * 0.72;
        targetBass = targetLevel * (0.72 + Math.sin(seconds * 5.2) * 0.15);
        targetMid = targetLevel * (0.9 + Math.sin(seconds * 8.8 + 0.5) * 0.1);
        targetTreble = targetLevel * (0.48 + Math.max(0, Math.sin(seconds * 15.4)) * 0.34);
      } else if (state === "listening") {
        const seconds = time / 1000;
        targetLevel = 0.08 + Math.max(0, Math.sin(seconds * 3.2)) * 0.1;
        targetBass = targetLevel * 0.7;
        targetMid = targetLevel;
        targetTreble = targetLevel * 0.54;
      }
      const smoothing = targetLevel > signal.current.level ? 0.22 : 0.08;
      signal.current.level += (targetLevel - signal.current.level) * smoothing;
      signal.current.bass += (targetBass - signal.current.bass) * smoothing;
      signal.current.mid += (targetMid - signal.current.mid) * smoothing;
      signal.current.treble += (targetTreble - signal.current.treble) * smoothing;
      frame = requestAnimationFrame(update);
    };
    frame = requestAnimationFrame(update);
    return () => cancelAnimationFrame(frame);
  }, [connection, signal, state]);

  return signal;
}
