from typing import ClassVar, override

from pydantic import BaseModel, Field, ValidationError
from pydantic_yaml import (
    parse_yaml_file_as,
    to_yaml_file,  # pyright: ignore[reportUnknownVariableType]
)
from PySide6.QtCore import QDir, QFile, QStandardPaths
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices


class Config(BaseModel):
    # model_config = ConfigDict(validate_assignment=True)
    left: str | None = None
    right: str | None = None
    source: str | None = None
    volume: str | None = None
    left_latency: int = Field(default=0, ge=0)
    right_latency: int = Field(default=0, ge=0)

    @property
    def left_device(self) -> QAudioDevice | None:
        return next(
            (
                device
                for device in QMediaDevices.audioOutputs()
                if device.description() == self.left
            ),
            None,
        )

    @left_device.setter
    def left_device(self, value: QAudioDevice | None) -> None:
        self.left = value and value.description()

    @property
    def right_device(self) -> QAudioDevice | None:
        return next(
            (
                device
                for device in QMediaDevices.audioOutputs()
                if device.description() == self.right
            ),
            None,
        )

    @right_device.setter
    def right_device(self, value: QAudioDevice | None) -> None:
        self.right = value and value.description()

    @property
    def source_device(self) -> QAudioDevice | None:
        return next(
            (
                device
                for device in QMediaDevices.audioInputs()
                if device.description() == self.source
            ),
            None,
        )

    @source_device.setter
    def source_device(self, value: QAudioDevice | None) -> None:
        self.source = value and value.description()

    @property
    def volume_device(self) -> QAudioDevice | None:
        return next(
            (
                device
                for device in QMediaDevices.audioOutputs()
                if device.description() == self.volume
            ),
            None,
        )

    @volume_device.setter
    def volume_device(self, value: QAudioDevice | None) -> None:
        self.volume = value and value.description()

    dir_: ClassVar[QDir]
    _file: ClassVar[QFile]

    @staticmethod
    def from_disk() -> Config:
        if not QDir().mkpath(
            QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppLocalDataLocation
            )
        ):
            raise OSError(
                "程序无法在本地数据目录中创建所需的文件夹，请检查权限或磁盘空间。"
            )
        Config.dir_ = QDir(
            path=QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.AppLocalDataLocation
            )
        )
        Config._file = QFile(Config.dir_.filePath("config.yml"))
        if Config._file.exists() and Config._file.size() > 0:
            try:
                return parse_yaml_file_as(
                    model_type=Config, file=Config._file.fileName()
                )
            except ValidationError:
                pass
        config = Config()
        to_yaml_file(file=Config._file.fileName(), model=config)
        return config

    @override
    def __setattr__(self, name: str, value: object) -> None:
        if name not in type(self).model_fields:
            super().__setattr__(name, value)
            return
        old_value: object = getattr(self, name)
        try:
            super().__setattr__(name, value)
        except ValidationError:
            super().__setattr__(name, old_value)
            raise
        to_yaml_file(file=self._file.fileName(), model=self)

    # @model_validator(mode="after")
    # def _validate(self) -> Self:
    #     if self.left is not None and self.left == self.right:
    #         raise ValueError("左右声道输出不能设置相同的设备：" + self.left)
    #     return self
