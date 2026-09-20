# Changelog

## 2.2.5 — 2026-09-20

- Fixed unreadable white-on-white text in the About dialog's tabs. The
  app's dark-theme stylesheet only reaches the dialog's own direct
  children, not the QTabWidget's separately-rendered tab pages, so those
  pages kept Qt's default light background while the inherited white
  text became nearly invisible against it. Both tabs now set their text
  to dark blue explicitly.

## 2.2.4 — 2026-09-20

- The About dialog is now tabbed: "About" (unchanged) plus a new "Support"
  tab with the Zelle donation note, so players who don't read the README
  (i.e. most people installing the .deb) still see it in-app.

## 2.2.3 — 2026-09-20

- The game now starts immediately on launch (a 2-player game, dealt and
  ready to play) instead of first blocking on the "how many players?"
  dialog. That dialog now only appears when explicitly starting a new
  game (Game > New Game / Ctrl+N); difficulty and player count both
  remain changeable at any time from the Game menu without interrupting
  play.

## 2.2.2 — 2026-09-20

- Fixed the application icon not being reliably recognized by the desktop's
  menu/dock/app-grid (e.g. Pop!_OS's COSMIC/GNOME-based shell). The icon was
  only installed under `hicolor/1024x1024/apps`, a size hicolor's own
  index.theme does not declare (it lists 16 up through 512, plus
  "scalable"), so the standard icon lookup could never find it. The icon is
  now installed at every size hicolor actually recognizes (generated from
  the source image at package-build time), plus a `/usr/share/pixmaps`
  fallback for older lookup paths.
- Added `postinst`/`postrm` maintainer scripts that refresh the desktop and
  icon caches on install/removal, so the Briscas entry and its icon appear
  in the applications menu immediately rather than waiting on an unrelated
  trigger or a logout.
- Verified end-to-end in this environment: installed the rebuilt .deb,
  confirmed all 13 icon sizes land with correct permissions, and confirmed
  `com.ericflores.briscas` is indexed in the regenerated
  `icon-theme.cache` (the file the desktop's icon lookup actually reads).

## 2.2.1 — 2026-09-20

- After a trick, the result now shows as a clear banner ("You win the
  trick! +N points" / "<seat> wins the trick...") in place of the score
  line for a couple of seconds, then the table clears and the status bar
  explicitly announces "Your turn — play a card." whenever it becomes the
  human player's turn to act (leading or replying). Previously the score
  changed silently and the finished trick lingered with no clear signal
  of when it was the player's turn again.
- The About dialog now shows the Briscas app icon at a larger size (128px)
  instead of the generic small system icon.
- Fixed the window-icon fallback (used when running from a source checkout
  instead of the installed .deb) to use the actual Briscas icon instead of
  a card-back image.
- Added a donation note (Zelle) to the bottom of README.md.

## 2.2.0 — 2026-09-20

- Added 2/3/4-player games, chosen from a "New Game" dialog before each deal:
  2 players (you vs. 1 computer, as before), 3 players (you vs. 2 computers,
  free-for-all scoring), and 4 players (you + a computer partner seated
  across the table vs. the other two computers, team scoring — matching the
  traditional partnership variant of Brisca).
- Generalized the trick engine, AI, and table UI from a fixed lead+reply
  pair to any number of seats, including handling player counts that don't
  evenly divide the 40-card deck (a seat can run a trick or two short of
  cards near the end, same as the real game, instead of crashing).
- Table slots are now labeled by seat identity (You / Partner / Opponent 1 /
  Opponent 2 / CPU N) so it stays clear whose card is where regardless of
  player count.
- Human-vs-human networked play is a possible future direction, not part of
  this release.

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
