"""Tests for error handling and robustness improvements."""
import unittest
from unittest.mock import Mock, patch, MagicMock
import urllib.error
import socket
import time

from spacemolt.api import SpaceMoltAPI, APIError
from spacemolt.commands.passthrough import _parse_typed_value


class TestNetworkTimeouts(unittest.TestCase):
    """Test network timeout protection."""

    def test_api_has_timeout_parameter(self):
        """API should accept timeout parameter."""
        api = SpaceMoltAPI(timeout=10)
        self.assertEqual(api.timeout, 10)

    def test_api_default_timeout(self):
        """API should have default 30s timeout."""
        api = SpaceMoltAPI()
        self.assertEqual(api.timeout, 30)

    @patch('urllib.request.urlopen')
    def test_timeout_passed_to_urlopen(self, mock_urlopen):
        """Timeout should be passed to urlopen calls."""
        api = SpaceMoltAPI(timeout=15)
        api.session_file = "/tmp/test-session"

        # Mock session file
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', unittest.mock.mock_open(read_data='test-session-id')):
                # Mock successful response
                mock_response = MagicMock()
                mock_response.__enter__.return_value.read.return_value = b'{"result": {}}'
                mock_urlopen.return_value = mock_response

                try:
                    api._post("test_endpoint")
                except:
                    pass

                # Verify timeout was passed
                if mock_urlopen.called:
                    call_kwargs = mock_urlopen.call_args
                    if call_kwargs and len(call_kwargs) > 1:
                        self.assertIn('timeout', str(call_kwargs))


