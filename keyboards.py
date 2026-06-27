from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from plans import PLANS


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🛒 Купить VPN", callback_data="menu:buy")
    kb.button(text="🔑 Мои подписки", callback_data="menu:subs")
    kb.button(text="❓ Помощь", callback_data="menu:help")
    kb.adjust(1)
    return kb.as_markup()


def plans_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, plan in PLANS.items():
        kb.button(
            text=f"{plan['title']} — {plan['price']} ₽",
            callback_data=f"plan:{key}",
        )
    kb.button(text="⬅️ Назад", callback_data="menu:main")
    kb.adjust(1)
    return kb.as_markup()


def plan_detail_menu(plan_key: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Оплатить", callback_data=f"pay:{plan_key}")
    kb.button(text="⬅️ К тарифам", callback_data="menu:buy")
    kb.adjust(1)
    return kb.as_markup()


def back_to_main() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ В меню", callback_data="menu:main")
    return kb.as_markup()
