const CARD_VERSION = "1.0.0";
const WIDTH = 800;
const HEIGHT = 480;
const HISTORY_LIMIT = 8;

class InkyCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = undefined;
    this._config = undefined;
    this._rendered = false;
    this._history = [];
    this._redo = [];
    this._drawing = false;
    this._drawEnabled = false;
    this._pending = undefined;
    this._requestId = undefined;
    this._requestTimeout = undefined;
  }

  static getStubConfig() {
    return {
      topic_prefix: "inky",
      image_entity: "image.inky_latest_photo",
      status_entity: "sensor.inky_display_status",
    };
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Inky card configuration is required");
    }
    this._config = {
      topic_prefix: "inky",
      image_entity: "image.inky_latest_photo",
      status_entity: "sensor.inky_display_status",
      max_image_bytes: 2000000,
      max_upload_bytes: 15000000,
      max_upload_pixels: 25000000,
      jpeg_quality: 0.9,
      command_timeout_seconds: 180,
      ...config,
    };
    if (typeof this._config.topic_prefix !== "string" || !this._config.topic_prefix.trim()) {
      throw new Error("topic_prefix must be a non-empty string");
    }
    this._config.topic_prefix = this._config.topic_prefix.replace(/\/+$/, "");
    this._config.jpeg_quality = Math.min(
      1,
      Math.max(0.5, Number(this._config.jpeg_quality) || 0.9),
    );
    this._config.max_image_bytes = Number(this._config.max_image_bytes) || 2000000;
    this._config.max_upload_bytes = Number(this._config.max_upload_bytes) || 15000000;
    this._config.max_upload_pixels = Number(this._config.max_upload_pixels) || 25000000;
    this._config.command_timeout_seconds = Number(this._config.command_timeout_seconds) || 180;
    if (this._rendered) {
      this._updateHaStatus();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._rendered && this._config) {
      this._render();
    }
    this._updateHaStatus();
  }

  getCardSize() {
    return 8;
  }

  disconnectedCallback() {
    this._clearRequestTimeout();
    this._requestId = undefined;
    const button = this.shadowRoot.getElementById("sendButton");
    if (button) button.disabled = false;
  }

  _render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        ha-card {
          overflow: hidden;
        }
        .content {
          display: grid;
          gap: 14px;
          padding: 16px;
        }
        .header {
          align-items: center;
          display: flex;
          gap: 10px;
          justify-content: space-between;
        }
        h2 {
          font-size: 20px;
          font-weight: 500;
          margin: 0;
        }
        .ha-status {
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .canvas-wrap {
          background:
            linear-gradient(45deg, #ddd 25%, transparent 25%),
            linear-gradient(-45deg, #ddd 25%, transparent 25%),
            linear-gradient(45deg, transparent 75%, #ddd 75%),
            linear-gradient(-45deg, transparent 75%, #ddd 75%);
          background-position:
            0 0,
            0 8px,
            8px -8px,
            -8px 0;
          background-size: 16px 16px;
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          line-height: 0;
          overflow: hidden;
          position: relative;
          touch-action: none;
        }
        canvas {
          aspect-ratio: 5 / 3;
          cursor: crosshair;
          height: auto;
          max-height: 70vh;
          object-fit: contain;
          width: 100%;
        }
        .toolbar {
          align-items: center;
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        .text-row {
          display: grid;
          gap: 8px;
          grid-template-columns: minmax(140px, 1fr) auto auto;
        }
        button,
        .file-button,
        select,
        input {
          background: var(--card-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 8px;
          box-sizing: border-box;
          color: var(--primary-text-color);
          font: inherit;
          min-height: 40px;
          padding: 8px 12px;
        }
        button {
          cursor: pointer;
        }
        .file-button {
          align-items: center;
          cursor: pointer;
          display: inline-flex;
          overflow: hidden;
          position: relative;
        }
        .file-button input {
          cursor: pointer;
          height: 100%;
          inset: 0;
          opacity: 0;
          position: absolute;
          width: 100%;
        }
        button:hover:not(:disabled) {
          background: var(--secondary-background-color);
        }
        button.active,
        button.primary {
          background: var(--primary-color);
          color: var(--text-primary-color, white);
        }
        button:disabled {
          cursor: wait;
          opacity: 0.55;
        }
        input[type="range"] {
          min-height: 30px;
          padding: 0;
          width: 90px;
        }
        .label {
          color: var(--secondary-text-color);
          font-size: 13px;
        }
        .editor-status {
          border-radius: 6px;
          color: var(--secondary-text-color);
          font-size: 13px;
          min-height: 20px;
          padding: 2px 0;
        }
        .editor-status.error {
          color: var(--error-color);
        }
        .spacer {
          flex: 1 1 auto;
        }
        @media (max-width: 600px) {
          .content {
            padding: 12px;
          }
          .text-row {
            grid-template-columns: 1fr auto;
          }
          .text-row input {
            grid-column: 1 / -1;
          }
          button,
          .file-button,
          select,
          input {
            min-height: 44px;
          }
        }
      </style>
      <ha-card>
        <div class="content">
          <div class="header">
            <h2>${this._escape(this._config.title || "Inky Editor")}</h2>
            <span class="ha-status" id="haStatus">Checking Inky…</span>
          </div>

          <div class="canvas-wrap">
            <canvas id="canvas" width="${WIDTH}" height="${HEIGHT}"></canvas>
          </div>

          <div class="toolbar">
            <label class="file-button">
              Upload photo
              <input id="photoInput" type="file" accept="image/jpeg,image/png,image/webp" />
            </label>
            <button id="latestButton" type="button">Use latest</button>
            <button id="drawButton" type="button">Draw</button>
            <span class="label">Color</span>
            <select id="color" aria-label="Markup color">
              <option value="#000000">Black</option>
              <option value="#ffffff">White</option>
              <option value="#f2c500">Yellow</option>
              <option value="#e1261c">Red</option>
              <option value="#1464f4">Blue</option>
              <option value="#159447">Green</option>
            </select>
            <span class="label">Width</span>
            <input id="width" type="range" min="3" max="40" value="12" />
          </div>

          <div class="text-row">
            <input
              id="text"
              type="text"
              maxlength="120"
              placeholder="Type a caption, then place it"
            />
            <select id="fontSize" aria-label="Caption size">
              <option value="32">Small</option>
              <option value="48" selected>Medium</option>
              <option value="68">Large</option>
            </select>
            <button id="textButton" type="button">Place text</button>
          </div>

          <div class="toolbar">
            <span class="label">Stickers</span>
            <button class="sticker" data-sticker="heart" type="button">♥ Heart</button>
            <button class="sticker" data-sticker="star" type="button">★ Star</button>
            <button class="sticker" data-sticker="smile" type="button">☺ Smile</button>
            <button class="sticker" data-sticker="sun" type="button">☀ Sun</button>
          </div>

          <div class="toolbar">
            <button id="undoButton" type="button">Undo</button>
            <button id="redoButton" type="button">Redo</button>
            <button id="clearButton" type="button">Clear</button>
            <span class="spacer"></span>
            <button id="sendButton" class="primary" type="button">Send to Inky</button>
          </div>
          <div class="editor-status" id="editorStatus">
            Upload a photo or start drawing.
          </div>
        </div>
      </ha-card>
    `;

    this._canvas = this.shadowRoot.getElementById("canvas");
    this._context = this._canvas.getContext("2d", { alpha: false });
    this._fillWhite();
    this._bindEvents();
    this._updateHistoryButtons();
    this._rendered = true;
  }

  _bindEvents() {
    const photoInput = this.shadowRoot.getElementById("photoInput");
    photoInput.addEventListener("change", async () => {
      const [file] = photoInput.files || [];
      if (file) {
        await this._loadFile(file);
      }
      photoInput.value = "";
    });
    this.shadowRoot
      .getElementById("latestButton")
      .addEventListener("click", () => this._loadLatest());
    this.shadowRoot
      .getElementById("drawButton")
      .addEventListener("click", () => this._toggleDraw());
    this.shadowRoot
      .getElementById("textButton")
      .addEventListener("click", () => this._selectText());
    this.shadowRoot.querySelectorAll(".sticker").forEach((button) => {
      button.addEventListener("click", () => this._selectSticker(button.dataset.sticker));
    });
    this.shadowRoot
      .getElementById("undoButton")
      .addEventListener("click", () => this._undoChange());
    this.shadowRoot
      .getElementById("redoButton")
      .addEventListener("click", () => this._redoChange());
    this.shadowRoot.getElementById("clearButton").addEventListener("click", () => this._clear());
    this.shadowRoot.getElementById("sendButton").addEventListener("click", () => this._send());

    this._canvas.addEventListener("pointerdown", (event) => this._pointerDown(event));
    this._canvas.addEventListener("pointermove", (event) => this._pointerMove(event));
    this._canvas.addEventListener("pointerup", (event) => this._pointerUp(event));
    this._canvas.addEventListener("pointercancel", (event) => this._pointerUp(event));
  }

  async _loadFile(file) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      this._setEditorStatus("Choose a JPEG, PNG, or WebP image.", true);
      return;
    }
    if (file.size > this._config.max_upload_bytes) {
      this._setEditorStatus(
        `Photo is ${file.size} bytes; upload limit is ${this._config.max_upload_bytes}.`,
        true,
      );
      return;
    }
    try {
      const { width, height } = await this._readImageDimensions(file);
      if (width * height > this._config.max_upload_pixels) {
        throw new Error(
          `${width}×${height} exceeds the ${this._config.max_upload_pixels} pixel limit`,
        );
      }
    } catch (error) {
      this._setEditorStatus(`Could not use photo: ${error.message}`, true);
      return;
    }
    const url = URL.createObjectURL(file);
    try {
      await this._loadImage(url);
      this._setEditorStatus("Photo loaded. Add markup or send it.");
    } catch (error) {
      this._setEditorStatus(`Could not load photo: ${error.message}`, true);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  async _loadLatest() {
    const entity = this._hass?.states[this._config.image_entity];
    const source = entity?.attributes?.entity_picture;
    if (!source) {
      this._setEditorStatus(`No image is available from ${this._config.image_entity}.`, true);
      return;
    }
    try {
      await this._loadImage(source);
      this._setEditorStatus("Latest Inky photo loaded.");
    } catch (error) {
      this._setEditorStatus(`Could not load the latest photo: ${error.message}`, true);
    }
  }

  _loadImage(source) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        if (image.width * image.height > 50000000) {
          reject(new Error("image dimensions exceed 50 megapixels"));
          return;
        }
        this._saveForUndo();
        const scale = Math.max(WIDTH / image.width, HEIGHT / image.height);
        const width = image.width * scale;
        const height = image.height * scale;
        this._context.fillStyle = "#ffffff";
        this._context.fillRect(0, 0, WIDTH, HEIGHT);
        this._context.drawImage(image, (WIDTH - width) / 2, (HEIGHT - height) / 2, width, height);
        resolve();
      };
      image.onerror = () => reject(new Error("the browser rejected the image"));
      image.src = source;
    });
  }

  async _readImageDimensions(file) {
    const buffer = await file.slice(0, 1048576).arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);

    if (
      file.type === "image/png" &&
      bytes.length >= 24 &&
      bytes[0] === 0x89 &&
      bytes[1] === 0x50 &&
      bytes[2] === 0x4e &&
      bytes[3] === 0x47
    ) {
      return { width: view.getUint32(16), height: view.getUint32(20) };
    }

    if (file.type === "image/jpeg" && bytes.length >= 4 && bytes[0] === 0xff && bytes[1] === 0xd8) {
      const startOfFrame = new Set([
        0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf,
      ]);
      let offset = 2;
      while (offset + 8 < bytes.length) {
        while (offset < bytes.length && bytes[offset] === 0xff) offset += 1;
        const marker = bytes[offset];
        offset += 1;
        if (marker === 0xd9 || marker === 0xda || offset + 1 >= bytes.length) break;
        if (marker === 0x01 || (marker >= 0xd0 && marker <= 0xd8)) continue;
        const length = view.getUint16(offset);
        if (length < 2 || offset + length > bytes.length) break;
        if (startOfFrame.has(marker) && length >= 7) {
          return {
            width: view.getUint16(offset + 5),
            height: view.getUint16(offset + 3),
          };
        }
        offset += length;
      }
    }

    if (
      file.type === "image/webp" &&
      bytes.length >= 30 &&
      this._ascii(bytes, 0, 4) === "RIFF" &&
      this._ascii(bytes, 8, 4) === "WEBP"
    ) {
      const chunk = this._ascii(bytes, 12, 4);
      if (chunk === "VP8X") {
        return {
          width: 1 + bytes[24] + (bytes[25] << 8) + (bytes[26] << 16),
          height: 1 + bytes[27] + (bytes[28] << 8) + (bytes[29] << 16),
        };
      }
      if (chunk === "VP8 " && bytes.length >= 30) {
        return {
          width: view.getUint16(26, true) & 0x3fff,
          height: view.getUint16(28, true) & 0x3fff,
        };
      }
      if (chunk === "VP8L" && bytes[20] === 0x2f) {
        const bits = view.getUint32(21, true);
        return {
          width: 1 + (bits & 0x3fff),
          height: 1 + ((bits >>> 14) & 0x3fff),
        };
      }
    }

    throw new Error("image dimensions could not be read");
  }

  _ascii(bytes, offset, length) {
    return String.fromCharCode(...bytes.subarray(offset, offset + length));
  }

  _toggleDraw() {
    this._pending = undefined;
    this._drawEnabled = !this._drawEnabled;
    this.shadowRoot.getElementById("drawButton").classList.toggle("active", this._drawEnabled);
    this._setEditorStatus(
      this._drawEnabled ? "Draw directly on the photo." : "Drawing tool switched off.",
    );
  }

  _selectText() {
    const text = this.shadowRoot.getElementById("text").value.trim();
    if (!text) {
      this._setEditorStatus("Enter some text first.", true);
      return;
    }
    this._drawEnabled = false;
    this.shadowRoot.getElementById("drawButton").classList.remove("active");
    this._pending = {
      type: "text",
      text,
      size: Number(this.shadowRoot.getElementById("fontSize").value),
    };
    this._setEditorStatus("Tap the photo where the caption should appear.");
  }

  _selectSticker(sticker) {
    this._drawEnabled = false;
    this.shadowRoot.getElementById("drawButton").classList.remove("active");
    this._pending = { type: "sticker", sticker };
    this._setEditorStatus("Tap the photo to place the sticker.");
  }

  _pointerDown(event) {
    const point = this._point(event);
    if (this._pending) {
      this._saveForUndo();
      if (this._pending.type === "text") {
        this._drawText(point.x, point.y, this._pending);
      } else {
        this._drawSticker(point.x, point.y, this._pending.sticker);
      }
      this._pending = undefined;
      this._setEditorStatus("Item placed.");
      return;
    }
    if (!this._drawEnabled) {
      return;
    }
    this._saveForUndo();
    this._drawing = true;
    this._canvas.setPointerCapture(event.pointerId);
    this._context.beginPath();
    this._context.moveTo(point.x, point.y);
    this._context.strokeStyle = this._selectedColor();
    this._context.lineWidth = Number(this.shadowRoot.getElementById("width").value);
    this._context.lineCap = "round";
    this._context.lineJoin = "round";
    this._context.lineTo(point.x + 0.01, point.y);
    this._context.stroke();
  }

  _pointerMove(event) {
    if (!this._drawing) {
      return;
    }
    const point = this._point(event);
    this._context.lineTo(point.x, point.y);
    this._context.stroke();
  }

  _pointerUp(event) {
    if (!this._drawing) {
      return;
    }
    this._drawing = false;
    this._context.closePath();
    if (this._canvas.hasPointerCapture(event.pointerId)) {
      this._canvas.releasePointerCapture(event.pointerId);
    }
  }

  _drawText(x, y, item) {
    const maxWidth = Math.min(700, Math.max(180, 2 * Math.min(x, WIDTH - x) - 20));
    const size = item.size;
    const lineHeight = Math.round(size * 1.18);
    this._context.font = `700 ${size}px sans-serif`;
    this._context.textAlign = "center";
    this._context.textBaseline = "middle";
    this._context.lineJoin = "round";
    const lines = this._wrapText(item.text, maxWidth);
    const startY = y - ((lines.length - 1) * lineHeight) / 2;
    lines.forEach((line, index) => {
      const lineY = startY + index * lineHeight;
      this._context.strokeStyle = this._selectedColor() === "#000000" ? "#ffffff" : "#000000";
      this._context.lineWidth = Math.max(4, Math.round(size / 10));
      this._context.strokeText(line, x, lineY, maxWidth);
      this._context.fillStyle = this._selectedColor();
      this._context.fillText(line, x, lineY, maxWidth);
    });
  }

  _wrapText(text, maxWidth) {
    const lines = [];
    text.split("\n").forEach((paragraph) => {
      const words = paragraph.split(/\s+/);
      let line = "";
      words.forEach((word) => {
        const candidate = line ? `${line} ${word}` : word;
        if (line && this._context.measureText(candidate).width > maxWidth) {
          lines.push(line);
          line = word;
        } else {
          line = candidate;
        }
      });
      lines.push(line);
    });
    return lines.slice(0, 4);
  }

  _drawSticker(x, y, sticker) {
    const context = this._context;
    const color = this._selectedColor();
    context.save();
    context.translate(x, y);
    context.fillStyle = color;
    context.strokeStyle = "#000000";
    context.lineWidth = 5;
    context.lineJoin = "round";

    if (sticker === "heart") {
      context.beginPath();
      context.moveTo(0, 38);
      context.bezierCurveTo(-65, 0, -42, -52, 0, -25);
      context.bezierCurveTo(42, -52, 65, 0, 0, 38);
      context.closePath();
      context.fill();
      context.stroke();
    } else if (sticker === "star") {
      context.beginPath();
      for (let index = 0; index < 10; index += 1) {
        const radius = index % 2 === 0 ? 52 : 23;
        const angle = -Math.PI / 2 + (index * Math.PI) / 5;
        const px = Math.cos(angle) * radius;
        const py = Math.sin(angle) * radius;
        if (index === 0) context.moveTo(px, py);
        else context.lineTo(px, py);
      }
      context.closePath();
      context.fill();
      context.stroke();
    } else if (sticker === "smile") {
      context.beginPath();
      context.arc(0, 0, 48, 0, Math.PI * 2);
      context.fill();
      context.stroke();
      context.fillStyle = "#000000";
      context.beginPath();
      context.arc(-17, -12, 5, 0, Math.PI * 2);
      context.arc(17, -12, 5, 0, Math.PI * 2);
      context.fill();
      context.beginPath();
      context.arc(0, 4, 25, 0.15 * Math.PI, 0.85 * Math.PI);
      context.stroke();
    } else if (sticker === "sun") {
      for (let index = 0; index < 12; index += 1) {
        const angle = (index * Math.PI) / 6;
        context.beginPath();
        context.moveTo(Math.cos(angle) * 48, Math.sin(angle) * 48);
        context.lineTo(Math.cos(angle) * 65, Math.sin(angle) * 65);
        context.stroke();
      }
      context.beginPath();
      context.arc(0, 0, 42, 0, Math.PI * 2);
      context.fill();
      context.stroke();
    }
    context.restore();
  }

  _saveForUndo() {
    this._history.push(this._context.getImageData(0, 0, WIDTH, HEIGHT));
    if (this._history.length > HISTORY_LIMIT) {
      this._history.shift();
    }
    this._redo = [];
    this._updateHistoryButtons();
  }

  _undoChange() {
    const snapshot = this._history.pop();
    if (!snapshot) return;
    this._redo.push(this._context.getImageData(0, 0, WIDTH, HEIGHT));
    this._context.putImageData(snapshot, 0, 0);
    this._updateHistoryButtons();
  }

  _redoChange() {
    const snapshot = this._redo.pop();
    if (!snapshot) return;
    this._history.push(this._context.getImageData(0, 0, WIDTH, HEIGHT));
    this._context.putImageData(snapshot, 0, 0);
    this._updateHistoryButtons();
  }

  _clear() {
    this._saveForUndo();
    this._fillWhite();
    this._setEditorStatus("Canvas cleared.");
  }

  _fillWhite() {
    this._context.fillStyle = "#ffffff";
    this._context.fillRect(0, 0, WIDTH, HEIGHT);
  }

  async _send() {
    if (!this._hass) {
      this._setEditorStatus("Home Assistant is not connected.", true);
      return;
    }
    const button = this.shadowRoot.getElementById("sendButton");
    button.disabled = true;
    this._setEditorStatus("Preparing image…");
    try {
      const blob = await new Promise((resolve, reject) => {
        this._canvas.toBlob(
          (result) => (result ? resolve(result) : reject(new Error("image encoding failed"))),
          "image/jpeg",
          this._config.jpeg_quality,
        );
      });
      if (blob.size > this._config.max_image_bytes) {
        throw new Error(
          `encoded image is ${blob.size} bytes; limit is ${this._config.max_image_bytes}`,
        );
      }
      const data = await this._blobToBase64(blob);
      const requestId =
        globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const payload = JSON.stringify({
        version: 1,
        request_id: requestId,
        content_type: "image/jpeg",
        data,
      });
      this._requestId = requestId;
      this._startRequestTimeout(requestId);
      await this._hass.callService("mqtt", "publish", {
        topic: `${this._config.topic_prefix}/display/set`,
        payload,
        qos: 1,
        retain: false,
      });
      if (this._requestId === requestId) {
        this._setEditorStatus("Sent to Inky. Waiting for the display…");
      }
    } catch (error) {
      this._clearRequestTimeout();
      this._requestId = undefined;
      this._setEditorStatus(`Could not send image: ${error.message}`, true);
    } finally {
      button.disabled = Boolean(this._requestId);
    }
  }

  _blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result).split(",", 2)[1]);
      reader.onerror = () => reject(new Error("could not read encoded image"));
      reader.readAsDataURL(blob);
    });
  }

  _updateHaStatus() {
    if (!this._rendered || !this._hass) return;
    const element = this.shadowRoot.getElementById("haStatus");
    const entity = this._hass.states[this._config.status_entity];
    if (!entity) {
      element.textContent = "Status entity not found";
      return;
    }
    if (entity.state === "unavailable") {
      element.textContent = "Inky offline";
      if (this._requestId) {
        this._setEditorStatus("Inky went offline before accepting the image.", true);
        this._requestId = undefined;
        this._clearRequestTimeout();
        this.shadowRoot.getElementById("sendButton").disabled = false;
      }
      return;
    }
    const labels = {
      idle: "Inky ready",
      queued: "Image queued",
      updating: "Display updating…",
      error: "Display error",
    };
    element.textContent = labels[entity.state] || `Inky: ${entity.state}`;
    const isCurrentRequest = this._requestId && entity.attributes.request_id === this._requestId;
    if (isCurrentRequest && entity.state === "idle") {
      this._setEditorStatus("Image is now displayed.");
      this._requestId = undefined;
      this._clearRequestTimeout();
      this.shadowRoot.getElementById("sendButton").disabled = false;
    } else if (isCurrentRequest && entity.state === "error") {
      this._setEditorStatus(entity.attributes.message || "Inky could not display the image.", true);
      this._requestId = undefined;
      this._clearRequestTimeout();
      this.shadowRoot.getElementById("sendButton").disabled = false;
    }
  }

  _startRequestTimeout(requestId) {
    this._clearRequestTimeout();
    this._requestTimeout = globalThis.setTimeout(() => {
      if (this._requestId !== requestId) return;
      this._requestId = undefined;
      this._requestTimeout = undefined;
      this.shadowRoot.getElementById("sendButton").disabled = false;
      this._setEditorStatus(
        "Timed out waiting for Inky. Check the device and MQTT connection.",
        true,
      );
    }, this._config.command_timeout_seconds * 1000);
  }

  _clearRequestTimeout() {
    if (this._requestTimeout !== undefined) {
      globalThis.clearTimeout(this._requestTimeout);
      this._requestTimeout = undefined;
    }
  }

  _updateHistoryButtons() {
    if (!this.shadowRoot.getElementById("undoButton")) return;
    this.shadowRoot.getElementById("undoButton").disabled = this._history.length === 0;
    this.shadowRoot.getElementById("redoButton").disabled = this._redo.length === 0;
  }

  _point(event) {
    const bounds = this._canvas.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) * WIDTH) / bounds.width,
      y: ((event.clientY - bounds.top) * HEIGHT) / bounds.height,
    };
  }

  _selectedColor() {
    return this.shadowRoot.getElementById("color").value;
  }

  _setEditorStatus(message, error = false) {
    if (!this._rendered && !this.shadowRoot.getElementById("editorStatus")) {
      return;
    }
    const element = this.shadowRoot.getElementById("editorStatus");
    element.textContent = message;
    element.classList.toggle("error", error);
  }

  _escape(value) {
    const span = document.createElement("span");
    span.textContent = value;
    return span.innerHTML;
  }
}

if (!customElements.get("inky-card")) {
  customElements.define("inky-card", InkyCard);
  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "inky-card",
    name: "Inky Editor",
    description: "Compose and send photos to an Inky e-paper display.",
    preview: true,
  });
  console.info(`%c INKY-CARD %c ${CARD_VERSION} `, "color: white; background: #159447", "");
}
