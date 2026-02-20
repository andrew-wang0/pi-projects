export type BackgroundOption = {
  id: string;
  label: string;
  src: string | null;
  textColor?: string;
  text_color?: string;
  bounds: {
    x1: number;
    y1: number;
    x2: number;
    y2: number;
  };
};

export const BACKGROUND_OPTIONS: BackgroundOption[] = [
  {
    id: "default",
    label: "Default",
    src: null,
    textColor: "#3f2b1d",
    bounds: {
      x1: 40,
      y1: 30,
      x2: 760,
      y2: 450,
    },
  },
  {
    id: "beach",
    label: "Beach",
    src: "/backgrounds/beach.jpg",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 300,
    },
  },
  {
    id: "fire",
    label: "Fire",
    src: "/backgrounds/fire.gif",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 470,
    },
  },
  {
    id: "fruits",
    label: "Fruits",
    src: "/backgrounds/fruits.gif",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 470,
    },
  },
  {
    id: "frances",
    label: "Frances",
    src: "/backgrounds/frances.jpg",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 470,
    },
  },
  {
    id: "sleep",
    label: "Sleep",
    src: "/backgrounds/sleep.jpg",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 470,
    },
  },
  {
    id: "night",
    label: "Night",
    src: "/backgrounds/night.gif",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 470,
    },
  },
  {
    id: "tranquil",
    label: "Tranquil",
    src: "/backgrounds/tranquil.gif",
    textColor: "#fff",
    bounds: {
      x1: 10,
      y1: 10,
      x2: 790,
      y2: 250,
    },
  },
];

export const DEFAULT_BACKGROUND_ID = "default";

export function getBackgroundOption(backgroundId: string) {
  return BACKGROUND_OPTIONS.find((option) => option.id === backgroundId) ?? BACKGROUND_OPTIONS[0];
}

export function getBackgroundTextColor(option: BackgroundOption) {
  return option.textColor ?? option.text_color;
}
