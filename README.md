# sol-delegates

On Solana, when you "approve" a dApp, it can become a **delegate** on your token account and move those tokens later without asking again. Most wallets never show you these approvals. Drainers love them.

`sol-delegates` reads your token accounts (SPL Token and Token-2022) and lists:

- delegates, and how much they can move (unlimited / full balance = high)
- close authorities that point to someone other than you
- frozen accounts (with `--all`)

It is read-only. It never asks for a key. For each finding it prints the `spl-token` command to fix it.

## Install

```
pip install git+https://github.com/onderbuilds/sol-delegates
```

No dependencies, Python 3.9+.

## Usage

```
$ sol-delegates <WALLET_ADDRESS>
42 token accounts checked for 7xKX...

[HIGH] mint EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v
  account 3Fp9...
  delegate Dr4in... can move unlimited (balance 120.5)
  fix: spl-token revoke 3Fp9...
```

Options:

- `--rpc URL` use your own RPC (the public one is rate limited)
- `--json` machine readable output
- `--all` include frozen accounts

Exit code is `1` when a high risk approval is found, so you can run it from cron or CI.

## Tests

```
python -m unittest
```

MIT
