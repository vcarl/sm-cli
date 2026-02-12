"""Tests for insurance commands."""

import argparse
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add client dir to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spacemolt.commands.insurance import (
    cmd_insurance,
    cmd_insurance_status,
    cmd_insurance_buy,
    cmd_insurance_claim,
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


def mock_api(response=None):
    """Return a MagicMock API whose _post returns *response*."""
    api = MagicMock()
    api._post.return_value = response or {}
    return api


# ---------------------------------------------------------------------------
# cmd_insurance_status Tests
# ---------------------------------------------------------------------------

class TestInsuranceStatus(unittest.TestCase):

    def test_no_coverage(self):
        """Test status when no insurance is active."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("No active insurance", output)
        self.assertIn("Hint:", output)

    def test_no_coverage_empty_dict(self):
        """Test status when insurance is an empty dict."""
        api = mock_api({"result": {"insurance": {}}})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("No active insurance", output)

    def test_with_coverage(self):
        """Test status with active insurance coverage."""
        api = mock_api({"result": {
            "insurance": {
                "ticks_remaining": 50,
                "coverage_amount": 100000,
            },
            "ship_value": 150000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Insurance Coverage:", output)
        self.assertIn("50", output)  # ticks remaining
        self.assertIn("100,000", output)  # coverage amount
        self.assertIn("150,000", output)  # ship value
        self.assertIn("66.7%", output)  # coverage percentage

    def test_expiry_warning_expired(self):
        """Test warning when insurance has expired."""
        api = mock_api({"result": {
            "insurance": {"ticks_remaining": 0, "coverage_amount": 50000},
            "ship_value": 100000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("expired", output.lower())

    def test_expiry_warning_low(self):
        """Test warning when insurance is about to expire."""
        api = mock_api({"result": {
            "insurance": {"ticks_remaining": 5, "coverage_amount": 50000},
            "ship_value": 100000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("expires soon", output.lower())

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"insurance": {"ticks_remaining": 50}}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["insurance"]["ticks_remaining"], 50)

    def test_alternative_field_names(self):
        """Test with alternative field names (ticks vs ticks_remaining, amount vs coverage_amount)."""
        api = mock_api({"result": {
            "insurance": {"ticks": 30, "amount": 75000},
            "ship_value": 100000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_status(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("30", output)
        self.assertIn("75,000", output)


# ---------------------------------------------------------------------------
# cmd_insurance_buy Tests
# ---------------------------------------------------------------------------

class TestInsuranceBuy(unittest.TestCase):

    def test_valid_purchase(self):
        """Test successful insurance purchase."""
        api = mock_api({"result": {
            "premium": 5000,
            "coverage": 100000,
            "expires_at": "2026-12-31",
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=50, json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Insurance purchased", output)
        self.assertIn("5000", output)  # premium
        self.assertIn("100,000", output)  # coverage
        self.assertIn("2026-12-31", output)  # expires

    def test_invalid_ticks_zero(self):
        """Test purchase with zero ticks."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=0, json=False))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        self.assertIn("greater than 0", output)
        # API should not be called
        api._post.assert_not_called()

    def test_invalid_ticks_negative(self):
        """Test purchase with negative ticks."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=-10, json=False))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_already_insured_error(self):
        """Test error when already has insurance."""
        api = mock_api({"error": {"message": "You already have active insurance"}})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=50, json=False))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("ERROR", output)
        self.assertIn("already have active insurance", output)

    def test_insufficient_credits_error(self):
        """Test error when insufficient credits."""
        api = mock_api({"error": "Insufficient credits"})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=50, json=False))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("ERROR", output)
        self.assertIn("Insufficient credits", output)

    def test_message_response(self):
        """Test when API returns a message instead of details."""
        api = mock_api({"result": {"message": "Insurance renewed successfully"}})
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=50, json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Insurance renewed successfully", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"premium": 5000, "coverage": 100000}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_insurance_buy(api, make_args(ticks=50, json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["premium"], 5000)

    def test_api_called_with_correct_params(self):
        """Test that API is called with correct parameters."""
        api = mock_api({"result": {}})
        with patch("builtins.print"):
            cmd_insurance_buy(api, make_args(ticks=100, json=False))

        api._post.assert_called_once_with("buy_insurance", {"ticks": 100})


# ---------------------------------------------------------------------------
# cmd_insurance_claim Tests
# ---------------------------------------------------------------------------

class TestInsuranceClaim(unittest.TestCase):

    def test_successful_claim(self):
        """Test successful insurance claim."""
        api = mock_api({"result": {
            "payout": 75000,
            "credits": 150000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Insurance claim successful", output)
        self.assertIn("75000", output)  # payout (without comma for simplicity)
        self.assertIn("150,000", output)  # new balance

    def test_no_insurance_error(self):
        """Test error when no insurance coverage."""
        api = mock_api({"error": {"message": "You have no insurance coverage"}})
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("no insurance", output.lower())
        self.assertIn("Hint:", output)

    def test_ship_not_destroyed_error(self):
        """Test error when ship is not destroyed."""
        api = mock_api({"error": "Ship is not destroyed"})
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("not destroyed", output)
        self.assertIn("still intact", output)

    def test_ship_alive_error(self):
        """Test error with 'alive' message."""
        api = mock_api({"error": "Ship is still alive"})
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("still intact", output)

    def test_alternative_field_names(self):
        """Test with alternative field names."""
        api = mock_api({"result": {
            "credits_received": 80000,
            "balance": 180000,
        }})
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("80000", output)
        self.assertIn("180,000", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"payout": 75000, "credits": 150000}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_insurance_claim(api, make_args(json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["payout"], 75000)


# ---------------------------------------------------------------------------
# cmd_insurance Routing Tests
# ---------------------------------------------------------------------------

class TestInsuranceRouting(unittest.TestCase):

    def test_default_shows_status(self):
        """Test that default action shows status."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_insurance(api, make_args(insurance_subcommand=None, json=False))

        # Should call get_status
        api._post.assert_called_with("get_status")
        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("No active insurance", output)

    def test_buy_subcommand(self):
        """Test buy subcommand routing."""
        api = mock_api({"result": {"premium": 5000, "coverage": 100000}})
        with patch("builtins.print"):
            cmd_insurance(api, make_args(
                insurance_subcommand="buy",
                ticks=50,
                json=False
            ))

        # Should call buy_insurance
        api._post.assert_called_with("buy_insurance", {"ticks": 50})

    def test_claim_subcommand(self):
        """Test claim subcommand routing."""
        api = mock_api({"result": {"payout": 75000}})
        with patch("builtins.print"):
            cmd_insurance(api, make_args(
                insurance_subcommand="claim",
                json=False
            ))

        # Should call claim_insurance
        api._post.assert_called_with("claim_insurance")


if __name__ == "__main__":
    unittest.main()
