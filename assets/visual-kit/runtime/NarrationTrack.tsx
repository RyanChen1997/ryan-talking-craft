import React from "react";
import {Audio} from "@remotion/media";

export type NarrationTrackProps = {
  src: string;
  volume?: number;
};

export const NarrationTrack: React.FC<NarrationTrackProps> = ({src, volume = 1}) => {
  const path = src.split("?", 1)[0]?.toLowerCase() ?? "";
  if (!path.endsWith(".wav")) {
    throw new Error(
      "NarrationTrack requires the continuous 48kHz PCM WAV created by prepare_narration.py",
    );
  }
  return <Audio src={src} volume={volume} />;
};
