from PyQt4 import QtCore, QtGui
import sys
import os

from turboactivate import (
    TurboActivate,
    GenuineOptions,
    TA_SKIP_OFFLINE,
    TurboActivateError,
    TurboActivateTrialUsedError,
    TurboActivateConnectionError,
    TurboActivateTrialExpiredError,
    TurboActivateTrialCorruptedError,
    TurboActivateConnectionDelayedError, 
    TurboActivateRevokedError,
    TurboActivateInUseError
)

from main import Scraper

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

ta = TurboActivate(resource_path('Data\AppData.dat'), "3edaca455978b6feefc1a0.09222620")

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class popUp():
    def __init__(self, title, msg,):
        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)

        self.popMsg = QtGui.QMessageBox()
        self.popMsg.setWindowIcon(self.icon)
        self.popMsg.setWindowTitle(title)
        self.popMsg.setText(msg)
        self.popMsg.addButton(QtGui.QMessageBox.Ok)
        self.popMsg.addButton(QtGui.QMessageBox.Cancel)
        self.popMsg.setDefaultButton(QtGui.QMessageBox.Ok)

        self.popMsg.exec_()

class Serial(object):
    def setupUi(self, MainWindow):
        self.win = MainWindow
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.setFixedSize(423, 129)
        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        MainWindow.setWindowIcon(self.icon)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.infoLabel = QtGui.QLabel(self.centralwidget)
        self.infoLabel.setGeometry(QtCore.QRect(10, 0, 411, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.infoLabel.setFont(font)
        self.infoLabel.setObjectName(_fromUtf8("infoLabel"))
        self.serialInput = QtGui.QLineEdit(self.centralwidget)
        self.serialInput.setGeometry(QtCore.QRect(10, 40, 401, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.serialInput.setFont(font)
        self.serialInput.setObjectName(_fromUtf8("serialInput"))
        self.contBtn = QtGui.QPushButton(self.centralwidget)
        self.contBtn.clicked.connect(self.serialCheck)
        self.contBtn.setGeometry(QtCore.QRect(110, 90, 81, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.contBtn.setFont(font)
        self.contBtn.setAutoFillBackground(False)
        self.contBtn.setObjectName(_fromUtf8("contBtn"))
        self.cancBtn = QtGui.QPushButton(self.centralwidget)
        self.cancBtn.clicked.connect(self.exit)
        self.cancBtn.setGeometry(QtCore.QRect(220, 90, 81, 31))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.cancBtn.setFont(font)
        self.cancBtn.setObjectName(_fromUtf8("cancBtn"))
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def serialCheck(self):
        key = str(self.serialInput.text())

        try:
            ta.set_product_key(key)
        except TurboActivateError:
            popUp("Activation Failed", "You have entered an invalid serial key.")
            return
        except:
        	return

        try:
            ta.activate()
        except TurboActivateRevokedError:
            popUp("Activation Failed", "Your serial key has been revoked.")
            return
        except TurboActivateInUseError:
            popUp("Activation Failed", "Serial key has already been activated.")
            return
        except:
        	return

        popUp("Activation Successful", "Program has been successfully activated.")

        self.win.close()
        self.scraperWin = QtGui.QMainWindow()
        self.scraper = Scraper(self.scraperWin)
        self.scraper.initUI()
        self.scraperWin.show()

    def exit(self):
        sys.exit()

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "Serial Check ~ Shopify Destroyer", None))
        self.infoLabel.setText(_translate("MainWindow", "Please enter the serial key you would have recieved in the box below:", None))
        self.contBtn.setText(_translate("MainWindow", "Continue", None))
        self.cancBtn.setText(_translate("MainWindow", "Cancel", None))


if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)

    opts = GenuineOptions()
    opts.days_between_checks(1)
    opts.grace_days(3)

    try:
        if ta.is_genuine(opts):
            scraperWin = QtGui.QMainWindow()
            scraper = Scraper(scraperWin)
            scraper.initUI()
            scraperWin.show()
            sys.exit(app.exec_())
    except (TurboActivateConnectionDelayedError, TurboActivateConnectionError) as e:
        popUp("Activation Failed", "Unable to connect to verification server")

        serialWin = QtGui.QMainWindow()
        serial = Serial()
        serial.setupUi(serialWin)
        serialWin.show()
        sys.exit(app.exec_())
    except TurboActivateError:
        serialWin = QtGui.QMainWindow()
        serial = Serial()
        serial.setupUi(serialWin)
        serialWin.show()
        sys.exit(app.exec_())