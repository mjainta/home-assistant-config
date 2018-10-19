import datetime
import logging
from threading import Lock

import voluptuous as vol

import homeassistant.core
from homeassistant.const import EVENT_HOMEASSISTANT_START
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_state_change, track_time_change

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'alarm_clock'

CONF_TIME = 'time'
CONF_TIME_HOUR = 'time_hour'
CONF_TIME_MIN = 'time_min'
CONF_ENTITY_ID = 'entity_id'
CONF_MASTER_CONTROL = 'master_control'
CONF_ADDITIONAL = 'additional'

ADDITIONAL_SCHEMA = vol.Schema({
  vol.Required(CONF_TIME): cv.time_period,
  vol.Required(CONF_ENTITY_ID): cv.string,
}, extra=vol.ALLOW_EXTRA)

CONFIG_SCHEMA = vol.Schema({
  DOMAIN: vol.Schema({
    vol.Required(CONF_TIME): cv.string,
    vol.Required(CONF_TIME_HOUR): cv.positive_int,
    vol.Required(CONF_TIME_MIN): cv.positive_int,
    vol.Required(CONF_ENTITY_ID): cv.string,
    vol.Optional(CONF_MASTER_CONTROL, default=''): cv.string,
    vol.Optional(CONF_ADDITIONAL, default=[]): ADDITIONAL_SCHEMA,
  }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
  time = config[DOMAIN].get(CONF_TIME)
  time_hour = config[DOMAIN].get(CONF_TIME_HOUR)
  time_min = config[DOMAIN].get(CONF_TIME_MIN)
  time = "{hour}:{min}".format(hour=time_hour, min=time_min)
  entity_id = config[DOMAIN].get(CONF_ENTITY_ID)
  master_control = config[DOMAIN].get(CONF_MASTER_CONTROL)

  additional = config[DOMAIN].get(CONF_ADDITIONAL)
  if additional:
    additional = ADDITIONAL_SCHEMA(additional)
    additional_time = additional.get(CONF_TIME)
    additional_entity_id = additional.get(CONF_ENTITY_ID)
  else:
    additional_time = None
    additional_entity_id = None

  AlarmClock(hass, time, entity_id, master_control,
    additional_time, additional_entity_id)

  return True


class AlarmClock(object):
  '''
  Represents configuration and state for a full-feature alarm clock.
  Setting an alarm requires a time, usually configured as an input; and an
  entity_id representing an entity that can be turned on (e.g. a light, a
  group or a scene).
  Optionally a master control can be specified by passing the name of an
  input; in that case the whole alarm clock will be off when the master
  control is disabled.
  An additional related alert is also supported that can be configured to
  fire before or after the main alert and trigger a different entity. A
  typical use case is to run a "sunrise" scene some time before the alarm
  goes off.
  '''

  def __init__(self, hass, time, entity_id, master_control,
    additional_time, additional_entity_id):
    '''
    Constructor.
    Arguments:
    hass -- the HASS object
    time -- the name of an input; we expect that state to be in format HH:MM
    entity_id -- entity ID of an entity that can be turned on
    master_control -- (optional) the name of an input; if the state is 'off'
      the timer will be disabled
    additional_time -- (optional) the time delta to the additional alarm
    additional_entity_id -- (optional) entity ID of an entity used for the
      additional alarm
    '''
    self.hass = hass
    self.time = time
    self.entity_id = entity_id
    self.master_control = master_control
    self.additional_time = additional_time
    self.additional_entity_id = additional_entity_id

    self.mutex = Lock()
    self.alarms = set()

    self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, self._started)

  def _started(self, event):
    '''
    Callback invoked when all components have been initialized. Setting up
    other listeners here ensures we won't get extra calls. This is when time
    events start firing anyway.
    '''
    _LOGGER.info('Starting alarm for {}'.format(self.time))

    track_state_change(self.hass, self.time, self._time_changed)
    if self.master_control:
      track_state_change(self.hass, self.master_control, self._master_control_changed)

    self._update_alarms()

  def _time_changed(self, entity_id, old_state, new_state):
    '''
    Callback invoked when the state of the component that controls the time
    changes.
    '''
    self._update_alarms()

  def _master_control_changed(self, entity_id, old_state, new_state):
    '''
    Callback invoked when the state of the master control component changes.
    '''
    self._update_alarms_with_enabled(new_state.state == 'on')

  def _update_alarms(self):
    '''
    Update alarms based on the controls, reading the enabled state from the
    master control.
    '''
    if self.master_control:
      _enabled = self.hass.states.get(self.master_control)
      is_enabled = True if not (_enabled is None) and _enabled.state == 'on' else False
    else:
      is_enabled = True

    self._update_alarms_with_enabled(is_enabled)

  def _update_alarms_with_enabled(self, is_enabled):
    '''
    Update alarms based on the controls.
    '''
    with self.mutex:
      if is_enabled:
        _LOGGER.info('(Re-)enabling alarms')
        self._clear_alarms()
        self._create_alarms()
      else:
        _LOGGER.info('Disabling alarms')
        self._clear_alarms()

  def _create_alarms(self):
    '''
    Create alarms with the specified times and enables the event listeners.
    '''
    _time = self.hass.states.get(self.time).state
    alarm_time = datetime.datetime.strptime(_time, '%H:%M')

    _LOGGER.info('Setting up alarms for %02d:%02d' %
      (alarm_time.hour, alarm_time.minute))

    alarm = Alarm(self.hass,
      alarm_time.hour, alarm_time.minute, self.entity_id)
    self.alarms.add(alarm)

    if self.additional_time:
      alarm_time = alarm_time + self.additional_time
      _LOGGER.info('Setting up an additional alarm for %02d:%02d' %
        (alarm_time.hour, alarm_time.minute))

      alarm = Alarm(self.hass,
        alarm_time.hour, alarm_time.minute, self.additional_entity_id)
      self.alarms.add(alarm)

  def _clear_alarms(self):
    '''
    Clear all alerts and their event listeners.
    '''
    for alarm in self.alarms:
      alarm.remove_listener()
    self.alarms.clear()


class Alarm(object):
  '''
  Represents a single alarm, which will go off at the specified hour and minute.
  When that happens the specified entity will be turned on.
  '''

  def __init__(self, hass, hour, minute, entity_id):
    self.hass = hass
    self.hour = hour
    self.minute = minute
    self.entity_id = entity_id

    _LOGGER.info('Setting up an alarm for %02d:%02d - %s' %
      (self.hour, self.minute, self.entity_id))

    self.unsubscribe = track_time_change(self.hass, lambda now: self._update(),
      hour=self.hour, minute=self.minute, second=0)

  def _update(self):
    _LOGGER.info('Alarm went off up at %02d:%02d - %s' %
      (self.hour, self.minute, self.entity_id))

    self.hass.services.call(
      'homeassistant', 'turn_on', {'entity_id': self.entity_id})

  def remove_listener(self):
    self.unsubscribe()
