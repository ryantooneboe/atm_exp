from datetime import datetime, timezone

import pytest
from atm_simulator import ATM


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest.fixture
def clean_atm():
    return ATM(initial_balance_gbp=500, pin="1234", now_provider=utc_now)


def set_withdrawn_last_24h(atm: ATM, total: int) -> None:
    if total <= 0:
        atm._withdrawals = []
        return
    atm._withdrawals = [(utc_now(), total)]


# =========================================================
# REQ-01: Authentication
# =========================================================

def test_req01_ac1_authenticate_valid_pin(clean_atm):
    clean_atm._failed_attempts = 0

    result = clean_atm.authenticate("1234")

    assert result is True
    assert clean_atm._failed_attempts == 0


def test_req01_ac2_invalid_pin_first_attempt(clean_atm):
    clean_atm._failed_attempts = 0

    with pytest.raises(ValueError, match="Invalid PIN"):
        clean_atm.authenticate("1111")

    assert clean_atm._failed_attempts == 1
    assert clean_atm._failed_attempts < clean_atm.MAX_PIN_ATTEMPTS


def test_req01_boundary_second_invalid_attempt(clean_atm):
    clean_atm._failed_attempts = 1

    with pytest.raises(ValueError, match="Invalid PIN"):
        clean_atm.authenticate("1111")

    assert clean_atm._failed_attempts == 2
    assert clean_atm._failed_attempts < clean_atm.MAX_PIN_ATTEMPTS


def test_req01_ac3_lock_after_three_attempts(clean_atm):
    clean_atm._failed_attempts = 2

    with pytest.raises(ValueError, match="Invalid PIN"):
        clean_atm.authenticate("1111")

    assert clean_atm._failed_attempts == 3
    assert clean_atm._failed_attempts >= clean_atm.MAX_PIN_ATTEMPTS


def test_req01_ac3_reject_after_locked(clean_atm):
    clean_atm._failed_attempts = clean_atm.MAX_PIN_ATTEMPTS

    with pytest.raises(ValueError, match="Account Locked"):
        clean_atm.authenticate("1234")

    assert clean_atm._is_authenticated is False


def test_req01_boundary_valid_4_digit_pin(clean_atm):
    clean_atm._failed_attempts = 0

    result = clean_atm.authenticate("1234")

    assert result is True


@pytest.mark.parametrize("pin", ["123", "12345"])
def test_req01_boundary_invalid_pin_length(clean_atm, pin):
    clean_atm._failed_attempts = 0

    with pytest.raises(ValueError, match="Invalid PIN"):
        clean_atm.authenticate(pin)

    assert clean_atm._failed_attempts == 1


# =========================================================
# REQ-02: Balance Inquiry
# =========================================================

def test_req02_ac1_return_balance(clean_atm):
    clean_atm._balance_gbp = 245
    clean_atm.authenticate("1234")

    result = clean_atm.get_balance()

    assert result == 245
    assert isinstance(result, int)


def test_req02_boundary_zero_balance():
    atm = ATM(initial_balance_gbp=0, pin="1234", now_provider=utc_now)
    atm.authenticate("1234")

    result = atm.get_balance()

    assert result == 0
    assert isinstance(result, int)


def test_req02_boundary_negative_balance():
    atm = ATM(initial_balance_gbp=-100, pin="1234", now_provider=utc_now)
    atm.authenticate("1234")

    result = atm.get_balance()

    assert result == -100
    assert isinstance(result, int)


# =========================================================
# REQ-03: Withdrawal Limits
# =========================================================

def test_req03_ac1_valid_multiple(clean_atm):
    clean_atm._balance_gbp = 200
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    dispensed = clean_atm.withdraw(40)

    assert dispensed == 40
    assert clean_atm.get_balance() == 160


def test_req03_ac2_invalid_multiple(clean_atm):
    clean_atm._balance_gbp = 200
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    with pytest.raises(ValueError, match="Invalid Amount"):
        clean_atm.withdraw(50)

    assert clean_atm.get_balance() == 200


@pytest.mark.parametrize("amount,result,response", [
    (39, "rejected", "Invalid Amount"),
    (40, "approved", "Approved"),
    (41, "rejected", "Invalid Amount"),
])
def test_req03_boundary_multiple(clean_atm, amount, result, response):
    clean_atm._balance_gbp = 200
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    if result == "approved":
        dispensed = clean_atm.withdraw(amount)
        assert dispensed == amount
        assert response == "Approved"
    else:
        with pytest.raises(ValueError, match=response):
            clean_atm.withdraw(amount)


def test_req03_boundary_minimum_multiple(clean_atm):
    clean_atm._balance_gbp = 200
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    dispensed = clean_atm.withdraw(20)

    assert dispensed == 20
    assert clean_atm.get_balance() == 180


