"""等待用户回填授权码的会话。

落雪和水鱼的绑定都是「BOT 先发起，用户再把一串码发回来」，两边都要回答
同一个问题：**这串码是不是发起绑定的那个人发回来的**。会话按
`(self_id, user_id)` 记，这个键本身就是那道约束——别人发的码落不到这条
记录上，也就走不进兑换那一步。

记录里同时存着是哪个服务在等码。两家的码长得一样（都是 `XXXX-XXXX-XXXX`），
不记服务的话，水鱼的确认码会被落雪的处理器接走，反之亦然。

一个用户同一时刻只保留一条：他发起新的绑定，就是不再继续上一条。
"""

from collections.abc import Callable
from time import monotonic

from .merge.models import ServiceName


class PendingBindingStore:
    def __init__(
        self,
        ttl: float = 10 * 60,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self.ttl = ttl
        self._clock = clock
        self._sessions: dict[tuple[int, int], tuple[ServiceName, float]] = {}

    def start(
        self,
        self_id: int,
        user_id: int,
        service: ServiceName,
        *,
        ttl: float | None = None,
    ) -> None:
        """记下这个用户正在等哪一家的码

        `ttl` 不填就用默认值。水鱼那条路要单独给：它的窗口是两段接起来的，
        见 `commands.mai_base.DIVINGFISH_SESSION_TTL`。
        """
        now = self._clock()
        self._clear_expired(now)
        self._sessions[(self_id, user_id)] = (service, now + (ttl or self.ttl))

    def active(self, self_id: int, user_id: int) -> ServiceName | None:
        """这个用户此刻在等哪一家的码，没有则返回 None"""
        now = self._clock()
        self._clear_expired(now)
        session = self._sessions.get((self_id, user_id))
        return session[0] if session else None

    def is_active(self, self_id: int, user_id: int, service: ServiceName) -> bool:
        return self.active(self_id, user_id) == service

    def consume(self, self_id: int, user_id: int) -> bool:
        now = self._clock()
        self._clear_expired(now)
        return self._sessions.pop((self_id, user_id), None) is not None

    def discard(self, self_id: int, user_id: int) -> None:
        self._sessions.pop((self_id, user_id), None)

    def _clear_expired(self, now: float) -> None:
        expired = [
            key
            for key, (_, expires_at) in self._sessions.items()
            if expires_at <= now
        ]
        for key in expired:
            del self._sessions[key]
