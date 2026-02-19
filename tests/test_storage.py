"""Tests for storage commands (unified /storage endpoint)."""

import argparse
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add client dir to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spacemolt.commands.storage import cmd_storage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(**kwargs):
    """Build a namespace that looks like argparse output."""
    defaults = {
        "storage_subcommand": None,
        "json": False,
        "target": "self",
        "item_id": None,
        "quantity": None,
        "credits": None,
        "message": None,
    }
    defaults.update(kwargs)
    ns = argparse.Namespace()
    for k, v in defaults.items():
        setattr(ns, k, v)
    return ns


def mock_api(response=None):
    """Return a MagicMock API whose _post returns *response*."""
    api = MagicMock()
    api._post.return_value = response or {}
    return api


# ---------------------------------------------------------------------------
# View Tests
# ---------------------------------------------------------------------------

class TestStorageView(unittest.TestCase):

    def test_empty_storage(self):
        api = mock_api({"result": {"items": [], "credits": 0}})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args())

        api._post.assert_called_with("storage", {"action": "view"})
        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("empty", output.lower())

    def test_with_items_and_credits(self):
        api = mock_api({"result": {
            "items": [{"item_id": "ore_gold", "quantity": 25}],
            "credits": 100000
        }})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args())

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Base Storage:", output)
        self.assertIn("100,000", output)
        self.assertIn("ore_gold", output)
        self.assertIn("x25", output)

    def test_faction_storage(self):
        api = mock_api({"result": {"items": [], "credits": 5000}})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(target="faction"))

        api._post.assert_called_with("storage", {"action": "view", "target": "faction"})
        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Faction Storage:", output)

    def test_endpoint_not_available(self):
        api = MagicMock()
        api._post.side_effect = Exception("Endpoint not found")
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args())

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("not available", output)

    def test_json_output(self):
        response = {"result": {"items": [], "credits": 5000}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["credits"], 5000)

    def test_error_response(self):
        api = mock_api({"error": {"message": "Must be docked"}})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args())

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Must be docked", output)


# ---------------------------------------------------------------------------
# Deposit Tests
# ---------------------------------------------------------------------------

class TestStorageDeposit(unittest.TestCase):

    def test_deposit_items(self):
        api = mock_api({"result": {"message": "Deposited 50 ore_iron"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                item_id="ore_iron",
                quantity=50,
            ))

        api._post.assert_called_with("storage", {
            "action": "deposit",
            "item_id": "ore_iron",
            "quantity": 50,
        })

    def test_deposit_credits(self):
        api = mock_api({"result": {"message": "Deposited 10000 credits"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                credits=10000,
            ))

        api._post.assert_called_with("storage", {
            "action": "deposit",
            "item_id": "credits",
            "quantity": 10000,
        })

    def test_deposit_to_faction(self):
        api = mock_api({"result": {"message": "Deposited to faction"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                item_id="ore_iron",
                quantity=50,
                target="faction",
            ))

        api._post.assert_called_with("storage", {
            "action": "deposit",
            "item_id": "ore_iron",
            "quantity": 50,
            "target": "faction",
        })

    def test_deposit_gift_to_player(self):
        api = mock_api({"result": {"message": "Gifted to player"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                item_id="ore_gold",
                quantity=5,
                target="alice",
                message="here you go",
            ))

        api._post.assert_called_with("storage", {
            "action": "deposit",
            "item_id": "ore_gold",
            "quantity": 5,
            "target": "alice",
            "message": "here you go",
        })

    def test_no_parameters_shows_usage(self):
        api = mock_api()
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(storage_subcommand="deposit"))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Usage:", output)
        api._post.assert_not_called()

    def test_error_response(self):
        api = mock_api({"error": {"message": "Not enough items in cargo"}})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                item_id="ore_iron",
                quantity=999,
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Not enough items", output)


# ---------------------------------------------------------------------------
# Withdraw Tests
# ---------------------------------------------------------------------------

class TestStorageWithdraw(unittest.TestCase):

    def test_withdraw_items(self):
        api = mock_api({"result": {"message": "Withdrew 30 ore_iron"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="withdraw",
                item_id="ore_iron",
                quantity=30,
            ))

        api._post.assert_called_with("storage", {
            "action": "withdraw",
            "item_id": "ore_iron",
            "quantity": 30,
        })

    def test_withdraw_credits(self):
        api = mock_api({"result": {"message": "Withdrew 5000 credits"}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="withdraw",
                credits=5000,
            ))

        api._post.assert_called_with("storage", {
            "action": "withdraw",
            "item_id": "credits",
            "quantity": 5000,
        })

    def test_no_parameters_shows_usage(self):
        api = mock_api()
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(storage_subcommand="withdraw"))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Usage:", output)
        api._post.assert_not_called()

    def test_json_output(self):
        response = {"result": {"success": True}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(
                storage_subcommand="withdraw",
                item_id="ore_iron",
                quantity=30,
                json=True,
            ))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertTrue(parsed["result"]["success"])


if __name__ == "__main__":
    unittest.main()
