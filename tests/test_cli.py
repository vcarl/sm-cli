"""Tests for the sm CLI: routing, argument parsing, passthrough, and formatted output."""

import argparse
import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add client dir to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from spacemolt.cli import build_parser, COMMAND_MAP, _known_commands, main
from spacemolt.commands import (
    ENDPOINT_ARGS,
    _parse_typed_value,
    _arg_name,
    _normalize_recipes,
    _build_recipe_indexes,
    _recipe_skill_tier,
    _recipe_one_line,
    _trace_ingredient_tree,
    _render_tree,
    _collect_raw_totals,
    cmd_passthrough,
    cmd_status,
    cmd_jump,
    cmd_buy,
    cmd_ship,
    cmd_base,
    cmd_poi,
    cmd_wrecks,
    cmd_listings,
    cmd_recipes,
    cmd_query_recipes,
    cmd_commands,
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
# _parse_typed_value
# ---------------------------------------------------------------------------

class TestParseTypedValue(unittest.TestCase):

    def test_int(self):
        self.assertEqual(_parse_typed_value("quantity:int", "5"), 5)

    def test_int_zero(self):
        self.assertEqual(_parse_typed_value("index:int", "0"), 0)

    def test_int_negative(self):
        self.assertEqual(_parse_typed_value("offset:int", "-3"), -3)

    def test_bool_true_variants(self):
        for val in ("true", "True", "TRUE", "1", "yes", "Yes"):
            self.assertTrue(_parse_typed_value("flag:bool", val), f"failed for {val}")

    def test_bool_false_variants(self):
        for val in ("false", "False", "0", "no", "nope", ""):
            self.assertFalse(_parse_typed_value("flag:bool", val), f"failed for {val}")

    def test_string_default(self):
        self.assertEqual(_parse_typed_value("name", "hello"), "hello")

    def test_explicit_str_type(self):
        self.assertEqual(_parse_typed_value("name:str", "hello"), "hello")

    def test_int_raises_on_non_numeric(self):
        with self.assertRaises(ValueError):
            _parse_typed_value("n:int", "abc")


# ---------------------------------------------------------------------------
# _arg_name
# ---------------------------------------------------------------------------

class TestArgName(unittest.TestCase):

    def test_plain(self):
        self.assertEqual(_arg_name("name"), "name")

    def test_typed(self):
        self.assertEqual(_arg_name("quantity:int"), "quantity")

    def test_bool_typed(self):
        self.assertEqual(_arg_name("anonymous:bool"), "anonymous")


# ---------------------------------------------------------------------------
# ENDPOINT_ARGS coverage
# ---------------------------------------------------------------------------

class TestEndpointArgs(unittest.TestCase):

    def test_key_endpoints_present(self):
        for ep in ["jump", "scan", "attack", "buy", "sell", "craft",
                    "forum_reply", "forum_list", "captains_log_add",
                    "install_mod", "find_route", "search_systems",
                    "list_item", "buy_listing", "faction_invite"]:
            self.assertIn(ep, ENDPOINT_ARGS, f"{ep} missing from ENDPOINT_ARGS")

    def test_all_specs_parseable(self):
        """Every spec in the table should have a valid name and optional type."""
        for ep, specs in ENDPOINT_ARGS.items():
            for spec in specs:
                name = _arg_name(spec)
                self.assertTrue(len(name) > 0, f"empty name in {ep}: {spec}")
                # type, if present, must be int, bool, or str
                if ":" in spec:
                    _, t = spec.rsplit(":", 1)
                    self.assertIn(t, ("int", "bool", "str"),
                                  f"bad type '{t}' in {ep}: {spec}")


# ---------------------------------------------------------------------------
# CLI routing
# ---------------------------------------------------------------------------

class TestKnownCommands(unittest.TestCase):

    def test_returns_set(self):
        known = _known_commands()
        self.assertIsInstance(known, set)

    def test_includes_original_commands(self):
        known = _known_commands()
        for cmd in ["login", "status", "sell-all", "mine", "chat", "raw"]:
            self.assertIn(cmd, known)

    def test_includes_new_formatted_commands(self):
        known = _known_commands()
        for cmd in ["ship", "poi", "base", "jump", "buy", "wrecks",
                     "listings", "recipes", "commands"]:
            self.assertIn(cmd, known)

    def test_passthrough_endpoints_not_known(self):
        """Passthrough-only endpoints should NOT be in the known set."""
        known = _known_commands()
        for cmd in ["scan", "attack", "forum_list", "get_map",
                     "craft", "faction_info"]:
            self.assertNotIn(cmd, known)


class TestCommandMapCompleteness(unittest.TestCase):

    def test_all_map_values_are_callable(self):
        for name, handler in COMMAND_MAP.items():
            self.assertTrue(callable(handler), f"{name} handler not callable")



# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------

class TestBuildParser(unittest.TestCase):

    def setUp(self):
        self.parser = build_parser()

    def test_no_args_shows_help(self):
        # parse_args([]) sets command=None
        args = self.parser.parse_args([])
        self.assertIsNone(args.command)

    def test_status(self):
        args = self.parser.parse_args(["status"])
        self.assertEqual(args.command, "status")

    def test_sell_with_defaults(self):
        args = self.parser.parse_args(["sell", "ore_iron"])
        self.assertEqual(args.item_id, "ore_iron")
        self.assertEqual(args.quantity, 1)

    def test_sell_with_quantity(self):
        args = self.parser.parse_args(["sell", "ore_copper", "10"])
        self.assertEqual(args.item_id, "ore_copper")
        self.assertEqual(args.quantity, 10)

    def test_buy_with_defaults(self):
        args = self.parser.parse_args(["buy", "fuel_cell"])
        self.assertEqual(args.item_id, "fuel_cell")
        self.assertEqual(args.quantity, 1)

    def test_buy_with_quantity(self):
        args = self.parser.parse_args(["buy", "fuel_cell", "5"])
        self.assertEqual(args.item_id, "fuel_cell")
        self.assertEqual(args.quantity, 5)

    def test_jump(self):
        args = self.parser.parse_args(["jump", "sys-abc-123"])
        self.assertEqual(args.target_system, "sys-abc-123")

    def test_travel(self):
        args = self.parser.parse_args(["travel", "poi-uuid-here"])
        self.assertEqual(args.poi_id, "poi-uuid-here")

    def test_chat(self):
        args = self.parser.parse_args(["chat", "local", "hello world"])
        self.assertEqual(args.channel, "local")
        self.assertEqual(args.message, "hello world")
        self.assertIsNone(args.target)

    def test_chat_private(self):
        args = self.parser.parse_args(["chat", "private", "hi", "player-123"])
        self.assertEqual(args.channel, "private")
        self.assertEqual(args.target, "player-123")

    def test_log_brief(self):
        args = self.parser.parse_args(["log", "--brief"])
        self.assertTrue(args.brief)

    def test_raw(self):
        args = self.parser.parse_args(["raw", "get_map"])
        self.assertEqual(args.endpoint, "get_map")
        self.assertIsNone(args.json_body)

    def test_raw_with_body(self):
        args = self.parser.parse_args(["raw", "sell", '{"item_id":"ore"}'])
        self.assertEqual(args.endpoint, "sell")
        self.assertEqual(args.json_body, '{"item_id":"ore"}')

    def test_json_flag(self):
        args = self.parser.parse_args(["--json", "status"])
        self.assertTrue(args.json)

    def test_unknown_command_raises(self):
        with self.assertRaises(SystemExit):
            self.parser.parse_args(["forum_list"])


# ---------------------------------------------------------------------------
# main() routing
# ---------------------------------------------------------------------------

class TestMainRouting(unittest.TestCase):
    """Test that main() routes to the right handler or passthrough."""

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_known_command_dispatches(self, mock_cmds, MockAPI):
        mock_cmds.cmd_status = MagicMock()
        # Put it in the real map temporarily
        with patch.dict(COMMAND_MAP, {"status": mock_cmds.cmd_status}):
            with patch("sys.argv", ["sm", "status"]):
                main()
        mock_cmds.cmd_status.assert_called_once()

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_unknown_command_goes_to_passthrough(self, mock_cmds, MockAPI):
        mock_cmds.cmd_passthrough = MagicMock()
        with patch("sys.argv", ["sm", "forum_list"]):
            main()
        mock_cmds.cmd_passthrough.assert_called_once()
        call_args = mock_cmds.cmd_passthrough.call_args
        self.assertEqual(call_args[0][1], "forum_list")  # endpoint
        self.assertEqual(call_args[0][2], [])  # extra_args
        self.assertFalse(call_args[1]["as_json"])

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_passthrough_with_positional_args(self, mock_cmds, MockAPI):
        mock_cmds.cmd_passthrough = MagicMock()
        with patch("sys.argv", ["sm", "scan", "player-uuid-123"]):
            main()
        call_args = mock_cmds.cmd_passthrough.call_args
        self.assertEqual(call_args[0][1], "scan")
        self.assertEqual(call_args[0][2], ["player-uuid-123"])

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_passthrough_with_kv_args(self, mock_cmds, MockAPI):
        mock_cmds.cmd_passthrough = MagicMock()
        with patch("sys.argv", ["sm", "attack", "target_id=abc"]):
            main()
        call_args = mock_cmds.cmd_passthrough.call_args
        self.assertEqual(call_args[0][2], ["target_id=abc"])

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_passthrough_with_json_flag(self, mock_cmds, MockAPI):
        mock_cmds.cmd_passthrough = MagicMock()
        with patch("sys.argv", ["sm", "forum_list", "--json"]):
            main()
        call_args = mock_cmds.cmd_passthrough.call_args
        self.assertTrue(call_args[1]["as_json"])

    @patch("spacemolt.cli.SpaceMoltAPI")
    @patch("spacemolt.cli.commands")
    def test_dash_to_underscore_in_passthrough(self, mock_cmds, MockAPI):
        mock_cmds.cmd_passthrough = MagicMock()
        with patch("sys.argv", ["sm", "forum-list"]):
            main()
        call_args = mock_cmds.cmd_passthrough.call_args
        self.assertEqual(call_args[0][1], "forum_list")

    @patch("spacemolt.cli.SpaceMoltAPI")
    def test_log_add_rewrite(self, MockAPI):
        """'sm log add text' should rewrite to log-add."""
        with patch.dict(COMMAND_MAP, {"log-add": MagicMock()}):
            with patch("sys.argv", ["sm", "log", "add", "my log entry"]):
                main()
            COMMAND_MAP["log-add"].assert_called_once()

    @patch("spacemolt.cli.SpaceMoltAPI")
    def test_json_flag_injected_into_known_command(self, MockAPI):
        handler = MagicMock()
        with patch.dict(COMMAND_MAP, {"ship": handler}):
            with patch("sys.argv", ["sm", "ship", "--json"]):
                main()
        args = handler.call_args[0][1]
        self.assertTrue(args.json)

    @patch("sys.stdout", new_callable=lambda: open(os.devnull, "w"))
    def test_no_args_prints_help(self, _):
        with patch("sys.argv", ["sm"]):
            # Should not raise — just print help
            main()


# ---------------------------------------------------------------------------
# cmd_passthrough
# ---------------------------------------------------------------------------

class TestCmdPassthrough(unittest.TestCase):

    def test_positional_args_mapped(self, ):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "scan", ["player-123"])
        api._post.assert_called_once_with("scan", {"target_id": "player-123"})

    def test_kv_args_mapped(self):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "attack", ["target_id=xyz"])
        api._post.assert_called_once_with("attack", {"target_id": "xyz"})

    def test_typed_int_arg(self):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "buy", ["ore_iron", "10"])
        api._post.assert_called_once_with("buy", {"item_id": "ore_iron", "quantity": 10})

    def test_typed_bool_arg(self):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "set_anonymous", ["true"])
        api._post.assert_called_once_with("set_anonymous", {"anonymous": True})

    def test_typed_int_via_kv(self):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "buy", ["item_id=fuel_cell", "quantity=5"])
        api._post.assert_called_once_with("buy", {"item_id": "fuel_cell", "quantity": 5})

    def test_mixed_positional_and_kv(self):
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "list_item", ["ore_iron", "quantity=10", "price_each=50"])
        body = api._post.call_args[0][1]
        self.assertEqual(body["item_id"], "ore_iron")
        self.assertEqual(body["quantity"], 10)
        self.assertEqual(body["price_each"], 50)

    def test_no_args_sends_empty_body(self):
        api = mock_api({"result": {}})
        with patch("builtins.print"):
            cmd_passthrough(api, "get_map", [])
        api._post.assert_called_once_with("get_map", {})

    def test_unknown_endpoint_no_specs(self):
        """Endpoints not in ENDPOINT_ARGS should still work with kv args."""
        api = mock_api({"result": {"ok": True}})
        with patch("builtins.print"):
            cmd_passthrough(api, "some_new_endpoint", ["foo=bar"])
        api._post.assert_called_once_with("some_new_endpoint", {"foo": "bar"})

    def test_extra_positional_warns(self):
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "scan", ["id1", "extra_stuff"])
        # Should have warned about the extra arg
        calls = [str(c) for c in mock_print.call_args_list]
        self.assertTrue(any("extra argument ignored" in c for c in calls))

    def test_as_json_outputs_full_response(self):
        resp = {"result": {"data": 123}, "notifications": []}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_map", [], as_json=True)
        printed = mock_print.call_args[0][0]
        self.assertEqual(json.loads(printed), resp)

    def test_error_response_prints_error(self):
        api = mock_api({"error": "not_found"})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "bad_endpoint", [])
        printed = mock_print.call_args[0][0]
        self.assertIn("ERROR", printed)

    def test_dict_error_response(self):
        api = mock_api({"error": {"code": "rate_limited", "message": "slow down"}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "mine", [])
        printed = mock_print.call_args[0][0]
        self.assertIn("slow down", printed)

    def test_multi_arg_endpoint(self):
        api = mock_api({"result": {}})
        with patch("builtins.print"):
            cmd_passthrough(api, "loot_wreck", ["wreck-1", "ore_iron", "5"])
        body = api._post.call_args[0][1]
        self.assertEqual(body, {"wreck_id": "wreck-1", "item_id": "ore_iron", "quantity": 5})


# ---------------------------------------------------------------------------
# Formatted handlers
# ---------------------------------------------------------------------------

class TestCmdStatus(unittest.TestCase):

    def test_basic_output(self):
        api = mock_api({"result": {
            "player": {
                "credits": 1500,
                "current_system_name": "Sol",
                "current_system_id": "sys-1",
                "current_poi_name": "Station Alpha",
                "current_poi_id": "poi-1",
                "docked_at_base": "base-1",
            },
            "ship": {
                "class_id": "prospector",
                "hull": 80, "max_hull": 100,
                "fuel": 45, "max_fuel": 50,
                "cargo_used": 3, "cargo_capacity": 10,
            },
        }})
        with patch("builtins.print") as mock_print:
            cmd_status(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("1500", output)
        self.assertIn("Sol", output)
        self.assertIn("prospector", output)
        self.assertIn("80/100", output)
        self.assertIn("45/50", output)


class TestCmdJump(unittest.TestCase):

    def test_success(self):
        api = mock_api({"result": {
            "destination": "Vega", "ticks": 10, "fuel_cost": 2,
        }})
        with patch("builtins.print") as mock_print:
            cmd_jump(api, make_args(target_system="sys-vega", json=False))
        printed = mock_print.call_args[0][0]
        self.assertIn("Vega", printed)
        self.assertIn("10 ticks", printed)
        self.assertIn("fuel: 2", printed)

    def test_error(self):
        api = mock_api({"error": "no_jump_gate"})
        with patch("builtins.print") as mock_print:
            cmd_jump(api, make_args(target_system="sys-x", json=False))
        self.assertIn("ERROR", mock_print.call_args[0][0])

    def test_json_mode(self):
        resp = {"result": {"destination": "Vega"}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_jump(api, make_args(target_system="sys-vega", json=True))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)


class TestCmdBuy(unittest.TestCase):

    def test_success(self):
        api = mock_api({"result": {"total_cost": 500}})
        with patch("builtins.print") as mock_print:
            cmd_buy(api, make_args(item_id="fuel_cell", quantity=5, json=False))
        printed = mock_print.call_args[0][0]
        self.assertIn("fuel_cell", printed)
        self.assertIn("x5", printed)
        self.assertIn("500", printed)

    def test_error(self):
        api = mock_api({"error": {"message": "not enough credits"}})
        with patch("builtins.print") as mock_print:
            cmd_buy(api, make_args(item_id="ship", quantity=1, json=False))
        self.assertIn("not enough credits", mock_print.call_args[0][0])


class TestCmdShip(unittest.TestCase):

    def test_with_modules(self):
        api = mock_api({"result": {"ship": {
            "class_id": "hauler",
            "hull": 200, "max_hull": 200,
            "shield": 50, "max_shield": 50,
            "fuel": 100, "max_fuel": 100,
            "cargo_used": 0, "cargo_capacity": 50,
            "cpu_used": 10, "cpu": 20,
            "power_used": 5, "power": 15,
            "modules": [
                {"name": "Mining Laser", "id": "mod-1", "slot": "high"},
                {"name": "Shield Booster", "id": "mod-2", "slot": "mid"},
            ],
        }}})
        with patch("builtins.print") as mock_print:
            cmd_ship(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("hauler", output)
        self.assertIn("Mining Laser", output)
        self.assertIn("[high]", output)
        self.assertIn("Modules (2)", output)


class TestCmdBase(unittest.TestCase):

    def test_with_services(self):
        api = mock_api({"result": {"base": {
            "name": "Sol Station",
            "id": "base-1",
            "owner": "NPC",
            "services": ["market", "repair", "refuel"],
            "has_market": True,
        }}})
        with patch("builtins.print") as mock_print:
            cmd_base(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Sol Station", output)
        self.assertIn("market", output)
        self.assertIn("repair", output)

    def test_error(self):
        api = mock_api({"error": "not_docked"})
        with patch("builtins.print") as mock_print:
            cmd_base(api, make_args(json=False))
        self.assertIn("ERROR", mock_print.call_args[0][0])


class TestCmdPoi(unittest.TestCase):

    def test_with_resources(self):
        api = mock_api({"result": {"poi": {
            "name": "Asteroid Belt Alpha",
            "type": "asteroid_belt",
            "id": "poi-1",
            "resources": [
                {"name": "Iron Ore", "richness": "abundant"},
                {"name": "Copper Ore", "richness": "moderate"},
            ],
        }}})
        with patch("builtins.print") as mock_print:
            cmd_poi(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Asteroid Belt Alpha", output)
        self.assertIn("Iron Ore", output)
        self.assertIn("abundant", output)


class TestCmdWrecks(unittest.TestCase):

    def test_no_wrecks(self):
        api = mock_api({"result": {"wrecks": []}})
        with patch("builtins.print") as mock_print:
            cmd_wrecks(api, make_args(json=False))
        self.assertIn("No wrecks", mock_print.call_args[0][0])

    def test_with_wrecks(self):
        api = mock_api({"result": {"wrecks": [{
            "id": "wreck-1",
            "owner": "pirate",
            "cargo": [{"item_id": "ore_iron", "quantity": 10}],
            "modules": [{"name": "Laser Mk1"}],
        }]}})
        with patch("builtins.print") as mock_print:
            cmd_wrecks(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("pirate", output)
        self.assertIn("ore_iron", output)
        self.assertIn("Laser Mk1", output)


class TestCmdListings(unittest.TestCase):

    def test_empty(self):
        api = mock_api({"result": {"listings": []}})
        with patch("builtins.print") as mock_print:
            cmd_listings(api, make_args(json=False))
        self.assertIn("No market listings", mock_print.call_args[0][0])

    def test_with_listings(self):
        api = mock_api({"result": {"listings": [
            {"item_id": "ore_iron", "quantity": 50, "price_each": 10,
             "seller_name": "Trader", "id": "list-1"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_listings(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("ore_iron", output)
        self.assertIn("Trader", output)


class TestCmdRecipes(unittest.TestCase):

    def test_empty(self):
        api = mock_api({"result": {"recipes": []}})
        with patch("builtins.print") as mock_print:
            cmd_recipes(api, make_args(json=False))
        self.assertIn("No recipes", mock_print.call_args[0][0])

    def test_with_recipe(self):
        api = mock_api({"result": {"recipes": [{
            "name": "Refined Steel",
            "id": "recipe-1",
            "inputs": [{"item_id": "ore_iron", "quantity": 5}],
            "outputs": [{"item_id": "refined_steel", "quantity": 1}],
            "requirements": [{"skill": "refinement", "level": 2}],
        }]}})
        with patch("builtins.print") as mock_print:
            cmd_recipes(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Refined Steel", output)
        self.assertIn("ore_iron x5", output)
        self.assertIn("refined_steel x1", output)
        self.assertIn("refinement L2", output)


class TestCmdCommands(unittest.TestCase):

    def test_grouped_output(self):
        api = mock_api({"result": {"commands": [
            {"name": "mine", "category": "resources", "description": "Mine ore"},
            {"name": "sell", "category": "trading", "description": "Sell items"},
            {"name": "attack", "category": "combat", "description": "Attack player"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_commands(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("RESOURCES", output)
        self.assertIn("TRADING", output)
        self.assertIn("COMBAT", output)
        self.assertIn("mine", output)

    def test_json_mode(self):
        resp = {"result": {"commands": [{"name": "mine", "category": "resources"}]}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_commands(api, make_args(json=True))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)

    def test_long_description_truncated(self):
        api = mock_api({"result": {"commands": [
            {"name": "test", "category": "misc",
             "description": "A" * 100},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_commands(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("...", output)


# ---------------------------------------------------------------------------
# Recipe helpers + query-recipes
# ---------------------------------------------------------------------------

# Shared fixture used across recipe tests
SAMPLE_RECIPES = {
    "basic_smelt_iron": {
        "id": "basic_smelt_iron", "name": "Basic Iron Smelting",
        "category": "Refining",
        "inputs": [{"item_id": "ore_iron", "quantity": 10}],
        "outputs": [{"item_id": "refined_steel", "quantity": 1, "quality_mod": True}],
        "required_skills": {}, "crafting_time": 3,
        "base_quality": 30, "skill_quality_mod": 3,
    },
    "refine_alloy": {
        "id": "refine_alloy", "name": "Alloy Refining",
        "category": "Refining",
        "inputs": [{"item_id": "refined_steel", "quantity": 1}],
        "outputs": [{"item_id": "refined_alloy", "quantity": 1, "quality_mod": True}],
        "required_skills": {"refinement": 2}, "crafting_time": 4,
        "base_quality": 40, "skill_quality_mod": 3,
    },
    "craft_hull_plate": {
        "id": "craft_hull_plate", "name": "Hull Plate",
        "category": "Components",
        "inputs": [
            {"item_id": "refined_steel", "quantity": 2},
            {"item_id": "refined_alloy", "quantity": 1},
        ],
        "outputs": [{"item_id": "comp_hull_plate", "quantity": 1, "quality_mod": False}],
        "required_skills": {"crafting_basic": 1}, "crafting_time": 5,
        "base_quality": 50, "skill_quality_mod": 3,
    },
    "craft_armor_plate_1": {
        "id": "craft_armor_plate_1", "name": "Build Armor Plate I",
        "category": "Defense",
        "inputs": [
            {"item_id": "refined_steel", "quantity": 4},
            {"item_id": "comp_hull_plate", "quantity": 1},
        ],
        "outputs": [{"item_id": "armor_plate_1", "quantity": 1, "quality_mod": True}],
        "required_skills": {"crafting_basic": 2}, "crafting_time": 8,
        "base_quality": 60, "skill_quality_mod": 4,
    },
}


class TestNormalizeRecipes(unittest.TestCase):

    def test_dict_input(self):
        result = _normalize_recipes(SAMPLE_RECIPES)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 4)

    def test_list_input(self):
        lst = list(SAMPLE_RECIPES.values())
        result = _normalize_recipes(lst)
        self.assertEqual(result, lst)

    def test_empty_dict(self):
        self.assertEqual(_normalize_recipes({}), [])

    def test_empty_list(self):
        self.assertEqual(_normalize_recipes([]), [])


class TestBuildRecipeIndexes(unittest.TestCase):

    def setUp(self):
        self.recipe_list = _normalize_recipes(SAMPLE_RECIPES)
        self.by_output, self.by_id = _build_recipe_indexes(self.recipe_list)

    def test_by_output_maps_item_to_recipe(self):
        self.assertEqual(self.by_output["refined_steel"]["id"], "basic_smelt_iron")
        self.assertEqual(self.by_output["comp_hull_plate"]["id"], "craft_hull_plate")
        self.assertEqual(self.by_output["armor_plate_1"]["id"], "craft_armor_plate_1")

    def test_by_id_maps_recipe_id_to_recipe(self):
        self.assertEqual(self.by_id["basic_smelt_iron"]["name"], "Basic Iron Smelting")
        self.assertEqual(self.by_id["craft_armor_plate_1"]["name"], "Build Armor Plate I")

    def test_raw_materials_not_in_by_output(self):
        self.assertNotIn("ore_iron", self.by_output)


class TestRecipeSkillTier(unittest.TestCase):

    def test_no_skills(self):
        level, label = _recipe_skill_tier(SAMPLE_RECIPES["basic_smelt_iron"])
        self.assertEqual(level, 0)
        self.assertEqual(label, "")

    def test_single_skill(self):
        level, label = _recipe_skill_tier(SAMPLE_RECIPES["refine_alloy"])
        self.assertEqual(level, 2)
        self.assertIn("refinement", label)

    def test_sorts_no_skills_first(self):
        tiers = [_recipe_skill_tier(r) for r in SAMPLE_RECIPES.values()]
        tiers.sort()
        self.assertEqual(tiers[0][0], 0)  # no-skill recipes sort first


class TestRecipeOneLine(unittest.TestCase):

    def test_single_input_output(self):
        line = _recipe_one_line(SAMPLE_RECIPES["basic_smelt_iron"])
        self.assertEqual(line, "10x ore_iron -> 1x refined_steel")

    def test_multi_input(self):
        line = _recipe_one_line(SAMPLE_RECIPES["craft_armor_plate_1"])
        self.assertIn("4x refined_steel", line)
        self.assertIn("1x comp_hull_plate", line)
        self.assertIn("->", line)
        self.assertIn("1x armor_plate_1", line)


class TestTraceIngredientTree(unittest.TestCase):

    def setUp(self):
        recipe_list = _normalize_recipes(SAMPLE_RECIPES)
        self.by_output, _ = _build_recipe_indexes(recipe_list)

    def test_raw_material_is_leaf(self):
        tree = _trace_ingredient_tree("ore_iron", 10, self.by_output)
        depth, item_id, qty, recipe, children = tree
        self.assertEqual(item_id, "ore_iron")
        self.assertEqual(qty, 10)
        self.assertIsNone(recipe)
        self.assertEqual(children, [])

    def test_single_step_recipe(self):
        tree = _trace_ingredient_tree("refined_steel", 1, self.by_output)
        depth, item_id, qty, recipe, children = tree
        self.assertEqual(item_id, "refined_steel")
        self.assertEqual(recipe["id"], "basic_smelt_iron")
        self.assertEqual(len(children), 1)
        # Child is ore_iron
        self.assertEqual(children[0][1], "ore_iron")
        self.assertEqual(children[0][2], 10)  # 1 * 10

    def test_deep_chain_multiplies_quantities(self):
        tree = _trace_ingredient_tree("armor_plate_1", 1, self.by_output)
        totals = _collect_raw_totals(tree)
        # armor_plate_1 needs:
        #   4x refined_steel = 40x ore_iron
        #   1x comp_hull_plate:
        #     2x refined_steel = 20x ore_iron
        #     1x refined_alloy:
        #       1x refined_steel = 10x ore_iron
        # Total: 70x ore_iron
        self.assertEqual(totals, {"ore_iron": 70})

    def test_quantity_scaling(self):
        tree = _trace_ingredient_tree("refined_steel", 3, self.by_output)
        totals = _collect_raw_totals(tree)
        self.assertEqual(totals, {"ore_iron": 30})

    def test_no_infinite_loops(self):
        """A cycle in recipes shouldn't cause infinite recursion."""
        # Create a circular recipe set
        circular = [
            {"id": "r1", "inputs": [{"item_id": "b", "quantity": 1}],
             "outputs": [{"item_id": "a", "quantity": 1}]},
            {"id": "r2", "inputs": [{"item_id": "a", "quantity": 1}],
             "outputs": [{"item_id": "b", "quantity": 1}]},
        ]
        by_output, _ = _build_recipe_indexes(circular)
        # Should terminate without error
        tree = _trace_ingredient_tree("a", 1, by_output)
        self.assertIsNotNone(tree)


class TestRenderTree(unittest.TestCase):

    def setUp(self):
        recipe_list = _normalize_recipes(SAMPLE_RECIPES)
        self.by_output, _ = _build_recipe_indexes(recipe_list)

    def test_single_step_rendering(self):
        tree = _trace_ingredient_tree("refined_steel", 1, self.by_output)
        lines = _render_tree(tree)
        self.assertTrue(any("refined_steel" in l for l in lines))
        self.assertTrue(any("ore_iron" in l for l in lines))
        self.assertTrue(any("basic_smelt_iron" in l for l in lines))

    def test_deep_tree_has_connectors(self):
        tree = _trace_ingredient_tree("armor_plate_1", 1, self.by_output)
        lines = _render_tree(tree)
        joined = "\n".join(lines)
        # Should have box-drawing connectors
        self.assertTrue("├" in joined or "└" in joined)
        # Root line should have skill requirement
        self.assertIn("crafting_basic", lines[0])

    def test_raw_leaf_has_no_recipe_annotation(self):
        tree = _trace_ingredient_tree("ore_iron", 5, self.by_output)
        lines = _render_tree(tree)
        self.assertEqual(len(lines), 1)
        self.assertNotIn("(", lines[0])  # no recipe annotation


class TestCollectRawTotals(unittest.TestCase):

    def setUp(self):
        recipe_list = _normalize_recipes(SAMPLE_RECIPES)
        self.by_output, _ = _build_recipe_indexes(recipe_list)

    def test_raw_material_only(self):
        tree = _trace_ingredient_tree("ore_iron", 5, self.by_output)
        self.assertEqual(_collect_raw_totals(tree), {"ore_iron": 5})

    def test_multi_raw_materials(self):
        # Create recipes with multiple raw inputs
        recipes = [
            {"id": "r1",
             "inputs": [{"item_id": "ore_a", "quantity": 3},
                        {"item_id": "ore_b", "quantity": 2}],
             "outputs": [{"item_id": "refined_x", "quantity": 1}]},
        ]
        by_output, _ = _build_recipe_indexes(recipes)
        tree = _trace_ingredient_tree("refined_x", 2, by_output)
        totals = _collect_raw_totals(tree)
        self.assertEqual(totals, {"ore_a": 6, "ore_b": 4})


class TestCmdQueryRecipes(unittest.TestCase):

    def _make_api(self):
        return mock_api({"result": {"recipes": SAMPLE_RECIPES}})

    def test_progression_default(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace=None, search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        # Should show skill tiers
        self.assertIn("No skill requirements", output)
        self.assertIn("crafting_basic", output)
        self.assertIn("refinement", output)
        # Should show categories
        self.assertIn("Refining", output)
        self.assertIn("Defense", output)
        # Should show chain markers
        self.assertIn("◆", output)
        # Should show legend
        self.assertIn("--trace", output)

    def test_progression_shows_recipe_flow(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace=None, search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("10x ore_iron -> 1x refined_steel", output)

    def test_search_finds_matches(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace=None, search="steel"))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        # All 4 recipes mention steel in inputs or outputs
        self.assertIn("Found 4 recipe(s)", output)
        self.assertIn("Basic Iron Smelting", output)
        self.assertIn("Hull Plate", output)

    def test_search_no_results(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace=None, search="nonexistent"))
        printed = mock_print.call_args[0][0]
        self.assertIn("No recipes matching", printed)

    def test_trace_by_item_id(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="armor_plate_1", search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("armor_plate_1", output)
        self.assertIn("ore_iron", output)
        self.assertIn("comp_hull_plate", output)
        # Should show raw totals
        self.assertIn("70x ore_iron", output)

    def test_trace_by_recipe_id(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="craft_armor_plate_1", search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("armor_plate_1", output)

    def test_trace_shows_tree_connectors(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="armor_plate_1", search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertTrue("├" in output or "└" in output)

    def test_trace_not_found(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="nonexistent_item", search=None))
        printed = mock_print.call_args[0][0]
        self.assertIn("No recipe produces", printed)

    def test_trace_fuzzy_match(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="armor", search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        # Should fuzzy-match to armor_plate_1
        self.assertIn("armor_plate_1", output)

    def test_trace_ambiguous_shows_candidates(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace="refined", search=None))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("did you mean", output.lower())

    def test_json_mode(self):
        resp = {"result": {"recipes": SAMPLE_RECIPES}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=True, trace=None, search=None))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)

    def test_empty_recipes(self):
        api = mock_api({"result": {"recipes": {}}})
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(json=False, trace=None, search=None))
        self.assertIn("No recipes", mock_print.call_args[0][0])


# ---------------------------------------------------------------------------
# Existing command regression
# ---------------------------------------------------------------------------

class TestExistingCommandsRegression(unittest.TestCase):
    """Ensure the original commands still work correctly after changes."""

    def test_cmd_cargo_empty(self):
        api = mock_api({"result": {"used": 0, "capacity": 10, "cargo": []}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_cargo
            cmd_cargo(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("0/10", output)
        self.assertIn("No cargo", output)

    def test_cmd_cargo_with_items(self):
        api = mock_api({"result": {
            "used": 5, "capacity": 10,
            "cargo": [
                {"item_id": "ore_iron", "quantity": 3},
                {"item_id": "ore_copper", "quantity": 2},
            ],
        }})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_cargo
            cmd_cargo(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("ore_iron x3", output)
        self.assertIn("ore_copper x2", output)

    def test_cmd_sell(self):
        api = mock_api({"result": {"credits_earned": 120}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_sell
            cmd_sell(api, make_args(item_id="ore_iron", quantity=10))
        printed = mock_print.call_args[0][0]
        self.assertIn("ore_iron", printed)
        self.assertIn("120", printed)

    def test_cmd_mine_success(self):
        api = mock_api({"result": {"message": "Mined iron ore x3"}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_mine
            cmd_mine(api, make_args())
        self.assertIn("Mined iron ore x3", mock_print.call_args[0][0])

    def test_cmd_mine_error(self):
        api = mock_api({"error": "not_at_asteroid_belt"})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_mine
            cmd_mine(api, make_args())
        self.assertIn("ERROR", mock_print.call_args[0][0])

    def test_cmd_refuel(self):
        api = mock_api({"result": {"fuel": 50, "max_fuel": 50}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_refuel
            cmd_refuel(api, make_args())
        self.assertIn("50/50", mock_print.call_args[0][0])

    def test_cmd_dock(self):
        api = mock_api({"result": {"base_name": "Starport", "base_id": "b1"}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_dock
            cmd_dock(api, make_args())
        self.assertIn("Starport", mock_print.call_args[0][0])

    def test_cmd_undock(self):
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_undock
            cmd_undock(api, make_args())
        self.assertIn("Undocked", mock_print.call_args[0][0])

    def test_cmd_skills_empty(self):
        api = mock_api({"result": {"player_skills": []}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_skills
            cmd_skills(api, make_args())
        self.assertIn("no skills", mock_print.call_args[0][0])

    def test_cmd_nearby_empty(self):
        api = mock_api({"result": {"nearby": []}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_nearby
            cmd_nearby(api, make_args())
        self.assertIn("No one nearby", mock_print.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
