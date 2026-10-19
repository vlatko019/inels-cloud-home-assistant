# Changelog

All notable changes to this project are documented here.

## [0.1.10-beta.1] - Pre-release

### Improved
- Expose shutter opening/closing state from the cloud's motor status and direction fields.
- Explicitly advertise supported cover actions to Home Assistant.
- Handle missing or malformed shutter-position values safely and preserve an unknown state instead of reporting the shutter as open.

### Testing
- This pre-release is intended for testing shutter state reporting before the stable 0.1.10 release.

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
