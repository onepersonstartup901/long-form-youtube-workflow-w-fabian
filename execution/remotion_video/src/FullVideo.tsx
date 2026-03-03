import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import type { AssemblyProps } from "./types";
import { IntroSequence } from "./components/IntroSequence";
import { NarrationSegmentView } from "./components/NarrationSegment";
import { TransitionSlide } from "./components/TransitionSlide";
import { OutroSequence } from "./components/OutroSequence";

export const FullVideo: React.FC<AssemblyProps> = (props) => {
  return (
    <AbsoluteFill style={{ backgroundColor: props.style.backgroundColor }}>
      {/* Audio layer — plays throughout */}
      <Audio src={staticFile(props.audioSrc)} />

      {/* Visual layers — rendered in sequence */}
      {props.segments.map((segment, i) => (
        <Sequence
          key={`${segment.type}-${i}`}
          from={segment.startFrame}
          durationInFrames={segment.durationInFrames}
        >
          {segment.type === "intro" && (
            <IntroSequence segment={segment} style={props.style} />
          )}
          {segment.type === "narration" && (
            <NarrationSegmentView segment={segment} style={props.style} />
          )}
          {segment.type === "transition" && (
            <TransitionSlide segment={segment} style={props.style} />
          )}
          {segment.type === "outro" && (
            <OutroSequence segment={segment} style={props.style} />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
