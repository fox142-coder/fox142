"""
Простейшее хранилище в памяти. При перезапуске бота данные обнуляются.

В продакшене замени на нормальную БД (SQLite / PostgreSQL).
Структура остаётся та же, поэтому переезд будет лёгким.
"""

import time
import uuid

# user_id -> {"subscriptions": [ {...}, ... ]}
_users: dict[int, dict] = {}


def get_user(user_id: int) -> dict:
    return _users.setdefault(user_id, {"subscriptions": []})


def add_subscription(user_id: int, plan_key: str, plan: dict) -> dict:
    """Создаёт подписку и тестовый VPN-конфиг."""
    now = int(time.time())
    expires = now + plan["days"] * 86400

    # ЗАГЛУШКА конфига. В реальном боте здесь вызов API панели
    # (Marzban / 3x-ui / Outline и т.п.), который вернёт настоящий ключ.
    fake_uuid = uuid.uuid4()
    config_link = (
        f"vless://{fake_uuid}@your-domain.com:443"
        f"?type=tcp&security=reality&sni=your-domain.com#TEST-{plan_key}"
    )

    sub = {
        "id": str(uuid.uuid4())[:8],
        "plan_key": plan_key,
        "title": plan["title"],
        "created_at": now,
        "expires_at": expires,
        "config": config_link,
    }
    get_user(user_id)["subscriptions"].append(sub)
    return sub


def get_subscriptions(user_id: int) -> list[dict]:
    return get_user(user_id)["subscriptions"]
