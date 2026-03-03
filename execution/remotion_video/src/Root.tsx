import React from "react";
import { Composition } from "remotion";
import { FullVideo } from "./FullVideo";
import { DEFAULT_STYLE } from "./theme";
import type { AssemblyProps } from "./types";

const defaultProps: AssemblyProps = {
  fps: 30,
  width: 1920,
  height: 1080,
  totalDurationInFrames: 300, // 10 seconds default for studio preview
  audioSrc: "",
  segments: [
    {
      type: "intro",
      startFrame: 0,
      durationInFrames: 90,
      title: "Preview Title",
      subtitle: "Preview Subtitle",
    },
    {
      type: "outro",
      startFrame: 90,
      durationInFrames: 150,
      channelName: "Your Channel",
      cta: "Subscribe & Hit the Bell",
    },
  ],
  style: DEFAULT_STYLE,
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition<any, AssemblyProps>
        id="FullVideo"
        component={FullVideo}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultProps}
        calculateMetadata={async ({ props }) => {
          return {
            durationInFrames: props.totalDurationInFrames as number,
            fps: props.fps as number,
            width: props.width as number,
            height: props.height as number,
          };
        }}
      />
    </>
  );
};
