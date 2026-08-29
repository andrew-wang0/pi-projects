const assert = require("node:assert/strict");
const test = require("node:test");

let InkyCard;

global.HTMLElement = class {
  attachShadow() {
    this.shadowRoot = {
      getElementById() {
        return undefined;
      },
    };
  }
};
global.customElements = {
  get() {
    return undefined;
  },
  define(_name, card) {
    InkyCard = card;
  },
};
global.window = {};
global.document = {
  createElement() {
    return { innerHTML: "", textContent: "" };
  },
};

require("./inky-card.js");

function imageFile(bytes, type) {
  return new Blob([Uint8Array.from(bytes)], { type });
}

test("requests a full-width sections card", () => {
  assert.deepEqual(new InkyCard().getGridOptions(), {
    columns: "full",
    min_columns: 6,
  });
});

test("maps and clamps pointer coordinates at any rendered size", () => {
  const card = new InkyCard();
  card._canvas = {
    getBoundingClientRect() {
      return { left: 10, top: 20, width: 400, height: 240 };
    },
  };

  assert.deepEqual(card._point({ clientX: 210, clientY: 140 }), {
    x: 400,
    y: 240,
  });
  assert.deepEqual(card._point({ clientX: -50, clientY: 400 }), {
    x: 0,
    y: 480,
  });
});

test("reads PNG dimensions before decoding", async () => {
  const bytes = new Uint8Array(24);
  bytes.set([0x89, 0x50, 0x4e, 0x47], 0);
  const view = new DataView(bytes.buffer);
  view.setUint32(16, 800);
  view.setUint32(20, 480);

  const dimensions = await new InkyCard()._readImageDimensions(imageFile(bytes, "image/png"));

  assert.deepEqual(dimensions, { width: 800, height: 480 });
});

test("reads JPEG dimensions before decoding", async () => {
  const bytes = new Uint8Array(21);
  bytes.set([0xff, 0xd8, 0xff, 0xc0, 0x00, 0x11, 0x08, 0x01, 0xe0, 0x03, 0x20], 0);

  const dimensions = await new InkyCard()._readImageDimensions(imageFile(bytes, "image/jpeg"));

  assert.deepEqual(dimensions, { width: 800, height: 480 });
});

test("reads extended WebP dimensions before decoding", async () => {
  const bytes = new Uint8Array(30);
  bytes.set(Buffer.from("RIFF"), 0);
  bytes.set(Buffer.from("WEBP"), 8);
  bytes.set(Buffer.from("VP8X"), 12);
  bytes.set([0x1f, 0x03, 0x00], 24);
  bytes.set([0xdf, 0x01, 0x00], 27);

  const dimensions = await new InkyCard()._readImageDimensions(imageFile(bytes, "image/webp"));

  assert.deepEqual(dimensions, { width: 800, height: 480 });
});

test("rejects an image with an unreadable header", async () => {
  await assert.rejects(
    new InkyCard()._readImageDimensions(imageFile([1, 2, 3], "image/jpeg")),
    /dimensions could not be read/,
  );
});
