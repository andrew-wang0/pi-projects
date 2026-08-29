from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
import threading
import time

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

from config import Config, MqttConfig
from hardware import ShowLight


LOGGER = logging.getLogger(__name__)


class HomeAssistant:
    def __init__(self, config: Config, light: ShowLight) -> None:
        self._config = config
        self._mqtt: MqttConfig = config.mqtt
        self._light = light
        self._connected = False
        self._client = None
        self._photo_event = threading.Event()
        self._ack_event = threading.Event()
        self._ack_lock = threading.Lock()
        self._registry_lock = threading.Lock()
        self._expected_ack: str | None = None
        self._received_ack: str | None = None
        self._shutdown = threading.Event()
        self._photo_thread: threading.Thread | None = None
        self._last_connect_warning = 0.0

        if not self._mqtt.host:
            return
        if mqtt is None:
            LOGGER.error("paho-mqtt is unavailable; continuing without Home Assistant")
            return

        try:
            client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2,
                client_id=f"{self._mqtt.device_id}-camera",
            )
            if self._mqtt.username:
                client.username_pw_set(self._mqtt.username, self._mqtt.password)
            client.will_set(self._topic("status"), "offline", qos=1, retain=True)
            client.reconnect_delay_set(min_delay=1, max_delay=30)
            client.on_connect = self._on_connect
            client.on_connect_fail = self._on_connect_fail
            client.on_disconnect = self._on_disconnect
            client.on_message = self._on_message
            self._client = client
        except Exception:
            LOGGER.exception("MQTT setup failed; continuing without Home Assistant")

    def start(self) -> None:
        if self._client is None:
            if not self._mqtt.host:
                LOGGER.info(
                    "Home Assistant MQTT is disabled; set MQTT_HOST to enable it"
                )
            return
        try:
            self._client.connect_async(self._mqtt.host, self._mqtt.port)
            self._client.loop_start()
            self._photo_thread = threading.Thread(
                target=self._photo_worker,
                daemon=True,
            )
            self._photo_thread.start()
        except Exception:
            LOGGER.exception("MQTT startup failed; continuing without Home Assistant")
            self._client.loop_stop()
            self._client = None

    def publish_photo(self, path: Path) -> None:
        self._register_photo(path)
        self._publish_latest_photo(path)
        self._photo_event.set()

    def _publish_latest_photo(self, path: Path) -> None:
        if not self._connected or self._client is None or mqtt is None:
            return
        try:
            message = self._client.publish(
                self._topic("photo"),
                path.read_bytes(),
                qos=1,
                retain=True,
            )
            if message.rc != mqtt.MQTT_ERR_SUCCESS:
                LOGGER.warning("Could not update the latest Home Assistant photo")
        except (OSError, RuntimeError, ValueError):
            LOGGER.warning("Could not update the latest Home Assistant photo")

    def _publish_photo_payload(self, path: Path, transfer_id: str) -> bool:
        if self._client is None or mqtt is None:
            return False
        try:
            payload = path.read_bytes()
            message = self._client.publish(
                self._topic("photo/archive"),
                payload,
                qos=1,
                retain=True,
            )
            if message.rc != mqtt.MQTT_ERR_SUCCESS:
                return False
            message.wait_for_publish(timeout=10)
            if not message.is_published():
                return False
            transfer = self._client.publish(
                self._topic("photo/transfer"),
                transfer_id,
                qos=1,
                retain=True,
            )
            if transfer.rc != mqtt.MQTT_ERR_SUCCESS:
                return False
            transfer.wait_for_publish(timeout=10)
            return transfer.is_published()
        except (OSError, RuntimeError, ValueError):
            LOGGER.warning("Could not publish %s; it remains queued locally", path)
            return False

    def close(self) -> None:
        if self._client is None:
            return
        self._connected = False
        self._shutdown.set()
        self._photo_event.set()
        self._ack_event.set()
        if self._photo_thread is not None:
            self._photo_thread.join()
        try:
            message = self._client.publish(
                self._topic("status"),
                "offline",
                qos=1,
                retain=True,
            )
            message.wait_for_publish(timeout=2)
        except (RuntimeError, ValueError):
            LOGGER.warning("Could not publish MQTT offline state")
        finally:
            try:
                self._client.disconnect()
            finally:
                self._client.loop_stop()

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code != 0:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return

        self._connected = True
        client.subscribe(self._topic("light/set"), qos=1)
        client.subscribe(self._topic("photo/ack"), qos=1)
        self._publish_discovery()
        client.publish(self._topic("status"), "online", qos=1, retain=True)
        self._publish_light_state()
        self._publish_latest_stored_photo()
        self._photo_event.set()
        LOGGER.info("Connected to Home Assistant MQTT at %s", self._mqtt.host)

    def _on_connect_fail(self, _client, _userdata) -> None:
        now = time.monotonic()
        if now - self._last_connect_warning >= 60:
            LOGGER.warning("Home Assistant MQTT is unavailable; continuing locally")
            self._last_connect_warning = now

    def _on_disconnect(
        self,
        _client,
        _userdata,
        _disconnect_flags,
        reason_code,
        _properties,
    ) -> None:
        self._connected = False
        self._ack_event.set()
        if reason_code != 0:
            LOGGER.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, _client, _userdata, message) -> None:
        if message.topic == self._topic("photo/ack"):
            received = message.payload.decode(errors="replace")
            with self._ack_lock:
                if received == self._expected_ack:
                    self._received_ack = received
                    self._ack_event.set()
            return
        if message.topic != self._topic("light/set"):
            return

        try:
            command = json.loads(message.payload)
            if not isinstance(command, dict):
                raise ValueError("command must be a JSON object")
            state = command.get("state")
            on = None if state is None else str(state).upper() == "ON"
            if state is not None and str(state).upper() not in {"ON", "OFF"}:
                raise ValueError("state must be ON or OFF")

            value = command.get("brightness")
            brightness = None if value is None else float(value) / 255
            transition = float(
                command.get(
                    "transition",
                    self._config.light_transition_seconds,
                )
            )
            self._light.set(
                on=on,
                brightness=brightness,
                transition=transition,
            )
            self._publish_light_state()
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            LOGGER.warning("Ignored invalid MQTT light command: %s", error)

    def _publish_discovery(self) -> None:
        assert self._client is not None
        device = {
            "identifiers": [self._mqtt.device_id],
            "name": "Inky Camera",
            "manufacturer": "Custom",
            "model": "Inky Impression 7.3 Camera",
        }
        availability = {
            "availability_topic": self._topic("status"),
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        light = {
            "name": "Light",
            "default_entity_id": f"light.{self._mqtt.device_id}_show_light",
            "unique_id": f"{self._mqtt.device_id}_show_light",
            "schema": "json",
            "command_topic": self._topic("light/set"),
            "state_topic": self._topic("light/state"),
            "brightness": True,
            "supported_color_modes": ["brightness"],
            "transition": True,
            "device": device,
            **availability,
        }
        image = {
            "name": "Latest Photo",
            "default_entity_id": f"image.{self._mqtt.device_id}_latest_photo",
            "unique_id": f"{self._mqtt.device_id}_latest_photo",
            "image_topic": self._topic("photo"),
            "content_type": "image/png",
            "device": device,
            **availability,
        }
        archive_image = {
            "name": "Archive Queue",
            "default_entity_id": f"image.{self._mqtt.device_id}_archive_queue",
            "unique_id": f"{self._mqtt.device_id}_archive_queue",
            "image_topic": self._topic("photo/archive"),
            "content_type": "image/png",
            "entity_category": "diagnostic",
            "device": device,
            **availability,
        }
        self._publish_config("light", "show_light", light)
        self._publish_config("image", "latest_photo", image)
        self._publish_config("image", "archive_queue", archive_image)
        legacy_sensor = (
            f"{self._mqtt.discovery_prefix}/sensor/"
            f"{self._mqtt.device_id}/last_photo/config"
        )
        self._client.publish(legacy_sensor, None, qos=1, retain=True)
        self._client.publish(self._topic("photo/name"), None, qos=1, retain=True)

    def _publish_config(self, component: str, entity: str, payload: dict) -> None:
        assert self._client is not None
        topic = (
            f"{self._mqtt.discovery_prefix}/{component}/"
            f"{self._mqtt.device_id}/{entity}/config"
        )
        self._client.publish(topic, json.dumps(payload), qos=1, retain=True)

    def _publish_light_state(self) -> None:
        if self._client is None:
            return
        on, brightness = self._light.state()
        payload = {
            "state": "ON" if on else "OFF",
            "brightness": round(brightness * 255),
            "color_mode": "brightness",
        }
        self._client.publish(
            self._topic("light/state"),
            json.dumps(payload),
            qos=1,
            retain=True,
        )

    def _photo_worker(self) -> None:
        while not self._shutdown.is_set():
            self._photo_event.wait()
            self._photo_event.clear()
            if self._shutdown.is_set():
                return
            if not self._sync_photos() and self._connected:
                if self._shutdown.wait(30):
                    return
                self._photo_event.set()

    def _publish_latest_stored_photo(self) -> None:
        try:
            latest = max(
                self._config.image_dir.glob("*.png"),
                key=lambda path: path.stat().st_mtime_ns,
            )
        except (OSError, ValueError):
            return
        self._publish_latest_photo(latest)

    def _sync_photos(self) -> bool:
        for path in self._pending_photos():
            if not self._connected or self._shutdown.is_set():
                return False
            try:
                digest = hashlib.sha256(path.name.encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
                transfer_id = digest.hexdigest()
            except OSError:
                continue

            with self._ack_lock:
                self._expected_ack = transfer_id
                self._received_ack = None
                self._ack_event.clear()
            if not self._publish_photo_payload(path, transfer_id):
                return False

            self._ack_event.wait(timeout=60)
            with self._ack_lock:
                acknowledged = self._received_ack == transfer_id
                self._expected_ack = None
            if self._shutdown.is_set() or not self._connected:
                return False
            if not acknowledged:
                LOGGER.warning("Home Assistant did not archive %s; retrying later", path)
                return False

            if not self._mark_synced(path):
                return False
            if self._client is not None:
                self._client.publish(
                    self._topic("photo/transfer"),
                    None,
                    qos=1,
                    retain=True,
                )
            LOGGER.info("Published archived photo %s", path)
        return True

    def _pending_photos(self) -> list[Path]:
        try:
            photos = sorted(
                self._config.image_dir.glob("*.png"),
                key=lambda path: (path.stat().st_mtime_ns, path.name),
            )
        except OSError:
            return []

        by_name = {path.name: path for path in photos}
        queue = self._config.image_dir / ".mqtt-photo-queue"
        with self._registry_lock:
            try:
                queued_names = queue.read_text().splitlines()
            except FileNotFoundError:
                queued_names = []
            except OSError:
                LOGGER.warning("Could not read MQTT photo queue")
                return []

            ordered_names = list(
                dict.fromkeys(name for name in queued_names if name in by_name)
            )
            missing = [path.name for path in photos if path.name not in ordered_names]
            if missing and not self._append_queue(missing):
                return []
            ordered_names.extend(missing)
            synced = self._synced_names()

        return [by_name[name] for name in ordered_names if name not in synced]

    def _register_photo(self, path: Path) -> None:
        with self._registry_lock:
            self._append_queue([path.name])

    def _append_queue(self, names: list[str]) -> bool:
        queue = self._config.image_dir / ".mqtt-photo-queue"
        try:
            with queue.open("a") as file:
                for name in names:
                    file.write(f"{name}\n")
                file.flush()
                os.fsync(file.fileno())
            self._fsync_image_directory()
            return True
        except OSError:
            LOGGER.warning("Could not update MQTT photo queue")
            return False

    def _synced_names(self) -> set[str]:
        registry = self._config.image_dir / ".mqtt-synced.json"
        try:
            names = json.loads(registry.read_text())
            if not isinstance(names, list) or not all(
                isinstance(name, str) for name in names
            ):
                raise ValueError("invalid registry")
            return set(names)
        except FileNotFoundError:
            return set()
        except (OSError, ValueError, json.JSONDecodeError):
            LOGGER.warning("Could not read MQTT photo registry; replaying all photos")
            return set()

    def _mark_synced(self, path: Path) -> bool:
        registry = self._config.image_dir / ".mqtt-synced.json"
        temporary = self._config.image_dir / ".mqtt-synced.tmp"
        with self._registry_lock:
            try:
                names = self._synced_names()
                names.add(path.name)
                with temporary.open("w") as file:
                    json.dump(sorted(names), file)
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(temporary, registry)
                self._fsync_image_directory()
                return True
            except OSError:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                LOGGER.warning("Could not update MQTT photo registry")
                return False

    def _fsync_image_directory(self) -> None:
        directory = os.open(self._config.image_dir, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def _topic(self, suffix: str) -> str:
        return f"{self._mqtt.topic_prefix}/{suffix}"
