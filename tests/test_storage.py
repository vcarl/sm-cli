"""Tests for storage commands."""

import argparse
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add client dir to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spacemolt.commands.storage import (
    cmd_storage,
    cmd_storage_view,
    cmd_storage_deposit,
    cmd_storage_withdraw,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_args(**kwargs):
    """Build a namespace that looks like argparse output."""
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def mock_api(response=None, require_docked_raises=None):
    """Return a MagicMock API whose _post returns *response*."""
    api = MagicMock()
    api._post.return_value = response or {}
    if require_docked_raises:
        api._require_docked.side_effect = require_docked_raises
    return api


# ---------------------------------------------------------------------------
# cmd_storage_view Tests
# ---------------------------------------------------------------------------

class TestStorageView(unittest.TestCase):

    def test_empty_storage(self):
        """Test viewing empty storage."""
        api = mock_api({"result": {"items": [], "credits": 0}})
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Storage is empty", output)
        self.assertIn("Hint:", output)

    def test_with_items_only(self):
        """Test storage with items but no credits."""
        api = mock_api({"result": {
            "items": [
                {"item_id": "ore_iron", "quantity": 100},
                {"name": "ore_copper", "quantity": 50},
            ],
            "credits": 0
        }})
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Base Storage:", output)
        self.assertIn("ore_iron", output)
        self.assertIn("x100", output)
        self.assertIn("ore_copper", output)
        self.assertIn("x50", output)

    def test_with_credits_only(self):
        """Test storage with credits but no items."""
        api = mock_api({"result": {"items": [], "credits": 50000}})
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Base Storage:", output)
        self.assertIn("50,000", output)

    def test_with_items_and_credits(self):
        """Test storage with both items and credits."""
        api = mock_api({"result": {
            "items": [{"item_id": "ore_gold", "quantity": 25}],
            "credits": 100000
        }})
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Base Storage:", output)
        self.assertIn("100,000", output)
        self.assertIn("ore_gold", output)
        self.assertIn("x25", output)

    def test_endpoint_not_available(self):
        """Test when view_storage endpoint doesn't exist."""
        api = MagicMock()
        api._post.side_effect = Exception("Endpoint not found")
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("not available", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"items": [], "credits": 5000}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["credits"], 5000)

    def test_malformed_items(self):
        """Test with malformed items (non-dict entries)."""
        api = mock_api({"result": {
            "items": ["invalid", {"item_id": "ore_iron", "quantity": 10}],
            "credits": 0
        }})
        with patch("builtins.print") as mock_print:
            cmd_storage_view(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        # Should handle gracefully and show valid items
        self.assertIn("ore_iron", output)


# ---------------------------------------------------------------------------
# cmd_storage_deposit Tests
# ---------------------------------------------------------------------------

class TestStorageDeposit(unittest.TestCase):

    def test_deposit_items_success(self):
        """Test successful item deposit."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id="ore_iron",
                quantity=50,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Deposited:", output)
        self.assertIn("ore_iron", output)
        self.assertIn("x50", output)
        api._post.assert_called_with("deposit_items", {
            "item_id": "ore_iron",
            "quantity": 50
        })

    def test_deposit_credits_success(self):
        """Test successful credit deposit."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id=None,
                quantity=None,
                credits=10000,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Deposited:", output)
        self.assertIn("10000", output)
        api._post.assert_called_with("deposit_credits", {"amount": 10000})

    def test_requires_docked(self):
        """Test that docked status is checked."""
        api = mock_api()
        api._require_docked.side_effect = Exception("Must be docked")
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id="ore_iron",
                quantity=50,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Error:", output)
        self.assertIn("Must be docked", output)
        # API should not be called
        api._post.assert_not_called()

    def test_no_parameters(self):
        """Test deposit with no parameters shows usage."""
        api = mock_api()
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id=None,
                quantity=None,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Usage:", output)
        api._post.assert_not_called()

    def test_insufficient_items_error(self):
        """Test error when insufficient items to deposit."""
        api = mock_api({"error": {"message": "Not enough items in cargo"}})
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id="ore_iron",
                quantity=999,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Not enough items", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"success": True}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_storage_deposit(api, make_args(
                item_id="ore_iron",
                quantity=50,
                credits=None,
                json=True
            ))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertTrue(parsed["result"]["success"])


# ---------------------------------------------------------------------------
# cmd_storage_withdraw Tests
# ---------------------------------------------------------------------------

class TestStorageWithdraw(unittest.TestCase):

    def test_withdraw_items_success(self):
        """Test successful item withdrawal."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id="ore_iron",
                quantity=30,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Withdrew:", output)
        self.assertIn("ore_iron", output)
        self.assertIn("x30", output)
        api._post.assert_called_with("withdraw_items", {
            "item_id": "ore_iron",
            "quantity": 30
        })

    def test_withdraw_credits_success(self):
        """Test successful credit withdrawal."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id=None,
                quantity=None,
                credits=5000,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Withdrew:", output)
        self.assertIn("5000", output)
        api._post.assert_called_with("withdraw_credits", {"amount": 5000})

    def test_requires_docked(self):
        """Test that docked status is checked."""
        api = mock_api()
        api._require_docked.side_effect = Exception("Must be docked at a base")
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id="ore_iron",
                quantity=30,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Error:", output)
        api._post.assert_not_called()

    def test_no_parameters(self):
        """Test withdraw with no parameters shows usage."""
        api = mock_api()
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id=None,
                quantity=None,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Usage:", output)
        api._post.assert_not_called()

    def test_insufficient_storage_error(self):
        """Test error when insufficient items in storage."""
        api = mock_api({"error": "Not enough items in storage"})
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id="ore_platinum",
                quantity=999,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Not enough items", output)

    def test_cargo_full_error(self):
        """Test error when cargo is full."""
        api = mock_api({"error": {"message": "Cargo hold is full"}})
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id="ore_iron",
                quantity=50,
                credits=None,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Cargo hold is full", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"success": True}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_storage_withdraw(api, make_args(
                item_id="ore_iron",
                quantity=30,
                credits=None,
                json=True
            ))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertTrue(parsed["result"]["success"])


# ---------------------------------------------------------------------------
# cmd_storage Routing Tests
# ---------------------------------------------------------------------------

class TestStorageRouting(unittest.TestCase):

    def test_default_shows_view(self):
        """Test that default action shows storage view."""
        api = mock_api({"result": {"items": [], "credits": 0}})
        with patch("builtins.print") as mock_print:
            cmd_storage(api, make_args(storage_subcommand=None))

        # Should call view_storage
        api._post.assert_called_with("view_storage")
        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("empty", output.lower())

    def test_deposit_subcommand(self):
        """Test deposit subcommand routing."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="deposit",
                item_id="ore_iron",
                quantity=50,
                credits=None,
                json=False
            ))

        # Should call deposit_items
        api._post.assert_called_with("deposit_items", {
            "item_id": "ore_iron",
            "quantity": 50
        })

    def test_withdraw_subcommand(self):
        """Test withdraw subcommand routing."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print"):
            cmd_storage(api, make_args(
                storage_subcommand="withdraw",
                item_id="ore_copper",
                quantity=25,
                credits=None,
                json=False
            ))

        # Should call withdraw_items
        api._post.assert_called_with("withdraw_items", {
            "item_id": "ore_copper",
            "quantity": 25
        })


if __name__ == "__main__":
    unittest.main()
