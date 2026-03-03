import React from "react";
import { useCurrentFrame, interpolate } from "remotion";
import type { CaptionGroup, VideoStyle } from "../types";

interface AnimatedCaptionProps {
  captions: CaptionGroup[];
  style: VideoStyle;
}

export const AnimatedCaption: React.FC<AnimatedCaptionProps> = ({
  captions,
  style,
}) => {
  const frame = useCurrentFrame();

  // Find the active caption group for the current frame
  const activeCaption = captions.find(
    (c) => frame >= c.startFrame && frame <= c.endFrame
  );

  if (!activeCaption) return null;

  const positionStyle: React.CSSProperties =
    style.captionPosition === "center"
      ? { top: "50%", transform: "translateY(-50%)" }
      : { bottom: 120 };

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        ...positionStyle,
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          justifyContent: "center",
          padding: "12px 24px",
          borderRadius: 8,
          backgroundColor: "rgba(0, 0, 0, 0.6)",
          maxWidth: "80%",
        }}
      >
        {activeCaption.words.map((word, i) => {
          const isActive = frame >= word.startFrame && frame <= word.endFrame;
          const isPast = frame > word.endFrame;

          // Scale animation when word becomes active
          const wordScale = isActive
            ? interpolate(
                frame,
                [word.startFrame, word.startFrame + 3],
                [1.2, 1.05],
                { extrapolateRight: "clamp" }
              )
            : 1;

          const color = word.highlight
            ? style.captionHighlightColor
            : isActive
              ? style.captionHighlightColor
              : isPast
                ? "rgba(255, 255, 255, 0.7)"
                : "rgba(255, 255, 255, 0.5)";

          return (
            <span
              key={i}
              style={{
                fontFamily: style.captionFont,
                fontSize: style.captionFontSize,
                fontWeight: 800,
                color,
                transform: `scale(${wordScale})`,
                transition: "color 0.1s",
                textShadow: `
                  ${style.captionStrokeWidth}px ${style.captionStrokeWidth}px 0 ${style.captionStrokeColor},
                  -${style.captionStrokeWidth}px ${style.captionStrokeWidth}px 0 ${style.captionStrokeColor},
                  ${style.captionStrokeWidth}px -${style.captionStrokeWidth}px 0 ${style.captionStrokeColor},
                  -${style.captionStrokeWidth}px -${style.captionStrokeWidth}px 0 ${style.captionStrokeColor}
                `,
              }}
            >
              {word.word}
            </span>
          );
        })}
      </div>
    </div>
  );
};
