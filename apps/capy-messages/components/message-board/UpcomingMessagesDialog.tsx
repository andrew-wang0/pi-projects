import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import CalendarMonthIcon from "@mui/icons-material/CalendarMonth";
import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import {
  Alert,
  AppBar,
  Badge,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Paper,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { DateCalendar } from "@mui/x-date-pickers/DateCalendar";
import { PickersDay, type PickersDayProps } from "@mui/x-date-pickers/PickersDay";
import dayjs, { type Dayjs } from "dayjs";
import React, { useLayoutEffect, useMemo, useRef, useState } from "react";

import { getBackgroundOption, getBackgroundTextColor } from "@/lib/background-options";
import type { ScheduledMessage } from "@/lib/message-store";

import { IMAGE_HEIGHT, IMAGE_WIDTH } from "./constants";

type UpcomingMessagesDialogProps = {
  open: boolean;
  step: number;
  selectedDay: Dayjs;
  scheduledMessages: ScheduledMessage[];
  onClose: () => void;
  onStepChange: (nextStep: number) => void;
  onDayChange: (nextDay: Dayjs) => void;
  onDeleteSchedule: (id: string) => void;
};

type DayCountProps = PickersDayProps & {
  countsByDay?: Record<string, number>;
};

const PREVIEW_WIDTH = 200;
const PREVIEW_HEIGHT = Math.round((PREVIEW_WIDTH * IMAGE_HEIGHT) / IMAGE_WIDTH);

function CalendarDayWithCount({ day, outsideCurrentMonth, countsByDay, ...other }: DayCountProps) {
  const count = outsideCurrentMonth ? 0 : (countsByDay?.[day.format("YYYY-MM-DD")] ?? 0);

  return (
    <Badge
      overlap="circular"
      color="error"
      badgeContent={count > 0 ? count : undefined}
      anchorOrigin={{ vertical: "top", horizontal: "right" }}
      sx={{
        "& .MuiBadge-badge": {
          backgroundColor: "error.main",
          color: "common.white",
          fontSize: "0.65rem",
          minWidth: 18,
          height: 18,
          px: 0.5,
          fontWeight: 700,
        },
      }}
    >
      <PickersDay day={day} outsideCurrentMonth={outsideCurrentMonth} {...other} />
    </Badge>
  );
}

function MessageBackgroundPreview({ schedule }: { schedule: ScheduledMessage }) {
  const background = getBackgroundOption(schedule.backgroundId);
  const textRef = useRef<HTMLSpanElement | null>(null);
  const textBoundsRef = useRef<HTMLDivElement | null>(null);
  const [fontSize, setFontSize] = useState(8);

  const scaledBounds = useMemo(() => {
    const scaleX = PREVIEW_WIDTH / IMAGE_WIDTH;
    const scaleY = PREVIEW_HEIGHT / IMAGE_HEIGHT;
    const { x1, y1, x2, y2 } = background.bounds;

    return {
      left: x1 * scaleX,
      top: y1 * scaleY,
      width: (x2 - x1) * scaleX,
      height: (y2 - y1) * scaleY,
    };
  }, [background.bounds]);

  useLayoutEffect(() => {
    const textEl = textRef.current;
    const boundsEl = textBoundsRef.current;

    if (!textEl || !boundsEl) {
      return;
    }

    const fitText = () => {
      const maxWidth = boundsEl.clientWidth;
      const maxHeight = boundsEl.clientHeight;

      if (maxWidth <= 0 || maxHeight <= 0) {
        return;
      }

      let low = 4;
      let high = Math.max(56, Math.ceil(Math.max(maxWidth, maxHeight) * 1.3));
      let best = low;

      while (low <= high) {
        const mid = Math.floor((low + high) / 2);
        textEl.style.fontSize = `${mid}px`;

        const fits = textEl.scrollWidth <= maxWidth && textEl.scrollHeight <= maxHeight;

        if (fits) {
          best = mid;
          low = mid + 1;
        } else {
          high = mid - 1;
        }
      }

      textEl.style.fontSize = `${best}px`;
      setFontSize(best);
    };

    fitText();

    const observer = new ResizeObserver(() => {
      fitText();
    });

    observer.observe(boundsEl);
    window.addEventListener("resize", fitText);

    return () => {
      observer.disconnect();
      window.removeEventListener("resize", fitText);
    };
  }, [schedule.message, schedule.backgroundId, scaledBounds.height, scaledBounds.width]);

  return (
    <Box
      sx={{
        width: PREVIEW_WIDTH,
        height: PREVIEW_HEIGHT,
        maxWidth: "44%",
        position: "relative",
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
        flexShrink: 0,
      }}
    >
      {background.src ? (
        <Box
          component="img"
          src={background.src}
          alt={`${background.label} preview`}
          sx={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "fill",
            pointerEvents: "none",
          }}
        />
      ) : null}

      <Box
        ref={textBoundsRef}
        sx={{
          position: "absolute",
          left: scaledBounds.left,
          top: scaledBounds.top,
          width: scaledBounds.width,
          height: scaledBounds.height,
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
            lineHeight: 1.1,
            display: "block",
            width: "100%",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            overflowWrap: "anywhere",
            fontSize: `${fontSize}px`,
            textShadow: background.id === "default" ? "none" : "0 1px 2px rgba(0, 0, 0, 0.3)",
          }}
        >
          {schedule.message}
        </Typography>
      </Box>
    </Box>
  );
}

