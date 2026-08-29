# Inky Home Assistant card

`inky-card.js` is a dependency-free Lovelace card for composing an 800×480
image and sending it to the Inky display. It supports:

- importing an image from the device or the latest Inky image entity;
- touch or mouse drawing in the panel's six colors;
- outlined captions sized for the e-paper panel;
- heart, star, smile, and sun stickers;
- undo, redo, clearing, and display status feedback.

## Install

Copy the card into Home Assistant's `www` directory:

```bash
mkdir -p /config/www/inky
cp inky-card.js /config/www/inky/inky-card.js
```

In Home Assistant, open **Settings → Dashboards**, select the three-dot menu,
open **Resources**, and add:

```text
URL: /local/inky/inky-card.js
Type: JavaScript module
```

Add a manual card to a dashboard:

```yaml
type: custom:inky-card
topic_prefix: inky
image_entity: image.inky_latest_photo
status_entity: sensor.inky_display_status
```

The defaults above match the Inky app defaults, so `type: custom:inky-card` is
enough unless the MQTT device ID or topic prefix was changed.

Optional settings:

```yaml
type: custom:inky-card
title: Family Inky
topic_prefix: inky
image_entity: image.inky_latest_photo
status_entity: sensor.inky_display_status
max_image_bytes: 2000000
max_upload_bytes: 15000000
max_upload_pixels: 25000000
jpeg_quality: 0.9
command_timeout_seconds: 180
```

The card calls Home Assistant's `mqtt.publish` action. The MQTT integration
must therefore be loaded and available to the dashboard user. The browser
resizes and crops imported images locally, then sends one JPEG only when
**Send to Inky** is selected.

Uploads accept JPEG, PNG, and WebP files. File headers are checked before the
browser decodes the image, with default limits of 15 MB and 25 megapixels to
protect mobile Home Assistant clients from oversized images.

Only add this card to dashboards for trusted Home Assistant users:
`mqtt.publish` is a broker-wide action, not an Inky-specific permission. Keep
the MQTT broker private to the local network and restrict the Inky broker
account to its `inky/#` topics with broker ACLs.

If Home Assistant caches an older card after an update, append a version to
the resource URL, such as `/local/inky/inky-card.js?v=2`, and reload the page.
If `/config/www` was newly created, restart Home Assistant before registering
the resource.
