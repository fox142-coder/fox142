import time

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

import keyboards as kb
import storage
import payments
import vpn
from config import config
from plans import PLANS

router = Router()


def _fmt_date(ts: int) -> str:
    return time.strftime("%d.%m.%Y", time.localtime(ts))


HELP_TEXT = (
    "❓ <b>Помощь</b>\n\n"
    "После оплаты бот сразу выдаёт ключ — вставь его в приложение VLESS "
    "(v2rayNG на Android, Streisand на iOS).\n\n"
    "Остались вопросы? Напиши в поддержку: @fayzee142"
)


def _subs_text(user_id: int) -> str:
    subs = storage.get_subscriptions(user_id)
    if not subs:
        return "🔑 У тебя пока нет подписок.\n\nКупи VPN в меню."
    text = "🔑 <b>Твои подписки:</b>\n\n"
    for s in subs:
        text += (
            f"• <b>{s['title']}</b> (до {_fmt_date(s['expires_at'])})\n"
            f"<code>{s['config']}</code>\n\n"
        )
    return text


# ---------- Команды ----------

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 <b>Привет!</b>\n\n"
        "Это бот для покупки VPN.\n"
        "Выбери действие в меню ниже или кнопками под чатом.",
        reply_markup=kb.reply_main(),   # кнопки быстрого доступа под чатом
    )
    await message.answer("Главное меню:", reply_markup=kb.main_menu())


@router.message(Command("buy"))
async def cmd_buy(message: Message):
    await message.answer("🛒 <b>Выбери тариф:</b>", reply_markup=kb.plans_menu())


@router.message(Command("subs"))
async def cmd_subs(message: Message):
    await message.answer(_subs_text(message.from_user.id), reply_markup=kb.back_to_main())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=kb.help_menu())


# ---------- Нажатия на кнопки быстрого доступа (под чатом) ----------

@router.message(F.text == kb.BTN_BUY)
async def btn_buy(message: Message):
    await message.answer("🛒 <b>Выбери тариф:</b>", reply_markup=kb.plans_menu())


@router.message(F.text == kb.BTN_SUBS)
async def btn_subs(message: Message):
    await message.answer(_subs_text(message.from_user.id), reply_markup=kb.back_to_main())


@router.message(F.text == kb.BTN_HELP)
async def btn_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=kb.help_menu())


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
    await call.message.edit_text(HELP_TEXT, reply_markup=kb.help_menu())
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
           if not config.provider_token
           else "Нажми «Оплатить» — доступна оплата картой и по СБП."),
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

    # Если подключён провайдер (ЮKassa) — отправляем реальный счёт.
    # В окне оплаты появится выбор: карта / СБП / QR (если СБП включён в кабинете).
    if config.provider_token:
        await payments.send_plan_invoice(call.message, plan_key, plan)
        await call.answer()
        return

    # Иначе — оплата не подключена: сразу выдаём ключ.
    # Если настроена панель (XUI_HOST) — ключ будет настоящим, иначе тестовым.
    try:
        sub = await vpn.issue_subscription(call.from_user.id, plan_key, plan)
    except Exception as e:
        await call.message.edit_text(
            "⚠️ Не удалось создать ключ. Попробуй позже или напиши в поддержку.",
            reply_markup=kb.back_to_main(),
        )
        await call.answer()
        return

    await call.message.edit_text(
        "✅ <b>Готово!</b>\n\n"
        f"Тариф: <b>{plan['title']}</b>\n"
        f"Действует до: {_fmt_date(sub['expires_at'])}\n\n"
        "Твой ключ (вставь в приложение VLESS):\n"
        f"<code>{sub['config']}</code>",
        reply_markup=kb.back_to_main(),
    )
    await call.answer("Готово ✅")
