"""Tests for market commands."""

import argparse
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add client dir to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spacemolt.commands.market import (
    cmd_market,
    cmd_market_orders,
    cmd_market_buy_order,
    cmd_market_sell_order,
    cmd_market_cancel_order,
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
# cmd_market_orders Tests
# ---------------------------------------------------------------------------

class TestMarketOrders(unittest.TestCase):

    def test_no_orders(self):
        """Test when there are no active orders."""
        api = mock_api({"result": {"orders": []}})
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("No active market orders", output)
        self.assertIn("Hint:", output)

    def test_buy_orders_only(self):
        """Test display of buy orders only."""
        api = mock_api({"result": {"orders": [
            {
                "type": "buy",
                "order_id": "buy-123",
                "item_id": "ore_iron",
                "quantity": 100,
                "price_each": 50,
                "filled": 0
            }
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Buy Orders:", output)
        self.assertIn("ore_iron", output)
        self.assertIn("x100", output)
        self.assertIn("50cr", output)
        self.assertIn("buy-123", output)

    def test_sell_orders_only(self):
        """Test display of sell orders only."""
        api = mock_api({"result": {"orders": [
            {
                "type": "sell",
                "id": "sell-456",
                "item_id": "ore_copper",
                "quantity": 50,
                "price": 75,
                "filled": 10
            }
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Sell Orders:", output)
        self.assertIn("ore_copper", output)
        self.assertIn("x40/50", output)  # remaining/total
        self.assertIn("75cr", output)
        self.assertIn("sell-456", output)
        self.assertIn("(10 filled)", output)

    def test_mixed_orders(self):
        """Test display of both buy and sell orders."""
        api = mock_api({"result": {"orders": [
            {
                "type": "buy",
                "order_id": "buy-123",
                "item_id": "ore_iron",
                "quantity": 100,
                "price_each": 50,
                "filled": 25
            },
            {
                "type": "sell",
                "order_id": "sell-456",
                "item_id": "ore_copper",
                "quantity": 50,
                "price_each": 75,
                "filled": 0
            }
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Buy Orders:", output)
        self.assertIn("Sell Orders:", output)
        self.assertIn("ore_iron", output)
        self.assertIn("ore_copper", output)
        self.assertIn("(25 filled)", output)

    def test_total_calculation(self):
        """Test that order totals are calculated correctly."""
        api = mock_api({"result": {"orders": [
            {
                "type": "buy",
                "order_id": "buy-123",
                "item_id": "ore_gold",
                "quantity": 10,
                "price_each": 1000,
                "filled": 3
            }
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        # Remaining: 7 @ 1000 = 7000
        self.assertIn("7,000cr", output)

    def test_endpoint_not_available(self):
        """Test when view_orders endpoint doesn't exist."""
        api = MagicMock()
        api._post.side_effect = Exception("Endpoint not found")
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=False))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("not available", output)

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"orders": []}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_market_orders(api, make_args(json=True))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["orders"], [])


# ---------------------------------------------------------------------------
# cmd_market_buy_order Tests
# ---------------------------------------------------------------------------

class TestMarketBuyOrder(unittest.TestCase):

    def test_valid_order(self):
        """Test creating a valid buy order."""
        api = mock_api({"result": {"order_id": "buy-789"}})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=50,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Buy order created", output)
        self.assertIn("buy-789", output)
        self.assertIn("ore_iron", output)
        self.assertIn("x100", output)
        self.assertIn("50cr", output)
        self.assertIn("5,000cr", output)  # total cost

    def test_invalid_quantity_zero(self):
        """Test buy order with zero quantity."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=0,
                price=50,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        self.assertIn("greater than 0", output)
        api._post.assert_not_called()

    def test_invalid_quantity_negative(self):
        """Test buy order with negative quantity."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=-10,
                price=50,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_invalid_price_zero(self):
        """Test buy order with zero price."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=0,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_invalid_price_negative(self):
        """Test buy order with negative price."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=-50,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_insufficient_credits_error(self):
        """Test error when insufficient credits."""
        api = mock_api({"error": {"message": "Insufficient credits"}})
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_platinum",
                quantity=1000,
                price=500,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Insufficient credits", output)

    def test_api_called_with_correct_params(self):
        """Test that API is called with correct parameters."""
        api = mock_api({"result": {"order_id": "buy-123"}})
        with patch("builtins.print"):
            cmd_market_buy_order(api, make_args(
                item_id="ore_copper",
                quantity=75,
                price=40,
                json=False
            ))

        api._post.assert_called_once_with("create_buy_order", {
            "item_id": "ore_copper",
            "quantity": 75,
            "price_each": 40
        })

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"order_id": "buy-456"}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_market_buy_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=50,
                json=True
            ))

        # JSON is the second print (after "Creating buy order..." message)
        output = mock_print.call_args_list[1][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["order_id"], "buy-456")


# ---------------------------------------------------------------------------
# cmd_market_sell_order Tests
# ---------------------------------------------------------------------------

class TestMarketSellOrder(unittest.TestCase):

    def test_valid_order(self):
        """Test creating a valid sell order."""
        api = mock_api({"result": {"order_id": "sell-999"}})
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_copper",
                quantity=50,
                price=80,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Sell order created", output)
        self.assertIn("sell-999", output)
        self.assertIn("ore_copper", output)
        self.assertIn("x50", output)
        self.assertIn("80cr", output)
        self.assertIn("4,000cr", output)  # total value

    def test_invalid_quantity_zero(self):
        """Test sell order with zero quantity."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_iron",
                quantity=0,
                price=50,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_invalid_price_zero(self):
        """Test sell order with zero price."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=0,
                json=False
            ))

        output = mock_print.call_args_list[0][0][0]
        self.assertIn("Error", output)
        api._post.assert_not_called()

    def test_insufficient_items_error(self):
        """Test error when insufficient items in cargo."""
        api = mock_api({"error": {"message": "Not enough items in cargo"}})
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_gold",
                quantity=999,
                price=100,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Not enough items", output)
        self.assertIn("don't have enough", output)
        self.assertIn("Hint:", output)

    def test_insufficient_items_alternative_wording(self):
        """Test error with alternative insufficient items wording."""
        api = mock_api({"error": "Insufficient ore_iron in cargo"})
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=50,
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Insufficient", output)
        self.assertIn("Hint:", output)

    def test_api_called_with_correct_params(self):
        """Test that API is called with correct parameters."""
        api = mock_api({"result": {"order_id": "sell-123"}})
        with patch("builtins.print"):
            cmd_market_sell_order(api, make_args(
                item_id="ore_silver",
                quantity=25,
                price=200,
                json=False
            ))

        api._post.assert_called_once_with("create_sell_order", {
            "item_id": "ore_silver",
            "quantity": 25,
            "price_each": 200
        })

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"order_id": "sell-789"}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_market_sell_order(api, make_args(
                item_id="ore_iron",
                quantity=100,
                price=50,
                json=True
            ))

        # JSON is the second print (after "Creating sell order..." message)
        output = mock_print.call_args_list[1][0][0]
        parsed = json.loads(output)
        self.assertEqual(parsed["result"]["order_id"], "sell-789")


# ---------------------------------------------------------------------------
# cmd_market_cancel_order Tests
# ---------------------------------------------------------------------------

class TestMarketCancelOrder(unittest.TestCase):

    def test_successful_cancel(self):
        """Test successful order cancellation."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print") as mock_print:
            cmd_market_cancel_order(api, make_args(
                order_id="buy-123",
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("Order cancelled", output)
        self.assertIn("buy-123", output)
        self.assertIn("Hint:", output)

    def test_order_not_found_error(self):
        """Test error when order doesn't exist."""
        api = mock_api({"error": {"message": "Order not found"}})
        with patch("builtins.print") as mock_print:
            cmd_market_cancel_order(api, make_args(
                order_id="invalid-999",
                json=False
            ))

        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("ERROR", output)
        self.assertIn("Order not found", output)

    def test_api_called_with_correct_params(self):
        """Test that API is called with correct parameters."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print"):
            cmd_market_cancel_order(api, make_args(
                order_id="sell-456",
                json=False
            ))

        api._post.assert_called_once_with("cancel_order", {
            "order_id": "sell-456"
        })

    def test_json_output(self):
        """Test JSON output mode."""
        response = {"result": {"success": True}}
        api = mock_api(response)
        with patch("builtins.print") as mock_print:
            cmd_market_cancel_order(api, make_args(
                order_id="buy-123",
                json=True
            ))

        output = mock_print.call_args_list[0][0][0]
        parsed = json.loads(output)
        self.assertTrue(parsed["result"]["success"])


# ---------------------------------------------------------------------------
# cmd_market Routing Tests
# ---------------------------------------------------------------------------

class TestMarketRouting(unittest.TestCase):

    def test_default_shows_orders(self):
        """Test that default action shows orders."""
        api = mock_api({"result": {"orders": []}})
        with patch("builtins.print") as mock_print:
            cmd_market(api, make_args(market_subcommand=None, json=False))

        # Should call view_orders
        api._post.assert_called_with("view_orders")
        output = "\n".join(str(c[0][0]) for c in mock_print.call_args_list)
        self.assertIn("No active market orders", output)

    def test_buy_subcommand(self):
        """Test buy subcommand routing."""
        api = mock_api({"result": {"order_id": "buy-123"}})
        with patch("builtins.print"):
            cmd_market(api, make_args(
                market_subcommand="buy",
                item_id="ore_iron",
                quantity=100,
                price=50,
                json=False
            ))

        # Should call create_buy_order
        api._post.assert_called_with("create_buy_order", {
            "item_id": "ore_iron",
            "quantity": 100,
            "price_each": 50
        })

    def test_sell_subcommand(self):
        """Test sell subcommand routing."""
        api = mock_api({"result": {"order_id": "sell-456"}})
        with patch("builtins.print"):
            cmd_market(api, make_args(
                market_subcommand="sell",
                item_id="ore_copper",
                quantity=50,
                price=75,
                json=False
            ))

        # Should call create_sell_order
        api._post.assert_called_with("create_sell_order", {
            "item_id": "ore_copper",
            "quantity": 50,
            "price_each": 75
        })

    def test_cancel_subcommand(self):
        """Test cancel subcommand routing."""
        api = mock_api({"result": {"success": True}})
        with patch("builtins.print"):
            cmd_market(api, make_args(
                market_subcommand="cancel",
                order_id="buy-789",
                json=False
            ))

        # Should call cancel_order
        api._post.assert_called_with("cancel_order", {"order_id": "buy-789"})


if __name__ == "__main__":
    unittest.main()
