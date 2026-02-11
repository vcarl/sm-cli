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
    cmd_travel,
    cmd_login,
    cmd_repair,
    cmd_log,
    cmd_pois,
    cmd_system,
    cmd_notifications,
    cmd_missions,
    cmd_active_missions,
    cmd_query_missions,
    cmd_skills,
    cmd_query_skills,
    cmd_skill,
    cmd_nearby,
    cmd_cargo,
    cmd_sell,
    cmd_mine,
    cmd_refuel,
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
        self.assertEqual(args.target_or_message, "hello world")
        self.assertIsNone(args.message)

    def test_chat_private(self):
        args = self.parser.parse_args(["chat", "private", "player-123", "hi"])
        self.assertEqual(args.channel, "private")
        self.assertEqual(args.target_or_message, "player-123")
        self.assertEqual(args.message, "hi")

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
            cmd_passthrough(api, "attack", ["target_id=xyz", "weapon_idx=0"])
        api._post.assert_called_once_with("attack", {"target_id": "xyz", "weapon_idx": 0})

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
        printed = mock_print.call_args_list[0][0][0]
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
        api = mock_api({"result": {
            "ship": {
                "class_id": "hauler",
                "hull": 200, "max_hull": 200,
                "shield": 50, "max_shield": 50,
                "fuel": 100, "max_fuel": 100,
                "cargo_used": 0, "cargo_capacity": 50,
                "cpu_used": 10, "cpu": 20,
                "power_used": 5, "power": 15,
                "modules": ["mod-1", "mod-2"],
                "cargo": [
                    {"item_id": "ore_iron", "quantity": 5},
                ],
            },
            "modules": [
                {"name": "Mining Laser", "id": "mod-1", "type": "mining", "quality_grade": "Standard", "wear_status": "Pristine"},
                {"name": "Shield Booster", "id": "mod-2", "type": "defense", "quality_grade": "Fine", "wear_status": "Worn"},
            ],
        }})
        with patch("builtins.print") as mock_print:
            cmd_ship(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("hauler", output)
        self.assertIn("Mining Laser", output)
        self.assertIn("[mining]", output)
        self.assertIn("Modules (2)", output)
        self.assertIn("Fine, Worn", output)
        self.assertIn("ore_iron x5", output)


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
        self.assertIn("No market listings", mock_print.call_args_list[0][0][0])

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
        self.assertIn("Starport", mock_print.call_args_list[0][0][0])

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
        api = mock_api({"result": {"nearby": [], "pirates": [], "pirate_count": 0}})
        with patch("builtins.print") as mock_print:
            from spacemolt.commands import cmd_nearby
            cmd_nearby(api, make_args())
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No one nearby", output)


# ---------------------------------------------------------------------------
# Passthrough formatters
# ---------------------------------------------------------------------------

class TestPassthroughFormatters(unittest.TestCase):
    """Test that passthrough commands with formatters show human-readable output."""

    def test_trades_formatted(self):
        api = mock_api({"result": {"trades": [
            {"id": "t1", "partner_name": "SpaceTrader", "status": "pending",
             "items_offered": [{"item_id": "ore_iron", "quantity": 10}]},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_trades", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("SpaceTrader", output)
        self.assertIn("pending", output)
        self.assertNotIn("{", output)

    def test_trades_empty(self):
        api = mock_api({"result": {"trades": []}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_trades", [])
        self.assertIn("No pending trades", mock_print.call_args[0][0])

    def test_drones_formatted(self):
        api = mock_api({"result": {"drones": [
            {"id": "d1234567890", "type": "mining", "status": "active"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_drones", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("mining", output)
        self.assertIn("active", output)
        self.assertNotIn("{", output)

    def test_drones_empty(self):
        api = mock_api({"result": {"drones": []}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_drones", [])
        self.assertIn("No active drones", mock_print.call_args[0][0])

    def test_ships_formatted(self):
        api = mock_api({"result": {"ships": [
            {"id": "s1", "class_id": "hauler", "name": "Big Bertha",
             "active": True, "hull": 200, "max_hull": 200},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_ships", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Big Bertha", output)
        self.assertIn("hauler", output)
        self.assertIn("ACTIVE", output)
        self.assertNotIn("{", output)

    def test_ships_empty(self):
        api = mock_api({"result": {"ships": []}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_ships", [])
        self.assertIn("No ships", mock_print.call_args[0][0])

    def test_faction_list_formatted(self):
        api = mock_api({"result": {"factions": [
            {"id": "f1", "name": "Star Alliance", "tag": "SA", "member_count": 5},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "faction_list", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Star Alliance", output)
        self.assertIn("[SA]", output)
        self.assertNotIn("{", output)

    def test_faction_info_formatted(self):
        api = mock_api({"result": {"faction": {
            "name": "Star Alliance", "tag": "SA", "id": "f1",
            "leader_name": "Admiral", "member_count": 5,
            "members": [{"username": "Player1", "role": "officer"}],
        }}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "faction_info", ["f1"])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Star Alliance", output)
        self.assertIn("Admiral", output)
        self.assertIn("Player1", output)
        self.assertNotIn("{", output)

    def test_faction_invites_formatted(self):
        api = mock_api({"result": {"invites": [
            {"faction_name": "Cool Faction", "faction_id": "f1", "invited_by": "Bob"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "faction_get_invites", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Cool Faction", output)
        self.assertIn("Bob", output)
        self.assertNotIn("{", output)

    def test_chat_history_formatted(self):
        api = mock_api({"result": {"messages": [
            {"sender_name": "Bob", "content": "hello", "channel": "local",
             "timestamp": "2025-01-01T12:00:00"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_chat_history", ["local", "50", "any"])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Bob", output)
        self.assertIn("hello", output)
        self.assertNotIn("{", output)

    def test_notes_formatted(self):
        api = mock_api({"result": {"notes": [
            {"id": "n1", "title": "My First Note", "created_at": "2025-01-01T00:00:00"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_notes", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("My First Note", output)
        self.assertNotIn("{", output)

    def test_read_note_formatted(self):
        api = mock_api({"result": {"note": {
            "id": "n1", "title": "Test Note", "content": "Hello world",
        }}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "read_note", ["n1"])
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Test Note", output)
        self.assertIn("Hello world", output)
        self.assertNotIn("{", output)

    def test_formatter_with_json_flag(self):
        """--json should bypass formatters and output raw JSON."""
        resp = {"result": {"trades": [{"id": "t1"}]}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_trades", [], as_json=True)
        printed = mock_print.call_args[0][0]
        self.assertEqual(json.loads(printed), resp)

    def test_action_message_extraction(self):
        """Action endpoints with 'message' field should show it, not JSON."""
        api = mock_api({"result": {"message": "Trade accepted!", "trade_id": "t1"}})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "trade_accept", ["t1"])
        calls = [c[0][0] for c in mock_print.call_args_list]
        self.assertIn("Trade accepted!", calls[0])
        combined = "\n".join(calls)
        self.assertIn("trade_id: t1", combined)


class TestAliasCommands(unittest.TestCase):
    """Test that alias commands are registered and known."""

    def test_alias_commands_known(self):
        known = _known_commands()
        for cmd in ["chat-history", "notes", "trades", "drones", "ships",
                     "faction-list", "faction-invites"]:
            self.assertIn(cmd, known, f"{cmd} not in known commands")

    def test_alias_subparsers_registered(self):
        parser = build_parser()
        for cmd in ["notes", "trades", "drones", "ships",
                     "faction-list", "faction-invites", "chat-history"]:
            args = parser.parse_args([cmd])
            self.assertEqual(args.command, cmd)


# ---------------------------------------------------------------------------
# Step 2: Unit tests for previously untested commands (#11)
# ---------------------------------------------------------------------------

class TestCmdTravel(unittest.TestCase):

    def test_success(self):
        api = mock_api({"result": {
            "destination": "Asteroid Belt Alpha",
            "ticks": 5,
            "fuel_cost": 1,
        }})
        with patch("builtins.print") as mock_print:
            cmd_travel(api, make_args(poi_id="poi-abc"))
        printed = mock_print.call_args_list[0][0][0]
        self.assertIn("Asteroid Belt Alpha", printed)
        self.assertIn("5 ticks", printed)
        self.assertIn("fuel: 1", printed)

    def test_error(self):
        api = mock_api({"error": "not_at_poi"})
        with patch("builtins.print") as mock_print:
            cmd_travel(api, make_args(poi_id="poi-bad"))
        self.assertIn("ERROR", mock_print.call_args[0][0])

    def test_no_fuel_cost(self):
        api = mock_api({"result": {"destination": "Station X", "ticks": 3}})
        with patch("builtins.print") as mock_print:
            cmd_travel(api, make_args(poi_id="poi-x"))
        printed = mock_print.call_args_list[0][0][0]
        self.assertIn("Station X", printed)
        self.assertNotIn("fuel", printed)


class TestCmdLogin(unittest.TestCase):

    def test_success(self):
        api = MagicMock()
        api.login.return_value = {"result": {
            "player": {"credits": 500, "current_system": "Sol", "current_poi": "Station",
                        "empire": 10, "docked_at_base": None},
            "ship": {"name": "Scout", "class_id": "starter",
                      "hull": 100, "max_hull": 100,
                      "shield": 50, "max_shield": 50,
                      "fuel": 40, "max_fuel": 50,
                      "cargo_used": 2, "cargo_capacity": 10},
            "system": {"name": "Sol"},
            "poi": {"name": "Station Alpha"},
        }}
        with patch("builtins.print") as mock_print:
            cmd_login(api, make_args(cred_file=None, json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Sol", output)
        self.assertIn("500 cr", output)

    def test_login_failure_returns_none(self):
        api = MagicMock()
        api.login.return_value = None
        with patch("builtins.print") as mock_print:
            cmd_login(api, make_args(cred_file=None, json=False))
        mock_print.assert_not_called()

    def test_json_mode(self):
        resp = {"result": {"player": {"credits": 100}}}
        api = MagicMock()
        api.login.return_value = resp
        with patch("builtins.print") as mock_print:
            cmd_login(api, make_args(cred_file=None, json=True))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)


class TestCmdRepair(unittest.TestCase):

    def test_success(self):
        api = mock_api({"result": {"hull": 200, "max_hull": 200}})
        with patch("builtins.print") as mock_print:
            cmd_repair(api, make_args())
        printed = mock_print.call_args[0][0]
        self.assertIn("Repaired", printed)
        self.assertIn("200/200", printed)

    def test_error(self):
        api = mock_api({"error": "not_docked"})
        with patch("builtins.print") as mock_print:
            cmd_repair(api, make_args())
        self.assertIn("ERROR", mock_print.call_args[0][0])


class TestCmdLog(unittest.TestCase):

    def test_with_entries(self):
        api = mock_api({"result": {"entries": [
            {"entry": "Found a rare asteroid field today.\nLots of platinum."},
            {"entry": "Sold cargo at Sol Station."},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_log(api, make_args(brief=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("rare asteroid", output)
        self.assertIn("Sold cargo", output)

    def test_brief_mode(self):
        api = mock_api({"result": {"entries": [
            {"entry": "Line one\nLine two\nLine three"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_log(api, make_args(brief=True))
        printed = mock_print.call_args[0][0]
        self.assertIn("Line one", printed)
        self.assertNotIn("Line two", printed)

    def test_empty_entries(self):
        api = mock_api({"result": {"entries": []}})
        with patch("builtins.print") as mock_print:
            cmd_log(api, make_args(brief=False))
        mock_print.assert_not_called()


class TestCmdPois(unittest.TestCase):

    def test_with_pois(self):
        api = mock_api({"result": {"pois": [
            {"name": "Asteroid Belt", "type": "asteroid_belt", "id": "poi-1", "distance": 2.5},
            {"name": "Station Alpha", "type": "station", "id": "poi-2", "distance": 0.1, "base_id": "base-1"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_pois(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Asteroid Belt", output)
        self.assertIn("Station Alpha", output)
        self.assertIn("base:base-1", output)
        self.assertIn("2.5 AU", output)

    def test_empty_pois(self):
        api = mock_api({"result": {"pois": []}})
        with patch("builtins.print") as mock_print:
            cmd_pois(api, make_args())
        mock_print.assert_not_called()


class TestCmdSystem(unittest.TestCase):

    def test_basic_output(self):
        api = mock_api({"result": {
            "system": {"name": "Sol", "police_level": 5, "connections": [
                {"name": "Alpha Centauri", "id": "sys-ac"},
            ]},
            "pois": [
                {"name": "Station", "type": "station", "id": "poi-1"},
            ],
        }})
        with patch("builtins.print") as mock_print:
            cmd_system(api, make_args())
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Sol", output)
        self.assertIn("Station", output)
        self.assertIn("Alpha Centauri", output)

    def test_string_connections(self):
        api = mock_api({"result": {
            "system": {"name": "Vega", "connections": ["sys-1", "sys-2"]},
            "pois": [],
        }})
        with patch("builtins.print") as mock_print:
            cmd_system(api, make_args())
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("sys-1", output)


class TestCmdNotifications(unittest.TestCase):

    def test_with_notifications(self):
        api = mock_api({"result": {}, "notifications": [{"msg": "test"}]})
        with patch("builtins.print") as mock_print:
            cmd_notifications(api, make_args())
        # Should NOT print "No notifications" since there are some
        for call in mock_print.call_args_list:
            self.assertNotIn("No notifications", call[0][0])

    def test_no_notifications(self):
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_notifications(api, make_args())
        self.assertIn("No notifications", mock_print.call_args[0][0])


class TestCmdMissions(unittest.TestCase):

    def test_with_missions(self):
        api = mock_api({"result": {"missions": [
            {"title": "Deliver Iron", "type": "delivery", "difficulty": "easy",
             "id": "m1", "description": "Bring iron to Sol",
             "reward_credits": 500, "location": "Sol", "distance": 2},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_missions(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Deliver Iron", output)
        self.assertIn("delivery", output)
        self.assertIn("500 cr", output)
        self.assertIn("Sol", output)

    def test_no_missions(self):
        api = mock_api({"result": {"missions": []}})
        with patch("builtins.print") as mock_print:
            cmd_missions(api, make_args(json=False))
        self.assertIn("No missions", mock_print.call_args[0][0])

    def test_json_mode(self):
        resp = {"result": {"missions": [{"title": "Test"}]}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_missions(api, make_args(json=True))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)


class TestCmdActiveMissions(unittest.TestCase):

    def test_with_active_missions(self):
        api = mock_api({"result": {"missions": [
            {"title": "Mine 100 Iron", "id": "m1", "status": "in_progress",
             "progress": {"current": 50, "target": 100},
             "deadline_tick": 500,
             "rewards": {"credits": 1000, "items": [{"item_id": "fuel_cell", "quantity": 5}]}},
        ], "max_missions": 3}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Mine 100 Iron", output)
        self.assertIn("in_progress", output)
        self.assertIn("50/100", output)
        self.assertIn("tick 500", output)
        self.assertIn("1000 cr", output)

    def test_no_active_missions(self):
        api = mock_api({"result": {"missions": [], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        printed = mock_print.call_args[0][0]
        self.assertIn("No active missions", printed)
        self.assertIn("0/5", printed)

    def test_description_displayed(self):
        api = mock_api({"result": {"missions": [
            {"title": "Copper Requisition", "id": "m1", "status": "in_progress",
             "description": "Mine 25 copper ore",
             "progress": {"current": 10, "target": 25},
             "rewards": {"credits": 1800}},
        ], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Mine 25 copper ore", output)
        self.assertIn("10/25", output)

    def test_objectives_displayed(self):
        api = mock_api({"result": {"missions": [
            {"title": "Supply Run", "id": "m1", "status": "in_progress",
             "objectives": [
                 {"description": "Mine copper", "current": 10, "target": 25},
                 {"description": "Deliver to Sol", "current": 0, "target": 1},
             ],
             "rewards": {"credits": 1800}},
        ], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Mine copper: 10/25", output)
        self.assertIn("Deliver to Sol: 0/1", output)

    def test_objectives_string_format(self):
        api = mock_api({"result": {"missions": [
            {"title": "Scout", "id": "m1", "status": "active",
             "objectives": ["Scan 3 sectors", "Return to base"]},
        ], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Scan 3 sectors", output)
        self.assertIn("Return to base", output)


class TestCmdQueryMissions(unittest.TestCase):

    def test_search(self):
        api = mock_api({"result": {"missions": [
            {"title": "Deliver Iron", "type": "delivery", "id": "m1",
             "difficulty": 1, "reward_credits": 500},
            {"title": "Kill Pirates", "type": "combat", "id": "m2",
             "difficulty": 3, "reward_credits": 2000},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_query_missions(api, make_args(
                json=False, active=False, search="iron", limit=10, page=1))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Deliver Iron", output)
        self.assertNotIn("Kill Pirates", output)

    def test_active_delegates(self):
        """--active should delegate to cmd_active_missions."""
        api = mock_api({"result": {"missions": [], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_query_missions(api, make_args(
                json=False, active=True, search=None, limit=10, page=1))
        printed = mock_print.call_args[0][0]
        self.assertIn("No active missions", printed)

    def test_no_results_search(self):
        api = mock_api({"result": {"missions": [
            {"title": "Deliver Iron", "type": "delivery", "id": "m1"},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_query_missions(api, make_args(
                json=False, active=False, search="nonexistent", limit=10, page=1))
        self.assertIn("No missions matching", mock_print.call_args[0][0])


class TestCmdSkills(unittest.TestCase):

    def test_with_skills(self):
        api = mock_api({"result": {"player_skills": [
            {"name": "Mining", "level": 3, "current_xp": 150, "next_level_xp": 300},
            {"name": "Trading", "level": 1, "current_xp": 10, "next_level_xp": 100},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_skills(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Mining", output)
        self.assertIn("L3", output)
        self.assertIn("Trading", output)

    def test_no_skills(self):
        api = mock_api({"result": {"player_skills": []}})
        with patch("builtins.print") as mock_print:
            cmd_skills(api, make_args())
        self.assertIn("no skills", mock_print.call_args[0][0])


SAMPLE_SKILL_DATA = {
    "mining_basic": {
        "id": "mining_basic", "name": "Basic Mining", "category": "Resource",
        "max_level": 5, "required_skills": {},
        "description": "Improves mining yield",
        "bonus_per_level": {"mining_yield": 0.1},
        "xp_per_level": [100, 250, 500, 1000, 2000],
    },
    "mining_advanced": {
        "id": "mining_advanced", "name": "Advanced Mining", "category": "Resource",
        "max_level": 3, "required_skills": {"mining_basic": 3},
        "description": "Unlocks rare ore mining",
        "bonus_per_level": {"rare_ore_chance": 0.05},
        "xp_per_level": [500, 1500, 4000],
    },
    "trading_basic": {
        "id": "trading_basic", "name": "Basic Trading", "category": "Commerce",
        "max_level": 5, "required_skills": {},
        "description": "Better trade prices",
        "bonus_per_level": {"price_bonus": 0.02},
        "xp_per_level": [100, 200, 400, 800, 1600],
    },
}


class TestCmdQuerySkills(unittest.TestCase):

    def _make_api(self, player_skills=None):
        return mock_api({"result": {
            "skills": SAMPLE_SKILL_DATA,
            "player_skills": player_skills or [],
        }})

    def test_list_by_category(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_skills(api, make_args(
                json=False, search=None, my=False, limit=10, page=1))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("RESOURCE", output)
        self.assertIn("COMMERCE", output)
        self.assertIn("Basic Mining", output)

    def test_search(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_query_skills(api, make_args(
                json=False, search="mining", my=False, limit=10, page=1))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Basic Mining", output)
        self.assertIn("Advanced Mining", output)
        self.assertNotIn("Trading", output)

    def test_no_skill_data(self):
        api = mock_api({"result": {"skills": {}, "player_skills": []}})
        with patch("builtins.print") as mock_print:
            cmd_query_skills(api, make_args(
                json=False, search=None, my=False, limit=10, page=1))
        self.assertIn("No skill data", mock_print.call_args[0][0])

    def test_json_mode(self):
        resp = {"result": {"skills": SAMPLE_SKILL_DATA, "player_skills": []}}
        api = mock_api(resp)
        with patch("builtins.print") as mock_print:
            cmd_query_skills(api, make_args(
                json=True, search=None, my=False, limit=10, page=1))
        self.assertEqual(json.loads(mock_print.call_args[0][0]), resp)

    def test_my_skills(self):
        api = self._make_api(player_skills=[
            {"skill_id": "mining_basic", "name": "Basic Mining", "level": 3,
             "current_xp": 400, "next_level_xp": 1000, "max_level": 5},
        ])
        with patch("builtins.print") as mock_print:
            cmd_query_skills(api, make_args(
                json=False, search=None, my=True, limit=10, page=1))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Basic Mining", output)
        self.assertIn("L3", output)


class TestCmdSkill(unittest.TestCase):

    def _make_api(self, player_skills=None):
        return mock_api({"result": {
            "skills": SAMPLE_SKILL_DATA,
            "player_skills": player_skills or [],
        }})

    def test_exact_match(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="mining_basic"))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Basic Mining", output)
        self.assertIn("Prerequisite tree", output)

    def test_fuzzy_match(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="trading"))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Basic Trading", output)

    def test_not_found(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="nonexistent_skill"))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("No skill matching", output)

    def test_no_skill_data(self):
        api = mock_api({"result": {"skills": {}, "player_skills": []}})
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="mining_basic"))
        self.assertIn("No skill data", mock_print.call_args[0][0])

    def test_shows_unlocks(self):
        """Should show what skills are unlocked at each level."""
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="mining_basic"))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        # mining_basic L3 unlocks mining_advanced
        self.assertIn("Advanced Mining", output)

    def test_shows_xp_table(self):
        api = self._make_api()
        with patch("builtins.print") as mock_print:
            cmd_skill(api, make_args(
                json=False, skill_id="mining_basic"))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("XP requirements", output)
        self.assertIn("L1:", output)


# ---------------------------------------------------------------------------
# Step 3: Error-path and edge-case tests (#12)
# ---------------------------------------------------------------------------

class TestCmdStatusErrors(unittest.TestCase):

    def test_empty_result(self):
        """cmd_status with empty result should not crash."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_status(api, make_args())
        # Should still print something (defaults to '?')
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("?", output)

    def test_missing_ship_key(self):
        """Result with player but no ship data."""
        api = mock_api({"result": {"player": {"credits": 100}}})
        with patch("builtins.print") as mock_print:
            cmd_status(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("100", output)


class TestCmdShipErrors(unittest.TestCase):

    def test_empty_ship(self):
        api = mock_api({"result": {"ship": {}}})
        with patch("builtins.print") as mock_print:
            cmd_ship(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("?", output)

    def test_modules_as_string_ids(self):
        """When modules are just string IDs, not rich dicts."""
        api = mock_api({"result": {"ship": {
            "class_id": "hauler",
            "hull": 100, "max_hull": 100,
            "shield": 50, "max_shield": 50,
            "fuel": 50, "max_fuel": 50,
            "cargo_used": 0, "cargo_capacity": 20,
            "cpu_used": 0, "cpu": 10,
            "power_used": 0, "power": 10,
            "modules": ["mod-id-1", "mod-id-2"],
            "cargo": [],
        }}})
        with patch("builtins.print") as mock_print:
            cmd_ship(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Modules (2)", output)
        self.assertIn("mod-id-1", output)


class TestCmdNearbyErrors(unittest.TestCase):

    def test_empty_nearby(self):
        api = MagicMock()
        api._post.return_value = {"result": {"nearby": [], "pirates": [], "pirate_count": 0}}
        api._print_notifications = MagicMock()
        with patch("builtins.print") as mock_print:
            cmd_nearby(api, make_args(scan=False, json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("No one nearby", output)

    def test_with_anonymous_player(self):
        api = MagicMock()
        api._post.side_effect = [
            {"result": {"nearby": [
                {"username": "hidden", "player_id": "p1", "ship_class": "starter",
                 "anonymous": True, "in_combat": False},
            ], "pirates": [], "pirate_count": 0}},
            {"result": {"poi": {"name": "Belt", "id": "poi-1", "type": "asteroid_belt"}}},
        ]
        api._print_notifications = MagicMock()
        with patch("builtins.print") as mock_print:
            cmd_nearby(api, make_args(scan=False, json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("anon", output)


class TestCmdPassthroughErrors(unittest.TestCase):

    def test_missing_args_shows_usage(self):
        """Calling an endpoint that requires args with no args shows usage."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "scan", [])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Usage:", output)
        # Should NOT have called the API
        api._post.assert_not_called()

    def test_partial_args_shows_missing(self):
        """Providing some but not all required args."""
        api = mock_api({})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "list_item", ["ore_iron", "10"])
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("Missing:", output)
        self.assertIn("price_each", output)

    def test_result_as_string(self):
        """API returning a plain string result."""
        api = mock_api({"result": "Action completed successfully."})
        with patch("builtins.print") as mock_print:
            cmd_passthrough(api, "get_map", [])
        self.assertIn("Action completed", mock_print.call_args[0][0])


class TestCmdQueryRecipesErrors(unittest.TestCase):

    def test_trace_nonexistent_item(self):
        api = mock_api({"result": {"recipes": SAMPLE_RECIPES}})
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(
                json=False, trace="totally_fake_item", search=None))
        printed = mock_print.call_args[0][0]
        self.assertIn("No recipe produces", printed)

    def test_empty_api_response(self):
        """Completely empty recipes from API."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(
                json=False, trace=None, search=None))
        self.assertIn("No recipes", mock_print.call_args[0][0])

    def test_error_response(self):
        """API returns an error for get_recipes."""
        api = mock_api({"result": {"recipes": {}}})
        with patch("builtins.print") as mock_print:
            cmd_query_recipes(api, make_args(
                json=False, trace=None, search=None))
        self.assertIn("No recipes", mock_print.call_args[0][0])


class TestCmdMissionsErrors(unittest.TestCase):

    def test_mission_with_reward_items(self):
        """Mission with item rewards but no credit reward."""
        api = mock_api({"result": {"missions": [
            {"title": "Salvage Run", "type": "salvage", "id": "m1",
             "reward_items": [{"item_id": "rare_ore", "quantity": 3}]},
        ]}})
        with patch("builtins.print") as mock_print:
            cmd_missions(api, make_args(json=False))
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("rare_ore x3", output)

    def test_active_mission_scalar_progress(self):
        """Active mission with progress as a plain string."""
        api = mock_api({"result": {"missions": [
            {"title": "Explore", "id": "m1", "status": "active",
             "progress": "3/10 sectors scanned",
             "rewards": {"credits": 500}},
        ], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("3/10 sectors scanned", output)

    def test_active_mission_list_rewards(self):
        """Active mission with rewards as a list instead of dict."""
        api = mock_api({"result": {"missions": [
            {"title": "Bounty", "id": "m1", "status": "active",
             "rewards": ["500 cr", "rare_gem x1"]},
        ], "max_missions": 5}})
        with patch("builtins.print") as mock_print:
            cmd_active_missions(api, make_args(json=False))
        output = "\n".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("500 cr", output)


class TestCmdCargoErrors(unittest.TestCase):

    def test_api_error_graceful(self):
        """Cargo with missing fields should use defaults."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_cargo(api, make_args())
        output = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("0/", output)


class TestCmdSellErrors(unittest.TestCase):

    def test_sell_error(self):
        api = mock_api({"error": "not_docked"})
        with patch("builtins.print") as mock_print:
            cmd_sell(api, make_args(item_id="ore_iron", quantity=5))
        self.assertIn("ERROR", mock_print.call_args[0][0])

    def test_sell_no_credits_field(self):
        """Sell response with no recognizable credits field."""
        api = mock_api({"result": {"status": "ok"}})
        with patch("builtins.print") as mock_print:
            cmd_sell(api, make_args(item_id="ore_iron", quantity=1))
        printed = mock_print.call_args[0][0]
        self.assertIn("Sold", printed)
        self.assertIn("ore_iron", printed)


class TestCmdMineErrors(unittest.TestCase):

    def test_mine_error(self):
        api = mock_api({"error": "not_at_asteroid_belt"})
        with patch("builtins.print") as mock_print:
            cmd_mine(api, make_args())
        self.assertIn("ERROR", mock_print.call_args[0][0])

    def test_mine_no_message(self):
        """Mine success but result has no message field."""
        api = mock_api({"result": {}})
        with patch("builtins.print") as mock_print:
            cmd_mine(api, make_args())
        # Should not crash; just doesn't print anything
        mock_print.assert_not_called()


class TestCmdRefuelErrors(unittest.TestCase):

    def test_refuel_error(self):
        api = mock_api({"error": "not_docked"})
        with patch("builtins.print") as mock_print:
            cmd_refuel(api, make_args())
        self.assertIn("ERROR", mock_print.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
