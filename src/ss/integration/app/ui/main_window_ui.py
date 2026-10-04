# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.11.2
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QPushButton, QSizePolicy, QVBoxLayout, QWidget)

from ss.integration.app.widgets.combo_box import ComboBox
import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        icon = QIcon()
        icon.addFile(u":/images/icon", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        MainWindow.setWindowIcon(icon)
        MainWindow.setStyleSheet(u"font-size: 11px")
        self.action = QAction(MainWindow)
        self.action.setObjectName(u"action")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.iconLabel = QLabel(self.centralwidget)
        self.iconLabel.setObjectName(u"iconLabel")
        self.iconLabel.setGeometry(QRect(10, 0, 131, 131))
        self.iconLabel.setTextFormat(Qt.TextFormat.AutoText)
        self.iconLabel.setPixmap(QPixmap(u":/images/icon"))
        self.iconLabel.setScaledContents(True)
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(140, 0, 431, 131))
        font = QFont()
        font.setFamilies([u"Comic Sans MS"])
        font.setBold(True)
        self.label.setFont(font)
        self.label.setStyleSheet(u"font-size: 70px")
        self.layoutWidget = QWidget(self.centralwidget)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(600, 70, 181, 56))
        self.gridLayout = QGridLayout(self.layoutWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.leftLatencyLabel = QLabel(self.layoutWidget)
        self.leftLatencyLabel.setObjectName(u"leftLatencyLabel")

        self.gridLayout.addWidget(self.leftLatencyLabel, 0, 0, 1, 1)

        self.leftLineEdit = QLineEdit(self.layoutWidget)
        self.leftLineEdit.setObjectName(u"leftLineEdit")

        self.gridLayout.addWidget(self.leftLineEdit, 0, 1, 1, 1)

        self.rightLatencyLabel = QLabel(self.layoutWidget)
        self.rightLatencyLabel.setObjectName(u"rightLatencyLabel")

        self.gridLayout.addWidget(self.rightLatencyLabel, 1, 0, 1, 1)

        self.rightLineEdit = QLineEdit(self.layoutWidget)
        self.rightLineEdit.setObjectName(u"rightLineEdit")

        self.gridLayout.addWidget(self.rightLineEdit, 1, 1, 1, 1)

        self.layoutWidget1 = QWidget(self.centralwidget)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.layoutWidget1.setGeometry(QRect(580, 40, 201, 26))
        self.horizontalLayout = QHBoxLayout(self.layoutWidget1)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.sourceLabel = QLabel(self.layoutWidget1)
        self.sourceLabel.setObjectName(u"sourceLabel")
        font1 = QFont()
        font1.setBold(True)
        self.sourceLabel.setFont(font1)
        self.sourceLabel.setStyleSheet(u"color: rgb(255, 0, 0)")

        self.horizontalLayout.addWidget(self.sourceLabel)

        self.comboBox = ComboBox(self.layoutWidget1)
        self.comboBox.setObjectName(u"comboBox")

        self.horizontalLayout.addWidget(self.comboBox)

        self.layoutWidget2 = QWidget(self.centralwidget)
        self.layoutWidget2.setObjectName(u"layoutWidget2")
        self.layoutWidget2.setGeometry(QRect(310, 480, 181, 111))
        self.verticalLayout = QVBoxLayout(self.layoutWidget2)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.startPushButton = QPushButton(self.layoutWidget2)
        self.startPushButton.setObjectName(u"startPushButton")
        self.startPushButton.setMinimumSize(QSize(0, 50))
        self.startPushButton.setStyleSheet(u"font-size: 16px")

        self.verticalLayout.addWidget(self.startPushButton)

        self.stopPushButton = QPushButton(self.layoutWidget2)
        self.stopPushButton.setObjectName(u"stopPushButton")
        self.stopPushButton.setMinimumSize(QSize(0, 50))
        self.stopPushButton.setStyleSheet(u"font-size: 16px")

        self.verticalLayout.addWidget(self.stopPushButton)

        self.layoutWidget3 = QWidget(self.centralwidget)
        self.layoutWidget3.setObjectName(u"layoutWidget3")
        self.layoutWidget3.setGeometry(QRect(20, 150, 761, 321))
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.leftDeviceLabel = QLabel(self.layoutWidget3)
        self.leftDeviceLabel.setObjectName(u"leftDeviceLabel")
        self.leftDeviceLabel.setStyleSheet(u"font-size: 15px")

        self.horizontalLayout_3.addWidget(self.leftDeviceLabel)

        self.rightDeviceLabel = QLabel(self.layoutWidget3)
        self.rightDeviceLabel.setObjectName(u"rightDeviceLabel")
        self.rightDeviceLabel.setStyleSheet(u"font-size: 15px")

        self.horizontalLayout_3.addWidget(self.rightDeviceLabel)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.leftListWidget = QListWidget(self.layoutWidget3)
        self.leftListWidget.setObjectName(u"leftListWidget")

        self.horizontalLayout_2.addWidget(self.leftListWidget)

        self.rightListWidget = QListWidget(self.layoutWidget3)
        self.rightListWidget.setObjectName(u"rightListWidget")

        self.horizontalLayout_2.addWidget(self.rightListWidget)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)

        self.refreshPushButton = QPushButton(self.centralwidget)
        self.refreshPushButton.setObjectName(u"refreshPushButton")
        self.refreshPushButton.setGeometry(QRect(20, 120, 91, 26))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"SoundSpliter", None))
        self.action.setText(QCoreApplication.translate("MainWindow", u"\u9996\u9009\u9879...", None))
        self.iconLabel.setText("")
        self.label.setText(QCoreApplication.translate("MainWindow", u"SoundSpliter", None))
        self.leftLatencyLabel.setText(QCoreApplication.translate("MainWindow", u"\u5de6\u58f0\u9053\u5ef6\u8fdf(ms):", None))
        self.leftLineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.rightLatencyLabel.setText(QCoreApplication.translate("MainWindow", u"\u53f3\u58f0\u9053\u5ef6\u8fdf(ms):", None))
        self.rightLineEdit.setText(QCoreApplication.translate("MainWindow", u"0", None))
        self.sourceLabel.setText(QCoreApplication.translate("MainWindow", u"\u97f3\u9891\u8f93\u5165\u6e90\u672a\u9009\u62e9\uff01", None))
        self.startPushButton.setText(QCoreApplication.translate("MainWindow", u"\u5f00\u59cb\u5206\u6d41", None))
        self.stopPushButton.setText(QCoreApplication.translate("MainWindow", u"\u505c\u6b62\u5206\u6d41", None))
        self.leftDeviceLabel.setText(QCoreApplication.translate("MainWindow", u"\u9009\u62e9\u5de6\u58f0\u9053\u8f93\u51fa\uff1a", None))
        self.rightDeviceLabel.setText(QCoreApplication.translate("MainWindow", u"\u9009\u62e9\u53f3\u58f0\u9053\u8f93\u51fa\uff1a", None))
        self.refreshPushButton.setText(QCoreApplication.translate("MainWindow", u"\u5237\u65b0\u8f93\u51fa\u8bbe\u5907", None))
    # retranslateUi

