#!/usr/bin/python3
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

import os
import sys
from PyQt6 import QtCore, QtGui, QtWidgets


# Set environment variables before QApplication creation
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

# Disable DPI scaling policy
QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)


class ImageWithLayout(QtWidgets.QWidget):

    def __init__(self, filename: str, title: str = "show_picture", parent: QtWidgets.QWidget = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(title)

        # Create image label
        image = QtWidgets.QLabel(self)
        pixmap = QtGui.QPixmap(filename)
        pixmap.setDevicePixelRatio(1.0)
        image.setPixmap(pixmap)
        image.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop | QtCore.Qt.AlignmentFlag.AlignLeft)

        # Create layout with zero margins and spacing
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(image)
        layout.setContentsMargins(0, 0, 0, 0)  # left, top, right, bottom
        layout.setSpacing(0)

        self.setLayout(layout)
        self.setStyleSheet('background: #ffffff;')
        self.showFullScreen()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    if len(sys.argv) < 2:
        print("Usage: python qt6_image.py <image_path>")
        sys.exit(1)

    some_image = ImageWithLayout(sys.argv[1])
    some_image.show()
    sys.exit(app.exec())
