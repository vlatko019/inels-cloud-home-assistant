# Changelog

All notable changes to this project are documented here.

## [0.2.0] - 2026-10-21

### Added
- Report shutter opening and closing state from the cloud's motor status and direction fields.
- Expose shutter movement indicators that respect each device's Normal/Reversed direction setting.

### Improved
- Explicitly advertise the cover actions currently supported by the integration: open, close, and set position.
- Handle missing or malformed shutter-position and movement values safely, preserving unknown state rather than inventing a position or direction.

### Notes
- A dedicated shutter stop command is not included in this release because the iNELS Cloud command semantics have not yet been confirmed. Investigation and implementation are planned for the 0.2.x release line.

## [0.1.9] - 2026-10-14

### Added
- Add a GitHub Actions validation workflow for pull requests and pushes to `main`.
- Validate all repository JSON files and check integration Python syntax before changes are merged.

## [0.1.8] - 2026-10-14

### Fixed
- Recover automatically with a fresh login when iNELS Cloud rejects a refresh token.
- Persist rotated access and refresh tokens so token rotation survives Home Assistant restarts.
- Route authentication failures during switch and shutter commands through Home Assistant's config-entry authentication handling.
- Handle synchronous WebSocket event callbacks correctly instead of awaiting a non-awaitable result.
- Ignore malformed WebSocket events with invalid `eui` values instead of raising conversion errors.

### Changed
- Store the iNELS Cloud username and password in the Home Assistant config entry to allow automatic reauthentication. The integration does not separately encrypt this data.
- Add a GitHub Actions workflow that creates a version tag and GitHub Release from the version in `custom_components/inels_cloud/manifest.json`.
