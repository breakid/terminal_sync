# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.4.0] - Unreleased

### Added

- Added support for updating an existing Ghostwriter log entry by ID (experimental)
- Config option to disable SSL certificate checking on the Ghostwriter server

### Changed

- Completely overhauled `terminal_sync` to be a CLI rather than a client-server application
  - This was done to simplify the application, make it more reliable, and fix an issue where the server (Docker container) would stop responding when left running for extended periods of time (e.g., 24 hours)

## [v0.3.0] - 2023-05-02

### Added

- Developer documentation

### Fixed

- Fixed a bug where multiple JSON objects were created for the same command if an exception occurred during creation
- Added missing `source_host` and `operator` fields to messages sent by the Bash client

### Changed

- Split README content into separate pages and added more details / explanations

## [v0.2.0] - 2023-04-26

### Added

- Added a new feature to save failed (or optionally all) logs locally (as JSON files)
- Created a script / library to export the JSON files to a GhostWriter CSV
  - Configured the server to automatically export a CSV file on shutdown (though stopping a Docker container doesn't seem to trigger it)

### Fixed

- Fixed several syntax errors in the Bash install / hook script that prevented successful installation

### Changed

- Updated Dockerfile to export requirements.txt (to ensure platform compatibility) and install using pip rather than PDM (to reduce runtime complexity)
- Increased minimum Python version to 3.10 due to use of PEP-604 style type hinting syntax
- Reduced default timeout values as the previous ones were painfully long if something failed and would negatively impact user experience

## [v0.1.0] - 2023-04-21

Initial release

### Added

- FastAPI server with command create and update endpoints
- Custom config class
- `config.yaml` template
- GhostWriter client
- Dockerfile and Docker Compose config that build a terminal_sync server image
- Bash script that installs dependencies and contains pre-exec and post-exec hooks
- PowerShell module containing pre-exec and post-exec hooks
- `README.md` documenting how to install, update, use, and troubleshoot terminal_sync
- Project management files (`CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`)
