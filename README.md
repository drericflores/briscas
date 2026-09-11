# Briscas

Briscas is a desktop implementation of the classic Spanish trick-taking card
game. It provides a PyQt5 interface, three computer difficulty levels, sound,
and persistent game statistics.

This repository reconstructs the maintainable source project from the surviving
Briscas 2.1.0 Debian binary package. Version 2.1.1 repairs Linux desktop
integration and Debian package layout.

## Build and test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
sh scripts/build-deb.sh
```

## Install

```sh
sudo apt install ./dist/briscas_2.1.1_all.deb
```

After installation, launch **Briscas** from the application menu or run
`briscas` in a terminal. If startup fails, diagnostics are written to
`~/.local/state/briscas/briscas.log`.

## Licensing status

Copyright © 2025–2026 Dr. Eric Oliver Flores Toro. All rights reserved.

The provenance and license of the bundled Spanish-card images and sound files
were not recorded in the surviving package. They are included for recovery and
historical continuity, but no third-party rights are claimed. Their licensing
must be verified or the assets replaced before redistribution. No open-source
license is granted by this repository at this time.
