# Copyright 2013-2018 Intranet AG and contributors
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

"""
Display controllers (DC backends) to perform user operations.

SUMMARY
------------------------------------------------------


INTERFACE
------------------------------------------------------

"""

import os
import re
import time
import logging
import numpy
import PIL.Image
from tempfile import NamedTemporaryFile

from . import inputmap
from .config import GlobalConfig, LocalConfig
from .imagelogger import ImageLogger
from .target import Image
from .location import Location
from .errors import *


log = logging.getLogger("guibot.controller")
__all__ = [
    "Controller",
    "AutoPyController",
    "XDoToolController",
    "VNCDoToolController",
    "PyAutoGUIController",
]


class Controller(LocalConfig):
    """
    Screen control backend, responsible for performing display operations.

    Examples of display operations include mouse clicking mouse clicking,
    key pressing, text typing, etc.
    """

    def __init__(self, configure: bool = True, synchronize: bool = True) -> None:
        """Build a screen controller backend."""
        super(Controller, self).__init__(configure=False, synchronize=False)

        # available and currently fully compatible methods
        self.categories["control"] = "control_methods"
        self.algorithms["control_methods"] = [
            "autopy",
            "pyautogui",
            "xdotool",
            "vncdotool",
        ]

        # other attributes
        self._backend_obj = None
        self._width = 0
        self._height = 0
        # NOTE: some backends require mouse pointer reinitialization so compensate for it
        self._pointer = Location(0, 0)
        self._keymap: inputmap.Key = None
        self._modmap: inputmap.KeyModifier = None
        self._mousemap: inputmap.MouseButton = None

        # additional preparation
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_width(self) -> int:
        """
        Getter for readonly attribute.

        :returns: width of the connected screen
        """
        return self._width

    width = property(fget=get_width)

    def get_height(self) -> int:
        """
        Getter for readonly attribute.

        :returns: height of the connected screen
        """
        return self._height

    height = property(fget=get_height)

    def get_keymap(self) -> inputmap.Key:
        """
        Getter for readonly attribute.

        :returns: map of keys to be used for the connected screen
        """
        return self._keymap

    keymap = property(fget=get_keymap)

    def get_mousemap(self) -> inputmap.MouseButton:
        """
        Getter for readonly attribute.

        :returns: map of mouse buttons to be used for the connected screen
        """
        return self._mousemap

    mousemap = property(fget=get_mousemap)

    def get_modmap(self) -> inputmap.KeyModifier:
        """
        Getter for readonly attribute.

        :returns: map of modifier keys to be used for the connected screen
        """
        return self._modmap

    modmap = property(fget=get_modmap)

    def get_mouse_location(self) -> Location:
        """
        Getter for readonly attribute.

        :returns: location of the mouse pointer
        """
        return self._pointer

    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(
        self, backend: str = None, category: str = "control", reset: bool = False
    ) -> None:
        if category != "control":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(Controller, self).configure_backend("dc", reset=True)
        if backend is None:
            backend = GlobalConfig.display_control_backend
        if backend not in self.algorithms[self.categories[category]]:
            raise UnsupportedBackendError(
                "Backend '%s' is not among the supported ones: "
                "%s" % (backend, self.algorithms[self.categories[category]])
            )

        log.log(9, "Setting backend for %s to %s", category, backend)
        self.params[category] = {}
        self.params[category]["backend"] = backend
        self.params[category]["mouse_toggle_delay"] = 0.05
        self.params[category]["after_click_delay"] = 0.1
        self.params[category]["delay_between_keys"] = 0.1
        self.params[category]["delay_before_keys"] = 0.2
        log.log(9, "%s %s\n", category, self.params[category])

    def configure_backend(
        self, backend: str = None, category: str = "control", reset: bool = False
    ) -> None:
        """
        Generate configuration dictionary for a given backend.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(
        self, backend: str = None, category: str = "control", reset: bool = False
    ) -> None:
        if category != "control":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(Controller, self).synchronize_backend("dc", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError(
                "Backend '%s' has not been configured yet" % backend
            )

    def synchronize_backend(
        self, backend: str = None, category: str = "control", reset: bool = False
    ) -> None:
        """
        Synchronize a category backend with the equalizer configuration.

        Custom implementation of the base method.

        See base method for details.

        Select a backend for the instance, synchronizing configuration
        like screen size, key map, mouse pointer handling, etc. The
        object that carries this configuration is called screen.
        """
        self.__synchronize_backend(backend, category, reset)

    def _region_from_args(self, *args: "Region") -> tuple[int, int, int, int, str]:
        if len(args) == 4:
            xpos = args[0]
            ypos = args[1]
            width = args[2]
            height = args[3]
        elif len(args) == 1:
            region = args[0]
            xpos = region.x
            ypos = region.y
            width = region.width
            height = region.height
        else:
            xpos = 0
            ypos = 0
            width = self._width
            height = self._height

        # clipping
        if xpos > self._width:
            xpos = self._width - 1
        if ypos > self._height:
            ypos = self._height - 1
        if xpos + width > self._width:
            width = self._width - xpos
        if ypos + height > self._height:
            height = self._height - ypos

        # TODO: Switch to in-memory conversion - patch backends or request get_raw() from authors
        with NamedTemporaryFile(prefix="guibot", suffix=".png") as f:
            # NOTE: the file can be open twice on unix but only once on windows so simply
            # use the generated filename to avoid this difference and remove it manually
            filename = f.name
        return xpos, ypos, width, height, filename

    def capture_screen(self, *args: "list[int] | Region | None") -> Image:
        """
        Get the current screen as image.

        :param args: region's (x, y, width, height) or a region object or
                     nothing to obtain an image of the full screen
        :returns: image of the current screen
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def mouse_move(self, location: Location, smooth: bool = True) -> None:
        """
        Move the mouse to a desired location.

        :param location: location on the screen to move to
        :param smooth: whether to sue smooth transition or just teleport the mouse
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def mouse_click(
        self, button: int = None, count: int = 1, modifiers: list[str] = None
    ) -> None:
        """
        Click the selected mouse button N times at the current mouse location.

        :param button: mouse button, e.g. self.mouse_map.LEFT_BUTTON
        :param count: number of times to click
        :param modifiers: special keys to hold during clicking
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def mouse_down(self, button: int) -> None:
        """
        Hold down a mouse button.

        :param button: button index depending on backend
                       (see :py:class:`inputmap.MouseButton` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def mouse_up(self, button: int) -> None:
        """
        Release a mouse button.

        :param button: button index depending on backend
                       (see :py:class:`inputmap.MouseButton` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def mouse_scroll(self, clicks: int = 10, horizontal: bool = False) -> None:
        """
        Scroll the mouse for a number of clicks.

        :param clicks: number of clicks to scroll up (positive) or down (negative)
        :param horizontal: whether to perform a horizontal scroll instead
                           (only available on some platforms)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def keys_toggle(self, keys: list[str] | str, up_down: bool) -> None:
        """
        Hold down or release together all provided keys.

        :param keys: characters or special keys depending on the backend
                     (see :py:class:`inputmap.Key` for extensive list)
        :param up_down: hold down if true else release
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def keys_press(self, keys: list[str] | str) -> None:
        """
        Press (hold down and release) together all provided keys.

        :param keys: characters or special keys depending on the backend
                     (see :py:class:`inputmap.Key` for extensive list)
        """
        self.imglog.type = "keys"
        self.imglog.log(30)
        time.sleep(self.params["control"]["delay_before_keys"])
        # BUG: pressing multiple times the same key does not work?
        self.keys_toggle(keys, True)
        self.keys_toggle(keys, False)

    def keys_type(self, text: list[str] | str, modifiers: list[str] = None) -> None:
        """
        Type (press consecutively) all provided keys.

        :param text: characters only (no special keys allowed)
        :param modifiers: special keys to hold during typing
                         (see :py:class:`inputmap.KeyModifier` for extensive list)
        :raises: :py:class:`NotImplementedError` if the base class method is called
        """
        raise NotImplementedError(
            "Method is not available for this controller implementation"
        )

    def log(self, lvl: int) -> None:
        """
        Log images with an arbitrary logging level.

        :param lvl: logging level for the message
        """
        # below selected logging level
        if lvl < self.imglog.logging_level:
            self.imglog.clear()
            return

        self.imglog.hotmaps += [numpy.array(self.capture_screen().pil_image)]
        self.imglog.draw_locations(
            [self.get_mouse_location().coords],
            self.imglog.hotmaps[-1],
            30,
            0,
            0,
            0,
        )
        name = "imglog%s-1control-%s.png" % (
            self.imglog.printable_step,
            self.imglog.type,
        )
        self.imglog.dump_hotmap(name, self.imglog.hotmaps[-1])

        self.imglog.clear()
        ImageLogger.step += 1


class AutoPyController(Controller):
    """
    Screen control backend implemented through AutoPy.

    AutoPy is a small python library portable to Windows and Linux operating systems.
    """

    def __init__(self, configure: bool = True, synchronize: bool = True) -> None:
        """Build a DC backend using AutoPy."""
        super(AutoPyController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self) -> Location:
        """
        Getter for readonly attribute.

        Custom implementation of the base method.

        See base method for details.
        """
        loc = self._backend_obj.mouse.location()
        # newer versions do their own scale conversion
        version = self._backend_obj.__version__.split(".")
        if (
            int(version[0]) > 3
            or int(version[0]) == 3
            and (int(version[1]) > 0 or int(version[2]) > 0)
        ):
            return Location(int(loc[0] * self._scale), int(loc[1] * self._scale))
        return Location(int(loc[0] / self._scale), int(loc[1] / self._scale))

    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(
        self, backend: str = None, category: str = "autopy", reset: bool = False
    ) -> None:
        if category != "autopy":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(AutoPyController, self).configure_backend("autopy", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(
        self, backend: str = None, category: str = "autopy", reset: bool = False
    ) -> None:
        """
        Generate configuration dictionary for a given backend.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(
        self, backend: str = None, category: str = "autopy", reset: bool = False
    ) -> None:
        if category != "autopy":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(AutoPyController, self).synchronize_backend("autopy", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError(
                "Backend '%s' has not been configured yet" % backend
            )

        import autopy

        self._backend_obj = autopy

        self._scale = self._backend_obj.screen.scale()
        self._width, self._height = self._backend_obj.screen.size()
        self._width = int(self._width * self._scale)
        self._height = int(self._height * self._scale)
        self._pointer = self.mouse_location
        self._keymap = inputmap.AutoPyKey()
        self._modmap = inputmap.AutoPyKeyModifier()
        self._mousemap = inputmap.AutoPyMouseButton()

    def synchronize_backend(
        self, backend: str = None, category: str = "autopy", reset: bool = False
    ) -> None:
        """
        Synchronize a category backend with the equalizer configuration.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args: "list[int] | Region | None") -> Image:
        """
        Get the current screen as image.

        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, filename = self._region_from_args(*args)

        # autopy works in points and requires a minimum of one point along a dimension
        xpos, ypos, width, height = (
            xpos / self._scale,
            ypos / self._scale,
            width / self._scale,
            height / self._scale,
        )
        xpos, ypos = float(xpos) - (1.0 - float(width)) if width < 1.0 else xpos, (
            float(ypos) - (1.0 - float(height)) if height < 1.0 else ypos
        )
        height, width = 1.0 if float(height) < 1.0 else height, (
            1.0 if float(width) < 1.0 else width
        )
        try:
            autopy_bmp = self._backend_obj.bitmap.capture_screen(
                ((xpos, ypos), (width, height))
            )
        except ValueError:
            return Image("", PIL.Image.new("RGB", (1, 1)))
        autopy_bmp.save(filename)

        with PIL.Image.open(filename) as f:
            pil_image = f.convert("RGB")
        os.unlink(filename)
        return Image("", pil_image)

    def mouse_move(self, location: Location, smooth: bool = True) -> None:
        """
        Move the mouse to a desired location.

        Custom implementation of the base method.

        See base method for details.
        """
        x, y = location.x / self._scale, location.y / self._scale
        if smooth:
            self._backend_obj.mouse.smooth_move(x, y)
        else:
            self._backend_obj.mouse.move(x, y)
        self._pointer = location

    def mouse_click(
        self, button: int = None, count: int = 1, modifiers: list[str] = None
    ) -> None:
        """
        Click the selected mouse button N times at the current mouse location.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "mouse"
        self.imglog.log(30)
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            self._backend_obj.mouse.click(button)
            # BUG: the mouse button of autopy is pressed down forever (on LEFT)
            time.sleep(self.params["control"]["mouse_toggle_delay"])
            self.mouse_up(button)
            time.sleep(self.params["control"]["after_click_delay"])
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button: int) -> None:
        """
        Hold down a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouse.toggle(button, True)

    def mouse_up(self, button: int) -> None:
        """
        Release a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouse.toggle(button, False)

    def keys_toggle(self, keys: list[str] | str, up_down: bool) -> None:
        """
        Hold down or release together all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            self._backend_obj.key.toggle(key, up_down, [])

    def keys_type(self, text: list[str] | str, modifiers: list[str] = None) -> None:
        """
        Type (press consecutively) all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "keys"
        self.imglog.log(30)
        time.sleep(self.params["control"]["delay_before_keys"])
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            for char in str(part):
                self._backend_obj.key.tap(char, [])
                time.sleep(self.params["control"]["delay_between_keys"])
            # alternative option:
            # autopy.key.type_string(text)

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class XDoToolController(Controller):
    """Screen control backend implemented through the xdotool client and thus portable to Linux operating systems."""

    def __init__(self, configure: bool = True, synchronize: bool = True) -> None:
        """Build a DC backend using XDoTool."""
        super(XDoToolController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self) -> Location:
        """
        Getter for readonly attribute.

        Custom implementation of the base method.

        See base method for details.
        """
        pos = self._backend_obj.run("getmouselocation")
        x = re.search(r"x:(\d+)", pos).group(1)
        y = re.search(r"y:(\d+)", pos).group(1)
        return Location(int(x), int(y))

    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(
        self, backend: str = None, category: str = "xdotool", reset: bool = False
    ) -> None:
        if category != "xdotool":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(XDoToolController, self).configure_backend("xdotool", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        self.params[category]["binary"] = "xdotool"

    def configure_backend(
        self, backend: str = None, category: str = "xdotool", reset: bool = False
    ) -> None:
        """
        Generate configuration dictionary for a given backend.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(
        self, backend: str = None, category: str = "xdotool", reset: bool = False
    ) -> None:
        if category != "xdotool":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(XDoToolController, self).synchronize_backend("xdotool", reset=True)
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError(
                "Backend '%s' has not been configured yet" % backend
            )

        import subprocess

        class XDoTool(object):
            def __init__(self, dc: Controller) -> None:
                self.dc = dc

            def run(self, command: str, *args: list[str]) -> str:
                process = [self.dc.params[category]["binary"]]
                process += [command]
                process += args
                return subprocess.check_output(process, shell=False).decode()

        self._backend_obj = XDoTool(self)

        self._width, self._height = self._backend_obj.run("getdisplaygeometry").split()
        self._width, self._height = int(self._width), int(self._height)
        self._pointer = self.mouse_location
        self._keymap = inputmap.XDoToolKey()
        self._modmap = inputmap.XDoToolKeyModifier()
        self._mousemap = inputmap.XDoToolMouseButton()

    def synchronize_backend(
        self, backend: str = None, category: str = "xdotool", reset: bool = False
    ) -> None:
        """
        Synchronize a category backend with the equalizer configuration.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args: "list[int] | Region | None") -> Image:
        """
        Get the current screen as image.

        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, filename = self._region_from_args(*args)
        import subprocess

        with subprocess.Popen(
            ("xwd", "-silent", "-root"), stdout=subprocess.PIPE
        ) as xwd:
            subprocess.call(
                (
                    "convert",
                    "xwd:-",
                    "-crop",
                    "%sx%s+%s+%s" % (width, height, xpos, ypos),
                    filename,
                ),
                stdin=xwd.stdout,
            )
        with PIL.Image.open(filename) as f:
            pil_image = f.convert("RGB")
        os.unlink(filename)
        return Image("", pil_image)

    def mouse_move(self, location: Location, smooth: bool = True) -> None:
        """
        Move the mouse to a desired location.

        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            # TODO: implement smooth mouse move?
            log.warning(
                "Smooth mouse move is not supported for the XDO controller,"
                " defaulting to instant mouse move"
            )
        self._backend_obj.run("mousemove", str(location.x), str(location.y))
        # handle race conditions where the backend coordinates are updated too
        # slowly by giving some time for the new location to take effect there
        time.sleep(0.3)
        self._pointer = location

    def mouse_click(
        self, button: int = None, count: int = 1, modifiers: list[str] = None
    ) -> None:
        """
        Click the selected mouse button N times at the current mouse location.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "mouse"
        self.imglog.log(30)
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # BUG: the xdotool click is too fast and non-configurable with timeout
            # self._backend_obj.run("click", str(button))
            self.mouse_down(button)
            time.sleep(self.params["control"]["mouse_toggle_delay"])
            self.mouse_up(button)
            time.sleep(self.params["control"]["after_click_delay"])
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button: int) -> None:
        """
        Hold down a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.run("mousedown", str(button))

    def mouse_up(self, button: int) -> None:
        """
        Release a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.run("mouseup", str(button))

    def keys_toggle(self, keys: list[str] | str, up_down: bool) -> None:
        """
        Hold down or release together all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            if up_down:
                self._backend_obj.run("keydown", str(key))
            else:
                self._backend_obj.run("keyup", str(key))

    def keys_type(self, text: list[str] | str, modifiers: list[str] = None) -> None:
        """
        Type (press consecutively) all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "keys"
        self.imglog.log(30)
        time.sleep(self.params["control"]["delay_before_keys"])
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            self._backend_obj.run("type", str(part))

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class VNCDoToolController(Controller):
    """
    Screen control backend implemented through the VNCDoTool client.

    This backend is thus portable to any guest OS that is accessible through a VNC/RFB protocol.
    """

    def __init__(self, configure: bool = True, synchronize: bool = True) -> None:
        """Build a DC backend using VNCDoTool."""
        super(VNCDoToolController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def __del__(self) -> None:
        """Destroy a DC backend using VNCDoTool via extra API shutdown."""
        # TODO: for official support for VNCDoTool 1.1+ add this destructor but
        # shuting down the Twisted API on destruction only makes PASS tests not
        # hang with CANCEL, FAIL, and other results hanging
        from vncdotool import api

        api.shutdown()

    def __configure_backend(
        self, backend: str = None, category: str = "vncdotool", reset: bool = False
    ) -> None:
        if category != "vncdotool":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(VNCDoToolController, self).configure_backend("vncdotool", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"
        # hostname of the vnc server
        self.params[category]["vnc_hostname"] = "localhost"
        # port of the vnc server
        self.params[category]["vnc_port"] = 0
        # password for the vnc server
        self.params[category]["vnc_password"] = None

    def configure_backend(
        self, backend: str = None, category: str = "vncdotool", reset: bool = False
    ) -> None:
        """
        Generate configuration dictionary for a given backend.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(
        self, backend: str = None, category: str = "vncdotool", reset: bool = False
    ) -> None:
        if category != "vncdotool":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(VNCDoToolController, self).synchronize_backend(
                "vncdotool", reset=True
            )
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError(
                "Backend '%s' has not been configured yet" % backend
            )

        from vncdotool import api

        if self._backend_obj:
            # api.connect() gives us a threaded client, so we need to clean up resources
            # to avoid dangling connections and deadlocks if synchronizing more than once
            self._backend_obj.disconnect()
        self._backend_obj = api.connect(
            "%s:%i"
            % (
                self.params[category]["vnc_hostname"],
                self.params[category]["vnc_port"],
            ),
            self.params[category]["vnc_password"],
        )
        # for special characters preprocessing for the vncdotool
        self._backend_obj.factory.force_caps = True

        # additional logging for vncdotool available so let's make use of it
        logging.getLogger("vncdotool.client").setLevel(10)
        logging.getLogger("vncdotool").setLevel(logging.ERROR)
        logging.getLogger("twisted").setLevel(logging.ERROR)

        # screen size
        with NamedTemporaryFile(prefix="guibot", suffix=".png") as f:
            filename = f.name
        screen = self._backend_obj.captureScreen(filename)
        os.unlink(filename)
        self._width = screen.width
        self._height = screen.height

        # sync pointer
        self.mouse_move(Location(self._width, self._height), smooth=False)
        self.mouse_move(Location(0, 0), smooth=False)
        self._pointer = Location(0, 0)

        self._keymap = inputmap.VNCDoToolKey()
        self._modmap = inputmap.VNCDoToolKeyModifier()
        self._mousemap = inputmap.VNCDoToolMouseButton()

    def synchronize_backend(
        self, backend: str = None, category: str = "vncdotool", reset: bool = False
    ) -> None:
        """
        Synchronize a category backend with the equalizer configuration.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args: "list[int] | Region | None") -> Image:
        """
        Get the current screen as image.

        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, _ = self._region_from_args(*args)
        self._backend_obj.refreshScreen()
        cropped = self._backend_obj.screen.crop(
            (xpos, ypos, xpos + width, ypos + height)
        )
        pil_image = cropped.convert("RGB")
        return Image("", pil_image)

    def mouse_move(self, location: Location, smooth: bool = True) -> None:
        """
        Move the mouse to a desired location.

        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            self._backend_obj.mouseDrag(location.x, location.y, step=30)
        else:
            self._backend_obj.mouseMove(location.x, location.y)
        self._pointer = location

    def mouse_click(
        self, button: int = None, count: int = 1, modifiers: list[str] = None
    ) -> None:
        """
        Click the selected mouse button N times at the current mouse location.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "mouse"
        self.imglog.log(30)
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # BUG: some VNC servers (as the QEMU built-in) don't handle click events
            # sent too fast, so we sleep between mouse up and down and avoid mousePress
            # self._backend_obj.mousePress(button)
            self.mouse_down(button)
            time.sleep(self.params["control"]["mouse_toggle_delay"])
            self.mouse_up(button)
            time.sleep(self.params["control"]["after_click_delay"])
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button: int) -> None:
        """
        Hold down a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseDown(button)

    def mouse_up(self, button: int) -> None:
        """
        Release a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseUp(button)

    def keys_toggle(self, keys: list[str] | str, up_down: bool) -> None:
        """
        Hold down or release together all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            if key == "\\":
                key = "bslash"
            elif key == "/":
                key = "fslash"
            elif key == " ":
                key = "space"
            if up_down:
                self._backend_obj.keyDown(key)
            else:
                self._backend_obj.keyUp(key)

    def keys_type(self, text: list[str] | str, modifiers: list[str] = None) -> None:
        """
        Type (press consecutively) all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "keys"
        self.imglog.log(30)
        time.sleep(self.params["control"]["delay_before_keys"])
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            for char in str(part):
                if char == "\\":
                    char = "bslash"
                elif char == "/":
                    char = "fslash"
                elif char == " ":
                    char = "space"
                elif char == "\n":
                    char = "return"
                time.sleep(self.params["control"]["delay_between_keys"])
                self._backend_obj.keyPress(char)

        if modifiers is not None:
            self.keys_toggle(modifiers, False)


