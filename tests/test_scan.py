import io
import json
import unittest
from contextlib import redirect_stdout

from soldelegates.cli import main
from soldelegates.rpc import TOKEN_2022_PROGRAM, TOKEN_PROGRAM, token_accounts
from soldelegates.scan import U64_MAX, scan, valid_address

OWNER = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
BAD = "HackerDe1egateXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"


def acc(pubkey, mint="So11111111111111111111111111111111111111112", amount=1000, **info):
    base = {"mint": mint, "owner": OWNER, "state": "initialized",
            "tokenAmount": {"amount": str(amount), "decimals": 6, "uiAmountString": str(amount / 1e6)}}
    base.update(info)
    return {"pubkey": pubkey, "program": TOKEN_PROGRAM, "info": base}


class ScanTests(unittest.TestCase):
    def test_clean_wallet(self):
        self.assertEqual(scan([acc("A1")], OWNER), [])

    def test_unlimited_delegate_is_high(self):
        a = acc("A1", delegate=BAD, delegatedAmount={"amount": str(U64_MAX)})
        f = scan([a], OWNER)
        self.assertEqual(f[0].level, "high")
        self.assertIn("unlimited", f[0].reason)
        self.assertEqual(f[0].fix, "spl-token revoke A1")

    def test_full_balance_delegate_is_high(self):
        a = acc("A1", amount=500, delegate=BAD, delegatedAmount={"amount": "500"})
        self.assertEqual(scan([a], OWNER)[0].level, "high")

    def test_partial_delegate_is_medium(self):
        a = acc("A1", amount=500, delegate=BAD,
                delegatedAmount={"amount": "100", "uiAmountString": "0.0001"})
        f = scan([a], OWNER)[0]
        self.assertEqual(f.level, "medium")
        self.assertIn("0.0001", f.reason)

    def test_foreign_close_authority(self):
        f = scan([acc("A1", closeAuthority=BAD)], OWNER)
        self.assertEqual(f[0].level, "medium")
        self.assertIn("authorize A1 close", f[0].fix)

    def test_own_close_authority_ignored(self):
        self.assertEqual(scan([acc("A1", closeAuthority=OWNER)], OWNER), [])

    def test_token2022_fix_has_program_id(self):
        a = acc("A1", delegate=BAD, delegatedAmount={"amount": str(U64_MAX)})
        a["program"] = TOKEN_2022_PROGRAM
        self.assertIn("--program-id", scan([a], OWNER)[0].fix)

    def test_frozen_and_sort_order(self):
        f = scan([acc("A1", state="frozen"),
                  acc("A2", delegate=BAD, delegatedAmount={"amount": str(U64_MAX)})], OWNER)
        self.assertEqual([x.level for x in f], ["high", "info"])

    def test_address_validation(self):
        self.assertTrue(valid_address(OWNER))
        self.assertFalse(valid_address("0xdeadbeef"))
        self.assertFalse(valid_address(""))


class RpcTests(unittest.TestCase):
    def test_token_accounts_reads_both_programs(self):
        seen = []

        def fake(url, method, params):
            seen.append(params[1]["programId"])
            if params[1]["programId"] == TOKEN_PROGRAM:
                return {"value": [{"pubkey": "A1", "account": {"data": {"parsed": {"info": {"mint": "M"}}}}}]}
            return {"value": [{"pubkey": "B1", "account": {"data": ["raw", "base64"]}}]}

        out = token_accounts(OWNER, "http://x", caller=fake)
        self.assertEqual(seen, [TOKEN_PROGRAM, TOKEN_2022_PROGRAM])
        self.assertEqual([a["pubkey"] for a in out], ["A1"])


class CliTests(unittest.TestCase):
    def run_cli(self, argv, accounts):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = main(argv, fetch=lambda w, r: accounts)
        return code, buf.getvalue()

    def test_exit_codes(self):
        code, out = self.run_cli([OWNER], [acc("A1")])
        self.assertEqual(code, 0)
        self.assertIn("clean", out)
        bad = acc("A1", delegate=BAD, delegatedAmount={"amount": str(U64_MAX)})
        code, out = self.run_cli([OWNER], [bad])
        self.assertEqual(code, 1)
        self.assertIn("spl-token revoke A1", out)

    def test_json(self):
        code, out = self.run_cli([OWNER, "--json"], [acc("A1", closeAuthority=BAD)])
        data = json.loads(out)
        self.assertEqual(data["token_accounts"], 1)
        self.assertEqual(data["findings"][0]["level"], "medium")

    def test_frozen_hidden_without_all(self):
        _, out = self.run_cli([OWNER], [acc("A1", state="frozen")])
        self.assertNotIn("frozen", out)
        _, out = self.run_cli([OWNER, "--all"], [acc("A1", state="frozen")])
        self.assertIn("frozen", out)

    def test_bad_address(self):
        self.assertEqual(main(["nope"], fetch=lambda w, r: []), 2)


if __name__ == "__main__":
    unittest.main()
