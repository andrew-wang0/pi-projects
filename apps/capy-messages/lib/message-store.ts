import { promises as fs } from "node:fs";
import path from "node:path";

import { BACKGROUND_OPTIONS, DEFAULT_BACKGROUND_ID } from "@/lib/background-options";

const DATA_DIR = path.join(process.cwd(), "data");
const DEFAULT_MESSAGE = "Tap settings to edit this message.";
const MAX_MESSAGE_LENGTH = 100;
const FILE_NAME_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.json$/;
const VALID_BACKGROUND_IDS = new Set(BACKGROUND_OPTIONS.map((option) => option.id));
type StoredMessageFile = {
  message: string;
  backgroundId: string;
};

export type ScheduledMessage = {
  id: string;
  message: string;
  backgroundId: string;
  startAt: string;
  createdAt: string;
};

export type MessageState = {
  activeMessage: string;
  activeBackgroundId: string;
  updatedAt: string;
  scheduledMessages: ScheduledMessage[];
};

function sanitizeMessage(input: string) {
  const trimmed = input.trim();
  const safeValue = trimmed.length === 0 ? DEFAULT_MESSAGE : trimmed;
  return safeValue.slice(0, MAX_MESSAGE_LENGTH);
}

function sanitizeBackgroundId(input: unknown) {
  return typeof input === "string" && VALID_BACKGROUND_IDS.has(input)
    ? input
    : DEFAULT_BACKGROUND_ID;
}

function pacificTimestampNoTimezone(date = new Date()) {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/Los_Angeles",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });

  const parts = formatter.formatToParts(date);
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "00";

  return `${get("year")}-${get("month")}-${get("day")}T${get("hour")}:${get("minute")}:${get("second")}`;
}

function normalizeToMinute(date: Date) {
  const next = new Date(date);
  next.setSeconds(0, 0);
  return next;
}

function keyFromFileName(fileName: string) {
  return fileName.slice(0, -5);
}

function fileNameFromKey(key: string) {
  return `${key}.json`;
}

async function ensureDataDir() {
  await fs.mkdir(DATA_DIR, { recursive: true });
}

async function listMessageFiles() {
  await ensureDataDir();

  const entries = await fs.readdir(DATA_DIR, { withFileTypes: true });

  return entries
    .filter((entry) => entry.isFile() && FILE_NAME_PATTERN.test(entry.name))
    .map((entry) => entry.name)
    .sort((a, b) => a.localeCompare(b));
}

async function readMessageFile(fileName: string): Promise<StoredMessageFile | null> {
  try {
    const filePath = path.join(DATA_DIR, fileName);
    const raw = await fs.readFile(filePath, "utf-8");
    const parsed = JSON.parse(raw) as { message?: unknown; backgroundId?: unknown };

    if (typeof parsed.message !== "string") {
      return null;
    }

    return {
      message: sanitizeMessage(parsed.message),
      backgroundId: sanitizeBackgroundId(parsed.backgroundId),
    };
  } catch {
    return null;
  }
}

async function writeMessageFile(key: string, message: string, backgroundId: string) {
  await ensureDataDir();

  const filePath = path.join(DATA_DIR, fileNameFromKey(key));
  const payload = {
    message: sanitizeMessage(message),
    backgroundId: sanitizeBackgroundId(backgroundId),
  };

  await fs.writeFile(filePath, JSON.stringify(payload, null, 2), "utf-8");
}

async function hasMessageFileForKey(key: string) {
  const filePath = path.join(DATA_DIR, fileNameFromKey(key));

  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function ensureAtLeastOneMessageFile() {
  const files = await listMessageFiles();

  if (files.length > 0) {
    return;
  }

  await writeMessageFile(
    pacificTimestampNoTimezone(new Date()),
    DEFAULT_MESSAGE,
    DEFAULT_BACKGROUND_ID,
  );
}

export async function readMessageState(): Promise<MessageState> {
  await ensureAtLeastOneMessageFile();

  const files = await listMessageFiles();
  const nowKey = pacificTimestampNoTimezone(new Date());

  let activeMessage = DEFAULT_MESSAGE;
  let activeBackgroundId = DEFAULT_BACKGROUND_ID;
  let updatedAt = nowKey;
  const scheduledMessages: ScheduledMessage[] = [];

  for (const fileName of files) {
    const key = keyFromFileName(fileName);
    const fileData = await readMessageFile(fileName);

    if (!fileData) {
      continue;
    }

    if (key <= nowKey) {
      activeMessage = fileData.message;
      activeBackgroundId = fileData.backgroundId;
      updatedAt = key;
      continue;
    }

    scheduledMessages.push({
      id: key,
      message: fileData.message,
      backgroundId: fileData.backgroundId,
      startAt: key,
      createdAt: key,
    });
  }

  return {
    activeMessage,
    activeBackgroundId,
    updatedAt,
    scheduledMessages,
  };
}

export async function saveActiveMessage(
  message: string,
  backgroundId: string = DEFAULT_BACKGROUND_ID,
): Promise<MessageState> {
  await writeMessageFile(pacificTimestampNoTimezone(new Date()), message, backgroundId);
  return readMessageState();
}

export async function scheduleMessage(
  message: string,
  startAt: string,
  backgroundId: string = DEFAULT_BACKGROUND_ID,
): Promise<MessageState> {
  const scheduleDate = normalizeToMinute(new Date(startAt));

  if (Number.isNaN(scheduleDate.getTime())) {
    throw new Error("Invalid schedule time.");
  }

  if (scheduleDate.getTime() <= Date.now()) {
    throw new Error("Schedule time must be in the future.");
  }

  const scheduleKey = pacificTimestampNoTimezone(scheduleDate);
  const scheduleMinuteKey = scheduleKey.slice(0, 16);

  const current = await readMessageState();
  const hasDuplicateMinute = current.scheduledMessages.some(
    (scheduledMessage) => scheduledMessage.startAt.slice(0, 16) === scheduleMinuteKey,
  );

  if (hasDuplicateMinute || (await hasMessageFileForKey(scheduleKey))) {
    throw new Error("A message is already scheduled for that time.");
  }

  await writeMessageFile(scheduleKey, message, backgroundId);
  return readMessageState();
}

export async function deleteScheduledMessage(id: string): Promise<MessageState> {
  const filePath = path.join(DATA_DIR, fileNameFromKey(id));

  try {
    await fs.unlink(filePath);
  } catch {
    // Ignore missing file and return the latest state.
  }

  return readMessageState();
}
