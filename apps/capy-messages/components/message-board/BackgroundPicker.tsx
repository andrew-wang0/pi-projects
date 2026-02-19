import { Box, List, ListItem, ListItemButton, ListItemText } from "@mui/material";
import React from "react";

import { BACKGROUND_OPTIONS } from "@/lib/background-options";

type BackgroundPickerProps = {
  selectedBackgroundId: string;
  onSelect: (nextBackgroundId: string) => void;
};

export default function BackgroundPicker({
  selectedBackgroundId,
  onSelect,
}: BackgroundPickerProps) {
  return (
    <List
      sx={{
        p: 0,
        display: "grid",
        gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
        gap: 1,
      }}
    >
      {BACKGROUND_OPTIONS.map((option) => (
        <ListItem key={option.id} disablePadding sx={{ m: 0 }}>
          <ListItemButton
            selected={selectedBackgroundId === option.id}
            onClick={() => onSelect(option.id)}
            sx={{
              width: "100%",
              height: "100%",
              px: 1,
              py: 1,
              gap: 0.75,
              flexDirection: "column",
              alignItems: "stretch",
              justifyContent: "flex-start",
              transition: (theme) => theme.transitions.create(["outline-color", "box-shadow"]),
              "&.Mui-selected": {
                outline: "2px solid",
                outlineColor: "primary.main",
                boxShadow: (theme) => `inset 0 0 0 1px ${theme.palette.primary.main}`,
              },
              "&.Mui-selected .background-preview": {
                borderColor: "primary.main",
              },
            }}
          >
            <Box
              className="background-preview"
              sx={{
                width: "100%",
                aspectRatio: "16 / 10",
                overflow: "hidden",
                bgcolor: "background.default",
                border: "1px solid",
                borderColor: "divider",
                flexShrink: 0,
              }}
            >
              {option.src ? (
                <Box
                  component="img"
                  src={option.src}
                  alt={`${option.label} preview`}
                  sx={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : null}
            </Box>

            <ListItemText
              primary={option.label}
              sx={{ my: 0 }}
              slotProps={{
                primary: { sx: { fontSize: "0.95rem", fontWeight: 700, textAlign: "center" } },
              }}
            />
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  );
}
