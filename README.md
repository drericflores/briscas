# Briscas

Briscas is a desktop implementation of the classic Spanish trick-taking card
game. It provides a PyQt5 interface, three computer difficulty levels, sound,
and persistent game statistics.

This repository reconstructs the maintainable source project from the surviving
Briscas 2.1.0 Debian binary package. Version 2.1.5 completes Linux desktop
integration, Debian package layout, table-card rendering, the face-up trump-card
display, final high-contrast game-table styling, and portable computer card backs.

## Build and test

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
sh scripts/build-deb.sh
```

## Install

```sh
sudo apt install ./dist/briscas_2.2.6_all.deb
```

After installation, launch **Briscas** from the application menu or run
`briscas` in a terminal. If startup fails, diagnostics are written to
`~/.local/state/briscas/briscas.log`.

## License

The reconstructed Briscas software is released under the MIT License. The
traditional Briscas card game and its rules are public domain.

The provenance and license of the bundled Spanish-card images and sound files
were not recorded in the surviving package. They are included for recovery and
historical continuity, but no third-party rights are claimed. Their licensing
must be verified or the assets replaced before third-party redistribution.

## Support

If you enjoy Briscas and would like to support its development, donations are
welcome via Zelle to eoftoro@gmail.com.
