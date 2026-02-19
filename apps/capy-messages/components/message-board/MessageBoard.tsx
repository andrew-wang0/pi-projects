"use client";

import { Box } from "@mui/material";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import dayjs, { type Dayjs } from "dayjs";
import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { type BackgroundOption, getBackgroundOption } from "@/lib/background-options";
import type { MessageState } from "@/lib/message-store";

import { EDIT_STEP_COUNT, SCHEDULE_STEP_COUNT } from "./constants";
import EditMessageDialog from "./EditMessageDialog";
import ScheduleMessageDialog from "./ScheduleMessageDialog";
import SettingsSpeedDial from "./SettingsSpeedDial";
import StandbyDisplay from "./StandbyDisplay";
import UpcomingMessagesDialog from "./UpcomingMessagesDialog";
import { areMessageStatesEqual, toBoundsStyle } from "./utils";

type MessageBoardProps = {
  initialState: MessageState;
};

type DialogMode = "none" | "edit" | "schedule" | "upcoming";
function earliestValidTimeForDay(day: Dayjs) {
  const dayStart = day.startOf("day");
  const earliestNow = dayjs().add(1, "minute").startOf("minute");

  if (dayStart.isAfter(earliestNow)) {
    return dayStart;
  }

  return earliestNow;
}

function nextDayDefaultScheduleTime() {
  return earliestValidTimeForDay(dayjs().add(1, "day"));
}

