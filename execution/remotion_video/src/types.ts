export interface AssemblyProps {
  [key: string]: unknown;
  fps: number;
  width: number;
  height: number;
  totalDurationInFrames: number;
  audioSrc: string;
  segments: Segment[];
  style: VideoStyle;
}

export type Segment =
  | IntroSegment
  | NarrationSegment
  | TransitionSegment
  | OutroSegment;

export interface IntroSegment {
  type: "intro";
  startFrame: number;
  durationInFrames: number;
  title: string;
  subtitle?: string;
}

export interface NarrationSegment {
  type: "narration";
  startFrame: number;
  durationInFrames: number;
  visual: VisualAsset;
  captions: CaptionGroup[];
  sectionTitle?: string;
}

export interface TransitionSegment {
  type: "transition";
  startFrame: number;
  durationInFrames: number;
  transitionStyle: "fade" | "wipe" | "zoom";
}

export interface OutroSegment {
  type: "outro";
  startFrame: number;
  durationInFrames: number;
  channelName: string;
  cta: string;
}

export interface VisualAsset {
  type: "image" | "video";
  src: string;
  animation: "ken_burns_in" | "ken_burns_out" | "pan_left" | "pan_right" | "static";
}

export interface CaptionGroup {
  startFrame: number;
  endFrame: number;
  text: string;
  words: CaptionWord[];
}

export interface CaptionWord {
  word: string;
  startFrame: number;
  endFrame: number;
  highlight: boolean;
}

export interface VideoStyle {
  backgroundColor: string;
  captionFont: string;
  captionColor: string;
  captionHighlightColor: string;
  captionPosition: "bottom" | "center";
  captionMaxWords: number;
  accentColor: string;
  captionFontSize: number;
  captionStrokeColor: string;
  captionStrokeWidth: number;
}
