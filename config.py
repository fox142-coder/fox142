import os
from dataclasses import dataclass


def _load_dotenv(path: str = ".env") -> None:
    """Минимальная загрузка .env без сторонних библиотек."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


@dataclass
class Config:
    # Токен от @BotFather — обязателен
    bot_token: str = os.getenv("BOT_TOKEN", "")

    # ID администратора (твой Telegram ID) — для команды /admin
    admin_id: int = int(os.getenv("ADMIN_ID", "0") or 0)

    # Тестовый режим: оплата эмулируется, реальные деньги не списываются
    test_mode: bool = os.getenv("TEST_MODE", "true").lower() == "true"

    # --- Оплата (СБП / карты через провайдера, напр. ЮKassa) ---
    # Получается в @BotFather: бот -> Payments -> Connect ЮKassa.
    # Если пусто -> используется тестовая заглушка (бот всё равно работает).
    provider_token: str = os.getenv("PROVIDER_TOKEN", "")
    currency: str = os.getenv("CURRENCY", "RUB")

    # --- Режим работы ---
    # false -> long polling (домен НЕ нужен, удобно для теста)
    # true  -> webhook (нужен свой домен + SSL)
    use_webhook: bool = os.getenv("USE_WEBHOOK", "false").lower() == "true"

    # Только для webhook-режима:
    webhook_host: str = os.getenv("WEBHOOK_HOST", "")        # https://your-domain.com
    webhook_path: str = os.getenv("WEBHOOK_PATH", "/webhook")
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "change-me")
    webapp_host: str = os.getenv("WEBAPP_HOST", "0.0.0.0")
    webapp_port: int = int(os.getenv("WEBAPP_PORT", "8080") or 8080)

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_host}{self.webhook_path}"


config = Config()
