"""Money (v4.11.1): coins and bills to count, total, and make change with (spec 11).

A track of the picture questions in races, beside blocks. Amounts are whole cents in code,
never decimals, so $0.10 + $0.20 is exactly 30 cents. Coins are drawn from public-domain
United States Mint images (``web/coins/``); bills are drawn by code. Standard library only.
"""

from __future__ import annotations

import random
import re
from typing import Any

MAX_LEVEL = 6
COINS = {"penny": 1, "nickel": 5, "dime": 10, "quarter": 25}  # name -> cents
COIN_MM = {"penny": 19.05, "nickel": 21.21, "dime": 17.91, "quarter": 24.26}  # real diameters
QUARTER_PX = 72  # a quarter's width on screen; the others scale from their diameters
COIN_PX = {name: round(QUARTER_PX * mm / COIN_MM["quarter"]) for name, mm in COIN_MM.items()}
BILLS = (1, 5, 20, 100)  # dollars
PAY_WITH = (1, 5, 20)  # bills a change question pays with
TOY = "🎁"  # what's bought when no interest has an emoji
_AMOUNT = re.compile(r"\$?(\d{0,4})(?:\.(\d{0,2}))?\$?")  # "1.35", "$1.5", ".65", "7."
_CENTS = re.compile(r"(\d{1,4})")  # "35"


def cents_typed(text: str, dollars: bool) -> int | None:
    """What was typed, in whole cents; None when it isn't an amount.

    Params:
        text: the typed answer.
        dollars: True to read "1.35" or "$1.35" (dollars); False to read "35" (cents).

    Example:
        >>> cents_typed(" $1.35 ", dollars=True), cents_typed("35", dollars=False)
        (135, 35)
    """
    t = "".join(text[:20].split())  # spaces anywhere don't count
    cents = t.endswith("¢")  # "65¢" is cents, even where dollars are asked
    t = t.removesuffix("¢")
    if not t.isascii():  # only plain digits and signs: never "²" or "३"
        return None
    if dollars and not cents:
        m = _AMOUNT.fullmatch(t)
        if m is None or not (m.group(1) or m.group(2)):  # "$" or "." alone is nothing
            return None
        part = (m.group(2) or "").ljust(2, "0")  # "1.5" is $1.50
        return int(m.group(1) or 0) * 100 + int(part)  # whole cents, never a float
    m = _CENTS.fullmatch(t)
    return int(m.group(1)) if m else None


def say_cents(cents: int, dollars: bool) -> str:
    """An amount as the screen shows it: "35¢", "$26", or "$1.35"."""
    if not dollars:
        return f"{cents}¢"  # coins alone are counted in cents
    whole, rest = divmod(cents, 100)  # whole cents: no rounding, ever
    return f"${whole}" if rest == 0 else f"${whole}.{rest:02d}"  # "$7", never "$7.00"


def _coins_line(names: list[str]) -> str:
    # "2 quarters, a dime, and a penny": how many of each, biggest first
    parts = []
    for name in sorted(set(names), key=lambda n: -COINS[n]):
        n = names.count(name)
        plural = "pennies" if name == "penny" else f"{name}s"
        parts.append(f"a {name}" if n == 1 else f"{n} {plural}")
    line = listing(parts)
    return line[0].upper() + line[1:]  # it starts the sentence


def listing(parts: list[str]) -> str:
    """"a", "a and b", or "a, b, and c"."""
    if len(parts) < 3:
        return " and ".join(parts)
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def question(
    level: int, rng: random.Random, emoji: str = ""
) -> tuple[str, int, dict[str, Any], str, bool]:
    """One money question at ``level``: (prompt, answer in cents, what to draw, how it adds
    up, whether it's answered in dollars).

    Example:
        >>> question(1, random.Random(2))[:2]
        ('This is a penny. How many cents is it worth?', 1)
    """
    kind = min(max(level, 1), MAX_LEVEL)  # a hand-edited level clamped
    draw: dict[str, Any] = {"kind": "money", "coins": [], "bills": [], "price": 0, "item": ""}
    if kind == 1:  # one coin and its worth
        name = rng.choice(list(COINS))
        draw["coins"] = [name]
        return (
            f"This is a {name}. How many cents is it worth?",
            COINS[name],
            draw,
            f"A {name} is {COINS[name]}¢.",
            False,
        )
    if kind == 2:  # a few of one coin
        name = rng.choice(list(COINS))
        coins = [name] * rng.randint(2, 4 if name == "quarter" else 5)  # under a dollar
        total = sum(COINS[c] for c in coins)
        draw["coins"] = coins
        return "How many cents?", total, draw, f"{_coins_line(coins)} make {total}¢.", False
    if kind == 3:  # mixed coins, under a dollar
        while True:  # a few tries for a mix under 100¢
            coins = [rng.choice(list(COINS)) for _ in range(rng.randint(2, 6))]
            if sum(COINS[c] for c in coins) < 100 and len(set(coins)) > 1:
                break
        coins.sort(key=lambda c: -COINS[c])  # biggest first, as people count
        total = sum(COINS[c] for c in coins)
        draw["coins"] = coins
        line = f"{_coins_line(coins)} make {total}¢."
        return "How many cents in all?", total, draw, line, False
    if kind == 4:  # bills only, in whole dollars
        bills = sorted((rng.choice(BILLS) for _ in range(rng.randint(2, 4))), reverse=True)
        total = sum(bills) * 100
        draw["bills"] = bills
        # "$20, $5, and $1": what's added, for after the answer
        listed = listing([f"${b}" for b in bills])
        return ("How many dollars?", total, draw, f"{listed} make {say_cents(total, True)}.", True)
    if kind == 5:  # bills and coins together
        bills = sorted((rng.choice(BILLS[:3]) for _ in range(rng.randint(1, 2))), reverse=True)
        coins = sorted(
            (rng.choice(list(COINS)) for _ in range(rng.randint(1, 3))), key=lambda c: -COINS[c]
        )  # 3 coins at most: 75¢, so "and 35¢" never reaches a dollar
        change = sum(COINS[c] for c in coins)  # the coins' part, under a dollar
        total = sum(bills) * 100 + change  # still whole cents
        draw.update(bills=bills, coins=coins)
        return (
            "How much money? Write it like 1.35",
            total,
            draw,
            f"{say_cents(sum(bills) * 100, True)} and {change}¢ make {say_cents(total, True)}.",
            True,
        )
    paid = rng.choice(PAY_WITH)  # making change: a bill for something cheaper
    # a price from a quarter of the bill up to just under it, in steps of 5¢
    price = rng.randrange(paid * 25 // 5 * 5, paid * 100, 5)
    draw.update(bills=[paid], price=price, item=emoji or TOY)  # the toy: an interest's emoji
    back = paid * 100 - price  # always more than 0
    return (
        f"You pay with ${paid} for a toy that costs {say_cents(price, True)}. How much change? "
        "Write it like 1.35",
        back,
        draw,
        f"${paid} − {say_cents(price, True)} = {say_cents(back, True)}.",
        True,
    )
