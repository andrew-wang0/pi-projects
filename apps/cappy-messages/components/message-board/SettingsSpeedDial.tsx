import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import EventNoteIcon from "@mui/icons-material/EventNote";
import ScheduleIcon from "@mui/icons-material/Schedule";
import { Box, ClickAwayListener, SpeedDial, SpeedDialAction, SpeedDialIcon } from "@mui/material";
import React from "react";

type SettingsSpeedDialProps = {
  open: boolean;
  hasInteracted: boolean;
  onOpen: () => void;
  onClose: () => void;
  onEdit: () => void;
  onSchedule: () => void;
  onUpcoming: () => void;
};

export default function SettingsSpeedDial({
  open,
  hasInteracted,
  onOpen,
  onClose,
  onEdit,
  onSchedule,
  onUpcoming,
}: SettingsSpeedDialProps) {
  return (
    <ClickAwayListener onClickAway={onClose}>
      <Box>
        <SpeedDial
          ariaLabel="Message settings"
          icon={<SpeedDialIcon />}
          FabProps={{
            color: "primary",
            size: "large",
          }}
          onClose={(_, reason) => {
            if (reason === "toggle" || reason === "escapeKeyDown") {
              onClose();
            }
          }}
          onOpen={(_, reason) => {
            if (reason === "toggle") {
              onOpen();
            }
          }}
          open={open}
          sx={{
            position: "fixed",
            right: 16,
            bottom: 16,
            "& .MuiFab-primary": {
              opacity: hasInteracted ? 1 : 0.38,
              transition: (theme) => theme.transitions.create(["opacity", "box-shadow"]),
              boxShadow: "0 10px 20px rgba(59, 39, 27, 0.35)",
            },
          }}
        >
          <SpeedDialAction
            icon={<EditOutlinedIcon />}
            slotProps={{
              fab: {
                size: "large",
              },
              tooltip: {
                title: "edit",
                open: true,
              },
            }}
            onClick={onEdit}
          />
          <SpeedDialAction
            icon={<ScheduleIcon />}
            slotProps={{
              fab: {
                size: "large",
              },
              tooltip: {
                title: "schedule",
                open: true,
              },
            }}
            onClick={onSchedule}
          />
          <SpeedDialAction
            icon={<EventNoteIcon />}
            slotProps={{
              fab: {
                size: "large",
              },
              tooltip: {
                title: "upcoming",
                open: true,
              },
            }}
            onClick={onUpcoming}
          />
        </SpeedDial>
      </Box>
    </ClickAwayListener>
  );
}
