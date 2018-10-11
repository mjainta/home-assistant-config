import random
import requests

from homeassistant.const import EVENT_HOMEASSISTANT_STOP

# The domain of your component. Should be equal to the name of your component.
DOMAIN = 'enledment'

CONF_TOPIC = 'enledment'
DEFAULT_TOPIC = 'home-assistant/enledment'

REQUIREMENTS=['requests']

#esp_address = "192.168.4.1"
esp_address = "192.168.2.109"

def setup(hass, config):
    """Initially turn off LED light"""
    payload = {
        "red": 0,
        "green": 0,
        "blue": 0,
        "fade_time": 0,
    }
    #requests.post("http://" + esp_address + "/api/fade?", json=payload)
    hass.states.set('enledment.color', 'off')

    def set_color(call):
        """Set LED color."""
        payload = {
            "red": call.data.get("red", 0),
            "green": call.data.get("green", 0),
            "blue": call.data.get("blue", 0),
            "fade_time": call.data.get("fade_time", 1000),
        }
        requests.post("http://" + esp_address + "/api/fade?", json=payload)
        return True

    hass.services.register(DOMAIN, 'set_color', set_color)

    def set_color_random(call):
        """Set LED color."""
        total_value_sum = 600
        dividers = sorted(random.sample(range(1, total_value_sum), 3 - 1))
        color_values = [a - b for a, b in zip(dividers + [total_value_sum], [0] + dividers)]
        color_values = [x - 1 for x in color_values]
        payload = {
            "red": random.randint(0, color_values[0]),
            "green": random.randint(0, color_values[1]),
            "blue": random.randint(0, color_values[2]),
            "fade_time": random.randint(3000, 3000),
        }
        print("JSON PAYLOAD", payload)
        requests.post("http://" + esp_address + "/api/fade?", json=payload)
        return True

    hass.services.register(DOMAIN, 'set_color_random', set_color_random)

    # Listener to start show
    def start_show(event):
        hass.states.set('enledment.show', 'on')
        
        while hass.states.get('enledment.show').state == 'on':
            send_random_color() 

    def stop_show(event):
        hass.states.set('enledment.show', 'off')

    def alarm(event):
        hass.states.set('enledment.show', 'off')
        hass.states.set('enledment.alarm', 'on')
        payload = {
            "red": 255,
            "green": 0,
            "blue": 0,
            "fade_time": 0,
        }
        print("JSON PAYLOAD", payload)
        requests.post("http://" + esp_address + "/api/fade?", json=payload)


    # Listen for when my_cool_event is fired
    hass.bus.listen('start_show', start_show)
    hass.bus.listen('stop_show', stop_show)
    hass.bus.listen('alarm', alarm)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_show)

    def send_random_color():
        total_value_sum = 600
        dividers = sorted(random.sample(range(1, total_value_sum), 3 - 1))
        color_values = [a - b for a, b in zip(dividers + [total_value_sum], [0] + dividers)]
        color_values = [x - 1 for x in color_values]
        payload = {
            "red": random.randint(0, color_values[0]),
            "green": random.randint(0, color_values[1]),
            "blue": random.randint(0, color_values[2]),
            "fade_time": random.randint(3000, 3000),
        }
        requests.post("http://" + esp_address + "/api/fade?", json=payload)

    return True
