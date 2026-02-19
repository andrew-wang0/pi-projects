import { Box, Typography } from "@mui/material";
import React from "react";

import {
  type BackgroundOption,
  DEFAULT_BACKGROUND_ID,
  getBackgroundTextColor,
} from "@/lib/background-options";

import type { BoundsStyle } from "./utils";

type StandbyDisplayProps = {
  background: BackgroundOption;
  message: string;
  textBoundsStyle: BoundsStyle;
  standbyFontSize: number;
  textRef: React.RefObject<HTMLSpanElement | null>;
  textBoundsRef: React.RefObject<HTMLDivElement | null>;
};

const StandbyBackground = React.memo(function StandbyBackground({ src }: { src: string | null }) {
  if (!src) {
    return null;
  }

  return (
    <Box
      component="img"
      src={src}
      alt="Selected background"
      sx={{
        position: "absolute",
        inset: 0,
        width: "100%",
        height: "100%",
        objectFit: "fill",
        pointerEvents: "none",
        userSelect: "none",
      }}
    />
  );
});

export default function StandbyDisplay({
  background,
  message,
  textBoundsStyle,
  standbyFontSize,
  textRef,
  textBoundsRef,
}: StandbyDisplayProps) {
  return (
    <>
      <StandbyBackground src={background.src} />

      <Box
        ref={textBoundsRef}
        sx={{
          position: "absolute",
          ...textBoundsStyle,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          overflow: "hidden",
        }}
      >
        <Typography
          ref={textRef}
          component="span"
          sx={{
            color: (theme) => getBackgroundTextColor(background) ?? theme.palette.text.primary,
            textAlign: "center",
            fontWeight: 700,
            textShadow:
              background.id === DEFAULT_BACKGROUND_ID ? "none" : "0 1px 3px rgba(0, 0, 0, 0.35)",
            lineHeight: 1.1,
            display: "block",
            width: "100%",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            overflowWrap: "anywhere",
            fontSize: `${standbyFontSize}px`,
          }}
        >
          {message}
        </Typography>
      </Box>
    </>
  );
}
