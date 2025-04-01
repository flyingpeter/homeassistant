import logging
import asyncio
import socket

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up switches for the TCP Relay."""
    host = entry.data[CONF_HOST]
    port = entry.data.get(CONF_PORT, 5000)

    device_name = host  # Default name is the IP

    # Create 8 relay entities
    _LOGGER.debug("Creating relay switches for host %s with port %d", host, port)
    switches = [RelaySwitch(hass, device_name, host, port, i) for i in range(8)]
    
    # Log the created switches
    _LOGGER.debug("Created relay switches: %s", [switch.name for switch in switches])

    # Add the switches to Home Assistant
    async_add_entities(switches, True)
    _LOGGER.debug("Switch entities added to Home Assistant.")

class RelaySwitch(SwitchEntity):
    """Representation of a TCP relay switch."""

    def __init__(self, hass, device_name, host, port, relay_index):
        """Initialize the switch."""
        self._hass = hass
        self._device_name = device_name
        self._host = host
        self._port = port
        self._relay_index = relay_index
        self._state = False  # Default state is off

    @property
    def name(self):
        """Return the name of the switch."""
        return f"{self._device_name} Relay {self._relay_index + 1}"

    @property
    def unique_id(self):
        """Return a unique ID for the switch."""
        return f"{self._host}_relay_{self._relay_index + 1}"

    @property
    def is_on(self):
        """Return True if the relay is on."""
        return self._state

    async def async_turn_on(self, **kwargs):
        """Turn the relay on."""
        await self._send_command(1)

    async def async_turn_off(self, **kwargs):
        """Turn the relay off."""
        await self._send_command(0)

    async def _send_command(self, value):
        """Send command to turn on/off the relay."""
        try:
            # Use asyncio to handle socket communication asynchronously
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setblocking(False)  # Set socket to non-blocking mode

            loop = asyncio.get_event_loop()

            await loop.sock_connect(sock, (self._host, self._port))  # Connect asynchronously

            command = f"set{self._relay_index + 1}{value}".encode("utf-8")
            await loop.sock_sendall(sock, command)  # Send command asynchronously
            _LOGGER.info("Sent command: %s", command.decode("utf-8"))

            sock.close()  # Close the socket after sending the command

        except Exception as e:
            _LOGGER.error("Error sending command to %s:%d - %s", self._host, self._port, e)

    async def async_update(self):
        """Update the relay state based on the latest response."""
        state = self._hass.states.get(f"{DOMAIN}.{self._host}_relays")
        if state and state.state.startswith("relay"):
            relay_states = state.state[5:]  # Extract 8-digit state
            self._state = relay_states[self._relay_index] == "1"
