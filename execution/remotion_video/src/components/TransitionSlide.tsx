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
  const mid = segment.durationInFrames / 2;
  const dur = segment.durationInFrames;

  const opacity = interpolate(frame, [0, mid, dur], [0, 1, 0], {
    extrapolateRight: "clamp",
  });

  const transitionStyle: React.CSSProperties = (() => {
    switch (segment.transitionStyle) {
      case "zoom": {
        const scale = interpolate(frame, [0, mid, dur], [0.6, 1.1, 0.6], {
          extrapolateRight: "clamp",
        });
        return { transform: `scale(${scale})` };
      }
      case "wipe": {
        const translateX = interpolate(frame, [0, mid, dur], [-100, 0, 100], {
          extrapolateRight: "clamp",
        });
        return { transform: `translateX(${translateX}%)` };
      }
      case "fade":
      default:
        return {};
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
        ...transitionStyle,
      }}
    />
  );
};
