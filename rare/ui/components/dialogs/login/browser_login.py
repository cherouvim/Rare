# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'browser_login.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_BrowserLogin(object):
    def setupUi(self, BrowserLogin):
        BrowserLogin.setObjectName("BrowserLogin")
        BrowserLogin.resize(246, 130)
        BrowserLogin.setWindowTitle("BrowserLogin")
        self.browser_layout = QtWidgets.QGridLayout(BrowserLogin)
        self.browser_layout.setObjectName("browser_layout")
        self.open_button = QtWidgets.QPushButton(BrowserLogin)
        self.open_button.setObjectName("open_button")
        self.browser_layout.addWidget(self.open_button, 1, 0, 1, 1)
        self.title_label = QtWidgets.QLabel(BrowserLogin)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.title_label.setFont(font)
        self.title_label.setObjectName("title_label")
        self.browser_layout.addWidget(self.title_label, 0, 0, 1, 2, QtCore.Qt.AlignTop)
        self.sid_edit = QtWidgets.QLineEdit(BrowserLogin)
        self.sid_edit.setObjectName("sid_edit")
        self.browser_layout.addWidget(self.sid_edit, 1, 1, 1, 1)
        self.info_label = QtWidgets.QLabel(BrowserLogin)
        font = QtGui.QFont()
        font.setItalic(True)
        self.info_label.setFont(font)
        self.info_label.setWordWrap(True)
        self.info_label.setObjectName("info_label")
        self.browser_layout.addWidget(self.info_label, 3, 0, 1, 2, QtCore.Qt.AlignBottom)
        self.status_label = QtWidgets.QLabel(BrowserLogin)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.status_label.sizePolicy().hasHeightForWidth())
        self.status_label.setSizePolicy(sizePolicy)
        self.status_label.setText("")
        self.status_label.setObjectName("status_label")
        self.browser_layout.addWidget(self.status_label, 2, 1, 1, 1)

        self.retranslateUi(BrowserLogin)
        QtCore.QMetaObject.connectSlotsByName(BrowserLogin)

    def retranslateUi(self, BrowserLogin):
        _translate = QtCore.QCoreApplication.translate
        self.open_button.setText(_translate("BrowserLogin", "Open Browser"))
        self.title_label.setText(_translate("BrowserLogin", "Login through browser"))
        self.sid_edit.setPlaceholderText(_translate("BrowserLogin", "Insert SID here"))
        self.info_label.setText(_translate("BrowserLogin",
                                           "Click the button to open the login page in a browser. After logging in, copy the SID code in the input above."))


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)
    BrowserLogin = QtWidgets.QWidget()
    ui = Ui_BrowserLogin()
    ui.setupUi(BrowserLogin)
    BrowserLogin.show()
    sys.exit(app.exec_())