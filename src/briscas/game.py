from __future__ import annotations

import random
from dataclasses import dataclass

SUITS = ("oro", "copa", "espada", "bastos")
RANKS = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)
STRENGTH = {rank: value for value, rank in enumerate((2, 4, 5, 6, 7, 10, 11, 12, 3, 1))}
POINTS = {1: 11, 3: 10, 12: 4, 11: 3, 10: 2}


@dataclass(frozen=True)
class Card:
    rank: int
    suit: str

    @property
    def points(self) -> int:
        return POINTS.get(self.rank, 0)


def make_deck(rng: random.Random | None = None) -> list[Card]:
    deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
    (rng or random).shuffle(deck)
    return deck


def winner_of_trick(lead: Card, reply: Card, trump: str) -> int:
    """Return 0 when the lead wins and 1 when the reply wins."""
    if reply.suit == lead.suit:
        return int(STRENGTH[reply.rank] > STRENGTH[lead.rank])
    if reply.suit == trump and lead.suit != trump:
        return 1
    return 0


def winner_index(plays: list[Card], trump: str) -> int:
    """Return the index within plays of the card that wins the trick, for any number of players."""
    best = 0
    for i in range(1, len(plays)):
        if winner_of_trick(plays[best], plays[i], trump) == 1:
            best = i
    return best


def ai_choose(hand: list[Card], trick: list[Card], trump: str, difficulty: str) -> int:
    """Choose a card index to play. trick holds the cards already played this trick (empty if leading)."""
    if difficulty == "easy":
        return random.randrange(len(hand))
    if not trick:
        key = lambda c: (c.points + (5 if c.suit == trump else 0), STRENGTH[c.rank])
        return min(range(len(hand)), key=lambda i: key(hand[i]))
    winners = [
        i for i, card in enumerate(hand)
        if winner_index(trick + [card], trump) == len(trick)
    ]
    if winners:
        return min(winners, key=lambda i: (hand[i].points, STRENGTH[hand[i].rank]))
    if difficulty == "hard":
        return min(range(len(hand)), key=lambda i: (hand[i].points, hand[i].suit == trump))
    return random.randrange(len(hand))