export default function MessageBoard({ initialState }: MessageBoardProps) {
  const [state, setState] = useState<MessageState>(initialState);
  const [speedDialOpen, setSpeedDialOpen] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [interactionNonce, setInteractionNonce] = useState(0);
  const [dialogMode, setDialogMode] = useState<DialogMode>("none");

  const [editDraft, setEditDraft] = useState(initialState.activeMessage);
  const [editBackgroundId, setEditBackgroundId] = useState(initialState.activeBackgroundId);
  const [editStep, setEditStep] = useState(0);

  const [scheduleDraft, setScheduleDraft] = useState(initialState.activeMessage);
  const [scheduleBackgroundId, setScheduleBackgroundId] = useState(initialState.activeBackgroundId);
  const [scheduleAt, setScheduleAt] = useState<Dayjs | null>(nextDayDefaultScheduleTime());
  const [scheduleStep, setScheduleStep] = useState(0);
  const [upcomingDay, setUpcomingDay] = useState<Dayjs>(dayjs().startOf("day"));
  const [upcomingStep, setUpcomingStep] = useState(0);

  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [standbyFontSize, setStandbyFontSize] = useState(72);

  const inactivityTimeoutRef = useRef<number | null>(null);
  const stateRef = useRef<MessageState>(initialState);
  const latestRefreshRequestIdRef = useRef(0);
  const standbyTextRef = useRef<HTMLSpanElement | null>(null);
  const standbyTextBoundsRef = useRef<HTMLDivElement | null>(null);
  const editInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);
  const scheduleInputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  const selectedBackground = useMemo<BackgroundOption>(() => {
    return getBackgroundOption(state.activeBackgroundId);
  }, [state.activeBackgroundId]);

  const textBoundsStyle = useMemo(() => {
    return toBoundsStyle(selectedBackground.bounds);
  }, [selectedBackground.bounds]);

  const nextScheduledAt = useMemo(() => {
    return state.scheduledMessages[0]?.startAt ?? null;
  }, [state.scheduledMessages]);

  const hasScheduleConflictAtMinute = useCallback(
    (value: Dayjs) => {
      const candidateMinuteKey = value.startOf("minute").format("YYYY-MM-DDTHH:mm");

      return state.scheduledMessages.some((scheduledMessage) => {
        const scheduledMinuteKey = dayjs(scheduledMessage.startAt)
          .startOf("minute")
          .format("YYYY-MM-DDTHH:mm");
        return scheduledMinuteKey === candidateMinuteKey;
      });
    },
    [state.scheduledMessages],
  );

  const getScheduleValidationError = useCallback(
    (value: Dayjs | null) => {
      if (!value || !value.isValid()) {
        return "Choose a valid date and time.";
      }

      if (value.toDate().getTime() <= Date.now()) {
        return "Schedule time must be in the future.";
      }

      if (hasScheduleConflictAtMinute(value)) {
        return "A message is already scheduled for that time.";
      }

      return null;
    },
    [hasScheduleConflictAtMinute],
  );

  const applyServerState = useCallback(
    (nextState: MessageState, source: "poll" | "mutation" | "schedule") => {
      const currentState = stateRef.current;

      if (
        source !== "mutation" &&
        nextState.updatedAt < currentState.updatedAt &&
        nextState.scheduledMessages.length <= currentState.scheduledMessages.length
      ) {
        return;
      }

      if (areMessageStatesEqual(currentState, nextState)) {
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
    const eventSource = new EventSource("/api/message/stream");

    eventSource.onmessage = (event) => {
      const payload = JSON.parse(event.data) as MessageState;
      applyServerState(payload, "poll");
    };

    eventSource.onerror = () => {
      void refreshState("poll");
    };

    const fallbackIntervalId = window.setInterval(() => {
      void refreshState("poll");
    }, 60000);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void refreshState("poll");
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      eventSource.close();
      window.clearInterval(fallbackIntervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [applyServerState, refreshState]);

  useEffect(() => {
    const markInteraction = () => {
      setHasInteracted(true);
      setInteractionNonce((value) => value + 1);

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
    if (!speedDialOpen) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setSpeedDialOpen(false);
    }, 5000);

    return () => {
      window.clearTimeout(timeoutId);
    };
  }, [speedDialOpen, interactionNonce]);

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

      let low = 8;
      let high = Math.max(220, Math.ceil(Math.max(maxWidth, maxHeight) * 1.5));
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
  }, [state.activeMessage, state.activeBackgroundId]);

  const openEdit = () => {
    setSpeedDialOpen(false);
    setEditError(null);
    setEditDraft(state.activeMessage);
    setEditBackgroundId(state.activeBackgroundId);
    setEditStep(0);
    setDialogMode("edit");
  };

  const openSchedule = () => {
    const defaultScheduleTime = nextDayDefaultScheduleTime();

    setSpeedDialOpen(false);
    setScheduleError(getScheduleValidationError(defaultScheduleTime));
    setScheduleDraft(state.activeMessage);
    setScheduleBackgroundId(state.activeBackgroundId);
    setScheduleAt(defaultScheduleTime);
    setScheduleStep(0);
    setDialogMode("schedule");
  };

  const openUpcoming = () => {
    setSpeedDialOpen(false);

    const firstUpcomingDay = state.scheduledMessages[0]?.startAt.slice(0, 10);
    setUpcomingStep(0);
    setUpcomingDay(
      firstUpcomingDay ? dayjs(firstUpcomingDay).startOf("day") : dayjs().startOf("day"),
    );
    setDialogMode("upcoming");
  };

  const closeDialog = () => {
    setDialogMode("none");
    setEditError(null);
    setScheduleError(null);
  };

  const blurActiveField = () => {
    const activeElement = document.activeElement;

    if (activeElement instanceof HTMLElement) {
      activeElement.blur();
    }
  };

  const goBackInEdit = () => {
    if (editStep === 0) {
      closeDialog();
      return;
    }

    setEditStep((step) => Math.max(0, step - 1));
  };

  const goBackInSchedule = () => {
    if (scheduleStep === 0) {
      closeDialog();
      return;
    }

    setScheduleStep((step) => Math.max(0, step - 1));
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
        body: JSON.stringify({
          message: editDraft,
          backgroundId: editBackgroundId,
        }),
      });

      const payload = (await response.json()) as MessageState & { error?: string };

      if (!response.ok) {
        setEditError(payload.error ?? "Unable to save message.");
        return;
      }

      applyServerState(payload, "mutation");
      closeDialog();
    } finally {
      setIsSavingEdit(false);
    }
  };

  const saveScheduledMessage = async () => {
    const scheduleAtValue = scheduleAt;
    const validationError = getScheduleValidationError(scheduleAtValue);

    if (validationError || !scheduleAtValue || !scheduleAtValue.isValid()) {
      setScheduleError(validationError ?? "Choose a valid date and time.");
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
          backgroundId: scheduleBackgroundId,
          startAt: scheduleAtValue.toDate().toISOString(),
        }),
      });

      const payload = (await response.json()) as MessageState & { error?: string };

      if (!response.ok) {
        setScheduleError(payload.error ?? "Unable to schedule message.");
        return;
      }

      applyServerState(payload, "mutation");
      closeDialog();
    } finally {
      setIsSavingSchedule(false);
    }
  };

  const handleScheduleAtChange = (nextValue: Dayjs | null) => {
    if (!nextValue || !nextValue.isValid()) {
      setScheduleAt(nextValue);
      setScheduleError(getScheduleValidationError(nextValue));
      return;
    }

    const previousValue = scheduleAt;
    const normalizedValue =
      !previousValue || !previousValue.isValid() || !nextValue.isSame(previousValue, "day")
        ? earliestValidTimeForDay(nextValue)
        : nextValue;

    setScheduleAt(normalizedValue);
    setScheduleError(getScheduleValidationError(normalizedValue));
  };

  const handleEditPrimaryAction = () => {
    if (editStep < EDIT_STEP_COUNT - 1) {
      if (editStep === 0) {
        blurActiveField();
      }

      setEditStep((step) => Math.min(EDIT_STEP_COUNT - 1, step + 1));
      return;
    }

    void saveEditMessage();
  };

  const handleSchedulePrimaryAction = () => {
    if (scheduleStep < SCHEDULE_STEP_COUNT - 1) {
      if (scheduleStep === 0) {
        const validationError = getScheduleValidationError(scheduleAt);

        if (validationError) {
          setScheduleError(validationError);
          return;
        }
      }

      if (scheduleStep === 1) {
        blurActiveField();
      }

      setScheduleError(null);
      setScheduleStep((step) => Math.min(SCHEDULE_STEP_COUNT - 1, step + 1));
      return;
    }

    void saveScheduledMessage();
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
          overflow: "hidden",
          bgcolor: "background.default",
        }}
      >
        <StandbyDisplay
          background={selectedBackground}
          message={state.activeMessage}
          textBoundsStyle={textBoundsStyle}
          standbyFontSize={standbyFontSize}
          textRef={standbyTextRef}
          textBoundsRef={standbyTextBoundsRef}
        />

        <SettingsSpeedDial
          open={speedDialOpen}
          hasInteracted={hasInteracted}
          onOpen={() => setSpeedDialOpen(true)}
          onClose={() => setSpeedDialOpen(false)}
          onEdit={openEdit}
          onSchedule={openSchedule}
          onUpcoming={openUpcoming}
        />

        <EditMessageDialog
          open={dialogMode === "edit"}
          step={editStep}
          draft={editDraft}
          backgroundId={editBackgroundId}
          isSaving={isSavingEdit}
          error={editError}
          onClose={closeDialog}
          onBack={goBackInEdit}
          onPrimaryAction={handleEditPrimaryAction}
          onDraftChange={setEditDraft}
          onBackgroundSelect={setEditBackgroundId}
          inputRef={editInputRef}
        />

        <ScheduleMessageDialog
          open={dialogMode === "schedule"}
          step={scheduleStep}
          draft={scheduleDraft}
          scheduledMessages={state.scheduledMessages}
          backgroundId={scheduleBackgroundId}
          scheduleAt={scheduleAt}
          isSaving={isSavingSchedule}
          error={scheduleError}
          onClose={closeDialog}
          onBack={goBackInSchedule}
          onPrimaryAction={handleSchedulePrimaryAction}
          onDraftChange={setScheduleDraft}
          onBackgroundSelect={setScheduleBackgroundId}
          onScheduleAtChange={handleScheduleAtChange}
          inputRef={scheduleInputRef}
        />

        <UpcomingMessagesDialog
          open={dialogMode === "upcoming"}
          step={upcomingStep}
          selectedDay={upcomingDay}
          scheduledMessages={state.scheduledMessages}
          onClose={closeDialog}
          onStepChange={setUpcomingStep}
          onDayChange={setUpcomingDay}
          onDeleteSchedule={(id) => {
            void deleteSchedule(id);
          }}
        />
      </Box>
    </LocalizationProvider>
  );
}
