"""Constants for the iNELS Cloud integration."""

from __future__ import annotations

DOMAIN = "inels_cloud"
NAME = "iNELS Cloud"

API_BASE = "https://inels.cloud"
LOGIN_PATH = "/v1/auth/login"
REFRESH_PATH = "/v1/auth/refresh"
DEVICES_PATH = "/api/v1/device-manager/project/devices"
COMMAND_PATH = "/tech/elanrf/command"
WEBSOCKET_URL = "wss://inels.cloud:7778/wssapp"

ORIGIN = "elkoep"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_ACCESS_TOKEN = "access_token"
CONF_REFRESH_TOKEN = "refresh_token"

EVENT_ACTION = "event"

DEV_TYPE_SWITCH = 2
DEV_TYPE_CLIMATE = 11
DEV_TYPE_SHUTTER = 21
DEV_TYPE_THERMOSTAT = 30

PLATFORMS = ["cover", "sensor", "switch"]
