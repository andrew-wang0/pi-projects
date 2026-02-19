import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CloseIcon from "@mui/icons-material/Close";
import {
  Alert,
  AppBar,
  Badge,
  Box,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import { PickersDay, type PickersDayProps } from "@mui/x-date-pickers/PickersDay";
import { StaticDateTimePicker } from "@mui/x-date-pickers/StaticDateTimePicker";
import type { Dayjs } from "dayjs";
import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { getBackgroundOption, getBackgroundTextColor } from "@/lib/background-options";
import type { ScheduledMessage } from "@/lib/message-store";

import BackgroundPicker from "./BackgroundPicker";
import { MAX_MESSAGE_LENGTH, SCHEDULE_STEP_COUNT } from "./constants";
import { toBoundsStyle } from "./utils";

type ScheduleMessageDialogProps = {
  open: boolean;
  step: number;
  draft: string;
  scheduledMessages: ScheduledMessage[];
  backgroundId: string;
  scheduleAt: Dayjs | null;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onBack: () => void;
  onPrimaryAction: () => void;
  onDraftChange: (nextValue: string) => void;
  onBackgroundSelect: (nextBackgroundId: string) => void;
  onScheduleAtChange: (nextValue: Dayjs | null) => void;
  inputRef: React.RefObject<HTMLInputElement | HTMLTextAreaElement | null>;
};

type DayCountProps = PickersDayProps & {
  countsByDay?: Record<string, number>;
};

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

function SchedulePreview({ message, backgroundId }: { message: string; backgroundId: string }) {
  const background = getBackgroundOption(backgroundId);
  const boundsStyle = useMemo(() => toBoundsStyle(background.bounds), [background.bounds]);
  const textRef = useRef<HTMLSpanElement | null>(null);
  const textBoundsRef = useRef<HTMLDivElement | null>(null);
  const [fontSize, setFontSize] = useState(14);

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

      let low = 6;
      let high = Math.max(120, Math.ceil(Math.max(maxWidth, maxHeight) * 1.4));
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
  }, [message, background.id, boundsStyle.height, boundsStyle.width]);

  return (
    <Box
      sx={{
        width: "100%",
        aspectRatio: "5 / 3",
        position: "relative",
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
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
          ...boundsStyle,
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
            textShadow: background.id === "default" ? "none" : "0 1px 3px rgba(0, 0, 0, 0.35)",
            lineHeight: 1.1,
            display: "block",
            width: "100%",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            overflowWrap: "anywhere",
            fontSize: `${fontSize}px`,
          }}
        >
          {message}
        </Typography>
      </Box>
    </Box>
  );
}

export default function ScheduleMessageDialog({
  open,
  step,
  draft,
  scheduledMessages,
  backgroundId,
  scheduleAt,
  isSaving,
  error,
  onClose,
  onBack,
  onPrimaryAction,
  onDraftChange,
  onBackgroundSelect,
  onScheduleAtChange,
  inputRef,
}: ScheduleMessageDialogProps) {
  const countsByDay = useMemo(() => {
    const counts: Record<string, number> = {};

    for (const schedule of scheduledMessages) {
      const dayKey = schedule.startAt.slice(0, 10);
      counts[dayKey] = (counts[dayKey] ?? 0) + 1;
    }

    return counts;
  }, [scheduledMessages]);

  const hasValidScheduleAt = Boolean(scheduleAt?.isValid());
  const scheduleAtLabel =
    hasValidScheduleAt && scheduleAt ? scheduleAt.format("MMM D, YYYY h:mm A") : "Not set";

  useEffect(() => {
    if (!open || step !== 1) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      const inputEl = inputRef.current;

      if (!inputEl) {
        return;
      }

      inputEl.focus({ preventScroll: true });
      inputEl.select();
    }, 0);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [open, step, inputRef]);

  return (
    <Dialog fullScreen open={open} onClose={onClose}>
      <AppBar position="sticky" color="secondary">
        <Toolbar sx={{ minHeight: 72 }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={onBack}
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
            Schedule Message
          </Typography>
          <Button
            color="primary"
            disabled={isSaving}
            onClick={onPrimaryAction}
            size="large"
            variant="contained"
            sx={{ fontSize: "1rem", px: 2.5, fontWeight: 800, boxShadow: 2 }}
          >
            {step < SCHEDULE_STEP_COUNT - 1 ? "Next" : isSaving ? "Saving..." : "Confirm"}
          </Button>
        </Toolbar>
      </AppBar>

      <DialogContent sx={{ pb: step === 1 ? "52dvh" : 2.5, pt: 2.5 }}>
        <Stack spacing={2.5}>
          {step === 0 ? (
            <StaticDateTimePicker
              displayStaticWrapperAs="mobile"
              orientation="landscape"
              value={scheduleAt}
              onChange={onScheduleAtChange}
              disablePast
              slotProps={{
                toolbar: {
                  hidden: false,
                },
                actionBar: {
                  actions: [],
                },
                day: {
                  countsByDay,
                } as Partial<DayCountProps>,
              }}
              slots={{ day: CalendarDayWithCount }}
              sx={{
                width: "100%",
                maxWidth: "100%",
              }}
            />
          ) : null}

          {step === 1 ? (
            <TextField
              inputRef={inputRef}
              label="Message"
              multiline
              minRows={4}
              maxRows={10}
              value={draft}
              onChange={(event) => onDraftChange(event.target.value.slice(0, MAX_MESSAGE_LENGTH))}
              helperText={`${draft.length}/${MAX_MESSAGE_LENGTH}`}
              spellCheck={false}
              autoCapitalize="sentences"
              autoCorrect="on"
              slotProps={{
                inputLabel: {
                  sx: { fontSize: "1.05rem" },
                },
                formHelperText: {
                  sx: { fontSize: "0.95rem", fontWeight: 600 },
                },
              }}
              sx={{
                "& .MuiInputBase-input": {
                  fontSize: "1.35rem",
                  lineHeight: 1.35,
                },
              }}
            />
          ) : null}

          {step === 2 ? (
            <>
              <Typography color="text.secondary" sx={{ fontSize: "1rem", fontWeight: 700 }}>
                Background
              </Typography>
              <BackgroundPicker selectedBackgroundId={backgroundId} onSelect={onBackgroundSelect} />
            </>
          ) : null}

          {step === 3 ? (
            <Stack spacing={1.5}>
              <Typography sx={{ fontSize: "1.2rem", fontWeight: 700 }}>Review</Typography>
              <Box
                sx={{
                  display: "flex",
                  gap: 2,
                  alignItems: "flex-start",
                  flexDirection: { xs: "column", sm: "row" },
                }}
              >
                <Stack spacing={0.75} sx={{ minWidth: 0, flex: 1, pt: 0.5 }}>
                  <Typography color="text.secondary" sx={{ fontSize: "0.95rem", fontWeight: 700 }}>
                    Show At
                  </Typography>
                  <Typography sx={{ fontSize: "1.15rem", fontWeight: 700 }}>
                    {scheduleAtLabel}
                  </Typography>
                </Stack>

                <Box sx={{ width: { xs: "100%", sm: "50%" }, maxWidth: 420, ml: { sm: "auto" } }}>
                  <SchedulePreview message={draft} backgroundId={backgroundId} />
                </Box>
              </Box>
            </Stack>
          ) : null}

          {error ? (
            <Alert severity="error" sx={{ fontSize: "1rem", "& .MuiAlert-icon": { fontSize: 24 } }}>
              {error}
            </Alert>
          ) : null}
        </Stack>
      </DialogContent>
    </Dialog>
  );
}
