"use client";

import CloseIcon from "@mui/icons-material/Close";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ScheduleIcon from "@mui/icons-material/Schedule";
import {
  Alert,
  AppBar,
  Box,
  Button,
  Dialog,
  DialogContent,
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
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";

import type { MessageState } from "@/lib/message-store";

const MAX_MESSAGE_LENGTH = 800;

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
  const inactivityTimeoutRef = useRef<number | null>(null);
  const stateRef = useRef<MessageState>(initialState);
  const latestRefreshRequestIdRef = useRef(0);

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
      void refreshState("schedule");
      return;
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

  const openEdit = () => {
    setSpeedDialOpen(false);
    setEditError(null);
    setEditDraft(state.activeMessage);
    setDialogMode("edit");

    window.setTimeout(() => {
      editInputRef.current?.focus();
      editInputRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 100);
  };

  const openSchedule = () => {
    setSpeedDialOpen(false);
    setScheduleError(null);
    setScheduleDraft(state.activeMessage);
    setScheduleAt(dayjs().add(1, "hour"));
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

    try {
      const response = await fetch("/api/message", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: editDraft }),
      });

      const payload = (await response.json()) as MessageState & { error?: string };

      if (!response.ok) {
        throw new Error(payload.error ?? "Unable to save message.");
      }

      applyServerState(payload, "mutation");
      closeDialog();
    } catch (error) {
      setEditError(error instanceof Error ? error.message : "Unable to save message.");
    } finally {
      setIsSavingEdit(false);
    }
  };

  const saveScheduledMessage = async () => {
    if (!scheduleAt || !scheduleAt.isValid()) {
      setScheduleError("Choose a valid date and time.");
      return;
    }

    setIsSavingSchedule(true);
    setScheduleError(null);

    try {
      const response = await fetch("/api/message", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: scheduleDraft,
          startAt: scheduleAt.toDate().toISOString(),
        }),
      });

      const payload = (await response.json()) as MessageState & { error?: string };

      if (!response.ok) {
        throw new Error(payload.error ?? "Unable to schedule message.");
      }

      applyServerState(payload, "mutation");
      closeDialog();
    } catch (error) {
      setScheduleError(error instanceof Error ? error.message : "Unable to schedule message.");
    } finally {
      setIsSavingSchedule(false);
    }
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
        <Typography
          sx={{
            color: "#3f2b1d",
            textAlign: "center",
            fontWeight: 700,
            lineHeight: 1.1,
            maxWidth: "94vw",
            whiteSpace: "pre-wrap",
            wordBreak: "break-word",
            fontSize: {
              xs: "clamp(2rem, 9vw, 3.2rem)",
              sm: "clamp(2.8rem, 6.5vw, 4.7rem)",
            },
          }}
        >
          {state.activeMessage}
        </Typography>

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
              <Typography color="text.secondary" sx={{ fontSize: "1rem", fontWeight: 600 }}>
                Last saved {formatDateTime(state.updatedAt)}
              </Typography>

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

              <Box>
                <Typography
                  color="text.secondary"
                  sx={{ mb: 1, fontSize: "1rem", fontWeight: 700 }}
                >
                  Upcoming messages
                </Typography>

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
                            primary: { sx: { fontSize: "1.05rem", fontWeight: 600 } },
                            secondary: { sx: { fontSize: "0.95rem" } },
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Box>
            </Stack>
          </DialogContent>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
}