export default function UpcomingMessagesDialog({
  open,
  step,
  selectedDay,
  scheduledMessages,
  onClose,
  onStepChange,
  onDayChange,
  onDeleteSchedule,
}: UpcomingMessagesDialogProps) {
  const [messageIndex, setMessageIndex] = useState(0);
  const [deleteTarget, setDeleteTarget] = useState<ScheduledMessage | null>(null);

  const countsByDay = useMemo(() => {
    const counts: Record<string, number> = {};

    for (const schedule of scheduledMessages) {
      const dayKey = schedule.startAt.slice(0, 10);
      counts[dayKey] = (counts[dayKey] ?? 0) + 1;
    }

    return counts;
  }, [scheduledMessages]);

  const selectedDayKey = selectedDay.format("YYYY-MM-DD");
  const selectedDayMessages = useMemo(() => {
    return scheduledMessages.filter((schedule) => schedule.startAt.slice(0, 10) === selectedDayKey);
  }, [scheduledMessages, selectedDayKey]);
  const hasSelectedDayMessages = selectedDayMessages.length > 0;

  const safeMessageIndex = Math.min(messageIndex, Math.max(0, selectedDayMessages.length - 1));
  const activeMessage = hasSelectedDayMessages ? selectedDayMessages[safeMessageIndex] : null;

  const goBack = () => {
    if (step === 0) {
      closeDeleteConfirm();
      onClose();
      return;
    }

    onStepChange(0);
  };

  const handlePrimary = () => {
    if (step === 0) {
      setMessageIndex(0);
      onStepChange(1);
      return;
    }

    closeDeleteConfirm();
    onClose();
  };

  const closeDeleteConfirm = () => {
    setDeleteTarget(null);
  };

  const confirmDelete = () => {
    if (!deleteTarget) {
      return;
    }

    onDeleteSchedule(deleteTarget.id);
    closeDeleteConfirm();
  };

  const handleDialogClose = () => {
    closeDeleteConfirm();
    onClose();
  };

  return (
    <Dialog fullScreen open={open} onClose={handleDialogClose}>
      <AppBar position="sticky" color="secondary">
        <Toolbar sx={{ minHeight: 72 }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={goBack}
            aria-label={step === 0 ? "Close" : "Back"}
            size="large"
          >
            {step === 0 ? (
              <CloseIcon sx={{ fontSize: 30 }} />
            ) : (
              <ArrowBackIcon sx={{ fontSize: 30 }} />
            )}
          </IconButton>
          <Typography
            sx={{ flexGrow: 1, ml: 1, fontSize: "1.4rem", fontWeight: 700 }}
            component="h2"
          >
            Upcoming Messages
          </Typography>
          <Button
            color="primary"
            onClick={handlePrimary}
            size="large"
            variant="contained"
            sx={{ fontSize: "1rem", px: 2.5, fontWeight: 800, boxShadow: 2 }}
          >
            {step === 0 ? "Next" : "Done"}
          </Button>
        </Toolbar>
      </AppBar>

      <DialogContent sx={step === 0 ? { p: 0 } : { pt: 2.5 }}>
        {step === 0 ? (
          <Box
            sx={{
              width: "100%",
              minHeight: "calc(100dvh - 72px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <DateCalendar
              value={selectedDay}
              onChange={(nextValue) => {
                if (nextValue) {
                  onDayChange(nextValue.startOf("day"));
                }
              }}
              showDaysOutsideCurrentMonth
              slots={{ day: CalendarDayWithCount }}
              slotProps={{
                day: {
                  countsByDay,
                } as Partial<DayCountProps>,
              }}
            />
          </Box>
        ) : (
          <Stack spacing={2.5}>
            <Stack direction="row" spacing={1} alignItems="center" justifyContent="space-between">
              <Stack direction="row" spacing={1} alignItems="center">
                <CalendarMonthIcon sx={{ fontSize: 24 }} />
                <Typography sx={{ fontSize: "1.1rem", fontWeight: 700 }}>
                  {selectedDay.format("dddd, MMM D")} ({selectedDayMessages.length})
                </Typography>
              </Stack>
              <Stack direction="row" spacing={1} alignItems="center">
                {hasSelectedDayMessages ? (
                  <Typography color="text.secondary" sx={{ fontSize: "0.95rem", fontWeight: 700 }}>
                    {safeMessageIndex + 1} / {selectedDayMessages.length}
                  </Typography>
                ) : null}
                <IconButton
                  aria-label="Previous message"
                  onClick={() => setMessageIndex((value) => Math.max(0, value - 1))}
                  disabled={!hasSelectedDayMessages || safeMessageIndex === 0}
                >
                  <ArrowBackIosNewIcon />
                </IconButton>
                <IconButton
                  aria-label="Next message"
                  onClick={() =>
                    setMessageIndex((value) => Math.min(selectedDayMessages.length - 1, value + 1))
                  }
                  disabled={
                    !hasSelectedDayMessages || safeMessageIndex >= selectedDayMessages.length - 1
                  }
                >
                  <ArrowForwardIosIcon />
                </IconButton>
              </Stack>
            </Stack>

            {hasSelectedDayMessages ? (
              <Paper elevation={1} sx={{ p: 1.5 }}>
                <Stack
                  direction="row"
                  spacing={1.5}
                  alignItems="stretch"
                  sx={{ minWidth: 0, flexGrow: 1 }}
                >
                  <Stack sx={{ minWidth: 0, flexGrow: 1 }} spacing={1.25}>
                    <Typography
                      sx={{
                        fontSize: "1.1rem",
                        fontWeight: 700,
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        overflowWrap: "anywhere",
                      }}
                    >
                      {activeMessage?.message}
                    </Typography>

                    <Typography
                      color="text.secondary"
                      sx={{ fontSize: "0.98rem", fontWeight: 600 }}
                    >
                      {dayjs(activeMessage?.startAt).format("h:mm A")}
                    </Typography>

                    <Box>
                      <Button
                        color="error"
                        variant="outlined"
                        size="large"
                        startIcon={<DeleteOutlineIcon />}
                        onClick={() => {
                          if (activeMessage) {
                            setDeleteTarget(activeMessage);
                          }
                        }}
                        sx={{ fontWeight: 700 }}
                      >
                        Delete
                      </Button>
                    </Box>
                  </Stack>

                  {activeMessage ? <MessageBackgroundPreview schedule={activeMessage} /> : null}
                </Stack>
              </Paper>
            ) : (
              <Alert
                severity="info"
                sx={{ fontSize: "1rem", "& .MuiAlert-icon": { fontSize: 24 } }}
              >
                No messages scheduled for this day.
              </Alert>
            )}
          </Stack>
        )}
      </DialogContent>

      <Dialog open={Boolean(deleteTarget)} onClose={closeDeleteConfirm}>
        <DialogTitle>Delete scheduled message?</DialogTitle>
        <DialogContent>
          <Stack spacing={1}>
            <Typography sx={{ fontWeight: 600 }}>
              {deleteTarget ? dayjs(deleteTarget.startAt).format("MMM D, YYYY h:mm A") : ""}
            </Typography>
            <Typography color="text.secondary">
              {deleteTarget ? deleteTarget.message : ""}
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeDeleteConfirm}>Cancel</Button>
          <Button color="error" variant="contained" onClick={confirmDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Dialog>
  );
}
