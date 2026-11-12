import re
from dataclasses import dataclass, field

from .rpc import TOKEN_2022_PROGRAM

U64_MAX = 2**64 - 1
_B58 = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def valid_address(addr):
    return bool(_B58.match(addr or ""))


@dataclass
class Finding:
    account: str
    mint: str
    level: str
    reason: str
    program: str
    fix: str = ""
    extra: dict = field(default_factory=dict)


def _amount(obj):
    if not obj:
        return 0
    try:
        return int(obj.get("amount", 0))
    except (TypeError, ValueError):
        return 0


def _ui(obj):
    if not obj:
        return "0"
    return obj.get("uiAmountString") or str(obj.get("uiAmount") or 0)


def check_account(acc, owner):
    info = acc["info"]
    pubkey = acc["pubkey"]
    mint = info.get("mint", "?")
    program = acc.get("program", "")
    flag = " --program-id " + TOKEN_2022_PROGRAM if program == TOKEN_2022_PROGRAM else ""
    found = []

    delegate = info.get("delegate")
    if delegate:
        delegated = _amount(info.get("delegatedAmount"))
        balance = _amount(info.get("tokenAmount"))
        if delegated >= U64_MAX:
            level, what = "high", "unlimited"
        elif balance and delegated >= balance:
            level, what = "high", "full balance"
        else:
            level, what = "medium", _ui(info.get("delegatedAmount"))
        found.append(Finding(
            pubkey, mint, level,
            f"delegate {delegate} can move {what} (balance {_ui(info.get('tokenAmount'))})",
            program, f"spl-token revoke {pubkey}{flag}",
            {"delegate": delegate, "delegated": delegated, "balance": balance},
        ))

    close_auth = info.get("closeAuthority")
    if close_auth and close_auth != owner:
        found.append(Finding(
            pubkey, mint, "medium",
            f"close authority is {close_auth}, not you",
            program, f"spl-token authorize {pubkey} close {owner}{flag}",
            {"closeAuthority": close_auth},
        ))

    if info.get("state") == "frozen":
        found.append(Finding(pubkey, mint, "info", "account is frozen by the mint", program))

    return found


def scan(accounts, owner):
    findings = []
    for acc in accounts:
        findings.extend(check_account(acc, owner))
    order = {"high": 0, "medium": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f.level, 9))
    return findings
