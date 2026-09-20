from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PyQt5.QtCore import QTimer, QUrl, Qt
from PyQt5.QtGui import QIcon, QPixmap

try:
    from PyQt5.QtMultimedia import QSoundEffect
except ImportError:
    QSoundEffect = None

from PyQt5.QtWidgets import (
    QAction, QActionGroup, QApplication, QCheckBox, QComboBox, QDialog,
    QFormLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSlider, QStatusBar, QVBoxLayout, QWidget,
)

from . import __version__
from .game import Card, ai_choose, make_deck, winner_index


def data_root() -> Path:
    override = os.environ.get("BRISCAS_DATA_DIR")
    if override:
        return Path(override)
    installed = Path("/usr/share/games/briscas")
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2] / "assets"


def app_icon_path() -> Path:
    installed = Path("/usr/share/icons/hicolor/1024x1024/apps/com.ericflores.briscas.png")
    if installed.exists():
        return installed
    return data_root() / "icons" / "briscas-lily.png"


def state_file() -> Path:
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")) / "briscas"
    root.mkdir(parents=True, exist_ok=True)
    return root / "statistics.json"


class SoundBank:
    def __init__(self) -> None:
        self.enabled = QSoundEffect is not None
        self.volume = 0.7
        self.effects: dict[str, QSoundEffect] = {}
        if not self.enabled:
            return
        for name in ("click", "deal", "play", "shuffle", "trick"):
            path = data_root() / "sounds" / f"{name}.wav"
            if path.exists():
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(path)))
                effect.setVolume(self.volume)
                self.effects[name] = effect

    def play(self, name: str) -> None:
        if self.enabled and name in self.effects:
            self.effects[name].play()

    def set_volume(self, value: int) -> None:
        self.volume = value / 100
        for effect in self.effects.values():
            effect.setVolume(self.volume)


class SettingsDialog(QDialog):
    def __init__(self, parent: "BriscasWindow") -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        form = QFormLayout(self)
        self.difficulty = QComboBox()
        self.difficulty.addItems(["easy", "medium", "hard"])
        self.difficulty.setCurrentText(parent.difficulty)
        self.sound = QCheckBox("Enable sound")
        self.sound.setChecked(parent.sounds.enabled)
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(round(parent.sounds.volume * 100))
        form.addRow("Difficulty", self.difficulty)
        form.addRow(self.sound)
        form.addRow("Volume", self.volume)
        button = QPushButton("Apply")
        button.clicked.connect(self.accept)
        form.addRow(button)


class PlayerCountDialog(QDialog):
    """Lets the player choose 2, 3, or 4 total players before a new game deals."""

    OPTIONS = (
        (2, "2 players — You vs. 1 computer"),
        (3, "3 players — You vs. 2 computers (free-for-all)"),
        (4, "4 players — You + partner vs. 2 computers (teams)"),
    )

    def __init__(self, parent: "BriscasWindow", current: int) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Game")
        layout = QFormLayout(self)
        self.count = QComboBox()
        for _, label in self.OPTIONS:
            self.count.addItem(label)
        current_index = next(
            (i for i, (n, _) in enumerate(self.OPTIONS) if n == current), 0
        )
        self.count.setCurrentIndex(current_index)
        layout.addRow("Players", self.count)
        button = QPushButton("Start")
        button.clicked.connect(self.accept)
        layout.addRow(button)

    @property
    def selected_count(self) -> int:
        return self.OPTIONS[self.count.currentIndex()][0]


class BriscasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Briscas {__version__}")
        self.setWindowIcon(QIcon(str(app_icon_path())))
        self.difficulty = "medium"
        self.num_players = 2
        self.sounds = SoundBank()
        self.stats = self.load_stats()
        self.awaiting_seat = 0
        self._deal_new_game()  # start playing immediately; no dialog on launch

    def seat_label(self, seat: int) -> str:
        if seat == 0:
            return "You"
        if self.num_players == 4:
            return "Partner" if seat == 2 else f"Opponent {1 if seat == 1 else 2}"
        return f"CPU {seat}"

    def scoreboard(self) -> list[tuple[str, int]]:
        if self.num_players == 4:
            your_team = self.scores[0] + self.scores[2]
            opponents = self.scores[1] + self.scores[3]
            return [("Your Team", your_team), ("Opponents", opponents)]
        return [(self.seat_label(seat), score) for seat, score in enumerate(self.scores)]

    def build_ui(self) -> None:
        self.card_buttons: list[QPushButton] = []
        self.menuBar().clear()
        game = self.menuBar().addMenu("&Game")
        new = QAction("&New Game", self, shortcut="Ctrl+N", triggered=self.new_game)
        settings = QAction("&Settings", self, shortcut="Ctrl+,", triggered=self.show_settings)
        stats = QAction("S&tatistics", self, triggered=self.show_stats)
        quit_action = QAction("&Quit", self, shortcut="Ctrl+Q", triggered=self.close)
        game.addActions([new, settings, stats])
        difficulty_menu = game.addMenu("&Difficulty")
        self.difficulty_actions: dict[str, QAction] = {}
        difficulty_group = QActionGroup(self)
        difficulty_group.setExclusive(True)
        for level in ("easy", "medium", "hard"):
            action = QAction(level.title(), self, checkable=True)
            action.triggered.connect(lambda checked=False, lvl=level: self.set_difficulty(lvl))
            difficulty_group.addAction(action)
            difficulty_menu.addAction(action)
            self.difficulty_actions[level] = action
        self.difficulty_actions[self.difficulty].setChecked(True)
        game.addAction(quit_action)
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(QAction("&About", self, triggered=self.show_about))

        root = QWidget()
        root.setObjectName("gameTableFrame")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 18, 18, 18)
        self.info = QLabel()
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("font-size: 16px; font-weight: bold; padding: 8px")
        layout.addWidget(self.info)

        opponents_row = QHBoxLayout()
        opponents_row.addStretch()
        self.opponent_card_labels: dict[int, list[QLabel]] = {}
        card_back = QPixmap(str(data_root() / "cards" / "posterior.png")).scaled(
            50, 76, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        for seat in range(1, self.num_players):
            group = QVBoxLayout()
            title = QLabel(f"{self.seat_label(seat)}:")
            title.setAlignment(Qt.AlignCenter)
            group.addWidget(title)
            cards_row = QHBoxLayout()
            labels: list[QLabel] = []
            for _ in range(3):
                label = QLabel()
                label.setAlignment(Qt.AlignCenter)
                label.setFixedSize(56, 82)
                label.setPixmap(card_back)
                cards_row.addWidget(label)
                labels.append(label)
            self.opponent_card_labels[seat] = labels
            group.addLayout(cards_row)
            opponents_row.addLayout(group)
            opponents_row.addSpacing(24)
        opponents_row.addStretch()
        layout.addLayout(opponents_row)

        table_row = QHBoxLayout()
        self.seat_slots: dict[int, tuple[QLabel, QLabel]] = {}
        slot_size = 180 if self.num_players <= 2 else 150
        for seat in range(self.num_players):
            caption = QLabel(self.seat_label(seat))
            caption.setAlignment(Qt.AlignCenter)
            caption.setStyleSheet("font-weight: bold; font-size: 13px; color: #f7e7bd;")
            card_label = QLabel("Waiting")
            card_label.setAlignment(Qt.AlignCenter)
            card_label.setFixedSize(slot_size, int(slot_size * 1.5))
            card_label.setStyleSheet("border: 2px solid #a58850; background: #174f2a; color: white")
            column = QVBoxLayout()
            column.addWidget(caption)
            column.addWidget(card_label)
            table_row.addLayout(column)
            self.seat_slots[seat] = (caption, card_label)

        self.trump_caption = QLabel("Trump")
        self.trump_caption.setAlignment(Qt.AlignCenter)
        self.trump_caption.setStyleSheet("font-weight: bold; font-size: 13px; color: #f7e7bd;")
        self.trump_card_label = QLabel("Trump Card")
        self.trump_card_label.setAlignment(Qt.AlignCenter)
        self.trump_card_label.setFixedSize(slot_size, int(slot_size * 1.5))
        self.trump_card_label.setStyleSheet(
            "border: 3px solid #e2b84c; background: #174f2a; color: #f7e7bd; font-weight: bold"
        )
        trump_column = QVBoxLayout()
        trump_column.addWidget(self.trump_caption)
        trump_column.addWidget(self.trump_card_label)
        table_row.addLayout(trump_column)

        layout.addLayout(table_row)
        self.player_title = QLabel("You:")
        self.player_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.player_title)
        self.hand_row = QHBoxLayout()
        layout.addLayout(self.hand_row)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
        self.setMinimumSize(max(980, 230 * (self.num_players + 1)), 680)
        self.setStyleSheet("""
            QMainWindow { background: #071f13; }
            QWidget#gameTableFrame {
                background: #0d3b21;
                border: 7px solid #d4af37;
                border-radius: 12px;
            }
            QWidget#gameTableFrame QLabel { color: #f7e7bd; }
            QMessageBox, QDialog { background-color: #0b2545; }
            QMessageBox QLabel, QDialog QLabel {
                color: #ffffff;
                background: transparent;
                font-size: 14px;
            }
            QMessageBox QPushButton, QDialog QPushButton {
                color: #ffffff;
                background-color: #173f6b;
                border: 2px solid #d4af37;
                border-radius: 5px;
                padding: 6px 18px;
                min-width: 72px;
            }
            QMessageBox QPushButton:hover, QDialog QPushButton:hover {
                background-color: #24588d;
            }
            QMessageBox QPushButton:pressed, QDialog QPushButton:pressed {
                background-color: #071b33;
            }
        """)

    def card_pixmap(self, card: Card, width: int = 150, height: int = 240) -> QPixmap:
        path = data_root() / "cards" / f"{card.rank}_{card.suit}.png"
        return QPixmap(str(path)).scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def load_stats(self) -> dict[str, int]:
        try:
            values = json.loads(state_file().read_text(encoding="utf-8"))
            return {key: int(values.get(key, 0)) for key in ("games", "wins", "losses", "draws")}
        except (OSError, ValueError, TypeError):
            return {"games": 0, "wins": 0, "losses": 0, "draws": 0}

    def save_stats(self) -> None:
        state_file().write_text(json.dumps(self.stats, indent=2) + "\n", encoding="utf-8")

    def new_game(self) -> None:
        dialog = PlayerCountDialog(self, self.num_players)
        if dialog.exec_() != QDialog.Accepted:
            return  # cancelled; leave the current game untouched
        self.num_players = dialog.selected_count
        self._deal_new_game()

    def _deal_new_game(self) -> None:
        self.build_ui()
        self.deck = make_deck()
        self.hands: list[list[Card]] = [
            [self.deck.pop() for _ in range(3)] for _ in range(self.num_players)
        ]
        self.trump_card = self.deck[0]
        self.trump = self.trump_card.suit
        self.leader = 0
        self.scores = [0] * self.num_players
        self.table: list[tuple[int, Card]] = []
        self.last_trick: list[tuple[int, Card]] = []
        self.turn_order: list[int] = []
        self.locked = False
        self._game_over_pending = False
        self.sounds.play("shuffle")
        self.start_trick()

    def render(self) -> None:
        score_text = "   ".join(f"{label}: {score}" for label, score in self.scoreboard())
        self.info.setText(
            f"Trump: {self.trump.title()}   {score_text}   "
            f"Cards left: {len(self.deck)}   Difficulty: {self.difficulty.title()}"
        )
        for seat, labels in self.opponent_card_labels.items():
            hand_len = len(self.hands[seat])
            for index, label in enumerate(labels):
                label.setVisible(index < hand_len)
        self.render_trump_card()
        self.render_table()
        for button in self.card_buttons:
            self.hand_row.removeWidget(button)
            button.deleteLater()
        self.card_buttons = []
        for index, card in enumerate(self.hands[0]):
            button = QPushButton()
            button.setIcon(QIcon(self.card_pixmap(card)))
            button.setIconSize(self.card_pixmap(card).size())
            button.setFixedSize(165, 255)
            button.setEnabled(not self.locked and self.awaiting_seat == 0)
            button.clicked.connect(lambda checked=False, i=index: self.player_play(i))
            self.hand_row.addWidget(button)
            self.card_buttons.append(button)

    def render_trump_card(self) -> None:
        """Keep the face-up card that established trump visible while it remains in the stock."""
        self.trump_card_label.setPixmap(QPixmap())
        if self.deck and self.trump_card is not None and self.trump_card in self.deck:
            self.show_table_card(self.trump_card_label, self.trump_card)
            self.trump_card_label.setToolTip(
                f"Trump card: {self.trump_card.rank} of {self.trump_card.suit.title()}"
            )
        else:
            self.trump_card_label.setText(f"Trump\n{self.trump.title()}")
            self.trump_card_label.setToolTip("The face-up trump card has been drawn")

    def render_table(self) -> None:
        """Render table cards by seat identity so it's always clear whose card is whose."""
        visible = self.table or self.last_trick
        visible_map = dict(visible)
        for seat, (caption, label) in self.seat_slots.items():
            label.setPixmap(QPixmap())
            caption.setText(self.seat_label(seat))
            if seat in visible_map:
                self.show_table_card(label, visible_map[seat])
            else:
                label.setText("Waiting")

    def show_table_card(self, label: QLabel, card: Card) -> None:
        label.setText("")
        label.setPixmap(self.card_pixmap(card, 170, 260))

    def start_trick(self) -> None:
        # Player counts that don't evenly divide the 40-card deck (e.g. 3) can leave some
        # seats a card short of others near the end; a seat with an empty hand sits out of
        # remaining tricks entirely rather than being asked to play a card it doesn't have.
        order = [(self.leader + i) % self.num_players for i in range(self.num_players)]
        self.turn_order = [seat for seat in order if self.hands[seat]]
        self.table = []
        self.render()
        self.advance_turn()

    def advance_turn(self) -> None:
        seat = self.turn_order[len(self.table)]
        self.awaiting_seat = seat
        if seat == 0:
            self.locked = False
            self.render()
            self.statusBar().showMessage("Your turn — play a card.", 2500)
        else:
            self.locked = True
            self.render()
            QTimer.singleShot(600, lambda: self.cpu_take_turn(seat))

    def cpu_take_turn(self, seat: int) -> None:
        hand = self.hands[seat]
        trick_cards = [card for _, card in self.table]
        card = hand.pop(ai_choose(hand, trick_cards, self.trump, self.difficulty))
        self.table.append((seat, card))
        self.render()
        if len(self.table) == len(self.turn_order):
            QTimer.singleShot(700, self.finish_trick)
        else:
            QTimer.singleShot(400, self.advance_turn)

    def player_play(self, index: int) -> None:
        if self.locked or self.awaiting_seat != 0 or index >= len(self.hands[0]):
            return
        self.locked = True
        card = self.hands[0].pop(index)
        self.table.append((0, card))
        self.sounds.play("play")
        self.render()
        if len(self.table) == len(self.turn_order):
            QTimer.singleShot(700, self.finish_trick)
        else:
            QTimer.singleShot(400, self.advance_turn)

    def finish_trick(self) -> None:
        cards = [card for _, card in self.table]
        winner_seat = self.table[winner_index(cards, self.trump)][0]
        points = sum(card.points for card in cards)
        self.scores[winner_seat] += points
        self.leader = winner_seat
        self.sounds.play("trick")
        if winner_seat == 0:
            announcement = f"You win the trick! +{points} points"
        else:
            announcement = f"{self.seat_label(winner_seat)} wins the trick. +{points} points."
        if self.deck:
            draw_order = [(winner_seat + i) % self.num_players for i in range(self.num_players)]
            for seat in draw_order:
                if not self.deck:
                    break
                self.hands[seat].append(self.deck.pop())
        self.last_trick = list(self.table)
        self.table = []
        self._game_over_pending = all(not hand for hand in self.hands)
        # Keep input locked through the pause until start_trick()/advance_turn() decides
        # whose turn it actually is; otherwise a stale awaiting_seat could let the
        # player's hand buttons appear clickable before the next trick has begun.
        self.render()
        # Show the result prominently (over the usual score line) and hold the finished
        # trick on the table for a couple of seconds before clearing it, so there's a
        # clear beat between "here's what just happened" and "the table is clear, go".
        self.info.setText(announcement)
        self.statusBar().showMessage(announcement, 2600)
        QTimer.singleShot(2000, self._after_trick_pause)

    def _after_trick_pause(self) -> None:
        self.last_trick = []
        if self._game_over_pending:
            self.end_game()
        else:
            self.start_trick()

    def end_game(self) -> None:
        self.stats["games"] += 1
        standings = self.scoreboard()
        best = max(score for _, score in standings)
        leaders = [label for label, score in standings if score == best]
        your_label = standings[0][0]
        if your_label in leaders and len(leaders) == 1:
            result = "You win!"
            self.stats["wins"] += 1
        elif your_label in leaders:
            result = "Draw."
            self.stats["draws"] += 1
        else:
            result = f"{leaders[0]} wins."
            self.stats["losses"] += 1
        self.save_stats()
        self.render()
        breakdown = "\n".join(f"{label}: {score}" for label, score in standings)
        QMessageBox.information(self, "Game Over", f"{result}\n\n{breakdown}")

    def set_difficulty(self, level: str) -> None:
        self.difficulty = level
        action = self.difficulty_actions.get(level)
        if action is not None and not action.isChecked():
            action.setChecked(True)
        self.render()

    def show_settings(self) -> None:
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.set_difficulty(dialog.difficulty.currentText())
            self.sounds.enabled = dialog.sound.isChecked()
            self.sounds.set_volume(dialog.volume.value())

    def show_stats(self) -> None:
        QMessageBox.information(self, "Statistics", "\n".join(f"{k.title()}: {v}" for k, v in self.stats.items()))

    def show_about(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("About Briscas")
        box.setTextFormat(Qt.RichText)
        box.setText(
            f"<h2>Briscas {__version__}</h2><p>A classic Spanish-card game against the computer.</p>"
            "<p>The traditional Briscas game rules are public domain.<br>"
            "This software is distributed under the MIT License.</p>"
        )
        icon_pixmap = QPixmap(str(app_icon_path())).scaled(
            128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        box.setIconPixmap(icon_pixmap)
        box.exec_()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Briscas")
    app.setDesktopFileName("com.ericflores.briscas")
    window = BriscasWindow()
    window.show()
    return app.exec_()
