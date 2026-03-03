import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import type { IntroSegment, VideoStyle } from "../types";

interface IntroSequenceProps {
  segment: IntroSegment;
  style: VideoStyle;
}

export const IntroSequence: React.FC<IntroSequenceProps> = ({
  segment,
  style,
}) => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [10, 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const titleY = interpolate(frame, [10, 25], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const subtitleOpacity = interpolate(frame, [25, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const lineWidth = interpolate(frame, [5, 30], [0, 400], {
    extrapolateLeft: "clamp",
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
        backgroundColor: style.backgroundColor,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* Accent line */}
      <div
        style={{
          width: lineWidth,
          height: 4,
          backgroundColor: style.accentColor,
          marginBottom: 40,
          borderRadius: 2,
        }}
      />

      {/* Title */}
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
        }}
      >
        <h1
          style={{
            fontFamily: style.captionFont,
            fontSize: 64,
            fontWeight: 800,
            color: style.captionColor,
            textAlign: "center",
            maxWidth: "80%",
            margin: "0 auto",
            lineHeight: 1.2,
          }}
        >
          {segment.title}
        </h1>
      </div>

      {/* Subtitle */}
      {segment.subtitle && (
        <div style={{ opacity: subtitleOpacity, marginTop: 20 }}>
          <p
            style={{
              fontFamily: style.captionFont,
              fontSize: 28,
              color: "rgba(255, 255, 255, 0.6)",
              textAlign: "center",
            }}
          >
            {segment.subtitle}
          </p>
        </div>
      )}
    </div>
  );
};
