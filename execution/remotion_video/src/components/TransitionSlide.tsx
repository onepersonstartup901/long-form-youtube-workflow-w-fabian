import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import type { TransitionSegment, VideoStyle } from "../types";

interface TransitionSlideProps {
  segment: TransitionSegment;
  style: VideoStyle;
}

export const TransitionSlide: React.FC<TransitionSlideProps> = ({
  segment,
  style,
}) => {
  const frame = useCurrentFrame();

  const opacity = (() => {
    switch (segment.transitionStyle) {
      case "fade":
        return interpolate(
          frame,
          [0, segment.durationInFrames / 2, segment.durationInFrames],
          [0, 1, 0],
          { extrapolateRight: "clamp" }
        );
      case "zoom":
      case "wipe":
      default:
        return interpolate(
          frame,
          [0, segment.durationInFrames / 2, segment.durationInFrames],
          [0, 1, 0],
          { extrapolateRight: "clamp" }
        );
    }
  })();

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        backgroundColor: style.backgroundColor,
        opacity,
      }}
    />
  );
};
