import random
import unittest

from briscas.game import Card, make_deck, winner_of_trick


class GameRulesTest(unittest.TestCase):
    def test_deck_has_40_unique_cards(self):
        deck = make_deck(random.Random(1))
        self.assertEqual(40, len(deck))
        self.assertEqual(40, len(set(deck)))

    def test_higher_same_suit_wins(self):
        self.assertEqual(1, winner_of_trick(Card(7, "oro"), Card(3, "oro"), "copa"))

    def test_trump_wins(self):
        self.assertEqual(1, winner_of_trick(Card(1, "oro"), Card(2, "copa"), "copa"))

    def test_off_suit_does_not_win(self):
        self.assertEqual(0, winner_of_trick(Card(2, "oro"), Card(1, "espada"), "copa"))


if __name__ == "__main__":
    unittest.main()
