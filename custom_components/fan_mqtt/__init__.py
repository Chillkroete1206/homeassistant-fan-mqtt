"""Initialize the fan_mqtt integration."""


async def async_setup_entry(hass, entry):
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["fan"])
    )
    return True


async def async_unload_entry(hass, entry):
    return await hass.config_entries.async_unload_platforms(entry, ["fan"])
