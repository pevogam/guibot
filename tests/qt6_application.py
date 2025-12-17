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

import sys, os
from PyQt6 import QtCore, QtGui, QtWidgets


import common_test


# Set environment variables before QApplication creation
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_FONT_DPI"] = "96"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

# Disable DPI scaling policy
QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)


class ControlsWithLayout(QtWidgets.QWidget):

    def __init__(self, parent: QtWidgets.QWidget = None):
        super().__init__(parent)
        self.setWindowTitle('guibot test application')

        # Use a cross-platform font family
        font_family = 'Arial'
        font_size = 10

        # Create widgets with consistent styling
        button_click = QtWidgets.QPushButton("close on click")
        button_click.setFixedSize(120, 30)
        button_click.setFont(QtGui.QFont(font_family, font_size))
        button_click.clicked.connect(QtWidgets.QApplication.quit)

        line_edit = QtWidgets.QLineEdit()
        line_edit.setPlaceholderText('type quit')
        line_edit.setFixedSize(120, 30)
        line_edit.setFont(QtGui.QFont(font_family, font_size))
        line_edit.textEdited.connect(self.quit_on_type)

        line_edit2 = QtWidgets.QLineEdit()
        line_edit2.setPlaceholderText('type anything')
        line_edit2.setFixedSize(120, 30)
        line_edit2.setFont(QtGui.QFont(font_family, font_size))
        line_edit2.editingFinished.connect(QtWidgets.QApplication.quit)

        text_edit = QtWidgets.QTextEdit('quit')
        text_edit.setFixedSize(120, 30)
        text_edit.setFont(QtGui.QFont(font_family, font_size))
        text_edit.setAcceptDrops(True)
        cursor = text_edit.textCursor()
        cursor.setPosition(0)
        cursor.setPosition(4, QtGui.QTextCursor.MoveMode.KeepAnchor)
        text_edit.setTextCursor(cursor)

        list_view = QtWidgets.QListWidget()
        list_view.addItem('double click')
        list_view.setFixedSize(120, 130)
        list_view.setFont(QtGui.QFont(font_family, font_size))
        list_view.itemDoubleClicked.connect(QtWidgets.QApplication.quit)

        right_click_view = QtWidgets.QListWidget()
        right_click_view.setFixedSize(120, 130)
        right_click_view.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addItem('contextmenu')
        right_click_view.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.ActionsContextMenu)

        quit_action = QtGui.QAction("close", self)
        quit_action.setFont(QtGui.QFont(font_family, font_size))
        right_click_view.addAction(quit_action)
        quit_action.triggered.connect(QtWidgets.QApplication.quit)

        label1 = DragQuitLabel("drag to close", self)
        label1.setFixedSize(120, 30)
        label1.setFont(QtGui.QFont(font_family, font_size))

        label2 = DropQuitLabel("drop to close", self)
        label2.setFixedSize(120, 30)
        label2.setFont(QtGui.QFont(font_family, font_size))

        label3 = MouseDownQuitLabel("mouse down", self)
        label3.setFixedSize(120, 30)
        label3.setFont(QtGui.QFont(font_family, font_size))

        label4 = MouseUpQuitLabel("mouse up", self)
        label4.setFixedSize(120, 30)
        label4.setFont(QtGui.QFont(font_family, font_size))

        image1 = ImageQuitLabel(self)
        pixmap1 = QtGui.QPixmap(os.path.join(common_test.unittest_dir, "images/shape_red_box.png"))
        pixmap1.setDevicePixelRatio(1.0)
        image1.setPixmap(pixmap1)

        image2 = ImageChangeLabel(image1, self)
        pixmap2 = QtGui.QPixmap(os.path.join(common_test.unittest_dir, "images/shape_green_box.png"))
        pixmap2.setDevicePixelRatio(1.0)
        image2.setPixmap(pixmap2)

        self.changing_image = image2
        self.changing_image_counter = 1

        vbox = QtWidgets.QVBoxLayout()
        vbox.setContentsMargins(2, 2, 2, 2)
        vbox.setSpacing(6)
        vbox.addWidget(button_click)
        vbox.addWidget(line_edit)
        vbox.addWidget(line_edit2)
        vbox.addWidget(text_edit)
        vbox.addStretch(1)
        vbox.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        hbox = QtWidgets.QHBoxLayout()
        hbox.setContentsMargins(2, 2, 2, 2)
        hbox.setSpacing(6)
        hbox.addWidget(list_view)
        hbox.addWidget(right_click_view)
        hbox.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        vbox2 = QtWidgets.QVBoxLayout()
        vbox2.setContentsMargins(2, 2, 2, 2)
        vbox2.setSpacing(6)
        vbox2.addWidget(label1)
        vbox2.addWidget(label2)
        vbox2.addWidget(label3)
        vbox2.addWidget(label4)
        vbox2.addStretch(1)
        vbox2.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        vbox3 = QtWidgets.QVBoxLayout()
        vbox3.setContentsMargins(2, 2, 2, 2)
        vbox3.setSpacing(6)
        vbox3.addWidget(image1)
        vbox3.addWidget(image2)
        vbox3.addStretch(1)
        vbox3.setAlignment(QtCore.Qt.AlignmentFlag.AlignTop)

        hbox2 = QtWidgets.QHBoxLayout()
        hbox2.setContentsMargins(10, 10, 10, 10)
        hbox2.setSpacing(3)
        hbox2.addLayout(vbox)
        hbox2.addLayout(hbox)
        hbox2.addLayout(vbox2)
        hbox2.addLayout(vbox3)
        hbox2.addStretch(1)
        hbox2.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)

        self.setLayout(hbox2)
        self.showFullScreen()

        QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('cleanlooks'))

    def quit_on_type(self) -> None:
        sender = self.sender()
        if sender.text() == "quit":
            self.close()

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if e.button() == QtCore.Qt.MouseButton.MiddleButton:
            self.close()

    def keyPressEvent(self, e: QtGui.QKeyEvent) -> None:
        if e.key() == QtCore.Qt.Key.Key_Escape:
            self.close()
        elif e.key() == QtCore.Qt.Key.Key_Shift:
            if self.changing_image_counter == 3:
                self.changing_image.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir,
                                                                        "images/shape_black_box.png")))
            else:
                self.changing_image_counter += 1

    def closeEvent(self, e: QtGui.QCloseEvent) -> None:
        self.close()


