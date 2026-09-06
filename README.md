# iNELS Cloud for Home Assistant

A custom Home Assistant integration for **iNELS Cloud / ELKO EP** installations.

> **Status: early development / experimental.**
>
> The integration is based on the iNELS Cloud web application's observed API and WebSocket traffic. APIs that are not publicly documented may change without notice.

## Current features

- UI-based setup through Home Assistant Config Flow
- iNELS Cloud username/password authentication
- Automatic access-token refresh and refresh-token rotation
- Automatic device discovery
- Cloud WebSocket state updates
- Shutter/cover support (`dev_type: 21`)
- Temperature and humidity sensors (`dev_type: 30`)
- Basic on/off switch support (`dev_type: 2`)

## Installation

### HACS

1. Open HACS.
2. Go to **Integrations**.
3. Open the three-dot menu and choose **Custom repositories**.
4. Add this GitHub repository URL.
5. Select **Integration**.
6. Install **iNELS Cloud**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**.
9. Search for **iNELS Cloud**.

### Manual

Copy `custom_components/inels_cloud` into:

```text
/config/custom_components/inels_cloud
```

Restart Home Assistant and add the integration from the UI.

## Authentication and security

The integration logs in using:

```text
POST https://inels.cloud/v1/auth/login
```

with the iNELS Cloud username, password, and `origin=elkoep`.

The integration stores the access/refresh tokens in the Home Assistant config entry. The password is not stored.

Refresh tokens are rotated by iNELS Cloud. Every successful refresh therefore replaces the stored refresh token.

**Never commit tokens, passwords, cookies, or other credentials to GitHub or include them in bug reports.**

## Architecture

```text
Home Assistant
      |
      +-- REST --------------------+
      |                             |
      |                       Device discovery
      |                       & commands
      |                             |
      +-- WebSocket ----------------+
             |
             v
       iNELS Cloud
```

REST is used for initial device discovery and commands. The iNELS Cloud WebSocket is used for push state updates.

## Known limitations

This is an early version. Device type support and command mappings are incomplete.

In particular:

- `dev_type: 11` climate/thermostat support is not implemented yet.
- Shutter stop-command mapping has not been confirmed.
- Some iNELS devices report `255` for an unknown shutter position.
- Device discovery currently happens during setup; newly added devices require a reload/restart.
- The exact command semantics for every ELANRF device type still need to be verified against the cloud service.
- The integration currently assumes the observed iNELS Cloud endpoints remain available.

## Contributing

Contributions are very welcome, especially from people who own iNELS / ELKO EP hardware that is different from the author's installation.

### Good ways to help

- Add support for another `dev_type`.
- Capture and document command payloads for a device.
- Improve WebSocket reconnect/authentication handling.
- Add tests for API responses and device mappings.
- Improve Home Assistant entity/device metadata.
- Test the integration on different Home Assistant versions.
- Improve translations and documentation.
- Report API changes when the iNELS Cloud web application changes.

### Safely collecting API information

If you want to help reverse-engineer a device:

1. Open the iNELS Cloud web application.
2. Open browser developer tools.
3. Use **Network → Fetch/XHR** for REST requests.
4. Use **Network → WS → Messages/Frames** for WebSocket traffic.
5. Capture only the request/response structure needed to identify the command.
6. **Redact all credentials before sharing anything.**

Never share:

- `Authorization: Bearer ...`
- `access_token`
- `refresh_token`
- passwords
- cookies
- session identifiers
- personal account information

A useful contribution looks like:

```json
{
  "dev_type": 21,
  "fce": "os",
  "value": 50
}
```

plus a description such as:

> `value=50` sets the shutter to approximately 50%.

### Development setup

A normal Home Assistant development environment is recommended.

For quick local testing, copy the integration into:

```text
/config/custom_components/inels_cloud
```

Then enable debug logging:

```yaml
logger:
  logs:
    custom_components.inels_cloud: debug
```

After making changes, restart Home Assistant or reload the integration as appropriate.

### Pull requests

Please keep pull requests focused:

- One feature/fix per PR where practical.
- Include tests for new API/device mappings.
- Do not commit credentials or real device identifiers unless they are clearly synthetic.
- Update the README when adding or changing supported device types.
- Explain any API behavior that was discovered experimentally.

### Issue reports

When reporting an issue, please include:

- Home Assistant version
- iNELS Cloud integration version
- Device type
- Sanitized device state/event payload
- Relevant debug logs
- Steps to reproduce

Do **not** include account credentials or live authentication tokens.

## Disclaimer

This project is an independent community integration and is not an official ELKO EP / iNELS product.

Use it at your own risk. The iNELS Cloud API and WebSocket protocol are not assumed to be stable public APIs.
