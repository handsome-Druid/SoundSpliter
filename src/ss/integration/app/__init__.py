from sys import argv, exit, modules
from types import TracebackType
from typing import NoReturn, Protocol

from PySide6.QtCore import Qt, Slot
from PySide6.QtMultimedia import QMediaDevices
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
)

from ss.common import Config
from ss.flow import Start

from .resources import resources_rc

modules["resources_rc"] = resources_rc
from .ui import Ui_MainWindow


class APP:
    class _DI(Protocol):
        def get[T](self, _: type[T], /) -> T: ...

    def __call__(self) -> NoReturn:
        app = QApplication(argv)
        self._window.show()
        exit(app.exec())

    def __init__(self, di: _DI, /, *, main_window: QMainWindow | None = None) -> None:
        self._ui = Ui_MainWindow()
        self._window: QMainWindow = main_window or QMainWindow()
        self._ui.setupUi(MainWindow=self._window)
        self._config: Config = di.get(Config)
        self._start: Start = di.get(Start)
        self._start.finished.connect(self._on_start_finished)
        self._ui.startPushButton.setEnabled(True)
        self._ui.stopPushButton.setEnabled(False)
        self._ui.startPushButton.clicked.connect(self._on_start_push_button_clicked)
        self._ui.stopPushButton.clicked.connect(self._on_stop_push_botton_clicked)
        self._ui.refreshPushButton.clicked.connect(self._on_refresh_push_button_clicked)
        self._ui.comboBox.activated.connect(self._on_combo_box_activated)
        self._ui.refreshPushButton.click()
        self._ui.startPushButton.click()

    @Slot(object, object, object)
    def _on_start_finished(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb=TracebackType | None,
    ) -> None:
        if exc_type is not None:
            QMessageBox.critical(
                self._window,
                "警告",
                str(object=exc) if exc is not None else str(object=exc_type),
            )
        self._ui.startPushButton.setEnabled(True)
        self._ui.stopPushButton.setEnabled(False)

    @Slot()
    def _on_start_push_button_clicked(self) -> None:
        self._start(None, None, None)
        self._ui.startPushButton.setEnabled(False)
        self._ui.stopPushButton.setEnabled(True)

    @Slot()
    def _on_stop_push_botton_clicked(self) -> None:
        self._start.__exit__(None, None, None)
        self._ui.startPushButton.setEnabled(True)
        self._ui.stopPushButton.setEnabled(False)

    @Slot()
    def _on_refresh_push_button_clicked(self) -> None:
        for device in QMediaDevices.audioOutputs():
            for name in ("left", "right"):
                description: str = device.description()
                item = QListWidgetItem(description)
                item.setData(Qt.ItemDataRole.UserRole, device)
                list_widget: QListWidget = getattr(self._ui, name + "ListWidget")
                list_widget.addItem(item)
                if description == getattr(self._config, name):
                    list_widget.setCurrentItem(item)

    @Slot()
    def _on_combo_box_activated(self) -> None:
        self._config.source = self._ui.comboBox.currentText()
