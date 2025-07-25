import asyncio
from copy import deepcopy
import random
import re
from pyrogram import Client
from pyrogram.types import Message
from pyrogram import filters
from filters import custom_filters
from app import Client
import logging

from libs.others import delete_message

logger = logging.getLogger("main")

GROUP = -1002022762746
BOT = 7124396542
MAX_BONUS = 100000
MAX_LOSE_TIME = 0
lose_time = 0
AUTO = False
ALL_CARDS = [
    f"{rank}{suit}"
    for rank in [
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "J",
        "Q",
        "K",
        "A",
    ]
    for suit in ["♠", "♥", "♦", "♣"]
]


class Deck:
    def __init__(self, dealer_cards: list[str], player_cards: list[str]):
        self.dealer_hand = deepcopy(dealer_cards)
        self.player_hand = deepcopy(player_cards)
        self.shuffle_card()
        while (card := self.guess_dealer_first_card()) == False:
            self.shuffle_card()
        self.dealer_hand = [card] + self.dealer_hand
        while self.dealer_hand_value() < 17:
            self.dealer_draw()
        logger.debug(f"dealer:{self.dealer_hand}")
        self.dealer_value = self.dealer_hand_value()

    def shuffle_card(self):
        self.cards = deepcopy(ALL_CARDS)
        for card in self.dealer_hand + self.player_hand:
            self.cards.remove(card)
        random.shuffle(self.cards)

    def guess_dealer_first_card(self):
        card = self.cards[-1]
        if len(self.dealer_hand) > 1:
            if self.calculate_hand_value([card] + self.dealer_hand[:-1]) > 16:
                return False
        if len(self.player_hand) - len(self.dealer_hand) > 1:
            if self.calculate_hand_value([card] + self.dealer_hand) < 17:
                return False
        self.cards.remove(card)
        return card

    def add(self):
        sub_0 = -1
        self.player_draw()
        while ((sub := self.calculate_result()) < 1) and (
            self.calculate_hand_value(self.player_hand) < 21
        ):
            if sub == 0:
                sub_0 = sub
            self.player_draw()
        logger.debug(f"player{self.player_hand}")
        return max(self.calculate_result(), sub_0)

    def draw_card(self):
        if self.cards:
            return self.cards.pop()
        else:
            return None

    def dealer_draw(self):
        card = self.draw_card()
        if card:
            self.dealer_hand.append(card)
        return card

    def player_draw(self):
        card = self.draw_card()
        if card:
            self.player_hand.append(card)
        return card

    def calculate_hand_value(self, hand):
        value = 0
        aces = 0
        for card in hand:
            rank = card[:-1]
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                aces += 1
                value += 11
            else:
                value += int(rank)

        while value > 21 and aces:
            value -= 10
            aces -= 1

        return value

    def dealer_hand_value(self):
        return self.calculate_hand_value(self.dealer_hand)

    def player_hand_value(self):
        return self.calculate_hand_value(self.player_hand)

    def calculate_result(self):
        dealer_value = self.dealer_value
        player_value = self.player_hand_value()
        if player_value == dealer_value:
            if player_value == 21:
                if len(self.player_hand) == 2 and len(self.dealer_hand) == 2:
                    return 0
                elif len(self.player_hand) == 2:
                    return 1
                elif len(self.dealer_hand) == 2:
                    return -1
            return 0
        elif player_value > 21 and dealer_value > 21:
            if len(self.dealer_hand)>len(self.player_hand):
                return -1
            return 0
        elif player_value > 21:
            return -1
        elif dealer_value > 21:
            return 1
        elif player_value > dealer_value:
            return 1
        elif player_value < dealer_value:
            return -1
        else:
            return 0


@Client.on_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄：\?\?\? ((?:[0-9JQKA]*.\s*)+)\n你\d+点：((?:[0-9JQKA]*.\s*)+)")
)
@Client.on_edited_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄：\?\?\? ((?:[0-9JQKA]*.\s*)+)\n你\d+点：((?:[0-9JQKA]*.\s*)+)")
)
async def blackjack(client: Client, message: Message):
    logger.info(message.text)
    match = message.matches[0]
    dealer_cards = match.group(1).split(" ")
    player_cards = match.group(2).split(" ")

    add_value = 0
    done_value = 0
    total_simulations = 1000

    for _ in range(total_simulations):
        deck = Deck(dealer_cards, player_cards)
        done_value += deck.calculate_result()
        add_value += deck.add()
    logger.info(f"{add_value}:{done_value}")
    await asyncio.sleep(1)
    if add_value >= done_value:
        await client.request_callback_answer(message.chat.id, message.id, "add")
    else:
        await client.request_callback_answer(message.chat.id, message.id, "done")


@Client.on_message(filters.command("xd21") & filters.me)
async def xd21(client: Client, message: Message):
    global AUTO, MAX_BONUS, MAX_LOSE_TIME

    if message.command[1] == "on":
        AUTO = True
        MAX_BONUS = int(message.command[2]) if len(message.command) > 2 else MAX_BONUS
        MAX_LOSE_TIME = (
            int(message.command[3]) if len(message.command) > 3 else MAX_LOSE_TIME
        )
        delete_message(await message.edit("21点启动"), 5)
        await client.send_message(
            message.chat.id,
            f"/blackjack@PTVicomoBot {int(MAX_BONUS/(2**MAX_LOSE_TIME))}",
        )
    else:
        AUTO = False
        delete_message(await message.edit("21点关闭"), 5)


@Client.on_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄.*?你(输|赢)了", re.DOTALL)
)
@Client.on_edited_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄.*?你(输|赢)了", re.DOTALL)
)
async def end_game(client: Client, message: Message):
    match = message.matches[0]
    x = match.group(1)
    global lose_time
    if x == "赢":
        lose_time = 0
    else:
        lose_time = min(lose_time + 1, MAX_LOSE_TIME)
    bonus = int(MAX_BONUS / (2 ** (MAX_LOSE_TIME - lose_time)))
    if AUTO:
        await asyncio.sleep(2)
        await client.send_message(
            message.chat.id,
            f"/blackjack@PTVicomoBot {bonus}",
        )


@Client.on_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄.*?平局", re.DOTALL)
)
@Client.on_edited_message(
    (custom_filters.reply_to_me | filters.private)
    & filters.regex(r"庄.*?平局", re.DOTALL)
)
async def next_game(client: Client, message: Message):
    bonus = int(MAX_BONUS / (2 ** (MAX_LOSE_TIME - lose_time)))
    if AUTO:
        await asyncio.sleep(2)
        await client.send_message(
            message.chat.id,
            f"/blackjack@PTVicomoBot {bonus}",
        )
