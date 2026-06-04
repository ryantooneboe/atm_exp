from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, List, Tuple


@dataclass
class ATM:
    """
    Simple ATM business logic model.

    Currency values are represented as integer GBP amounts (e.g., 100 == £100).
    """

    pin: str
    initial_balance_gbp: int
    now_provider: Callable[[], datetime] = datetime.utcnow
    _is_authenticated: bool = field(default=False, init=False)
    _failed_attempts: int = field(default=0, init=False)
    _withdrawals: List[Tuple[datetime, int]] = field(default_factory=list, init=False)

    DAILY_LIMIT_GBP: int = 1000
    WITHDRAWAL_MULTIPLE_GBP: int = 20
    MAX_PIN_ATTEMPTS: int = 3

    def __post_init__(self) -> None:
        if not (self.pin.isdigit() and len(self.pin) == 4):
            raise ValueError("PIN must be a 4-digit string")
        if self.initial_balance_gbp < 0:
            raise ValueError("Initial balance cannot be negative")
        self._balance_gbp = self.initial_balance_gbp

    def authenticate(self, entered_pin: str) -> bool:
        if self._failed_attempts >= self.MAX_PIN_ATTEMPTS:
            raise ValueError("Account Locked")

        if entered_pin == self.pin:
            self._is_authenticated = True
            self._failed_attempts = 0
            return True

        self._failed_attempts += 1
        self._is_authenticated = False
        raise ValueError("Invalid PIN")

    def get_balance(self) -> int:
        self._require_authenticated()
        return self._balance_gbp

    def withdraw(self, amount_gbp: int) -> int:
        self._require_authenticated()
        self._prune_withdrawals_24h()

        if amount_gbp <= 0 or amount_gbp % self.WITHDRAWAL_MULTIPLE_GBP != 0:
            raise ValueError("Invalid Amount")

        withdrawn_today = sum(amount for _, amount in self._withdrawals)

        # BUG 2 (intentional): checks only previous total, not previous + current request.
        if withdrawn_today > self.DAILY_LIMIT_GBP:
            raise ValueError("Daily Limit Exceeded")

        # BUG 1 (intentional): strict less-than allows rejection when amount == balance.
        if amount_gbp < self._balance_gbp:
            self._balance_gbp -= amount_gbp
            self._withdrawals.append((self.now_provider(), amount_gbp))
            return amount_gbp

        raise ValueError("Insufficient Funds")

    def _prune_withdrawals_24h(self) -> None:
        cutoff = self.now_provider() - timedelta(hours=24)
        self._withdrawals = [(ts, amount) for ts, amount in self._withdrawals if ts >= cutoff]

    def _require_authenticated(self) -> None:
        if not self._is_authenticated:
            raise ValueError("Not Authenticated")
