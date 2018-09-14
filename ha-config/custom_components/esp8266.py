import random
import requests

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

# The domain of your component. Should be equal to the name of your component.
DOMAIN = 'esp8266'

CONF_TOPIC = 'esp8266'
DEFAULT_TOPIC = 'home-assistant/esp8266'

REQUIREMENTS=['requests']

esp_address = "10.123.106.116"

def setup(hass, config):
    """Initially turn off LED light"""
    payload = {
        "RED": 0,
        "GREEN": 0,
        "BLUE": 0,
        "FADE_TIME": 0,
    }
    #r = requests.get("http://" + esp_address + "/setColor?", params=payload)
    hass.states.set('eps8266.set_color', 'ESP8266 Connected!')

    def set_color(call):
        """Set LED color."""
        payload = {
            "RED": call.data.get("red", 0),
            "GREEN": call.data.get("green", 0),
            "BLUE": call.data.get("blue", 0),
            "FADE_TIME": call.data.get("fade_time", 1000),
        }
        r = requests.get("http://" + esp_address + "/setColor?", params=payload)
        return True

    hass.services.register(DOMAIN, 'set_color', set_color)

    def set_color_random(call):
        """Set LED color."""
        payload = {
            "RED": random.randint(0,1023),
            "GREEN": random.randint(0,1023),
            "BLUE": random.randint(0,1023),
            "FADE_TIME": random.randint(1000,5000),
        }
        r = requests.get("http://" + esp_address + "/setColor?", params=payload)
        return True

    hass.services.register(DOMAIN, 'set_color_random', set_color_random)

    # Listener to start show
    def start_show(event):
        hass.states.set('eps8266.show', 'on')
        
        while hass.states.get('eps8266.show').state == 'on':
            send_random_color() 

    def stop_show(event):
        hass.states.set('eps8266.show', 'off')

    # Listen for when my_cool_event is fired
    hass.bus.listen('start_show', start_show)
    hass.bus.listen('stop_show', stop_show)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_show)

    def send_random_color():
        payload = {
            "RED": random.randint(0,1023),
            "GREEN": random.randint(0,1023),
            "BLUE": random.randint(0,1023),
            "FADE_TIME": random.randint(1000,5000),
        }
        r = requests.get("http://" + esp_address + "/setColor?", params=payload)

    return True
