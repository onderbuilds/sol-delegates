import argparse
import json
import sys
from dataclasses import asdict

from . import __version__
from .rpc import DEFAULT_RPC, RpcError, token_accounts
from .scan import scan, valid_address


def main(argv=None, fetch=token_accounts):
    p = argparse.ArgumentParser(
        prog="sol-delegates",
        description="List SPL token approvals (delegates) and odd close authorities on a Solana wallet.",
    )
    p.add_argument("wallet", help="wallet address (owner)")
    p.add_argument("--rpc", default=DEFAULT_RPC, help="RPC url (default: public mainnet)")
    p.add_argument("--all", action="store_true", help="also show frozen accounts")
    p.add_argument("--json", action="store_true", help="print JSON")
    p.add_argument("--version", action="version", version=__version__)
    args = p.parse_args(argv)

    if not valid_address(args.wallet):
        print(f"not a valid Solana address: {args.wallet}", file=sys.stderr)
        return 2
    try:
        accounts = fetch(args.wallet, args.rpc)
    except RpcError as e:
        print(f"rpc error: {e}", file=sys.stderr)
        return 2

    findings = scan(accounts, args.wallet)
    if not args.all:
        findings = [f for f in findings if f.level != "info"]
    if args.json:
        print(json.dumps({"wallet": args.wallet, "token_accounts": len(accounts),
                          "findings": [asdict(f) for f in findings]}, indent=2))
    else:
        print(f"{len(accounts)} token accounts checked for {args.wallet}")
        if not findings:
            print("no delegates or foreign close authorities. clean.")
        for f in findings:
            print(f"\n[{f.level.upper()}] mint {f.mint}")
            print(f"  account {f.account}")
            print(f"  {f.reason}")
            if f.fix:
                print(f"  fix: {f.fix}")
    return 1 if any(f.level == "high" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
