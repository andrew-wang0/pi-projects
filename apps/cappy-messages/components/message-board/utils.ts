import type { BackgroundOption } from "@/lib/background-options";
import type { MessageState } from "@/lib/message-store";

import { IMAGE_HEIGHT, IMAGE_WIDTH } from "./constants";

export type BoundsStyle = {
  left: string;
  top: string;
  width: string;
  height: string;
};

export function formatDateTime(value: string) {
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

export function toBoundsStyle(bounds: BackgroundOption["bounds"]): BoundsStyle {
  const { x1, y1, x2, y2 } = bounds;

  return {
    left: `${(x1 / IMAGE_WIDTH) * 100}%`,
    top: `${(y1 / IMAGE_HEIGHT) * 100}%`,
    width: `${((x2 - x1) / IMAGE_WIDTH) * 100}%`,
    height: `${((y2 - y1) / IMAGE_HEIGHT) * 100}%`,
  };
}

export function areMessageStatesEqual(a: MessageState, b: MessageState) {
  if (
    a.activeMessage !== b.activeMessage ||
    a.activeBackgroundId !== b.activeBackgroundId ||
    a.updatedAt !== b.updatedAt ||
    a.scheduledMessages.length !== b.scheduledMessages.length
  ) {
    return false;
  }

  for (let index = 0; index < a.scheduledMessages.length; index += 1) {
    const left = a.scheduledMessages[index];
    const right = b.scheduledMessages[index];

    if (
      left.id !== right.id ||
      left.message !== right.message ||
      left.backgroundId !== right.backgroundId ||
      left.startAt !== right.startAt ||
      left.createdAt !== right.createdAt
    ) {
      return false;
    }
  }

  return true;
}
