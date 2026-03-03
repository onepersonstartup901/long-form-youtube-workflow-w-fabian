import React from "react";
import { OffthreadVideo, staticFile } from "remotion";
import type { NarrationSegment as NarrationSegmentType, VideoStyle } from "../types";
import { KenBurns } from "./KenBurns";
import { AnimatedCaption } from "./AnimatedCaption";

interface NarrationSegmentProps {
  segment: NarrationSegmentType;
  style: VideoStyle;
}

export const NarrationSegmentView: React.FC<NarrationSegmentProps> = ({
  segment,
  style,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        backgroundColor: style.backgroundColor,
      }}
    >
      {/* Visual layer */}
      {segment.visual.type === "image" ? (
        <KenBurns
          visual={segment.visual}
          durationInFrames={segment.durationInFrames}
        />
      ) : (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
          }}
        >
          <OffthreadVideo
            src={staticFile(segment.visual.src)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
            }}
          />
        </div>
      )}

      {/* Section title card (if present) */}
      {segment.sectionTitle && (
        <SectionTitle title={segment.sectionTitle} style={style} />
      )}

      {/* Captions layer */}
      <AnimatedCaption captions={segment.captions} style={style} />
    </div>
  );
};

const SectionTitle: React.FC<{ title: string; style: VideoStyle }> = ({
  title,
  style,
}) => {
  return (
    <div
      style={{
        position: "absolute",
        top: 40,
        left: 40,
        padding: "8px 20px",
        backgroundColor: style.accentColor,
        borderRadius: 6,
        opacity: 0.9,
      }}
    >
      <span
        style={{
          fontFamily: style.captionFont,
          fontSize: 24,
          fontWeight: 700,
          color: "#ffffff",
          textTransform: "uppercase",
          letterSpacing: 1,
        }}
      >
        {title}
      </span>
    </div>
  );
};