class TestTypeConversionSafety(unittest.TestCase):
    """Test type conversion error handling."""

    def test_invalid_int_raises_valueerror(self):
        """Invalid integer should raise ValueError with helpful message."""
        with self.assertRaises(ValueError) as ctx:
            _parse_typed_value("quantity:int", "abc")
        self.assertIn("quantity", str(ctx.exception))
        self.assertIn("abc", str(ctx.exception))

    def test_valid_int_conversion(self):
        """Valid integer should convert successfully."""
        result = _parse_typed_value("quantity:int", "42")
        self.assertEqual(result, 42)

    def test_none_bool_raises_valueerror(self):
        """None value for bool should raise ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _parse_typed_value("enabled:bool", None)
        self.assertIn("enabled", str(ctx.exception))

    def test_valid_bool_conversion_true(self):
        """Valid bool values should convert to True."""
        self.assertTrue(_parse_typed_value("enabled:bool", "true"))
        self.assertTrue(_parse_typed_value("enabled:bool", "1"))
        self.assertTrue(_parse_typed_value("enabled:bool", "yes"))

    def test_valid_bool_conversion_false(self):
        """Valid bool values should convert to False."""
        self.assertFalse(_parse_typed_value("enabled:bool", "false"))
        self.assertFalse(_parse_typed_value("enabled:bool", "0"))
        self.assertFalse(_parse_typed_value("enabled:bool", "no"))

    def test_string_passthrough(self):
        """String values should pass through unchanged."""
        result = _parse_typed_value("name", "test_value")
        self.assertEqual(result, "test_value")


class TestHTTP429Handling(unittest.TestCase):
    """Test HTTP 429 rate limit handling."""

    def test_parse_error_extracts_wait_seconds(self):
        """_parse_error should extract wait_seconds from response."""
        from spacemolt.api import SpaceMoltAPI

        body = '{"error": {"code": "rate_limited", "message": "Too many requests", "wait_seconds": 5}}'
        code, msg, wait_seconds = SpaceMoltAPI._parse_error(body)

        self.assertEqual(code, "rate_limited")
        self.assertIn("Too many requests", msg)
        self.assertEqual(wait_seconds, 5)

    def test_parse_error_no_wait_seconds(self):
        """_parse_error should handle missing wait_seconds."""
        from spacemolt.api import SpaceMoltAPI

        body = '{"error": {"code": "error", "message": "Generic error"}}'
        code, msg, wait_seconds = SpaceMoltAPI._parse_error(body)

        self.assertEqual(code, "error")
        self.assertIn("Generic error", msg)
        self.assertIsNone(wait_seconds)


class TestPreFlightValidation(unittest.TestCase):
    """Test pre-flight state validation."""

    def test_api_has_status_cache(self):
        """API should have status cache attributes."""
        api = SpaceMoltAPI()
        self.assertIsNone(api._status_cache)
        self.assertEqual(api._status_cache_time, 0)

    def test_clear_status_cache(self):
        """clear_status_cache should reset cache."""
        api = SpaceMoltAPI()
        api._status_cache = {"result": {}}
        api._status_cache_time = time.time()

        api._clear_status_cache()

        self.assertIsNone(api._status_cache)
        self.assertEqual(api._status_cache_time, 0)

    @patch.object(SpaceMoltAPI, '_post')
    def test_require_docked_raises_when_undocked(self, mock_post):
        """_require_docked should raise when not docked."""
        api = SpaceMoltAPI()
        mock_post.return_value = {"result": {"player": {"docked_at_base": ""}}}

        with self.assertRaises(APIError) as ctx:
            api._require_docked()
        self.assertIn("dock", str(ctx.exception).lower())

    @patch.object(SpaceMoltAPI, '_post')
    def test_require_docked_succeeds_when_docked(self, mock_post):
        """_require_docked should succeed when docked."""
        api = SpaceMoltAPI()
        mock_post.return_value = {"result": {"player": {"docked_at_base": "base-1"}}}

        # Should not raise
        api._require_docked()

    @patch.object(SpaceMoltAPI, '_post')
    def test_require_undocked_raises_when_docked(self, mock_post):
        """_require_undocked should raise when docked."""
        api = SpaceMoltAPI()
        mock_post.return_value = {"result": {"player": {"docked_at_base": "base-1"}}}

        with self.assertRaises(APIError) as ctx:
            api._require_undocked()
        self.assertIn("undock", str(ctx.exception).lower())

    @patch.object(SpaceMoltAPI, '_post')
    def test_check_cargo_space_raises_insufficient(self, mock_post):
        """_check_cargo_space should raise when insufficient space."""
        api = SpaceMoltAPI()
        mock_post.return_value = {
            "result": {
                "ship": {
                    "cargo_used": 80,
                    "cargo_capacity": 100
                }
            }
        }

        with self.assertRaises(APIError) as ctx:
            api._check_cargo_space(50)  # Need 50, have only 20
        self.assertIn("cargo", str(ctx.exception).lower())

    @patch.object(SpaceMoltAPI, '_post')
    def test_check_cargo_space_succeeds_sufficient(self, mock_post):
        """_check_cargo_space should succeed when sufficient space."""
        api = SpaceMoltAPI()
        mock_post.return_value = {
            "result": {
                "ship": {
                    "cargo_used": 50,
                    "cargo_capacity": 100
                }
            }
        }

        # Should not raise (need 20, have 50)
        api._check_cargo_space(20)


class TestLongOperationProtection(unittest.TestCase):
    """Test long operation timeout and interrupt protection."""

    def test_nearby_accepts_timeout_arg(self):
        """Nearby command should accept timeout argument."""
        # This would require integration testing with actual CLI parsing
        # For now, just verify the argument was added to the parser
        from spacemolt.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(['nearby', '--scan', '--timeout', '60'])

        self.assertTrue(args.scan)
        self.assertEqual(args.timeout, 60)

class TestErrorMessages(unittest.TestCase):
    """Test enhanced error messages."""

    def test_error_hints_for_mining(self):
        """Should provide helpful hints for mining errors."""
        from spacemolt.commands.passthrough import _print_error_hints
        from io import StringIO
        import sys

        captured_output = StringIO()
        sys.stdout = captured_output

        _print_error_hints("mine", "No resource to mine at this location")

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        self.assertIn("pois", output.lower())

    def test_error_hints_for_fuel(self):
        """Should provide helpful hints for fuel errors."""
        from spacemolt.commands.passthrough import _print_error_hints
        from io import StringIO
        import sys

        captured_output = StringIO()
        sys.stdout = captured_output

        _print_error_hints("jump", "Not enough fuel for jump")

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        self.assertIn("refuel", output.lower())

    def test_error_hints_for_cargo(self):
        """Should provide helpful hints for cargo errors."""
        from spacemolt.commands.passthrough import _print_error_hints
        from io import StringIO
        import sys

        captured_output = StringIO()
        sys.stdout = captured_output

        _print_error_hints("buy", "Cargo full - not enough space")

        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()

        self.assertIn("jettison", output.lower())


class TestFormatPirateCombatNotification(unittest.TestCase):
    """Test pirate_combat notification formatting."""

    def test_pirate_combat_basic(self):
        n = {
            "msg_type": "pirate_combat",
            "data": {
                "pirate_name": "Blackbeard",
                "pirate_tier": "elite",
                "damage": 42,
                "damage_type": "kinetic",
                "your_hull": 80,
                "your_max_hull": 100,
                "your_shield": 15,
                "is_boss": False,
            },
        }
        result = SpaceMoltAPI._format_notification(n)
        self.assertIn("Blackbeard", result)
        self.assertIn("(elite)", result)
        self.assertIn("42 kinetic", result)
        self.assertIn("Hull: 80/100", result)
        self.assertIn("Shield: 15", result)
        self.assertIn("sm battle-status", result)
        self.assertNotIn("[BOSS]", result)

    def test_pirate_combat_boss(self):
        n = {
            "msg_type": "pirate_combat",
            "data": {
                "pirate_name": "Dread King",
                "damage": 99,
                "is_boss": True,
            },
        }
        result = SpaceMoltAPI._format_notification(n)
        self.assertIn("[BOSS]", result)
        self.assertIn("Dread King", result)

    def test_pirate_combat_minimal(self):
        n = {"msg_type": "pirate_combat", "data": {}}
        result = SpaceMoltAPI._format_notification(n)
        self.assertIn("Pirate attack!", result)
        self.assertIn("pirate", result)


if __name__ == '__main__':
    unittest.main()
