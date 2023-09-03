# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

# [0.10.1] - 2023-09-03
### Added
- Added support for bleak version `~0.21`.

# [0.10.0] - 2023-08-24
### Added
- Added support for initializing `IdasenDesk` with a `BLEDevice` instead of a MAC address.
- Added `connect` and `disconnect` methods as an alternative to the context manager.
- Added a `disconnected_callback` argument to the `IdasenDesk` constructor.
- Added a `pair` method.

### Changed
- Changed `build-system.requires` from `["poetry>=0.12"]` to `["poetry-core"]`.

### Fixed
- Fixed the `stop` method not stopping the desk.

## [0.9.6] - 2023-03-18
### Added
- Added support for bleak version `~0.20`.

## [0.9.5] - 2023-03-11
### Fixed
- Fixed configuration validation to accept 36-character MAC addresses as seen on macOS.

## [0.9.4] - 2022-10-14
### Added
- Added support for bleak version `~0.19`.

## [0.9.3] - 2022-09-23
### Added
- Added support for bleak version `~0.18`.

## [0.9.2] - 2022-09-12
### Added
- Added support for bleak version `~0.17`.

## [0.9.1] - 2022-08-31
### Added
- Added support for bleak version `~0.16`.

## [0.9.0] - 2022-07-29
### Added
- Added support for bleak version `~0.15`.

### Changed
- Changed `IdasenDesk.is_connected` from an async method to a property.

### Removed
- Removed support for bleak versions `~0.12`, `~0.13`, and `~0.14`.

## [0.8.3] - 2022-03-31
### Added
- Added support for voluptuous version `~0.13`.

## [0.8.2] - 2022-01-10
### Added
- Added support for bleak version `~0.14`.

## [0.8.1] - 2021-10-20
### Added
- Added support for bleak version `~0.13`.
- Added support for pyyaml version `^6.0.0`.

## [0.8.0] - 2021-10-02
### Fixed
- Use service UUID instead of device name for discovery.
  This fixes discovery for desks with non-standard names.

### Removed
- Dropped support for beak version `0.11`.

## [0.7.1] - 2021-06-19
### Added
- Added support for bleak version `0.12`.

## [0.7.0] - 2021-05-08
### Added
- Added `--version` to the CLI.

### Changed
- Updated bleak dependency from `0.9` to `0.11`.
- Changed changelog from rst to markdown.

## [0.6.0] - 2020-12-05
### Changed
- Stop moving the desk if the safety feature kicks in.

## [0.5.0] - 2020-11-14
### Added
- Added python 3.9 support.

### Changed
- Added automatic retry to failed connections.

### Fixed
- Allow the `init` subcommand to work without a MAC address.

## [0.4.0] - 2020-10-20
### Added
- Added `save` and `delete` sub-commands to the CLI to save and delete
  desk positions.

### Changed
- Changed the configuration file format, see the README for details.
- Updated bleak dependency to 0.9.0.

### Fixed
- Fixed a bug with the `init` sub-command raising an exception.

## [0.3.0] - 2020-10-10
### Added
- Added `discover` class method to `IdasenDesk`.

### Changed
- The `init` subcommand will now attempt to discover the MAC address.

## [0.2.1] - 2020-10-07
### Fixed
- Fixed CLI `--verbose` argument doing nothing.

## [0.2.0] - 2020-09-26
### Changed
- Added URL to `yaml` file created with `idasen init`.
- Updated bleak dependency to 0.8.0

## [0.1.0] - 2020-09-07
- Initial release

[Unreleased]: https://github.com/newAM/idasen/compare/v0.10.1...HEAD
[0.10.1]: https://github.com/newAM/idasen/compare/v0.10.0...v0.10.1
[0.10.0]: https://github.com/newAM/idasen/compare/v0.9.6...v0.10.0
[0.9.6]: https://github.com/newAM/idasen/compare/v0.9.5...v0.9.6
[0.9.5]: https://github.com/newAM/idasen/compare/v0.9.4...v0.9.5
[0.9.4]: https://github.com/newAM/idasen/compare/v0.9.3...v0.9.4
[0.9.3]: https://github.com/newAM/idasen/compare/v0.9.2...v0.9.3
[0.9.2]: https://github.com/newAM/idasen/compare/v0.9.1...v0.9.2
[0.9.1]: https://github.com/newAM/idasen/compare/v0.9.0...v0.9.1
[0.9.0]: https://github.com/newAM/idasen/compare/v0.8.3...v0.9.0
[0.8.3]: https://github.com/newAM/idasen/compare/v0.8.2...v0.8.3
[0.8.2]: https://github.com/newAM/idasen/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/newAM/idasen/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/newAM/idasen/compare/v0.7.1...v0.8.0
[0.7.1]: https://github.com/newAM/idasen/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/newAM/idasen/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/newAM/idasen/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/newAM/idasen/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/newAM/idasen/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/newAM/idasen/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/newAM/idasen/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/newAM/idasen/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/newAM/idasen/releases/tag/v0.1.0
