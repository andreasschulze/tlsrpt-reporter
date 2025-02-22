All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.0] - 2025-02-22 - first public release

### Fixed
- docs: fixed typo in the filedaemon service name [PR #2028]
- Renamed package to tlsrpt_reporter
- Improved robustness in case of malformed report destinations
- Separate handling of setup errors and runtime errors for reportd
- Improved error handling: Added typenames when logging generic exceptions   
- Catch all errors when fetcher run fails
- Normalize domain name to avoid sending multiple reports for the same domain in different notations like uppercase vs lowercase.
- fix license statements

### Added
- Log error for datagrams with wrong protocol version