def test_req03_negative_balance_valid_multiple():
    atm = ATM(initial_balance_gbp=500, pin="1234", now_provider=utc_now)
    atm._balance_gbp = -20
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        atm.withdraw(40)

    assert atm.get_balance() == -20


def test_req03_negative_invalid_amount_and_balance():
    atm = ATM(initial_balance_gbp=500, pin="1234", now_provider=utc_now)
    atm._balance_gbp = -20
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Invalid Amount"):
        atm.withdraw(50)

    assert atm.get_balance() == -20


@pytest.mark.parametrize("balance,amount", [
    (1, 20),
    (20, 20),
    (100, 40),
])
def test_req03_boundary_negative(clean_atm, balance, amount):
    clean_atm._balance_gbp = -balance
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        clean_atm.withdraw(amount)


# =========================================================
# REQ-04: Overdraft Protection
# =========================================================

def test_req04_ac1_exact_balance():
    atm = ATM(initial_balance_gbp=100, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    atm.withdraw(100)

    assert atm.get_balance() == 0


def test_req04_ac2_exceeds_balance():
    atm = ATM(initial_balance_gbp=100, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        atm.withdraw(120)

    assert atm.get_balance() == 100


@pytest.mark.parametrize("amount,result", [
    (80, "approved"),
    (100, "approved"),
    (120, "ValueError \"Insufficient Funds\" raised"),
])
def test_req04_boundary_balance(clean_atm, amount, result):
    clean_atm._balance_gbp = 100
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    if result == "approved":
        dispensed = clean_atm.withdraw(amount)
        assert dispensed == amount
        assert clean_atm.get_balance() == (100 - amount)
    else:
        with pytest.raises(ValueError, match="Insufficient Funds"):
            clean_atm.withdraw(amount)
        assert clean_atm.get_balance() == 100


@pytest.mark.parametrize("amount", [99, 101])
def test_req03_req04_cross_boundary(clean_atm, amount):
    clean_atm._balance_gbp = 100
    set_withdrawn_last_24h(clean_atm, 0)
    clean_atm.authenticate("1234")

    with pytest.raises(ValueError, match="Invalid Amount"):
        clean_atm.withdraw(amount)

    assert clean_atm.get_balance() == 100


def test_req04_negative_already_negative():
    atm = ATM(initial_balance_gbp=500, pin="1234", now_provider=utc_now)
    atm._balance_gbp = -10
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        atm.withdraw(20)

    assert atm.get_balance() == -10


def test_req04_negative_zero_to_negative():
    atm = ATM(initial_balance_gbp=0, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        atm.withdraw(20)

    assert atm.get_balance() == 0


@pytest.mark.parametrize("balance", [1, 0, -1])
def test_req04_boundary_negative(balance):
    atm = ATM(initial_balance_gbp=balance, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 0)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Insufficient Funds"):
        atm.withdraw(20)

    assert atm.get_balance() == balance


# =========================================================
# REQ-05: Daily Limit
# =========================================================

def test_req05_ac1_exact_limit():
    atm = ATM(initial_balance_gbp=1500, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 800)
    atm.authenticate("1234")

    atm.withdraw(200)

    withdrawn_today = sum(amount for _, amount in atm._withdrawals)
    assert withdrawn_today == 1000


def test_req05_ac2_exceeds_limit():
    atm = ATM(initial_balance_gbp=1500, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 900)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Daily Limit Exceeded"):
        atm.withdraw(200)

    withdrawn_today = sum(amount for _, amount in atm._withdrawals)
    assert withdrawn_today == 900
    assert atm.get_balance() == 1500


@pytest.mark.parametrize("already_withdrawn,result", [
    (960, "approved"),
    (980, "approved"),
    (1000, "ValueError \"Daily Limit Exceeded\" raised"),
])
def test_req05_boundary(already_withdrawn, result):
    atm = ATM(initial_balance_gbp=2000, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, already_withdrawn)
    atm.authenticate("1234")

    if result == "approved":
        atm.withdraw(20)
        withdrawn_today = sum(amount for _, amount in atm._withdrawals)
        assert withdrawn_today == already_withdrawn + 20
    else:
        with pytest.raises(ValueError, match="Daily Limit Exceeded"):
            atm.withdraw(20)


@pytest.mark.parametrize("amount", [19, 21])
def test_req03_req05_cross_boundary(amount):
    atm = ATM(initial_balance_gbp=2000, pin="1234", now_provider=utc_now)
    set_withdrawn_last_24h(atm, 980)
    atm.authenticate("1234")

    with pytest.raises(ValueError, match="Invalid Amount"):
        atm.withdraw(amount)
