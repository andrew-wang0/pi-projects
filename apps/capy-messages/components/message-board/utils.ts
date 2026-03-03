import type { BackgroundOption } from "@/lib/background-options";
import type { MessageState } from "@/lib/message-store";

import { IMAGE_HEIGHT, IMAGE_WIDTH } from "./constants";

export type BoundsStyle = {
  left: string;
  top: string;
  width: string;
  height: string;
};

type FitFontSizeArgs = {
  textEl: HTMLElement;
  boundsEl: HTMLElement;
  text: string;
  minFontSize: number;
  maxFontSize: number;
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

function createWordMeasureElement(textEl: HTMLElement) {
  const computed = window.getComputedStyle(textEl);
  const measureEl = document.createElement("span");
  measureEl.style.position = "absolute";
  measureEl.style.visibility = "hidden";
  measureEl.style.pointerEvents = "none";
  measureEl.style.whiteSpace = "nowrap";
  measureEl.style.fontFamily = computed.fontFamily;
  measureEl.style.fontWeight = computed.fontWeight;
  measureEl.style.fontStyle = computed.fontStyle;
  measureEl.style.letterSpacing = computed.letterSpacing;
  measureEl.style.textTransform = computed.textTransform;
  measureEl.style.lineHeight = computed.lineHeight;
  document.body.appendChild(measureEl);
  return measureEl;
}

export function findBestFittingFontSize({
  textEl,
  boundsEl,
  text,
  minFontSize,
  maxFontSize,
}: FitFontSizeArgs) {
  const maxWidth = boundsEl.clientWidth;
  const maxHeight = boundsEl.clientHeight;

  if (maxWidth <= 0 || maxHeight <= 0) {
    return minFontSize;
  }

  const words = text.match(/\S+/g) ?? [];
  const measureEl = words.length > 0 ? createWordMeasureElement(textEl) : null;

  let low = minFontSize;
  let high = maxFontSize;
  let best = minFontSize;

  try {
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      textEl.style.fontSize = `${mid}px`;

      const fitsBounds = textEl.scrollWidth <= maxWidth && textEl.scrollHeight <= maxHeight;
      let widestWordFits = true;

      if (fitsBounds && measureEl) {
        measureEl.style.fontSize = `${mid}px`;

        for (const word of words) {
          measureEl.textContent = word;
          if (measureEl.getBoundingClientRect().width > maxWidth) {
            widestWordFits = false;
            break;
          }
        }
      }

      if (fitsBounds && widestWordFits) {
        best = mid;
        low = mid + 1;
      } else {
        high = mid - 1;
      }
    }
  } finally {
    measureEl?.remove();
  }

  return best;
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
