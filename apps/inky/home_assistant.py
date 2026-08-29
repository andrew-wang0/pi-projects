from __future__ import annotations

import json
import logging
from pathlib import Path

import paho.mqtt.client as mqtt

from config import Config, MqttConfig
from hardware import ShowLight


LOGGER = logging.getLogger(__name__)


class HomeAssistant:
    def __init__(self, config: Config, light: ShowLight) -> None:
        self._config = config
        self._mqtt: MqttConfig = config.mqtt
        self._light = light
        self._connected = False
        self._client: mqtt.Client | None = None

        if not self._mqtt.host:
            return

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"{self._mqtt.device_id}-camera",
        )
        if self._mqtt.username:
            client.username_pw_set(self._mqtt.username, self._mqtt.password)
        client.will_set(self._topic("status"), "offline", qos=1, retain=True)
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message
        self._client = client

    def start(self) -> None:
        if self._client is None:
            LOGGER.info("Home Assistant MQTT is disabled; set MQTT_HOST to enable it")
            return
        self._client.connect_async(self._mqtt.host, self._mqtt.port)
        self._client.loop_start()

    def publish_photo(self, path: Path) -> None:
        if not self._connected or self._client is None:
            return
        if self._publish_photo_payload(path):
            self._mark_published(path)

    def _publish_photo_payload(self, path: Path) -> bool:
        assert self._client is not None
        message = self._client.publish(
            self._topic("photo"),
            path.read_bytes(),
            qos=1,
            retain=True,
        )
        return message.rc == mqtt.MQTT_ERR_SUCCESS

    def close(self) -> None:
        if self._client is None:
            return
        try:
            if self._connected:
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
        self._publish_discovery()
        client.publish(self._topic("status"), "online", qos=1, retain=True)
        self._publish_light_state()
        self._publish_latest_photo()
        LOGGER.info("Connected to Home Assistant MQTT at %s", self._mqtt.host)

    def _on_disconnect(
        self,
        _client,
        _userdata,
        _disconnect_flags,
        reason_code,
        _properties,
    ) -> None:
        self._connected = False
        if reason_code != 0:
            LOGGER.warning("MQTT disconnected: %s", reason_code)

    def _on_message(self, _client, _userdata, message) -> None:
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
            transition = float(command.get("transition", 0))
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
        self._publish_config("light", "show_light", light)
        self._publish_config("image", "latest_photo", image)
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

    def _publish_latest_photo(self) -> None:
        try:
            latest = max(
                self._config.image_dir.glob("*.png"),
                key=lambda path: path.stat().st_mtime_ns,
            )
        except (OSError, ValueError):
            return
        marker = self._config.image_dir / ".mqtt-last-photo"
        try:
            if marker.read_text().strip() == latest.name:
                return
        except OSError:
            pass
        if self._publish_photo_payload(latest):
            self._mark_published(latest)

    def _mark_published(self, path: Path) -> None:
        try:
            (self._config.image_dir / ".mqtt-last-photo").write_text(path.name)
        except OSError:
            LOGGER.warning("Could not update MQTT photo marker")

    def _topic(self, suffix: str) -> str:
        return f"{self._mqtt.topic_prefix}/{suffix}"
