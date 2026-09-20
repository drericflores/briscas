# Changelog

## 2.1.7 — 2026-09-20

- Added a visible, checkable Game → Difficulty menu (Easy/Medium/Hard) and
  showed the active difficulty in the info bar, since the difficulty
  setting previously existed only inside the Settings dialog with no
  on-screen indicator of which mode was selected. Renamed the "normal"
  level to "medium" to match the requested Easy/Medium/Hard naming.
- Labeled the table's lead and reply card slots with their actual owner
  ("Your Lead" / "Computer's Lead" / "Your Reply" / "Computer's Reply")
  instead of the static "Lead"/"Reply" text, and added a "You:" label
  above the player's hand to mirror the existing "Computer:" label, so
  it's always clear whose card is whose.
- Announced the outcome of each trick in the status bar (e.g. "You win
  the trick! +11 points" / "Computer wins the trick. +2 points for the
  computer."), since previously the score changed silently with no
  indication of who won the trick.

## 2.1.6 — 2026-09-20

- Fixed an incorrect path calculation in `data_root()` that pointed one
  directory above the project root when running from a source checkout
  instead of an installed `.deb`, leaving card, sound, and icon assets
  unresolved on machines that hadn't installed the packaged build.
- Made the `PyQt5.QtMultimedia` import optional: a machine missing the
  separate `python3-pyqt5.qtmultimedia` package (present on one machine,
  absent on another) no longer crashes on startup before any window is
  shown; the game now launches with sound disabled instead.

## 2.1.5 — 2026-09-11

- Replaced unsupported Unicode playing-card-back characters with the packaged
  Spanish card-back image.
- Dynamically hide computer card backs as the computer's hand is depleted.

## 2.1.4 — 2026-09-11

- Changed About, game-result, statistics, and settings dialogs to a readable
  dark-blue scheme with white text.
- Added gold-bordered dark-blue dialog buttons with clear interaction states.
- Added a substantial gold frame around the green game table.
- Licensed the reconstructed software under MIT and documented the traditional
  game rules as public domain.
- Declared the reconstructed game feature-complete after final visual polish.

## 2.1.3 — 2026-09-11

- Display the initial face-up card that establishes the trump suit.
- Keep the trump card visible in its own gold-bordered table position.
- Replace the card with a persistent trump-suit indicator after it is drawn.

## 2.1.2 — 2026-09-11

- Added the new Lily-playing-Briscas PNG application icon.
- Made lead and reply cards render directly from game state.
- Kept the completed trick visible until the next lead begins.

## 2.1.1 — 2026-09-11

- Reconstructed maintainable source from the surviving 2.1.0 binary package.
- Added a desktop launcher, application icon, and visible startup diagnostics.
- Moved the executable from `/usr/local/bin` to Debian-managed `/usr/bin`.
- Replaced the 57.7 MB embedded Python runtime with system PyQt5 dependencies.
- Corrected package metadata, permissions, section, and filesystem layout.
- Added deterministic game-rule tests and a reproducible package build script.
