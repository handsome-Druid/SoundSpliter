from typing import ClassVar, Self, override

from pydantic import BaseModel, Field, ValidationError, model_validator
from pydantic_yaml import (
    parse_yaml_file_as,
    to_yaml_file,  # pyright: ignore[reportUnknownVariableType]
)
from PySide6.QtCore import QDir, QFile, QFileInfo
from PySide6.QtMultimedia import QAudioDevice, QMediaDevices


class Config(BaseModel):
    left: str | None = None
    right: str | None = None
    source: str | None = None
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

    if "__compiled__" in globals():
        _file: ClassVar[QFile] = QFile(
            QDir(globals()["__compiled__"].containing_dir).filePath("config.yml")
        )
    else:
        _dir: ClassVar[QDir] = QFileInfo(QFile(__file__)).dir()
        for _ in range(3):
            if not _dir.cdUp():
                raise OSError("cd " + _dir.absolutePath() + "/../ 失败")
        _file: ClassVar[QFile] = QFile(_dir.filePath("config.yml"))

    @staticmethod
    def from_disk() -> Config:
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
        super().__setattr__(name, value)
        if name in type(self).model_fields:
            to_yaml_file(file=self._file.fileName(), model=self)

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.left is not None and self.left == self.right:
            raise ValueError("左右声道输出不能设置相同的设备：" + self.left)
        return self