class DragQuitLabel(QtWidgets.QLabel):

    def __init__(self, title: str, parent: QtWidgets.QWidget) -> None:
        super().__init__(title, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        self.parent().close()
        # TODO: this only works on some platforms and not others despite
        # identical version but likely due to different dependency versions
        # self.parent().close()
        QtWidgets.QApplication.quit()


class DropQuitLabel(QtWidgets.QLabel):

    def __init__(self, title: str, parent: QtWidgets.QWidget) -> None:
        super().__init__(title, parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QtGui.QDragEnterEvent) -> None:
        if e.mimeData().hasFormat('text/plain'):
            e.accept()
        else:
            e.ignore()

    def dropEvent(self, e: QtGui.QDropEvent) -> None:
        self.parent().close()


class MouseDownQuitLabel(QtWidgets.QLabel):

    def __init__(self, title: str, parent: QtWidgets.QWidget) -> None:
        super().__init__(title, parent)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self.parent().close()


class MouseUpQuitLabel(QtWidgets.QLabel):

    def __init__(self, title: str, parent: QtWidgets.QWidget) -> None:
        super().__init__(title, parent)

    def mouseReleaseEvent(self, e: QtGui.QMouseEvent) -> None:
        self.parent().close()


class ImageQuitLabel(QtWidgets.QLabel):

    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        self.parent().close()


class ImageChangeLabel(QtWidgets.QLabel):

    def __init__(self, image, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.image = image
        self.counter = 1

    def mousePressEvent(self, e: QtGui.QMouseEvent) -> None:
        if self.counter == 3:
            self.image.setPixmap(QtGui.QPixmap(os.path.join(common_test.unittest_dir,
                                                            "images/shape_black_box.png")))
        else:
            self.counter += 1


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    some_controls = ControlsWithLayout()
    some_controls.show()
    sys.exit(app.exec())
