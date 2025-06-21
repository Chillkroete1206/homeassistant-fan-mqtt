import asyncio
import logging
import json

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_TOPIC_IN,
    CONF_TOPIC_OUT,
    CONF_PAYLOAD_ONOFF,
    CONF_PAYLOAD_UP,
    CONF_PAYLOAD_DOWN,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
MAX_SPEED = 6


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up the dummy fan from a config entry."""
    data = config_entry.options or config_entry.data

    fan = DummyFan(
        hass=hass,
        unique_id=f"dummy_fan_{config_entry.entry_id}",
        topic_in=data[CONF_TOPIC_IN],
        topic_out=data[CONF_TOPIC_OUT],
        payload_onoff=data[CONF_PAYLOAD_ONOFF],
        payload_up=data[CONF_PAYLOAD_UP],
        payload_down=data[CONF_PAYLOAD_DOWN],
    )

    async_add_entities([fan])

    async def message_received(msg):
        _LOGGER.debug("Raw MQTT message received: %s", msg.payload)
        try:
            payload = json.loads(msg.payload)
            rf_data = payload.get("RfReceived", {}).get("Data")
            _LOGGER.debug("Extracted RF Data: %s", rf_data)

            if rf_data == fan.payload_down:
                _LOGGER.debug("Matched FAN_DOWN command")
                fan.decrease_speed(no_mqtt=True)
            elif rf_data == fan.payload_up:
                _LOGGER.debug("Matched FAN_UP command")
                fan.increase_speed(no_mqtt=True)
            elif rf_data == fan.payload_onoff:
                _LOGGER.debug("Matched TOGGLE command")
                if fan.is_on:
                    await fan.async_turn_off()
                else:
                    await fan.async_turn_on()
            else:
                _LOGGER.debug("No matching command for RF code: %s", rf_data)
        except Exception as e:
            _LOGGER.warning("Failed to parse MQTT message: %s", e)

    await mqtt.async_subscribe(hass, fan.topic_in, message_received, 1)


class DummyFan(FanEntity):
    """Dummy fan entity that simulates speed control via MQTT."""

    def __init__(
        self,
        hass,
        unique_id,
        topic_in,
        topic_out,
        payload_onoff,
        payload_up,
        payload_down,
    ):
        self.hass = hass
        self._attr_name = "Dummy Fan"
        self._attr_unique_id = unique_id
        self._attr_supported_features = (
            FanEntityFeature.SET_SPEED
            | FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
        )
        self._attr_is_on = False
        self._attr_percentage = 0
        self._attr_percentage_step = round(100 / MAX_SPEED)

        self.topic_in = topic_in
        self.topic_out = topic_out
        self.payload_onoff = payload_onoff
        self.payload_up = payload_up
        self.payload_down = payload_down

        self._speed = 0

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        """Turn the fan on, optionally with a given percentage."""
        await self._send_command(self.payload_onoff)
        self._attr_is_on = True

        if percentage is not None:
            self._speed = self._percentage_to_speed(percentage)
        elif self._speed == 0:
            self._speed = 1

        self._attr_percentage = self._speed_to_percentage(self._speed)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        """Turn the fan off."""
        await self._send_command(self.payload_onoff)
        self._attr_is_on = False
        self._speed = 0
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage):
        """Set the fan speed by percentage."""
        target_speed = self._percentage_to_speed(percentage)
        if target_speed == self._speed and self._attr_is_on:
            return

        if not self._attr_is_on:
            _LOGGER.debug("Fan is off – turning on before setting speed")
            await self._send_command(self.payload_onoff)
            self._attr_is_on = True
            self._speed = 0
            await asyncio.sleep(1)

        diff = target_speed - self._speed
        if diff > 0:
            for _ in range(diff):
                await self._send_command(self.payload_up)
                await asyncio.sleep(1)

        self._speed = target_speed
        self._attr_percentage = self._speed_to_percentage(self._speed)
        self.async_write_ha_state()

    def _percentage_to_speed(self, percentage):
        return max(1, min(MAX_SPEED, round((percentage / 100) * MAX_SPEED)))

    def _speed_to_percentage(self, speed):
        return int((speed / MAX_SPEED) * 100)

    def decrease_speed(self, no_mqtt=False):
        if not self._attr_is_on:
            _LOGGER.debug("Ignoring decrease_speed – fan is off")
            return

        if self._speed > 1:
            self._speed -= 1
            _LOGGER.debug("Decreased speed to %s", self._speed)
            if not no_mqtt:
                self.hass.async_create_task(self._send_command(self.payload_down))
        elif self._speed == 1:
            _LOGGER.debug("At minimum speed – ignoring further decrease")
            return
        else:
            _LOGGER.debug("Speed already 0 – turning off")
            self._attr_is_on = False
            if not no_mqtt:
                self.hass.async_create_task(self._send_command(self.payload_onoff))

        self._attr_percentage = self._speed_to_percentage(self._speed)
        self.async_write_ha_state()

    def increase_speed(self, no_mqtt=False):
        if not self._attr_is_on:
            _LOGGER.debug("Ignoring increase_speed – fan is off")
            return

        if self._speed < MAX_SPEED:
            self._speed += 1
            _LOGGER.debug("Increased speed to %s", self._speed)
            if not no_mqtt:
                self.hass.async_create_task(self._send_command(self.payload_up))

        self._attr_percentage = self._speed_to_percentage(self._speed)
        self.async_write_ha_state()

    async def _send_command(self, payload_hex_str):
        """Send MQTT message with RF payload in Tasmota JSON format."""
        payload = {
            "Data": payload_hex_str,
            "Bits": 18,
            "Protocol": 8,
            "Pulse": 320,
            "Repeat": 2,
        }
        mqtt_payload = json.dumps(payload)
        _LOGGER.debug("Publishing to %s: %s", self.topic_out, mqtt_payload)
        await mqtt.async_publish(
            self.hass, self.topic_out, mqtt_payload, qos=1, retain=False
        )

    @property
    def device_info(self):
        """Return device info for device registry."""
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": "Dummy Fan",
            "manufacturer": "MQTT Dummy Inc.",
            "model": "MQTT Fan v1",
        }
