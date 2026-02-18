"use client";

import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ScheduleIcon from "@mui/icons-material/Schedule";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  AppBar,
  Box,
  Button,
  Dialog,
  DialogContent,
  Divider,
  IconButton,
  List,
  ListItem,
  ListItemText,
  SpeedDial,
  SpeedDialAction,
  SpeedDialIcon,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { MobileDateTimePicker } from "@mui/x-date-pickers/MobileDateTimePicker";
import dayjs, { type Dayjs } from "dayjs";
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import type { MessageState } from "@/lib/message-store";

const MAX_MESSAGE_LENGTH = 100;

type MessageBoardProps = {
  initialState: MessageState;
};

type DialogMode = "none" | "edit" | "schedule";

function formatDateTime(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return "Invalid date";
  }

  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export default function MessageBoard({ initialState }: MessageBoardProps) {
  const [state, setState] = useState<MessageState>(initialState);
  const [speedDialOpen, setSpeedDialOpen] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [dialogMode, setDialogMode] = useState<DialogMode>("none");

  const [editDraft, setEditDraft] = useState(initialState.activeMessage);
  const [scheduleDraft, setScheduleDraft] = useState(initialState.activeMessage);
  const [scheduleAt, setScheduleAt] = useState<Dayjs | null>(dayjs().add(1, "hour"));

  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [isSchedulePickerOpen, setIsSchedulePickerOpen] = useState(false);
  const [isUpcomingExpanded, setIsUpcomingExpanded] = useState(false);
  const [standbyFontSize, setStandbyFontSize] = useState(72);
  const inactivityTimeoutRef = useRef<number | null>(null);
  const stateRef = useRef<MessageState>(initialState);
  const latestRefreshRequestIdRef = useRef(0);
  const standbyTextRef = useRef<HTMLSpanElement | null>(null);
  const standbyTextBoundsRef = useRef<HTMLDivElement | null>(null);

  const editInputRef = useRef<HTMLInputElement | null>(null);

  const nextScheduledAt = useMemo(() => {
    return state.scheduledMessages[0]?.startAt ?? null;
  }, [state.scheduledMessages]);

  const applyServerState = useCallback(
    (nextState: MessageState, source: "poll" | "mutation" | "schedule") => {
      const currentState = stateRef.current;

      // Poll/scheduled refresh responses can arrive late; never let them overwrite newer UI state.
      if (
        source !== "mutation" &&
        nextState.updatedAt < currentState.updatedAt &&
        nextState.scheduledMessages.length <= currentState.scheduledMessages.length
      ) {
        return;
      }

      stateRef.current = nextState;
      setState(nextState);
    },
    [],
  );

  const refreshState = useCallback(
    async (source: "poll" | "schedule" = "poll") => {
      const requestId = ++latestRefreshRequestIdRef.current;
      const response = await fetch("/api/message", { cache: "no-store" });
      if (!response.ok) {
        return;
      }

      const payload = (await response.json()) as MessageState;

      if (requestId !== latestRefreshRequestIdRef.current) {
        return;
      }

      applyServerState(payload, source);
    },
    [applyServerState],
  );

  useEffect(() => {
    let timeoutId: number | null = null;
    let cancelled = false;

    const tick = async () => {
      if (cancelled) {
        return;
      }

      await refreshState("poll");

      timeoutId = window.setTimeout(() => {
        void tick();
      }, 1000);
    };

    timeoutId = window.setTimeout(() => {
      void tick();
    }, 1000);

    return () => {
      cancelled = true;
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [refreshState]);

  useEffect(() => {
    const markInteraction = () => {
      setHasInteracted(true);

      if (inactivityTimeoutRef.current !== null) {
        window.clearTimeout(inactivityTimeoutRef.current);
      }

      inactivityTimeoutRef.current = window.setTimeout(() => {
        setHasInteracted(false);
      }, 5000);
    };

    window.addEventListener("pointerdown", markInteraction);
    window.addEventListener("keydown", markInteraction);

    return () => {
      window.removeEventListener("pointerdown", markInteraction);
      window.removeEventListener("keydown", markInteraction);

      if (inactivityTimeoutRef.current !== null) {
        window.clearTimeout(inactivityTimeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!nextScheduledAt) {
      return;
    }

    const runAt = new Date(nextScheduledAt).getTime() - Date.now() + 500;
    if (runAt <= 0) {
      const timeoutId = window.setTimeout(() => {
        void refreshState("schedule");
      }, 0);
      return () => {
        window.clearTimeout(timeoutId);
      };
    }

    const timeoutId = window.setTimeout(
      () => {
        void refreshState("schedule");
      },
      Math.min(runAt, 2147483647),
    );

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [nextScheduledAt, refreshState]);

  useLayoutEffect(() => {
    const textEl = standbyTextRef.current;
    const boundsEl = standbyTextBoundsRef.current;

    if (!textEl || !boundsEl) {
      return;
    }

    const fitText = () => {
      const maxWidth = boundsEl.clientWidth;
      const maxHeight = boundsEl.clientHeight;

      if (maxWidth <= 0 || maxHeight <= 0) {
        return;
      }

      let low = 16;
      let high = 220;
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
      setStandbyFontSize(best);
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
  }, [state.activeMessage]);

  const openEdit = () => {
    setSpeedDialOpen(false);
    setEditError(null);
    setEditDraft(state.activeMessage);
    setDialogMode("edit");

    window.setTimeout(() => {
      editInputRef.current?.focus({ preventScroll: true });
    }, 100);
  };

  const openSchedule = () => {
    setSpeedDialOpen(false);
    setScheduleError(null);
    setScheduleDraft(state.activeMessage);
    setScheduleAt(dayjs().add(1, "hour"));
    setIsUpcomingExpanded(false);
    setDialogMode("schedule");
  };

  const closeDialog = () => {
    setDialogMode("none");
    setEditError(null);
    setScheduleError(null);
  };

  const saveEditMessage = async () => {
    setIsSavingEdit(true);
    setEditError(null);

    const response = await fetch("/api/message", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ message: editDraft }),
    }).catch(() => null);

    if (!response) {
      setEditError("Unable to save message.");
      setIsSavingEdit(false);
      return;
    }

    const payload = (await response.json()) as MessageState & { error?: string };

    if (!response.ok) {
      setEditError(payload.error ?? "Unable to save message.");
      setIsSavingEdit(false);
      return;
    }

    applyServerState(payload, "mutation");
    closeDialog();
    setIsSavingEdit(false);
  };

  const saveScheduledMessage = async () => {
    if (!scheduleAt || !scheduleAt.isValid()) {
      setScheduleError("Choose a valid date and time.");
      return;
    }

    setIsSavingSchedule(true);
    setScheduleError(null);

    const response = await fetch("/api/message", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message: scheduleDraft,
        startAt: scheduleAt.toDate().toISOString(),
      }),
    }).catch(() => null);

    if (!response) {
      setScheduleError("Unable to schedule message.");
      setIsSavingSchedule(false);
      return;
    }

    const payload = (await response.json()) as MessageState & { error?: string };

    if (!response.ok) {
      setScheduleError(payload.error ?? "Unable to schedule message.");
      setIsSavingSchedule(false);
      return;
    }

    applyServerState(payload, "mutation");
    closeDialog();
    setIsSavingSchedule(false);
  };

  const deleteSchedule = async (id: string) => {
    const response = await fetch(`/api/message?id=${encodeURIComponent(id)}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      return;
    }

    const payload = (await response.json()) as MessageState;
    applyServerState(payload, "mutation");
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box
        sx={{
          width: "100%",
          minHeight: "100dvh",
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          p: 2,
          bgcolor: "background.default",
        }}
      >
        <Box
          ref={standbyTextBoundsRef}
          sx={{
            width: "94vw",
            maxWidth: 1200,
            height: "92dvh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          <Typography
            ref={standbyTextRef}
            component="span"
            sx={{
              color: "#3f2b1d",
              textAlign: "center",
              fontWeight: 700,
              lineHeight: 1.1,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              overflowWrap: "anywhere",
              fontSize: `${standbyFontSize}px`,
            }}
          >
            {state.activeMessage}
          </Typography>
        </Box>

        <SpeedDial
          ariaLabel="Message settings"
          icon={<SpeedDialIcon />}
          FabProps={{
            color: "primary",
            size: "large",
          }}
          onClose={() => setSpeedDialOpen(false)}
          onOpen={() => setSpeedDialOpen(true)}
          open={speedDialOpen}
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
              tooltip: {
                title: "edit",
                open: true,
              },
            }}
            onClick={openEdit}
          />
          <SpeedDialAction
            icon={<ScheduleIcon />}
            slotProps={{
              tooltip: {
                title: "schedule",
                open: true,
              },
            }}
            onClick={openSchedule}
          />
        </SpeedDial>

        <Dialog fullScreen open={dialogMode === "edit"} onClose={closeDialog}>
          <AppBar position="sticky">
            <Toolbar sx={{ minHeight: 72 }}>
              <IconButton
                color="inherit"
                edge="start"
                onClick={closeDialog}
                aria-label="Close"
                size="large"
              >
                <CloseIcon sx={{ fontSize: 30 }} />
              </IconButton>
              <Typography
                sx={{ flexGrow: 1, ml: 1, fontSize: "1.4rem", fontWeight: 700 }}
                component="h2"
              >
                Edit Message
              </Typography>
              <Button
                color="secondary"
                disabled={isSavingEdit}
                onClick={saveEditMessage}
                size="large"
                variant="contained"
                sx={{ fontSize: "1rem", px: 2.5, fontWeight: 800, boxShadow: 2 }}
              >
                {isSavingEdit ? "Saving..." : "Save"}
              </Button>
            </Toolbar>
          </AppBar>

          <DialogContent sx={{ pb: "52dvh", pt: 2.5 }}>
            <Stack spacing={2.5}>
              <TextField
                inputRef={editInputRef}
                label="Message"
                multiline
                minRows={5}
                maxRows={12}
                value={editDraft}
                onChange={(event) => setEditDraft(event.target.value.slice(0, MAX_MESSAGE_LENGTH))}
                helperText={`${editDraft.length}/${MAX_MESSAGE_LENGTH}`}
                autoFocus
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
                    fontSize: "1.5rem",
                    lineHeight: 1.35,
                  },
                }}
              />

              {editError ? (
                <Alert
                  severity="error"
                  sx={{ fontSize: "1rem", "& .MuiAlert-icon": { fontSize: 24 } }}
                >
                  {editError}
                </Alert>
              ) : null}
            </Stack>
          </DialogContent>
        </Dialog>

        <Dialog fullScreen open={dialogMode === "schedule"} onClose={closeDialog}>
          <AppBar position="sticky" color="secondary">
            <Toolbar sx={{ minHeight: 72 }}>
              <IconButton
                color="inherit"
                edge="start"
                onClick={closeDialog}
                aria-label="Close"
                size="large"
              >
                <CloseIcon sx={{ fontSize: 30 }} />
              </IconButton>
              <Typography
                sx={{ flexGrow: 1, ml: 1, fontSize: "1.4rem", fontWeight: 700 }}
                component="h2"
              >
                Schedule Message
              </Typography>
              <Button
                color="primary"
                disabled={isSavingSchedule}
                onClick={saveScheduledMessage}
                size="large"
                variant="contained"
                sx={{ fontSize: "1rem", px: 2.5, fontWeight: 800, boxShadow: 2 }}
              >
                {isSavingSchedule ? "Saving..." : "Schedule"}
              </Button>
            </Toolbar>
          </AppBar>

          <DialogContent sx={{ pb: "52dvh", pt: 2.5 }}>
            <Stack spacing={2.5}>
              <TextField
                label="Message"
                multiline
                minRows={4}
                maxRows={10}
                value={scheduleDraft}
                onChange={(event) =>
                  setScheduleDraft(event.target.value.slice(0, MAX_MESSAGE_LENGTH))
                }
                helperText={`${scheduleDraft.length}/${MAX_MESSAGE_LENGTH}`}
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

              <MobileDateTimePicker
                label="Show at"
                value={scheduleAt}
                onChange={(value) => setScheduleAt(value)}
                orientation="landscape"
                open={isSchedulePickerOpen}
                onOpen={() => setIsSchedulePickerOpen(true)}
                onClose={() => setIsSchedulePickerOpen(false)}
                disablePast
                slotProps={{
                  mobilePaper: {
                    sx: {
                      margin: 0,
                      maxHeight: "100dvh",
                    },
                  },
                  textField: {
                    onClick: () => setIsSchedulePickerOpen(true),
                    onFocus: (event: React.FocusEvent<HTMLInputElement>) => {
                      event.target.blur();
                      setIsSchedulePickerOpen(true);
                    },
                    inputProps: {
                      readOnly: true,
                    },
                    slotProps: {
                      inputLabel: {
                        sx: { fontSize: "1.05rem" },
                      },
                      formHelperText: {
                        sx: { fontSize: "0.95rem", fontWeight: 600 },
                      },
                    },
                    sx: {
                      "& .MuiInputBase-input": {
                        fontSize: "1.2rem",
                      },
                    },
                  },
                }}
              />

              {scheduleError ? (
                <Alert
                  severity="error"
                  sx={{ fontSize: "1rem", "& .MuiAlert-icon": { fontSize: 24 } }}
                >
                  {scheduleError}
                </Alert>
              ) : null}

              <Divider />

              <Accordion
                expanded={isUpcomingExpanded}
                onChange={(_, expanded) => setIsUpcomingExpanded(expanded)}
                disableGutters
                elevation={0}
                sx={{
                  border: "1px solid",
                  borderColor: "divider",
                  borderRadius: 1,
                  overflow: "hidden",
                  "&:before": {
                    display: "none",
                  },
                }}
              >
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography color="text.secondary" sx={{ fontSize: "1rem", fontWeight: 700 }}>
                    Upcoming messages ({state.scheduledMessages.length})
                  </Typography>
                </AccordionSummary>
                <AccordionDetails>
                  {state.scheduledMessages.length === 0 ? (
                    <Typography color="text.secondary" sx={{ fontSize: "1rem" }}>
                      No scheduled messages.
                    </Typography>
                  ) : (
                    <List sx={{ p: 0 }}>
                      {state.scheduledMessages.map((schedule) => (
                        <ListItem
                          key={schedule.id}
                          secondaryAction={
                            <IconButton
                              edge="end"
                              aria-label="Delete schedule"
                              onClick={() => void deleteSchedule(schedule.id)}
                              color="error"
                            >
                              <DeleteOutlineIcon />
                            </IconButton>
                          }
                          sx={{
                            pr: 7,
                            mb: 1,
                            backgroundColor: "background.paper",
                          }}
                        >
                          <ListItemText
                            primary={schedule.message}
                            secondary={`Starts ${formatDateTime(schedule.startAt)}`}
                            slotProps={{
                              primary: {
                                sx: {
                                  fontSize: "1.05rem",
                                  fontWeight: 600,
                                  whiteSpace: "nowrap",
                                  overflow: "hidden",
                                  textOverflow: "ellipsis",
                                  display: "block",
                                },
                              },
                              secondary: { sx: { fontSize: "0.95rem" } },
                            }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                </AccordionDetails>
              </Accordion>
            </Stack>
          </DialogContent>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
}
