"""
Модуль оплаты через СБП (и карты) для Telegram-бота.

Как это работает:
  • СБП в Telegram принимается через платёжного провайдера (ЮKassa и т.п.).
  • В @BotFather: твой бот → Payments → подключаешь ЮKassa → получаешь PROVIDER_TOKEN.
  • Сам СБП включается в кабинете ЮKassa отдельной настройкой. После этого
    в окне оплаты у пользователя автоматически появляется выбор: карта / СБП / QR.
  • В коде это обычный «счёт» (invoice): отправляем счёт -> ловим pre_checkout
    -> ловим successful_payment -> выдаём подписку.

Важно:
  • Оплата через бота работает ТОЛЬКО в мобильном приложении Telegram
    (не в десктопе и не в вебе).
  • Сумма в счёте указывается в КОПЕЙКАХ (price * 100).
  • Для теста в @BotFather есть "Connect ЮKassa Test" — даёт тестовый
    PROVIDER_TOKEN и тестовую карту, СБП в тесте может быть недоступен.
  • Для реальных платежей по закону нужны самозанятость/ИП и онлайн-касса
    (фискализация). Тогда понадобится передавать чек (receipt) в invoice.
"""

import time

from aiogram import Router, F
from aiogram.types import (
    Message,
    LabeledPrice,
    PreCheckoutQuery,
)

import keyboards as kb
import storage
from config import config
from plans import PLANS

payments_router = Router()


def _fmt_date(ts: int) -> str:
    return time.strftime("%d.%m.%Y", time.localtime(ts))


async def send_plan_invoice(message: Message, plan_key: str, plan: dict) -> None:
    """Отправляет счёт на оплату. СБП появится как способ оплаты,
    если он включён в кабинете провайдера."""
    prices = [
        LabeledPrice(label=plan["title"], amount=plan["price"] * 100)  # копейки!
    ]
    await message.answer_invoice(
        title=f"VPN — {plan['title']}",
        description=f"Доступ к VPN на {plan['days']} дней",
        payload=f"plan:{plan_key}",          # вернётся к нам после оплаты
        provider_token=config.provider_token,
        currency=config.currency,            # "RUB"
        prices=prices,
        # --- если включена фискализация (онлайн-касса), раскомментируй: ---
        # need_email=True,
        # send_email_to_provider=True,
        # provider_data='{"receipt": {...}}',  # формат чека см. в доках провайдера
    )


# Шаг 1: Telegram спрашивает «всё ли ок с заказом» перед списанием.
# Нужно ответить ok=True в течение 10 секунд, иначе оплата отменится.
@payments_router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


# Шаг 2: оплата прошла — выдаём подписку.
@payments_router.message(F.successful_payment)
async def on_successful_payment(message: Message):
    sp = message.successful_payment
    payload = sp.invoice_payload                 # "plan:month_1"
    plan_key = payload.split(":", 1)[1] if ":" in payload else payload
    plan = PLANS.get(plan_key)

    if not plan:
        await message.answer("Оплата получена, но тариф не распознан. Напиши в поддержку.")
        return

    sub = storage.add_subscription(message.from_user.id, plan_key, plan)

    # provider_payment_charge_id — номер транзакции у провайдера, полезно сохранить
    charge_id = sp.provider_payment_charge_id

    await message.answer(
        "✅ <b>Оплата получена!</b>\n\n"
        f"Тариф: <b>{plan['title']}</b>\n"
        f"Действует до: {_fmt_date(sub['expires_at'])}\n"
        f"Способ оплаты: СБП / карта\n\n"
        "Твой ключ:\n"
        f"<code>{sub['config']}</code>\n\n"
        f"<i>Чек № {charge_id}</i>",
        reply_markup=kb.back_to_main(),
    )
