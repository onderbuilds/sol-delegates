import json
import urllib.request

DEFAULT_RPC = "https://api.mainnet-beta.solana.com"
TOKEN_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


class RpcError(Exception):
    pass


def call(url, method, params, timeout=20):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except OSError as e:
        raise RpcError(f"could not reach {url}: {e}") from e
    if "error" in data:
        raise RpcError(data["error"].get("message", str(data["error"])))
    return data["result"]


def token_accounts(owner, url=DEFAULT_RPC, caller=call):
    out = []
    for program in (TOKEN_PROGRAM, TOKEN_2022_PROGRAM):
        res = caller(url, "getTokenAccountsByOwner",
                     [owner, {"programId": program}, {"encoding": "jsonParsed"}])
        for item in res.get("value", []):
            data = item["account"]["data"]
            info = data.get("parsed", {}).get("info") if isinstance(data, dict) else None
            if not info:
                continue
            out.append({"pubkey": item["pubkey"], "program": program, "info": info})
    return out
