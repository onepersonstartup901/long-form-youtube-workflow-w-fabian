import React from "react";
import { Img, useCurrentFrame, interpolate, staticFile } from "remotion";
import type { VisualAsset } from "../types";

interface KenBurnsProps {
  visual: VisualAsset;
  durationInFrames: number;
}

export const KenBurns: React.FC<KenBurnsProps> = ({ visual, durationInFrames }) => {
  const frame = useCurrentFrame();

  const scale = (() => {
    switch (visual.animation) {
      case "ken_burns_in":
        return interpolate(frame, [0, durationInFrames], [1, 1.15], {
          extrapolateRight: "clamp",
        });
      case "ken_burns_out":
        return interpolate(frame, [0, durationInFrames], [1.15, 1], {
          extrapolateRight: "clamp",
        });
      default:
        return 1;
    }
  })();

  // Use percentage-based pan for noticeable motion (~5% of frame width)
  const translateX = (() => {
    switch (visual.animation) {
      case "pan_left":
        return interpolate(frame, [0, durationInFrames], [2, -3], {
          extrapolateRight: "clamp",
        });
      case "pan_right":
        return interpolate(frame, [0, durationInFrames], [-2, 3], {
          extrapolateRight: "clamp",
        });
      default:
        return 0;
    }
  })();

  // Fade in
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        overflow: "hidden",
        opacity,
      }}
    >
      <Img
        src={staticFile(visual.src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "cover",
          transform: `scale(${scale}) translateX(${translateX}%)`,
        }}
      />
    </div>
  );
};
