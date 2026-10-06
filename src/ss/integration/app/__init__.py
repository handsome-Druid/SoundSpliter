from collections.abc import Callable
from sys import argv, exit, modules
from types import TracebackType
from typing import NoReturn, Protocol

from pydantic import ValidationError
from PySide6.QtCore import QEvent, QLockFile, QPoint, QRect, QSettings, Qt, QTimer, Slot
from PySide6.QtGui import QAction, QCloseEvent, QCursor, QGuiApplication, QIcon, QScreen
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices
from PySide6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidget,
)
from shiboken6 import isValid

from ss.common import Config
from ss.flow import Start

from .resources import resources_rc

modules["resources_rc"] = resources_rc
from .ui import Ui_MainWindow


class APP:
    class _DI(Protocol):
        def get[T](self, _: type[T], /) -> T: ...
        def close(self): ...

    def __call__(self) -> NoReturn:
        if not self._hide:
            self._window.show()
            self._show_action.trigger()
        else:
            self._hidden = getattr(self, "_hidden", set())
            self._hidden.add(self._window)
        exit(self._app.exec())

    def __init__(self, di: _DI, /, *, main_window: QMainWindow | None = None) -> None:
        try:
            self._di: APP._DI = di
            if "--hide" in argv:
                argv.remove("--hide")
                self._hide = True
            else:
                self._hide = False
            self._app = QApplication(argv)
            self._app.aboutToQuit.connect(self._di.close)
            self._ui = Ui_MainWindow()
            self._window: QMainWindow = main_window or QMainWindow()
            self._ui.setupUi(MainWindow=self._window)
            self._message_box = QMessageBox(parent=self._window)
            self._app.setApplicationName(self._window.windowTitle())
            self._config: Config = self._di.get(Config)
            self._start: Start = self._di.get(Start)
            self._lock = QLockFile(self._config.dir_.filePath(".lock"))
            self._lock.setStaleLockTime(0)
            if not self._lock.tryLock(0):
                if self._lock.error() == QLockFile.LockError.LockFailedError:
                    raise RuntimeError("已有一个程序实例正在运行，请检查系统托盘。")
                else:
                    raise RuntimeError("无法创建单实例锁，请检查目录权限。")
            self._window.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, on=False)
            icon = QIcon(":/image/icon")
            self._tray_icon = QSystemTrayIcon(
                parent=self._window, toolTip=self._window.windowTitle(), icon=icon
            )
            self._tray_icon.activated.connect(self._on_tray_icon_activated)
            self._start_action = QAction(
                self._ui.startPushButton.text(), parent=self._window
            )
            self._start_action.triggered.connect(self._ui.startPushButton.click)
            self._stop_action = QAction(
                self._ui.stopPushButton.text(), parent=self._window
            )
            self._stop_action.triggered.connect(self._ui.stopPushButton.click)
            self._quit_action = QAction("退出", parent=self._window)
            self._quit_action.triggered.connect(self._on_quit_action_triggered)
            self._show_action = QAction("显示主窗口", parent=self._window)
            self._show_action.triggered.connect(self._on_show_action_triggered)
            self._hide_action = QAction("隐藏到托盘", parent=self._window)
            self._hide_action.triggered.connect(self._on_hide_action_triggered)
            self._tray_menu = QMenu(
                self._window.windowTitle(), parent=self._window, icon=icon
            )
            self._tray_menu.addActions((self._show_action, self._hide_action))
            self._tray_menu.addSeparator()
            self._tray_menu.addActions((self._start_action, self._stop_action))
            self._tray_menu.addSeparator()
            self._tray_menu.addAction(self._quit_action)
            self._tray_icon.setContextMenu(self._tray_menu)
            self._tray_icon.show()
            changeEvent_: Callable[[QEvent], None] = self._window.changeEvent

            def changeEvent(event: QEvent) -> None:
                if (
                    event.type() == QEvent.Type.WindowStateChange
                    and self._window.isMinimized()
                ):
                    self._hidden = getattr(self, "_hidden", set())
                    self._hidden.update(
                        widget
                        for widget in self._app.topLevelWidgets()
                        if widget.isVisible() and widget.hide() is None
                    )
                    event.accept()
                else:
                    changeEvent_(event)

            self._window.changeEvent = changeEvent
            closeEvent_: Callable[[QCloseEvent], None] = self._window.closeEvent

            def closeEvent(event: QCloseEvent) -> None:
                if (
                    self._message_box.question(
                        self._window,
                        self._app.applicationName(),
                        "确认要退出吗？",
                        buttons=self._message_box.StandardButton.Yes
                        | self._message_box.StandardButton.No,
                        defaultButton=self._message_box.StandardButton.No,
                    )
                    == self._message_box.StandardButton.Yes
                ):
                    closeEvent_(event)
                else:
                    event.ignore()

            self._window.closeEvent = closeEvent
            self._startup_command: str = '"' + argv[0] + '" --hide'
            if "__compiled__" in globals():
                self._settings = QSettings(
                    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Run",
                    QSettings.Format.NativeFormat,
                )
                if self._settings.contains(self._app.applicationName()):
                    self._ui.startupCheckBox.setChecked(True)
                    if (
                        self._settings.value(self._app.applicationName())
                        != self._startup_command
                    ):
                        self._settings.setValue(
                            self._app.applicationName(), self._startup_command
                        )
                else:
                    self._ui.startupCheckBox.setChecked(False)
                self._ui.startupCheckBox.checkStateChanged.connect(
                    self._on_startup_check_box_check_state_changed
                )
            else:
                self._ui.startupCheckBox.setEnabled(False)
                self._ui.startupCheckBox.hide()
            self._start.finished.connect(self._on_start_finished)
            self._ui.startPushButton.setEnabled(True)
            self._ui.stopPushButton.setEnabled(False)
            self._ui.startPushButton.clicked.connect(self._on_start_push_button_clicked)
            self._ui.stopPushButton.clicked.connect(self._on_stop_push_button_clicked)
            self._ui.refreshPushButton.clicked.connect(
                self._on_refresh_push_button_clicked
            )
            self._ui.leftListWidget.currentItemChanged.connect(
                self.on_left_list_widget_current_item_changed
            )
            self._ui.rightListWidget.currentItemChanged.connect(
                self.on_right_list_widget_current_item_changed
            )
            self._ui.audioInputComboBox.activated.connect(
                self._on_audio_input_combo_box_activated
            )
            self._ui.leftSpinBox.setValue(self._config.left_latency)
            self._ui.rightSpinBox.setValue(self._config.right_latency)
            self._ui.leftSpinBox.valueChanged.connect(
                self._on_left_spin_box_value_changed
            )
            self._ui.rightSpinBox.valueChanged.connect(
                self._on_right_spin_box_value_changed
            )
            self._mediadevices = QMediaDevices(parent=self._window)
            self._ui.audioOutputComboBox.setEnabled(False)
            self._ui.audioOutputComboBox.activated.connect(
                self._on_audio_output_combo_box_activated
            )
            self._ui.audioCheckBox.setChecked(False)
            self._ui.audioCheckBox.checkStateChanged.connect(
                self._on_check_box_check_state_changed
            )
            if self._config.volume_device is not None:
                assert self._config.volume is not None
                self._ui.audioCheckBox.setChecked(True)
                self._ui.audioOutputComboBox.addItem(
                    self._config.volume, userData=self._config.volume_device
                )
                self._ui.audioOutputComboBox.setCurrentIndex(
                    self._ui.audioOutputComboBox.count() - 1
                )
            if self._config.source_device is not None:
                self._ui.audioInputComboBox.addItem(
                    self._config.source_device.description(),
                    userData=self._config.source_device,
                )
                self._ui.audioInputComboBox.setCurrentIndex(
                    self._ui.audioInputComboBox.count() - 1
                )
                self._ui.sourceLabel.setText("音频输入源已选择：")
                self._ui.sourceLabel.setStyleSheet("color: rgb(40, 167, 69)")
            else:
                for device in self._mediadevices.audioInputs():
                    description: str = device.description()
                    if "CABLE Output" in device.description():
                        self._ui.audioInputComboBox.addItem(
                            description, userData=device
                        )
                        self._ui.audioInputComboBox.setCurrentIndex(
                            self._ui.audioInputComboBox.count() - 1
                        )
                        self._ui.sourceLabel.setText("音频输入源已选择：")
                        self._ui.sourceLabel.setStyleSheet("color: rgb(40, 167, 69)")
                        self._config.source_device = device
                        if not self._ui.audioCheckBox.isChecked():
                            for device in self._mediadevices.audioOutputs():
                                description: str = device.description()
                                if "CABLE Input" in device.description():
                                    self._ui.audioCheckBox.setChecked(True)
                                    self._ui.audioOutputComboBox.addItem(
                                        description, userData=device
                                    )
                                    self._ui.audioOutputComboBox.setCurrentIndex(
                                        self._ui.audioOutputComboBox.count() - 1
                                    )
                                    self._config.volume_device = device
                                    break
                        break
            self._ui.refreshPushButton.click()
            self._started = False
            self._mediadevices.audioInputsChanged.connect(self._on_audio_device_changed)
            self._mediadevices.audioOutputsChanged.connect(
                self._on_audio_device_changed
            )
            self._ui.startPushButton.click()
        except BaseException as e:
            getattr(self, "_message_box", QMessageBox).critical(
                getattr(self, "_window", None),
                self._app.applicationName() if hasattr(self, "_app") else "Critical",
                str(e),
            )
            raise

    @Slot(object, object, object)
    def _on_start_finished(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._ui.startPushButton.setEnabled(True)
        self._ui.refreshPushButton.setEnabled(True)
        self._ui.leftListWidget.setEnabled(True)
        self._ui.rightListWidget.setEnabled(True)
        self._ui.leftSpinBox.setEnabled(True)
        self._ui.rightSpinBox.setEnabled(True)
        self._ui.audioInputComboBox.setEnabled(True)
        self._ui.audioCheckBox.setEnabled(True)
        if self._ui.audioCheckBox.isChecked():
            self._ui.audioOutputComboBox.setEnabled(True)
        else:
            self._ui.audioOutputComboBox.setEnabled(False)
        self._ui.stopPushButton.setEnabled(False)
        self._start_action.setEnabled(True)
        self._stop_action.setEnabled(False)
        if exc_type is not None:
            if self._window.isVisible():
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    self._app.applicationName(),
                    str(object=exc) if exc is not None else str(object=exc_type),
                    buttons=QMessageBox.StandardButton.Ok,
                    parent=self._window,
                )
                self._message_boxes: set[QMessageBox] = getattr(
                    self, "_message_boxes", set()
                )
                self._message_boxes.add(box)
                box.finished.connect(
                    lambda: getattr(self, "_message_boxes", set()).discard(box)
                )
                box.finished.connect(
                    lambda: getattr(self, "_hidden", set()).discard(box)
                )
                box.finished.connect(box.deleteLater)
                box.open()
            else:
                self._pending_msg: list[str] = getattr(self, "_pending_msg", [])
                self._pending_msg.append(str(object=exc))

    @Slot()
    def _on_start_push_button_clicked(self) -> None:
        self._start(None, None, None)
        self._ui.startPushButton.setEnabled(False)
        self._ui.refreshPushButton.setEnabled(False)
        self._ui.leftListWidget.setEnabled(False)
        self._ui.rightListWidget.setEnabled(False)
        self._ui.leftSpinBox.setEnabled(False)
        self._ui.rightSpinBox.setEnabled(False)
        self._ui.audioInputComboBox.setEnabled(False)
        self._ui.audioOutputComboBox.setEnabled(False)
        self._ui.audioCheckBox.setEnabled(False)
        self._ui.stopPushButton.setEnabled(True)
        self._start_action.setEnabled(False)
        self._stop_action.setEnabled(True)
        self._started = True

    @Slot()
    def _on_stop_push_button_clicked(self) -> None:
        self._start.__exit__(None, None, None)
        self._started = False

    @Slot()
    def _on_refresh_push_button_clicked(self) -> None:
        self._ui.leftListWidget.setCurrentRow(-1)
        self._ui.rightListWidget.setCurrentRow(-1)
        self._ui.leftListWidget.clear()
        self._ui.rightListWidget.clear()
        for device in self._mediadevices.audioOutputs():
            for name in ("left", "right"):
                description: str = device.description()
                item = QListWidgetItem(description)
                item.setData(Qt.ItemDataRole.UserRole, device)
                list_widget: QListWidget = getattr(self._ui, name + "ListWidget")
                list_widget.addItem(item)
                if description == getattr(self._config, name):
                    list_widget.setCurrentItem(item)

    @Slot()
    def _on_audio_input_combo_box_activated(self) -> None:
        device: QAudioDevice = self._ui.audioInputComboBox.currentData(
            Qt.ItemDataRole.UserRole
        )
        self._config.source_device = device
        self._ui.sourceLabel.setText("音频输入源已选择：")
        self._ui.sourceLabel.setStyleSheet("color: rgb(40, 167, 69)")
        if "CABLE Output" in device.description():
            for device in self._mediadevices.audioOutputs():
                if "CABLE Input" in device.description():
                    self._config.volume_device = device
                    self._ui.audioCheckBox.setChecked(True)
                    self._ui.audioOutputComboBox.clear()
                    self._ui.audioOutputComboBox.addItem(
                        device.description(), userData=device
                    )
                    self._ui.audioOutputComboBox.setCurrentIndex(
                        self._ui.audioOutputComboBox.count() - 1
                    )
                    break

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_left_list_widget_current_item_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        try:
            self._config.left_device = current.data(Qt.ItemDataRole.UserRole)
        except ValidationError as e:
            if self._window.isVisible():
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    self._app.applicationName(),
                    str(object=e),
                    buttons=QMessageBox.StandardButton.Ok,
                    parent=self._window,
                )
                self._message_boxes = getattr(self, "_message_boxes", set())
                self._message_boxes.add(box)
                box.finished.connect(
                    lambda: getattr(self, "_message_boxes", set()).discard(box)
                )
                box.finished.connect(
                    lambda: getattr(self, "_hidden", set()).discard(box)
                )
                box.finished.connect(box.deleteLater)
                box.open()
            else:
                self._pending_msg: list[str] = getattr(self, "_pending_msg", [])
                self._pending_msg.append(str(object=e))
            QTimer.singleShot(
                0,
                lambda: (
                    self._ui.leftListWidget.setCurrentRow(-1)
                    if previous is None
                    else self._ui.leftListWidget.setCurrentItem(previous)
                ),
            )

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_right_list_widget_current_item_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        try:
            self._config.right_device = current.data(Qt.ItemDataRole.UserRole)
        except ValidationError as e:
            if self._window.isVisible():
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    self._app.applicationName(),
                    str(object=e),
                    buttons=QMessageBox.StandardButton.Ok,
                    parent=self._window,
                )
                self._message_boxes = getattr(self, "_message_boxes", set())
                self._message_boxes.add(box)
                box.finished.connect(
                    lambda: getattr(self, "_message_boxes", set()).discard(box)
                )
                box.finished.connect(
                    lambda: getattr(self, "_hidden", set()).discard(box)
                )
                box.finished.connect(box.deleteLater)
                box.open()
            else:
                self._pending_msg: list[str] = getattr(self, "_pending_msg", [])
                self._pending_msg.append(str(object=e))
            QTimer.singleShot(
                0,
                lambda: (
                    self._ui.rightListWidget.setCurrentRow(-1)
                    if previous is None
                    else self._ui.rightListWidget.setCurrentItem(previous)
                ),
            )

    @Slot(Qt.CheckState)
    def _on_check_box_check_state_changed(self, state: Qt.CheckState) -> None:
        if state == Qt.CheckState.Checked:
            self._ui.audioOutputComboBox.setEnabled(True)
            source_device: QAudioDevice | None = self._config.source_device
            if (
                source_device is not None
                and "CABLE Output" in source_device.description()
            ):
                for device in self._mediadevices.audioOutputs():
                    if "CABLE Input" in device.description():
                        self._config.volume_device = device
                        self._ui.audioOutputComboBox.clear()
                        self._ui.audioOutputComboBox.addItem(
                            device.description(), userData=device
                        )
                        self._ui.audioOutputComboBox.setCurrentIndex(
                            self._ui.audioOutputComboBox.count() - 1
                        )
                        break
        else:
            self._ui.audioOutputComboBox.setCurrentIndex(-1)
            self._ui.audioOutputComboBox.setEnabled(False)
            self._config.volume_device = None

    @Slot()
    def _on_audio_output_combo_box_activated(self) -> None:
        self._config.volume_device = self._ui.audioOutputComboBox.currentData(
            Qt.ItemDataRole.UserRole
        )

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._show_action.trigger()

    @Slot()
    def _on_hide_action_triggered(self) -> None:
        self._hidden: set[QWidget] = getattr(self, "_hidden", set())
        self._hidden.update(
            widget
            for widget in self._app.topLevelWidgets()
            if widget.isVisible() and widget.hide() is None
        )

    @Slot()
    def _on_show_action_triggered(self) -> None:
        if self._window.isMinimized():
            self._window.showNormal()
        if hasattr(self, "_hidden"):
            for widget in self._hidden:
                if isValid(widget):
                    widget.show()
            del self._hidden
        screen: QScreen = (
            QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        )
        available: QRect = screen.availableGeometry()
        center: QPoint = screen.availableGeometry().center()
        for window in self._app.topLevelWidgets():
            if window.isVisible() and not available.contains(window.frameGeometry()):
                window.move(center - window.frameGeometry().center() + window.pos())
        self._window.raise_()
        self._window.activateWindow()
        modal: QWidget | None = self._app.activeModalWidget()
        if hasattr(self, "_pending_msg"):
            box = QMessageBox(
                QMessageBox.Icon.Critical,
                self._app.applicationName(),
                "\n".join(self._pending_msg),
                buttons=QMessageBox.StandardButton.Ok,
                parent=self._window,
            )
            self._message_boxes = getattr(self, "_message_boxes", set())
            self._message_boxes.add(box)
            box.finished.connect(
                lambda: getattr(self, "_message_boxes", set()).discard(box)
            )
            box.finished.connect(lambda: getattr(self, "_hidden", set()).discard(box))
            box.finished.connect(box.deleteLater)
            del self._pending_msg
            box.finished.connect(
                lambda: (
                    (modal.raise_(), modal.activateWindow())
                    if (modal := self._app.activeModalWidget()) is not None
                    else None
                )
            )
            box.open()
        elif modal is not None:
            modal.raise_()
            modal.activateWindow()

    @Slot()
    def _on_quit_action_triggered(self) -> None:
        self._window.hide()
        self._app.quit()

    @Slot()
    def _on_audio_device_changed(self) -> None:
        if not self._started or not self._ui.startPushButton.isEnabled():
            return
        if (
            self._config.source_device is not None
            and self._config.left_device is not None
            and self._config.right_device is not None
        ):
            self._hidden = getattr(self, "_hidden", set())
            if hasattr(self, "_message_boxes"):
                for box in self._message_boxes.copy():
                    box.close()
                    box.deleteLater()
                    self._hidden.discard(box)
                del self._message_boxes
            if hasattr(self, "_pending_msg"):
                del self._pending_msg
            self._ui.startPushButton.click()

    @Slot(Qt.CheckState)
    def _on_startup_check_box_check_state_changed(self, state: Qt.CheckState) -> None:
        if state == Qt.CheckState.Checked:
            self._settings.setValue(self._app.applicationName(), self._startup_command)
        else:
            self._settings.remove(self._app.applicationName())

    @Slot(int)
    def _on_left_spin_box_value_changed(self, value: int) -> None:
        try:
            self._config.left_latency = value
        except ValidationError as e:
            if self._window.isVisible():
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    self._app.applicationName(),
                    str(object=e),
                    buttons=QMessageBox.StandardButton.Ok,
                    parent=self._window,
                )
                self._message_boxes = getattr(self, "_message_boxes", set())
                self._message_boxes.add(box)
                box.finished.connect(
                    lambda: getattr(self, "_message_boxes", set()).discard(box)
                )
                box.finished.connect(
                    lambda: getattr(self, "_hidden", set()).discard(box)
                )
                box.finished.connect(box.deleteLater)
                box.open()
            else:
                self._pending_msg: list[str] = getattr(self, "_pending_msg", [])
                self._pending_msg.append(str(object=e))
            QTimer.singleShot(
                0, lambda: self._ui.leftSpinBox.setValue(self._config.left_latency)
            )

    @Slot(int)
    def _on_right_spin_box_value_changed(self, value: int) -> None:
        try:
            self._config.right_latency = value
        except ValidationError as e:
            if self._window.isVisible():
                box = QMessageBox(
                    QMessageBox.Icon.Critical,
                    self._app.applicationName(),
                    str(object=e),
                    buttons=QMessageBox.StandardButton.Ok,
                    parent=self._window,
                )
                self._message_boxes = getattr(self, "_message_boxes", set())
                self._message_boxes.add(box)
                box.finished.connect(
                    lambda: getattr(self, "_message_boxes", set()).discard(box)
                )
                box.finished.connect(
                    lambda: getattr(self, "_hidden", set()).discard(box)
                )
                box.finished.connect(box.deleteLater)
                box.open()
            else:
                self._pending_msg: list[str] = getattr(self, "_pending_msg", [])
                self._pending_msg.append(str(object=e))
            QTimer.singleShot(
                0, lambda: self._ui.rightSpinBox.setValue(self._config.right_latency)
            )
