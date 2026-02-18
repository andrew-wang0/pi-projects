import { promises as fs } from "node:fs";
import path from "node:path";

const DATA_DIR = path.join(process.cwd(), "data");
const DEFAULT_MESSAGE = "Tap settings to edit this message.";
const MAX_MESSAGE_LENGTH = 100;
const FILE_NAME_PATTERN = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.json$/;

export type ScheduledMessage = {
  id: string;
  message: string;
  startAt: string;
  createdAt: string;
};

export type MessageState = {
  activeMessage: string;
  updatedAt: string;
  scheduledMessages: ScheduledMessage[];
};

function sanitizeMessage(input: string) {
  const trimmed = input.trim();
  const safeValue = trimmed.length === 0 ? DEFAULT_MESSAGE : trimmed;
  return safeValue.slice(0, MAX_MESSAGE_LENGTH);
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

async function readMessageFile(fileName: string): Promise<string | null> {
  try {
    const filePath = path.join(DATA_DIR, fileName);
    const raw = await fs.readFile(filePath, "utf-8");
    const parsed = JSON.parse(raw) as { message?: unknown };

    if (typeof parsed.message !== "string") {
      return null;
    }

    return sanitizeMessage(parsed.message);
  } catch {
    return null;
  }
}

async function writeMessageFile(key: string, message: string) {
  await ensureDataDir();

  const filePath = path.join(DATA_DIR, fileNameFromKey(key));
  const payload = { message: sanitizeMessage(message) };

  await fs.writeFile(filePath, JSON.stringify(payload, null, 2), "utf-8");
}

async function ensureAtLeastOneMessageFile() {
  const files = await listMessageFiles();

  if (files.length > 0) {
    return;
  }

  await writeMessageFile(pacificTimestampNoTimezone(new Date()), DEFAULT_MESSAGE);
}

export async function readMessageState(): Promise<MessageState> {
  await ensureAtLeastOneMessageFile();

  const files = await listMessageFiles();
  const nowKey = pacificTimestampNoTimezone(new Date());

  let activeMessage = DEFAULT_MESSAGE;
  let updatedAt = nowKey;
  const scheduledMessages: ScheduledMessage[] = [];

  for (const fileName of files) {
    const key = keyFromFileName(fileName);
    const message = await readMessageFile(fileName);

    if (!message) {
      continue;
    }

    if (key <= nowKey) {
      activeMessage = message;
      updatedAt = key;
      continue;
    }

    scheduledMessages.push({
      id: key,
      message,
      startAt: key,
      createdAt: key,
    });
  }

  return {
    activeMessage,
    updatedAt,
    scheduledMessages,
  };
}

export async function saveActiveMessage(message: string): Promise<MessageState> {
  await writeMessageFile(pacificTimestampNoTimezone(new Date()), message);
  return readMessageState();
}

export async function scheduleMessage(message: string, startAt: string): Promise<MessageState> {
  const scheduleDate = new Date(startAt);

  if (Number.isNaN(scheduleDate.getTime())) {
    throw new Error("Invalid schedule time.");
  }

  if (scheduleDate.getTime() <= Date.now()) {
    throw new Error("Schedule time must be in the future.");
  }

  await writeMessageFile(pacificTimestampNoTimezone(scheduleDate), message);
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
