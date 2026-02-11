"""Tests for the register command."""

import unittest
from unittest.mock import Mock
from io import StringIO
import sys

from spacemolt.commands.actions import cmd_register
from spacemolt.cli import build_parser


class TestRegisterParser(unittest.TestCase):
    """Test register command argument parsing."""

    def test_register_with_all_args(self):
        parser = build_parser()
        args = parser.parse_args(["register", "TestUser", "solarian"])
        self.assertEqual(args.command, "register")
        self.assertEqual(args.username, "TestUser")
        self.assertEqual(args.empire, "solarian")

    def test_register_all_empires(self):
        parser = build_parser()
        empires = ["solarian", "voidborn", "crimson", "nebula", "outerrim"]
        for empire in empires:
            args = parser.parse_args(["register", "TestUser", empire])
            self.assertEqual(args.empire, empire)

    def test_register_requires_username(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["register"])

    def test_register_requires_empire(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["register", "TestUser"])

    def test_register_invalid_empire(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["register", "TestUser", "invalid-empire"])


class TestRegisterCommand(unittest.TestCase):
    """Test register command execution."""

    def test_register_success_interactive(self):
        # Mock API (needs to handle both session creation and register)
        api = Mock()
        api._post.side_effect = [
            {"session": {"id": "test-session-123"}},  # session creation
            {"result": {"username": "TestUser", "empire": "solarian", "password": "test-password-123", "session_id": "test-session-id-456"}}  # register
        ]
        api.session_file = "/tmp/test-session"

        # Mock args
        args = Mock()
        args.username = "TestUser"
        args.empire = "solarian"
        args.json = False

        # Capture stdout (interactive mode - isatty returns True)
        captured = StringIO()
        captured.isatty = lambda: True
        sys.stdout = captured

        cmd_register(api, args)
        sys.stdout = sys.__stdout__

        output = captured.getvalue()

        # Verify output contains key information (interactive mode)
        self.assertIn("REGISTRATION SUCCESSFUL", output)
        self.assertIn("TestUser", output)
        self.assertIn("solarian", output)
        self.assertIn("test-password-123", output)
        self.assertIn("WARNING", output)
        self.assertIn("NO password recovery", output)

    def test_register_success_piped(self):
        # Mock API (needs to handle both session creation and register)
        api = Mock()
        api._post.side_effect = [
            {"session": {"id": "test-session-123"}},  # session creation
            {"result": {"username": "TestUser", "empire": "solarian", "password": "test-password-123", "session_id": "test-session-id-456"}}  # register
        ]
        api.session_file = "/tmp/test-session"

        # Mock args
        args = Mock()
        args.username = "TestUser"
        args.empire = "solarian"
        args.json = False

        # Capture stdout (piped mode - isatty returns False)
        captured = StringIO()
        captured.isatty = lambda: False
        sys.stdout = captured

        cmd_register(api, args)
        sys.stdout = sys.__stdout__

        output = captured.getvalue()

        # Verify output is credentials format only (piped mode)
        self.assertIn("Username: TestUser", output)
        self.assertIn("Password: test-password-123", output)
        self.assertNotIn("REGISTRATION SUCCESSFUL", output)
        self.assertNotIn("WARNING", output)

    def test_register_json_mode(self):
        # Mock API
        api = Mock()
        api._post.return_value = {
            "result": {
                "username": "TestUser",
                "empire": "solarian",
                "password": "test-password-123",
            }
        }
        api.session_file = "/tmp/test-session"

        # Mock args
        args = Mock()
        args.username = "TestUser"
        args.empire = "solarian"
        args.json = True

        # Capture stdout
        captured = StringIO()
        sys.stdout = captured

        cmd_register(api, args)
        sys.stdout = sys.__stdout__

        output = captured.getvalue()

        # Verify JSON output
        self.assertIn('"username"', output)
        self.assertIn('"password"', output)
        self.assertIn('"empire"', output)

    def test_register_error_handling(self):
        # Mock API with error (first call creates session, second returns error)
        api = Mock()
        api._post.side_effect = [
            {"session": {"id": "test-session"}},  # session creation
            {"error": {"message": "Username already taken"}}  # register error
        ]
        api.session_file = "/tmp/test-session"

        # Mock args
        args = Mock()
        args.username = "TakenUser"
        args.empire = "solarian"
        args.json = False

        # Capture stdout
        captured = StringIO()
        sys.stdout = captured

        cmd_register(api, args)
        sys.stdout = sys.__stdout__

        output = captured.getvalue()

        # Verify error is displayed
        self.assertIn("ERROR", output)
        self.assertIn("Username already taken", output)

    def test_register_calls_api_correctly(self):
        # Mock API
        api = Mock()
        api._post.side_effect = [
            {"session": {"id": "test-session"}},  # session creation
            {"result": {"username": "TestUser", "empire": "voidborn", "password": "test-pass"}}  # register
        ]
        api.session_file = "/tmp/test-session"

        # Mock args
        args = Mock()
        args.username = "TestUser"
        args.empire = "voidborn"
        args.json = False

        # Capture stdout to suppress output
        captured = StringIO()
        captured.isatty = lambda: True
        sys.stdout = captured

        cmd_register(api, args)
        sys.stdout = sys.__stdout__

        # Verify API was called correctly (session, then register)
        self.assertEqual(api._post.call_count, 2)
        # First call: create session
        self.assertEqual(api._post.call_args_list[0][0][0], "session")
        # Second call: register
        self.assertEqual(api._post.call_args_list[1][0][0], "register")


if __name__ == "__main__":
    unittest.main()
