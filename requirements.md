# Simple ATM Simulator Requirements

## REQ-01: Authentication
A user must provide a valid 4-digit PIN. 3 consecutive failed attempts locks the account.

- AC1: Given a valid PIN, When entered, Then authenticate the user.
- AC2: Given an invalid PIN, When entered, Then deny access and increment the failure counter.
- AC3: Given 3 consecutive failed attempts, When a 4th attempt is made (even if correct), Then reject the attempt and return an "Account Locked" error.

## REQ-02: Balance Inquiry
Returns the current available balance.

- AC1: Given an authenticated user, When a balance check is requested, Then return the exact numerical balance in GBP.

## REQ-03: Withdrawal Limits
Cash withdrawals must be requested in multiples of £20.

- AC1: Given a requested withdrawal of £40, When processed, Then approve the amount.
- AC2: Given a requested withdrawal of £50, When processed, Then reject the transaction with an "Invalid Amount" error.

## REQ-04: Overdraft Protection
The system must reject withdrawals exceeding the available balance.

- AC1: Given a balance of £100, When a withdrawal of £100 is requested, Then approve the transaction and reduce the balance to £0.
- AC2: Given a balance of £100, When a withdrawal of £120 is requested, Then raise a ValueError with "Insufficient Funds" and do not modify the balance.

## REQ-05: Daily Limit
A user cannot withdraw more than £1,000 in a single 24-hour period.

- AC1: Given previous withdrawals today totaling £800, When a new withdrawal of £200 is requested, Then approve the transaction.
- AC2: Given previous withdrawals today totaling £900, When a new withdrawal of £200 is requested, Then raise a ValueError for "Daily Limit Exceeded".
