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
from .game import Card, ai_choose, make_deck, winner_of_trick


def data_root() -> Path:
    override = os.environ.get("BRISCAS_DATA_DIR")
    if override:
        return Path(override)
    installed = Path("/usr/share/games/briscas")
    if installed.is_dir():
        return installed
    return Path(__file__).resolve().parents[2] / "assets"


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


class BriscasWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"Briscas {__version__}")
        self.setMinimumSize(980, 680)
        icon = Path("/usr/share/icons/hicolor/1024x1024/apps/com.ericflores.briscas.png")
        self.setWindowIcon(QIcon(str(icon if icon.exists() else data_root() / "cards" / "posterior.png")))
        self.difficulty = "medium"
        self.sounds = SoundBank()
        self.stats = self.load_stats()
        self.deck: list[Card] = []
        self.player_hand: list[Card] = []
        self.cpu_hand: list[Card] = []
        self.trump = "oro"
        self.trump_card: Card | None = None
        self.leader = "player"
        self.table: list[tuple[str, Card]] = []
        self.last_trick: list[tuple[str, Card]] = []
        self.player_score = self.cpu_score = 0
        self.locked = False
        self.card_buttons: list[QPushButton] = []
        self.build_ui()
        self.new_game()

    def build_ui(self) -> None:
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
        self.info.setStyleSheet("font-size: 18px; font-weight: bold; padding: 8px")
        layout.addWidget(self.info)
        cpu_row = QHBoxLayout()
        cpu_row.addStretch()
        self.cpu_title = QLabel("Computer:")
        self.cpu_title.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        cpu_row.addWidget(self.cpu_title)
        self.cpu_card_labels: list[QLabel] = []
        card_back = QPixmap(str(data_root() / "cards" / "posterior.png")).scaled(
            54, 82, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        for _ in range(3):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(60, 88)
            label.setPixmap(card_back)
            cpu_row.addWidget(label)
            self.cpu_card_labels.append(label)
        cpu_row.addStretch()
        layout.addLayout(cpu_row)
        table = QHBoxLayout()
        self.lead_caption = QLabel("Lead")
        self.trump_caption = QLabel("Trump")
        self.reply_caption = QLabel("Reply")
        self.lead_card = QLabel("Lead")
        self.trump_card_label = QLabel("Trump Card")
        self.reply_card = QLabel("Reply")
        for caption, label in (
            (self.lead_caption, self.lead_card),
            (self.trump_caption, self.trump_card_label),
            (self.reply_caption, self.reply_card),
        ):
            caption.setAlignment(Qt.AlignCenter)
            caption.setStyleSheet("font-weight: bold; font-size: 13px; color: #f7e7bd;")
            label.setAlignment(Qt.AlignCenter)
            label.setFixedSize(180, 270)
            label.setStyleSheet("border: 2px solid #a58850; background: #174f2a; color: white")
            column = QVBoxLayout()
            column.addWidget(caption)
            column.addWidget(label)
            table.addLayout(column)
        self.trump_card_label.setStyleSheet(
            "border: 3px solid #e2b84c; background: #174f2a; color: #f7e7bd; font-weight: bold"
        )
        layout.addLayout(table)
        self.player_title = QLabel("You:")
        self.player_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.player_title)
        self.hand_row = QHBoxLayout()
        layout.addLayout(self.hand_row)
        self.setCentralWidget(root)
        self.setStatusBar(QStatusBar())
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
        self.deck = make_deck()
        self.player_hand = [self.deck.pop() for _ in range(3)]
        self.cpu_hand = [self.deck.pop() for _ in range(3)]
        self.trump_card = self.deck[0]
        self.trump = self.trump_card.suit
        self.leader = "player"
        self.table = []
        self.last_trick = []
        self.player_score = self.cpu_score = 0
        self.locked = False
        self.sounds.play("shuffle")
        self.render()

    def render(self) -> None:
        self.info.setText(
            f"Trump: {self.trump.title()}   You: {self.player_score}   "
            f"CPU: {self.cpu_score}   Cards left: {len(self.deck)}   "
            f"Difficulty: {self.difficulty.title()}"
        )
        for index, label in enumerate(self.cpu_card_labels):
            label.setVisible(index < len(self.cpu_hand))
        self.render_trump_card()
        self.render_table()
        for button in self.card_buttons:
            self.hand_row.removeWidget(button)
            button.deleteLater()
        self.card_buttons = []
        for index, card in enumerate(self.player_hand):
            button = QPushButton()
            button.setIcon(QIcon(self.card_pixmap(card)))
            button.setIconSize(self.card_pixmap(card).size())
            button.setFixedSize(165, 255)
            button.setEnabled(not self.locked and self.leader == "player")
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
        """Render table cards from state so a hand refresh cannot erase them."""
        visible = self.table or self.last_trick
        roles = ("Lead", "Reply")
        labels = (self.lead_card, self.reply_card)
        captions = (self.lead_caption, self.reply_caption)
        for index, (label, caption, role) in enumerate(zip(labels, captions, roles)):
            label.setPixmap(QPixmap())
            if index < len(visible):
                owner, card = visible[index]
                self.show_table_card(label, card)
                owner_text = "Your" if owner == "player" else "Computer's"
                caption.setText(f"{owner_text} {role}")
            else:
                label.setText(role)
                caption.setText(role)

    def show_table_card(self, label: QLabel, card: Card) -> None:
        label.setText("")
        label.setPixmap(self.card_pixmap(card, 170, 260))

    def player_play(self, index: int) -> None:
        if self.locked or index >= len(self.player_hand):
            return
        self.locked = True
        card = self.player_hand.pop(index)
        if self.table and self.table[0][0] == "computer":
            self.table.append(("player", card))
            self.show_table_card(self.reply_card, card)
            self.sounds.play("play")
            self.render()
            QTimer.singleShot(700, self.finish_trick)
            return
        self.table = [("player", card)]
        self.last_trick = []
        self.show_table_card(self.lead_card, card)
        self.sounds.play("play")
        self.render()
        QTimer.singleShot(550, self.cpu_reply)

    def cpu_reply(self) -> None:
        lead = self.table[0][1]
        card = self.cpu_hand.pop(ai_choose(self.cpu_hand, lead, self.trump, self.difficulty))
        self.table.append(("computer", card))
        self.show_table_card(self.reply_card, card)
        QTimer.singleShot(700, self.finish_trick)

    def finish_trick(self) -> None:
        lead_owner, lead = self.table[0]
        _, reply = self.table[1]
        reply_wins = winner_of_trick(lead, reply, self.trump) == 1
        if reply_wins:
            winner = "computer" if lead_owner == "player" else "player"
        else:
            winner = lead_owner
        points = lead.points + reply.points
        if winner == "player":
            self.player_score += points
        else:
            self.cpu_score += points
        self.leader = winner
        self.sounds.play("trick")
        if winner == "player":
            self.statusBar().showMessage(f"You win the trick! +{points} points", 3000)
        else:
            self.statusBar().showMessage(f"Computer wins the trick. +{points} points for the computer.", 3000)
        if self.deck:
            first = self.deck.pop()
            second = self.deck.pop() if self.deck else None
            if winner == "player":
                self.player_hand.append(first)
                if second:
                    self.cpu_hand.append(second)
            else:
                self.cpu_hand.append(first)
                if second:
                    self.player_hand.append(second)
        self.last_trick = list(self.table)
        self.table = []
        self.locked = False
        if not self.player_hand and not self.cpu_hand:
            self.end_game()
        elif self.leader == "computer":
            self.render()
            QTimer.singleShot(650, self.cpu_lead)
        else:
            self.render()

    def cpu_lead(self) -> None:
        self.locked = True
        card = self.cpu_hand.pop(ai_choose(self.cpu_hand, None, self.trump, self.difficulty))
        self.table = [("computer", card)]
        self.last_trick = []
        self.show_table_card(self.lead_card, card)
        self.locked = False
        self.render()
        for button in self.card_buttons:
            button.setEnabled(True)

    def end_game(self) -> None:
        self.stats["games"] += 1
        if self.player_score > self.cpu_score:
            result = "You win!"
            self.stats["wins"] += 1
        elif self.player_score < self.cpu_score:
            result = "Computer wins."
            self.stats["losses"] += 1
        else:
            result = "Draw."
            self.stats["draws"] += 1
        self.save_stats()
        self.render()
        QMessageBox.information(self, "Game Over", f"{result}\nFinal score: {self.player_score}–{self.cpu_score}")

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
        QMessageBox.about(
            self, "About Briscas",
            f"<h2>Briscas {__version__}</h2><p>A classic Spanish-card game against the computer.</p>"
            "<p>The traditional Briscas game rules are public domain.<br>"
            "This software is distributed under the MIT License.</p>",
        )


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Briscas")
    app.setDesktopFileName("com.ericflores.briscas")
    window = BriscasWindow()
    window.show()
    return app.exec_()
