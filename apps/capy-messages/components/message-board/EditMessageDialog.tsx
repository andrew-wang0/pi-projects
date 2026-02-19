import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CloseIcon from "@mui/icons-material/Close";
import {
  Alert,
  AppBar,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Stack,
  TextField,
  Toolbar,
  Typography,
} from "@mui/material";
import React, { useEffect } from "react";

import BackgroundPicker from "./BackgroundPicker";
import { EDIT_STEP_COUNT, MAX_MESSAGE_LENGTH } from "./constants";

type EditMessageDialogProps = {
  open: boolean;
  step: number;
  draft: string;
  backgroundId: string;
  isSaving: boolean;
  error: string | null;
  onClose: () => void;
  onBack: () => void;
  onPrimaryAction: () => void;
  onDraftChange: (nextValue: string) => void;
  onBackgroundSelect: (nextBackgroundId: string) => void;
  inputRef: React.RefObject<HTMLInputElement | HTMLTextAreaElement | null>;
};

export default function EditMessageDialog({
  open,
  step,
  draft,
  backgroundId,
  isSaving,
  error,
  onClose,
  onBack,
  onPrimaryAction,
  onDraftChange,
  onBackgroundSelect,
  inputRef,
}: EditMessageDialogProps) {
  useEffect(() => {
    if (!open || step !== 0) {
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
      <AppBar position="sticky">
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
            Edit Message
          </Typography>
          <Button
            color="secondary"
            disabled={isSaving}
            onClick={onPrimaryAction}
            size="large"
            variant="contained"
            sx={{ fontSize: "1rem", px: 2.5, fontWeight: 800, boxShadow: 2 }}
          >
            {step < EDIT_STEP_COUNT - 1 ? "Next" : isSaving ? "Saving..." : "Confirm"}
          </Button>
        </Toolbar>
      </AppBar>

      <DialogContent sx={{ pb: step === 0 ? "52dvh" : 2.5, pt: 2.5 }}>
        <Stack spacing={2.5}>
          {step === 0 ? (
            <TextField
              inputRef={inputRef}
              label="Message"
              multiline
              minRows={5}
              maxRows={12}
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
                  fontSize: "1.5rem",
                  lineHeight: 1.35,
                },
              }}
            />
          ) : null}

          {step === 1 ? (
            <>
              <Typography color="text.secondary" sx={{ fontSize: "1rem", fontWeight: 700 }}>
                Background
              </Typography>
              <BackgroundPicker selectedBackgroundId={backgroundId} onSelect={onBackgroundSelect} />
            </>
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
