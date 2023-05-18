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

SUMMARY
------------------------------------------------------
Main guibot interface for GUI automation.

This frontend is recommended for use in most normal cases.


INTERFACE
------------------------------------------------------

"""

import os
import logging

from .errors import *
from .fileresolver import FileResolver
from .region import Region
from .target import Image


log = logging.getLogger('guibot')
log.addHandler(logging.NullHandler())


class GuiBot(Region):
    """
    The main guibot object is the root (first and screen wide) region
    with some convenience functions added.

    .. seealso:: Real API is inherited from :py:class:`region.Region`.
    """

    def __init__(self, dc=None, cv=None):
        """
        Build a guibot object.

        :param dc: DC backend used for any display control
        :type dc: :py:class:`controller.Controller` or None
        :param cv: CV backend used for any target finding
        :type cv: :py:class:`finder.Finder` or None

        We will initialize with default region of full screen and default
        display control and computer vision backends if none are provided.
        """
        super(GuiBot, self).__init__(dc=dc, cv=cv)

        self.file_resolver = FileResolver()

    def add_path(self, directory):
        """
        Add a path to the list of currently accessible paths
        if it wasn't already added.

        :param str directory: path to add
        """
        self.file_resolver.add_path(directory)

    def remove_path(self, directory):
        """
        Remove a path from the list of currently accessible paths.

        :param str directory: path to add
        """
        self.file_resolver.remove_path(directory)

    def find_all(self, target, timeout=10, allow_zero=False,
                 upper_threshold=0.89, lower_threshold=0.69, similarity_step=0.033):
        """
        TODO: Decide about best place for this later on.
        """
        if isinstance(target, str):
            target_name = target
            target = self._target_from_string(target)
        else:
            target_name = target.filename
        cv_backend = self._determine_cv_backend(target)
        try:
            print(cv_backend.matcher.params["find"]["similarity"])
            cv_similarity = cv_backend.matcher.params["find"]["similarity"]
        except AttributeError:
            cv_similarity = cv_backend.params["find"]["similarity"]
        print(cv_backend.params["find"]["similarity"])
        cv_similarity.value = upper_threshold
        while cv_similarity.value >= lower_threshold:
            log.info(f"Trying {target_name} with similarity {cv_similarity.value}>{lower_threshold}")
            matches = super().find_all(target, timeout, allow_zero=True)
            if len(matches) > 0:
                for i, match in enumerate(matches):
                    match_image = self.dc_backend.capture_screen(match)
                    if isinstance(target, Image):
                        filename = target.filename
                    else:
                        logging.warning("Unsupported type of target for the technique "
                                        "of lowering similarity")
                        return matches
                    if i > 0:
                        filename = filename.replace(".png", "") + f"_{i+1}.png"
                    if cv_similarity.value < upper_threshold:
                        logging.info(f"Saving a new {filename} with similarity {cv_similarity.value}")
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
