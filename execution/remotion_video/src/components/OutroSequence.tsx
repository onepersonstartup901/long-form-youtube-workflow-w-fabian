import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import type { OutroSegment, VideoStyle } from "../types";

interface OutroSequenceProps {
  segment: OutroSegment;
  style: VideoStyle;
}

export const OutroSequence: React.FC<OutroSequenceProps> = ({
  segment,
  style,
}) => {
  const frame = useCurrentFrame();

  const fadeIn = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  const ctaScale = interpolate(frame, [30, 45], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const ctaOpacity = interpolate(frame, [30, 45], [0, 1], {
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
        opacity: fadeIn,
      }}
    >
      {/* Channel name */}
      <p
        style={{
          fontFamily: style.captionFont,
          fontSize: 32,
          color: "rgba(255, 255, 255, 0.5)",
          marginBottom: 20,
          letterSpacing: 2,
          textTransform: "uppercase",
        }}
      >
        {segment.channelName}
      </p>

      {/* CTA */}
      <div
        style={{
          opacity: ctaOpacity,
          transform: `scale(${ctaScale})`,
        }}
      >
        <div
          style={{
            padding: "20px 60px",
            backgroundColor: style.accentColor,
            borderRadius: 12,
          }}
        >
          <p
            style={{
              fontFamily: style.captionFont,
              fontSize: 36,
              fontWeight: 700,
              color: "#ffffff",
              textAlign: "center",
            }}
          >
            {segment.cta}
          </p>
        </div>
      </div>

      {/* Subscribe hint */}
      <p
        style={{
          fontFamily: style.captionFont,
          fontSize: 22,
          color: "rgba(255, 255, 255, 0.4)",
          marginTop: 30,
        }}
      >
        Subscribe for more
      </p>
    </div>
  );
};
