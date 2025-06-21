import voluptuous as vol
from homeassistant import config_entries
from .const import *

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_TOPIC_IN, default=DEFAULT_TOPIC_IN): str,
        vol.Required(CONF_TOPIC_OUT, default=DEFAULT_TOPIC_OUT): str,
        vol.Required(CONF_PAYLOAD_ONOFF, default=DEFAULT_PAYLOAD_ONOFF): str,
        vol.Required(CONF_PAYLOAD_UP, default=DEFAULT_PAYLOAD_UP): str,
        vol.Required(CONF_PAYLOAD_DOWN, default=DEFAULT_PAYLOAD_DOWN): str,
    }
)


class DummyFanConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="Dummy Fan", data=user_input)
        return self.async_show_form(step_id="user", data_schema=STEP_USER_DATA_SCHEMA)

    @classmethod
    def async_get_options_flow(cls, config_entry):
        return DummyFanOptionsFlowHandler(config_entry)


class DummyFanOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.options or self.config_entry.data
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_TOPIC_IN, default=data.get(CONF_TOPIC_IN, DEFAULT_TOPIC_IN)
                ): str,
                vol.Required(
                    CONF_TOPIC_OUT, default=data.get(CONF_TOPIC_OUT, DEFAULT_TOPIC_OUT)
                ): str,
                vol.Required(
                    CONF_PAYLOAD_ONOFF,
                    default=data.get(CONF_PAYLOAD_ONOFF, DEFAULT_PAYLOAD_ONOFF),
                ): str,
                vol.Required(
                    CONF_PAYLOAD_UP,
                    default=data.get(CONF_PAYLOAD_UP, DEFAULT_PAYLOAD_UP),
                ): str,
                vol.Required(
                    CONF_PAYLOAD_DOWN,
                    default=data.get(CONF_PAYLOAD_DOWN, DEFAULT_PAYLOAD_DOWN),
                ): str,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
