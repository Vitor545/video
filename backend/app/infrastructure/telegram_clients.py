"""
Cache compartilhado de TelegramClient por session_path.

Todo módulo que precisa de um client (sync, downloads, auth) usa get_client(),
garantindo que apenas UM TelegramClient por session SQLite seja aberto por vez.
Evita 'database is locked' quando sync e download rodam simultaneamente.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)

_clients: dict[str, object] = {}
_locks: dict[str, asyncio.Lock] = {}


async def get_client(api_id: int, api_hash: str, session_path: str):
    """Retorna um TelegramClient conectado e autorizado, reutilizando se já existir."""
    from telethon import TelegramClient

    if session_path not in _locks:
        _locks[session_path] = asyncio.Lock()

    async with _locks[session_path]:
        client = _clients.get(session_path)
        if client is not None and client.is_connected():
            if await client.is_user_authorized():
                return client
            else:
                # Sessão expirou — descarta e refaz
                try:
                    await client.disconnect()
                except Exception:
                    pass
                _clients.pop(session_path, None)

        logger.info("Conectando TelegramClient para session: %s", session_path)
        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            raise RuntimeError(
                "Sessão Telegram não autenticada ou expirada. "
                "Execute o processo de autenticação antes de sincronizar."
            )
        _clients[session_path] = client
        return client


async def release_all() -> None:
    """Desconecta todos os clients (chamar em shutdown)."""
    for path, client in list(_clients.items()):
        try:
            await client.disconnect()
        except Exception:
            pass
    _clients.clear()
