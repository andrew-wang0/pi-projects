import { type FSWatcher, mkdirSync, watch } from "node:fs";
import path from "node:path";

type MessageStateListener = () => void;

const listeners = new Set<MessageStateListener>();
let watcherStarted = false;
let watcher: FSWatcher | null = null;
let pendingNotifyTimeout: NodeJS.Timeout | null = null;

function emitChange() {
  for (const listener of Array.from(listeners)) {
    listener();
  }
}

function scheduleEmitChange() {
  if (pendingNotifyTimeout) {
    clearTimeout(pendingNotifyTimeout);
  }

  pendingNotifyTimeout = setTimeout(() => {
    pendingNotifyTimeout = null;
    emitChange();
  }, 120);
}

function ensureWatcher() {
  if (watcherStarted) {
    return;
  }

  watcherStarted = true;

  const dataDir = path.join(process.cwd(), "data");

  try {
    mkdirSync(dataDir, { recursive: true });
    watcher = watch(dataDir, { persistent: false }, () => {
      scheduleEmitChange();
    });

    watcher.on("error", () => {
      watcher?.close();
      watcher = null;
    });
  } catch {
    // Watcher is best-effort; API notifications still keep clients in sync.
  }
}

export function subscribeMessageState(listener: MessageStateListener) {
  ensureWatcher();
  listeners.add(listener);

  return () => {
    listeners.delete(listener);
  };
}

export function notifyMessageStateChanged() {
  emitChange();
}
