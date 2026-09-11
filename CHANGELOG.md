# Changelog

## 2.1.1 — 2026-09-11

- Reconstructed maintainable source from the surviving 2.1.0 binary package.
- Added a desktop launcher, application icon, and visible startup diagnostics.
- Moved the executable from `/usr/local/bin` to Debian-managed `/usr/bin`.
- Replaced the 57.7 MB embedded Python runtime with system PyQt5 dependencies.
- Corrected package metadata, permissions, section, and filesystem layout.
- Added deterministic game-rule tests and a reproducible package build script.
