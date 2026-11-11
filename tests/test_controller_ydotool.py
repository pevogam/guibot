#!/usr/bin/python3
# Copyright 2026 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import os
import subprocess
import unittest
from unittest import mock

import PIL.Image

import common_test
from guibot.config import GlobalConfig, TemporaryConfig
from guibot.controller import Controller, YDoToolController
from guibot.errors import UnsupportedBackendError, UninitializedBackendError
from guibot.location import Location
from guibot.region import Region


class YDoToolControllerTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.dict(
            os.environ,
            {
                "WAYLAND_DISPLAY": "",
                "XDG_SESSION_TYPE": "x11",
                "XDG_CURRENT_DESKTOP": "",
            },
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.screen = PIL.Image.new("RGB", (640, 480), "white")
        self.screen.putpixel((20, 10), (10, 20, 30))
        self.addCleanup(self.screen.close)
        patcher = mock.patch("PIL.ImageGrab.grab", side_effect=self.grab_screen)
        self.grab = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("subprocess.check_output", return_value=b"")
        self.run = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch("guibot.controller.time.sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)
        self.controller = YDoToolController()
        self.controller.imglog.log = mock.Mock()
        self.run.reset_mock()
        self.sleep.reset_mock()

    def grab_screen(self, bbox=None):
        return self.screen.copy() if bbox is None else self.screen.crop(bbox)

    def command(self, *args, input=None):
        return mock.call(["ydotool", *args], input=input, shell=False)

    def save_screenshot(self, command):
        self.screen.save(command[-1])
        return 0

    def test_configuration_and_synchronization(self) -> None:
        """Initialize without X11 geometry or pointer queries and allow a custom binary."""
        controller = YDoToolController(synchronize=False)
        self.run.assert_not_called()
        self.assertEqual(controller.width, 0)
        self.assertEqual(controller.params["control"]["backend"], "ydotool")
        self.assertIn("ydotool", Controller().algorithms["control_methods"])
        controller.params["ydotool"]["binary"] = "/opt/tools/ydotool"
        controller.synchronize_backend(reset=True)
        self.assertEqual((controller.width, controller.height), (640, 480))
        self.assertEqual(controller.mouse_location.coords, (0, 0))
        self.run.assert_called_once_with(
            ["/opt/tools/ydotool", "mousemove", "--absolute", "-x", "0", "-y", "0"],
            input=None,
            shell=False,
        )
        controller.configure_backend(reset=True)
        self.assertEqual(controller.params["ydotool"]["binary"], "ydotool")
        self.assertEqual(set(controller.params), {"type", "control", "ydotool"})

    def test_backend_validation(self) -> None:
        """Reject foreign categories and unsynchronized backend choices before running commands."""
        for category in ("control", "xdotool", "unknown"):
            with self.subTest(category=category):
                with self.assertRaises(UnsupportedBackendError):
                    self.controller.configure_backend(category=category)
                with self.assertRaises(UnsupportedBackendError):
                    self.controller.synchronize_backend(category=category)
        with self.assertRaises(UninitializedBackendError):
            self.controller.synchronize_backend(backend="unknown")
        self.run.assert_not_called()

    def test_global_backend_selection(self) -> None:
        """Select the controller through the same global setting used by normal regions."""
        previous = GlobalConfig.display_control_backend
        with TemporaryConfig() as config:
            config.display_control_backend = "ydotool"
            with mock.patch(
                "guibot.region.YDoToolController", return_value=self.controller
            ) as create:
                region = Region(cv=mock.Mock())
            create.assert_called_once_with()
            self.assertIs(region.dc_backend, self.controller)
            self.assertEqual(region.ENTER, 28)
            self.assertEqual(region.MOD_CTRL, 29)
            self.assertEqual(region.LEFT_BUTTON, 0)
            region.press_keys([region.CTRL, "a"])
        self.assertEqual(GlobalConfig.display_control_backend, previous)
        self.assertEqual(
            self.run.call_args_list,
            [
                self.command("key", "--key-delay", "0", "29:1", "30:1"),
                self.command("key", "--key-delay", "0", "30:0", "29:0"),
            ],
        )

    def test_capture_and_clipping(self) -> None:
        """Capture full screens, coordinates, and regions with correct pixels and clipping."""
        screen = self.controller.capture_screen()
        self.assertEqual((screen.width, screen.height), (640, 480))
        self.assertEqual(screen.pil_image.mode, "RGB")
        captured = self.controller.capture_screen(20, 10, 100, 50)
        self.assertEqual((captured.width, captured.height), (100, 50))
        self.assertEqual(captured.pil_image.getpixel((0, 0)), (10, 20, 30))
        region = Region(20, 10, 100, 50, dc=self.controller, cv=mock.Mock())
        captured = self.controller.capture_screen(region)
        self.assertEqual((captured.width, captured.height), (100, 50))
        self.assertEqual(captured.pil_image.getpixel((0, 0)), (10, 20, 30))
        captured = self.controller.capture_screen(630, 470, 100, 50)
        self.assertEqual((captured.width, captured.height), (10, 10))
        captured = self.controller.capture_screen(60000, 50000, 80000, 40000)
        self.assertEqual((captured.width, captured.height), (1, 1))
        self.run.assert_not_called()

    def test_native_wayland_capture(self) -> None:
        """Bypass Pillow's X11 path and use the desktop's native tool for geometry and capture."""
        for desktop, command in (
            ("GNOME", ["gnome-screenshot", "-f"]),
            ("KDE", ["spectacle", "-n", "-b", "-f", "-o"]),
            ("sway", ["grim", "-s", "1"]),
        ):
            with self.subTest(desktop=desktop), mock.patch.dict(
                os.environ,
                {
                    "WAYLAND_DISPLAY": "wayland-0",
                    "DISPLAY": ":1",
                    "XDG_CURRENT_DESKTOP": desktop,
                },
            ), mock.patch(
                "shutil.which", side_effect=lambda tool: "/usr/bin/" + tool
            ), mock.patch(
                "subprocess.check_call", side_effect=self.save_screenshot
            ) as capture:
                self.grab.reset_mock()
                controller = YDoToolController()
                self.assertEqual((controller.width, controller.height), (640, 480))
                image = controller.capture_screen(20, 10, 100, 50)
                self.assertEqual((image.width, image.height), (100, 50))
                self.assertEqual(image.pil_image.getpixel((0, 0)), (10, 20, 30))
                self.grab.assert_not_called()
                self.assertEqual(capture.call_count, 2)
                for call in capture.call_args_list:
                    self.assertEqual(call.args[0][:-1], command)
                    self.assertFalse(os.path.exists(call.args[0][-1]))

    def test_explicit_screenshot_tool(self) -> None:
        """Honor a chosen capture tool independently of automatic session detection."""
        self.controller.params["ydotool"]["screenshot_tool"] = "grim"
        self.grab.reset_mock()
        with mock.patch(
            "subprocess.check_call", side_effect=self.save_screenshot
        ) as capture:
            image = self.controller.capture_screen()
        self.assertEqual((image.width, image.height), (640, 480))
        self.assertEqual(capture.call_args.args[0][:-1], ["grim", "-s", "1"])
        self.grab.assert_not_called()
        self.controller.params["ydotool"]["screenshot_tool"] = "pillow"
        with mock.patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}):
            self.controller.capture_screen()
        self.grab.assert_called_once_with()

    def test_missing_or_unknown_screenshot_tool(self) -> None:
        """Report missing native capture tools instead of silently capturing XWayland."""
        self.grab.reset_mock()
        with mock.patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}), mock.patch(
            "shutil.which", return_value=None
        ):
            with self.assertRaisesRegex(
                UnsupportedBackendError, "Wayland screen capture requires"
            ):
                self.controller.capture_screen()
        self.controller.params["ydotool"]["screenshot_tool"] = "unknown"
        with self.assertRaisesRegex(
            UnsupportedBackendError, "Unsupported screenshot tool"
        ):
            self.controller.capture_screen()
        self.grab.assert_not_called()

    def test_capture_failure_cleanup(self) -> None:
        """Propagate native tool failures and remove partial screenshots."""

        def fail_capture(command):
            self.save_screenshot(command)
            raise subprocess.CalledProcessError(1, command)

        self.controller.params["ydotool"]["screenshot_tool"] = "grim"
        with mock.patch("subprocess.check_call", side_effect=fail_capture) as capture:
            with self.assertRaises(subprocess.CalledProcessError):
                self.controller.capture_screen()
        self.assertFalse(os.path.exists(capture.call_args.args[0][-1]))

    def test_region_modifiers(self) -> None:
        """Use numeric key modifiers through region clicking, dragging, and typing APIs."""
        region = Region(dc=self.controller, cv=mock.Mock())
        with mock.patch.object(region, "hover"):
            for method in (
                "click",
                "right_click",
                "middle_click",
                "double_click",
                "multi_click",
            ):
                with self.subTest(method=method):
                    self.run.reset_mock()
                    getattr(region, method)(
                        Location(20, 10), modifiers=[region.MOD_CTRL]
                    )
                    self.assertEqual(
                        self.run.call_args_list[0],
                        self.command("key", "--key-delay", "0", "29:1"),
                    )
                    self.assertEqual(
                        self.run.call_args_list[-1],
                        self.command("key", "--key-delay", "0", "29:0"),
                    )
            region.drag_from(Location(20, 10), modifiers=[region.MOD_CTRL])
            region.drop_at(Location(30, 10), modifiers=[region.MOD_CTRL])
        for method in (
            region.type_text,
            lambda text, modifiers: region.type_at(text, None, modifiers),
        ):
            for modifiers in (region.MOD_ALT, [region.MOD_ALT]):
                with self.subTest(method=method, modifiers=modifiers):
                    self.run.reset_mock()
                    method("typed", modifiers=modifiers)
                    self.assertEqual(
                        self.run.call_args_list,
                        [
                            self.command("key", "--key-delay", "0", "56:1"),
                            self.command(
                                "type",
                                "--key-delay",
                                "100",
                                "--file",
                                "-",
                                input=b"typed",
                            ),
                            self.command("key", "--key-delay", "0", "56:0"),
                        ],
                    )

    def test_mouse_move_and_scroll(self) -> None:
        """Track absolute controller moves while wheel input leaves pointer coordinates intact."""
        self.controller.mouse_move(Location(50, 60), smooth=False)
        self.assertEqual(self.controller.mouse_location.coords, (50, 60))
        self.controller.mouse_scroll(-3)
        self.controller.mouse_scroll(2, horizontal=True)
        self.assertEqual(self.controller.mouse_location.coords, (50, 60))
        self.assertEqual(
            self.run.call_args_list,
            [
                self.command("mousemove", "--absolute", "-x", "50", "-y", "60"),
                self.command("mousemove", "--wheel", "-x", "0", "-y", "-3"),
                self.command("mousemove", "--wheel", "-x", "2", "-y", "0"),
            ],
        )

    def test_mouse_buttons_and_click_delays(self) -> None:
        """Distinguish every mouse button and preserve configured hold and click delays."""
        buttons = self.controller.mousemap
        for button, down, up in (
            (buttons.LEFT_BUTTON, "0x40", "0x80"),
            (buttons.RIGHT_BUTTON, "0x41", "0x81"),
            (buttons.CENTER_BUTTON, "0x42", "0x82"),
        ):
            with self.subTest(button=button):
                self.run.reset_mock()
                self.controller.mouse_down(button)
                self.controller.mouse_up(button)
                self.assertEqual(
                    self.run.call_args_list,
                    [
                        self.command("click", "--next-delay", "0", down),
                        self.command("click", "--next-delay", "0", up),
                    ],
                )
        self.run.reset_mock()
        self.controller.mouse_click(
            count=2, modifiers=[self.controller.modmap.MOD_CTRL]
        )
        self.assertEqual(
            self.run.call_args_list,
            [
                self.command("key", "--key-delay", "0", "29:1"),
                self.command("click", "--next-delay", "0", "0x40"),
                self.command("click", "--next-delay", "0", "0x80"),
                self.command("click", "--next-delay", "0", "0x40"),
                self.command("click", "--next-delay", "0", "0x80"),
                self.command("key", "--key-delay", "0", "29:0"),
            ],
        )
        self.assertEqual(
            self.sleep.call_args_list, [mock.call(0.05), mock.call(0.1)] * 2
        )

    def test_keys_and_characters(self) -> None:
        """Handle a single special key, chords, uppercase letters, and shifted punctuation."""
        key = self.controller.keymap
        self.assertEqual(key.to_string(key.ENTER), "Enter")
        self.assertEqual(key.to_string(key.F20), "F20")
        self.assertEqual(self.controller.modmap.MOD_ALT, key.ALT)
        self.controller.keys_press(key.ENTER)
        self.controller.keys_toggle([key.CTRL, "A", "!"], True)
        self.controller.keys_toggle([key.CTRL, "A", "!"], False)
        self.assertEqual(
            self.run.call_args_list,
            [
                self.command("key", "--key-delay", "0", "28:1"),
                self.command("key", "--key-delay", "0", "28:0"),
                self.command("key", "--key-delay", "0", "29:1", "42:1", "30:1", "2:1"),
                self.command("key", "--key-delay", "0", "2:0", "30:0", "42:0", "29:0"),
            ],
        )

    def test_invalid_keys_and_empty_input(self) -> None:
        """Reject unsupported keys before emitting a partial chord and ignore empty input."""
        for key in ("Return", "é", None):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self.controller.keys_toggle(
                        [self.controller.keymap.CTRL, key], True
                    )
        with self.assertRaises(UnicodeEncodeError):
            self.controller.keys_type("é")
        self.controller.keys_toggle([], True)
        self.controller.keys_type("")
        self.run.assert_not_called()

    def test_literal_text_and_delays(self) -> None:
        """Send literal text through stdin so options, shell syntax, and backslashes remain text."""
        text = "--help; $(echo test) 'quoted' \\n\n"
        self.controller.params["control"]["delay_between_keys"] = 0.025
        self.controller.keys_type(
            [text, "tail"], modifiers=[self.controller.modmap.MOD_ALT]
        )
        self.assertEqual(
            self.run.call_args_list,
            [
                self.command("key", "--key-delay", "0", "56:1"),
                self.command(
                    "type",
                    "--key-delay",
                    "25",
                    "--file",
                    "-",
                    input=(text + "tail").encode(),
                ),
                self.command("key", "--key-delay", "0", "56:0"),
            ],
        )
        self.sleep.assert_called_once_with(0.2)

    def test_command_failure_releases_modifiers(self) -> None:
        """Propagate command failures and release any held keyboard modifiers."""
        failure = subprocess.CalledProcessError(1, "ydotool")
        for action in (
            lambda: self.controller.keys_type("text", modifiers=[29]),
            lambda: self.controller.mouse_click(modifiers=[29]),
        ):
            with self.subTest(action=action):
                self.run.reset_mock()
                self.run.side_effect = [b"", failure, b""]
                with self.assertRaises(subprocess.CalledProcessError):
                    action()
                self.assertEqual(
                    self.run.call_args_list[-1],
                    self.command("key", "--key-delay", "0", "29:0"),
                )


if __name__ == "__main__":
    unittest.main()