class PyAutoGUIController(Controller):
    """
    Screen control backend implemented through PyAutoGUI.

    PyAutoGUI is a python library portable to MacOS, Windows, and Linux operating systems.
    """

    def __init__(self, configure: bool = True, synchronize: bool = True) -> None:
        """Build a DC backend using PyAutoGUI."""
        super(PyAutoGUIController, self).__init__(configure=False, synchronize=False)
        if configure:
            self.__configure_backend(reset=True)
        if synchronize:
            self.__synchronize_backend(reset=False)

    def get_mouse_location(self) -> Location:
        """
        Getter for readonly attribute.

        Custom implementation of the base method.

        See base method for details.
        """
        x, y = self._backend_obj.position()
        return Location(x, y)

    mouse_location = property(fget=get_mouse_location)

    def __configure_backend(
        self, backend: str = None, category: str = "pyautogui", reset: bool = False
    ) -> None:
        if category != "pyautogui":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(PyAutoGUIController, self).configure_backend("pyautogui", reset=True)

        self.params[category] = {}
        self.params[category]["backend"] = "none"

    def configure_backend(
        self, backend: str = None, category: str = "pyautogui", reset: bool = False
    ) -> None:
        """
        Generate configuration dictionary for a given backend.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__configure_backend(backend, category, reset)

    def __synchronize_backend(
        self, backend: str = None, category: str = "pyautogui", reset: bool = False
    ) -> None:
        if category != "pyautogui":
            raise UnsupportedBackendError(
                "Backend category '%s' is not supported" % category
            )
        if reset:
            super(PyAutoGUIController, self).synchronize_backend(
                "pyautogui", reset=True
            )
        if backend is not None and self.params[category]["backend"] != backend:
            raise UninitializedBackendError(
                "Backend '%s' has not been configured yet" % backend
            )

        import pyautogui

        # allow for (0,0) and edge coordinates
        pyautogui.FAILSAFE = False
        self._backend_obj = pyautogui

        self._width, self._height = self._backend_obj.size()
        self._pointer = self.mouse_location
        self._keymap = inputmap.PyAutoGUIKey()
        self._modmap = inputmap.PyAutoGUIKeyModifier()
        self._mousemap = inputmap.PyAutoGUIMouseButton()

    def synchronize_backend(
        self, backend: str = None, category: str = "pyautogui", reset: bool = False
    ) -> None:
        """
        Synchronize a category backend with the equalizer configuration.

        Custom implementation of the base method.

        See base method for details.
        """
        self.__synchronize_backend(backend, category, reset)

    def capture_screen(self, *args: "list[int] | Region | None") -> Image:
        """
        Get the current screen as image.

        Custom implementation of the base method.

        See base method for details.
        """
        xpos, ypos, width, height, _ = self._region_from_args(*args)

        pil_image = self._backend_obj.screenshot(region=(xpos, ypos, width, height))
        return Image("", pil_image)

    def mouse_move(self, location: Location, smooth: bool = True) -> None:
        """
        Move the mouse to a desired location.

        Custom implementation of the base method.

        See base method for details.
        """
        if smooth:
            self._backend_obj.moveTo(location.x, location.y, duration=1)
        else:
            self._backend_obj.moveTo(location.x, location.y)
        self._pointer = location

    def mouse_click(
        self, button: int = None, count: int = 1, modifiers: list[str] = None
    ) -> None:
        """
        Click the selected mouse button N times at the current mouse location.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "mouse"
        self.imglog.log(30)
        button = self._mousemap.LEFT_BUTTON if button is None else button
        if modifiers is not None:
            self.keys_toggle(modifiers, True)
        for _ in range(count):
            # NOTE: we don't use higher level API calls since we want to also
            # control the toggle speed
            # self._backend_obj.click(clicks=count, interval=click_timeout, button=button)
            self._backend_obj.mouseDown(button=button)
            time.sleep(self.params["control"]["mouse_toggle_delay"])
            self._backend_obj.mouseUp(button=button)
            time.sleep(self.params["control"]["after_click_delay"])
        if modifiers is not None:
            self.keys_toggle(modifiers, False)

    def mouse_down(self, button: int) -> None:
        """
        Hold down a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseDown(button=button)

    def mouse_up(self, button: int) -> None:
        """
        Release a mouse button.

        Custom implementation of the base method.

        See base method for details.
        """
        self._backend_obj.mouseUp(button=button)

    def mouse_scroll(self, clicks: int = 10, horizontal: bool = False) -> None:
        """
        Scroll the mouse for a number of clicks.

        Custom implementation of the base method.

        See base method for details.
        """
        if horizontal:
            self._backend_obj.hscroll(clicks)
        else:
            self._backend_obj.scroll(clicks)

    def keys_toggle(self, keys: list[str] | str, up_down: bool) -> None:
        """
        Hold down or release together all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        for key in keys:
            if up_down:
                self._backend_obj.keyDown(key)
            else:
                self._backend_obj.keyUp(key)

    def keys_type(self, text: list[str] | str, modifiers: list[str] = None) -> None:
        """
        Type (press consecutively) all provided keys.

        Custom implementation of the base method.

        See base method for details.
        """
        self.imglog.type = "keys"
        self.imglog.log(30)
        time.sleep(self.params["control"]["delay_before_keys"])
        if modifiers is not None:
            self.keys_toggle(modifiers, True)

        for part in text:
            self._backend_obj.typewrite(
                part, interval=self.params["control"]["delay_between_keys"]
            )

        if modifiers is not None:
            self.keys_toggle(modifiers, False)
