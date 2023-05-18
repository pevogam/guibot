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
Main guibot interface for GUI automation.

SUMMARY
------------------------------------------------------

This frontend is recommended for use in most normal cases.

INTERFACE
------------------------------------------------------

"""

import os
import logging

from .errors import *
from .fileresolver import FileResolver
from .region import Region
from .controller import Controller
from .finder import Finder
from .target import Target, Image


log = logging.getLogger("guibot")
log.addHandler(logging.NullHandler())


class GuiBot(Region):
    """
    The main guibot object is the root (first and screen wide) region with some convenience functions added.

    .. seealso:: Real API is inherited from :py:class:`region.Region`.
    """

    def __init__(self, dc: Controller = None, cv: Finder = None) -> None:
        """
        Build a guibot object.

        :param dc: DC backend used for any display control
        :param cv: CV backend used for any target finding

        We will initialize with default region of full screen and default
        display control and computer vision backends if none are provided.
        """
        super(GuiBot, self).__init__(dc=dc, cv=cv)

        self.file_resolver = FileResolver()

    def add_path(self, directory: str) -> None:
        """
        Add a path to the list of currently accessible paths if it wasn't already added.

        :param directory: path to add
        """
        self.file_resolver.add_path(directory)

    def remove_path(self, directory: str) -> None:
        """
        Remove a path from the list of currently accessible paths.

        :param directory: path to add
        """
        self.file_resolver.remove_path(directory)

    def find_all(
        self,
        target: str | Target,
        timeout: int = 10,
        allow_zero: bool = False,
        upper_threshold: float = 0.89,
        lower_threshold: float = 0.69,
        similarity_step: float = 0.033,
    ) -> "list[Match]":
        """
        Find multiples of a target on the screen refreshing the expected target data.

        :param target: target to look for
        :param timeout: timeout before giving up
        :param allow_zero: whether to allow zero matches or raise error
        :param upper_threshold: highest possible similarity
        :param lower_threshold: lowest possible similarity
        :param similarity_step: similarity step for each follow-up attempt
        :returns: matches obtained from finding the target within the region
        :raises: :py:class:`errors.FindError` if no matches are found
                 and zero matches are not allowed

        ..todo:: Find better placement for this override.
        """
        if isinstance(target, str):
            target = self._target_from_string(target)
        cv_backend = self._determine_cv_backend(target)
        dc_backend = self.dc_backend

        try:
            cv_similarity = cv_backend.matcher.params["find"]["similarity"]
        except AttributeError:
            cv_similarity = cv_backend.params["find"]["similarity"]
        print(cv_similarity)
        cv_similarity.value = upper_threshold

        while cv_similarity.value >= lower_threshold:
            log.info(
                f"Trying {target} with similarity {cv_similarity.value}>{lower_threshold}"
            )
            matches = super().find_all(target, timeout, allow_zero=True)
            if len(matches) > 0:
                for i, match in enumerate(matches):
                    match_image = dc_backend.capture_screen(match)
                    if isinstance(target, Image):
                        filename = target.filename
                    else:
                        logging.warning(
                            "Unsupported type of target for the technique "
                            "of lowering similarity"
                        )
                        return matches
                    if i > 0:
                        filename = filename.replace(".png", "") + f"_{i + 1}.png"
                    if cv_similarity.value < upper_threshold:
                        logging.info(
                            f"Saving a new {filename} with similarity {cv_similarity.value}"
                        )
                        Image._cache[filename] = match_image._pil_image
                        filepath = os.path.join("/tmp/guibot", filename)
                        match_image.save(filepath)
                return matches
            else:
                timeout = 1
                cv_similarity.value -= similarity_step
        if allow_zero:
            return []
        raise FindError(target)
