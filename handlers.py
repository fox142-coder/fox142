import time

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

import keyboards as kb
import storage
from config import config
from plans import PLANS

router = Router()


def _fmt_date(ts: int) -> str:
    return time.strftime("%d.%m.%Y", time.localtime(ts))


# ---------- Команды ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Это бот для покупки VPN.\n"
        "Выбери действие в меню ниже.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != config.admin_id:
        await message.answer("⛔ Команда только для администратора.")
        return
    total_users = len(storage._users)
    total_subs = sum(len(u["subscriptions"]) for u in storage._users.values())
    await message.answer(
        f"📊 <b>Статистика</b>\n"
        f"Пользователей: {total_users}\n"
        f"Подписок выдано: {total_subs}\n"
        f"Тестовый режим: {'да' if config.test_mode else 'нет'}"
    )


# ---------- Главное меню ----------

@router.callback_query(F.data == "menu:main")
async def show_main(call: CallbackQuery):
    await call.message.edit_text(
        "Главное меню. Выбери действие:",
        reply_markup=kb.main_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "menu:buy")
async def show_plans(call: CallbackQuery):
    await call.message.edit_text(
        "🛒 <b>Выбери тариф:</b>",
        reply_markup=kb.plans_menu(),
    )
    await call.answer()


@router.callback_query(F.data == "menu:help")
async def show_help(call: CallbackQuery):
    await call.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "После оплаты бот выдаёт ключ-конфиг.\n"
        "Вопросы — пиши в поддержку: @your_support",
        reply_markup=kb.back_to_main(),
    )
    await call.answer()


@router.callback_query(F.data == "menu:subs")
async def show_subs(call: CallbackQuery):
    subs = storage.get_subscriptions(call.from_user.id)
    if not subs:
        await call.message.edit_text(
            "🔑 У тебя пока нет подписок.\n\nКупи VPN в меню.",
            reply_markup=kb.back_to_main(),
        )
        await call.answer()
        return

    text = "🔑 <b>Твои подписки:</b>\n\n"
    for s in subs:
        text += (
            f"• <b>{s['title']}</b> (до {_fmt_date(s['expires_at'])})\n"
            f"<code>{s['config']}</code>\n\n"
        )
    await call.message.edit_text(text, reply_markup=kb.back_to_main())
    await call.answer()


# ---------- Выбор тарифа ----------

@router.callback_query(F.data.startswith("plan:"))
async def show_plan_detail(call: CallbackQuery):
    plan_key = call.data.split(":", 1)[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await call.answer("Тариф не найден", show_alert=True)
        return

    await call.message.edit_text(
        f"📦 <b>{plan['title']}</b>\n\n"
        f"Срок: {plan['days']} дней\n"
        f"Цена: <b>{plan['price']} ₽</b>\n\n"
        + ("🧪 <i>Тестовый режим: оплата эмулируется.</i>"
           if config.test_mode else "Нажми «Оплатить» для перехода к оплате."),
        reply_markup=kb.plan_detail_menu(plan_key),
    )
    await call.answer()


# ---------- Оплата ----------

@router.callback_query(F.data.startswith("pay:"))
async def process_payment(call: CallbackQuery):
    plan_key = call.data.split(":", 1)[1]
    plan = PLANS.get(plan_key)
    if not plan:
        await call.answer("Тариф не найден", show_alert=True)
        return

    if config.test_mode:
        # === ТЕСТ: эмулируем успешную оплату ===
        sub = storage.add_subscription(call.from_user.id, plan_key, plan)
        await call.message.edit_text(
            "✅ <b>Оплата прошла (тест)!</b>\n\n"
            f"Тариф: <b>{plan['title']}</b>\n"
            f"Действует до: {_fmt_date(sub['expires_at'])}\n\n"
            "Твой ключ:\n"
            f"<code>{sub['config']}</code>",
            reply_markup=kb.back_to_main(),
        )
        await call.answer("Готово ✅")
    else:
        # === ПРОДАКШЕН ===
        # Здесь подключи реальную оплату:
        #  - Telegram Payments (bot.send_invoice / provider_token)
        #  - YooKassa, CryptoBot, и т.п.
        # После подтверждения оплаты вызови storage.add_subscription(...)
        await call.message.edit_text(
            "💳 Здесь будет реальная оплата.\n"
            "Подключи платёжный провайдер в handlers.py.",
            reply_markup=kb.back_to_main(),
        )
        await call.answer()
