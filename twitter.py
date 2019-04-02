from PyQt4 import QtCore, QtGui
from pypref import Preferences
import sys
import os

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

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

class twitterDetail(object):
    def __init__(self):
        self.pref = Preferences(directory=os.path.join(os.environ['APPDATA'], 'Shopify Destroyer'), filename='bot_pref.py')
        self.sucess = False

    def setupUi(self, dialog):
    	self.win = dialog
        dialog.setObjectName(_fromUtf8("dialog"))
        dialog.setFixedSize(535, 197)
        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        dialog.setWindowIcon(self.icon)
        self.infoLabel = QtGui.QLabel(dialog)
        self.infoLabel.setGeometry(QtCore.QRect(10, 0, 521, 41))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.infoLabel.setFont(font)
        self.infoLabel.setObjectName(_fromUtf8("infoLabel"))
        self.ckeyLabel = QtGui.QLabel(dialog)
        self.ckeyLabel.setGeometry(QtCore.QRect(20, 40, 91, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.ckeyLabel.setFont(font)
        self.ckeyLabel.setObjectName(_fromUtf8("ckeyLabel"))
        self.csecretLabel = QtGui.QLabel(dialog)
        self.csecretLabel.setGeometry(QtCore.QRect(20, 70, 111, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.csecretLabel.setFont(font)
        self.csecretLabel.setObjectName(_fromUtf8("csecretLabel"))
        self.akeyLabel = QtGui.QLabel(dialog)
        self.akeyLabel.setGeometry(QtCore.QRect(20, 100, 71, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.akeyLabel.setFont(font)
        self.akeyLabel.setObjectName(_fromUtf8("akeyLabel"))
        self.asecretLabel = QtGui.QLabel(dialog)
        self.asecretLabel.setGeometry(QtCore.QRect(20, 130, 91, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.asecretLabel.setFont(font)
        self.asecretLabel.setObjectName(_fromUtf8("asecretLabel"))
        self.ckeyEdit = QtGui.QLineEdit(dialog)
        self.ckeyEdit.setGeometry(QtCore.QRect(150, 40, 351, 20))
        self.ckeyEdit.setText(_fromUtf8(""))
        self.ckeyEdit.setObjectName(_fromUtf8("ckeyEdit"))
        self.csecretEdit = QtGui.QLineEdit(dialog)
        self.csecretEdit.setGeometry(QtCore.QRect(150, 70, 351, 20))
        self.csecretEdit.setObjectName(_fromUtf8("csecretEdit"))
        self.akeyEdit = QtGui.QLineEdit(dialog)
        self.akeyEdit.setGeometry(QtCore.QRect(150, 100, 351, 20))
        self.akeyEdit.setObjectName(_fromUtf8("akeyEdit"))
        self.asecretEdit = QtGui.QLineEdit(dialog)
        self.asecretEdit.setGeometry(QtCore.QRect(150, 130, 351, 20))
        self.asecretEdit.setObjectName(_fromUtf8("asecretEdit"))
        self.continueBtn = QtGui.QPushButton(dialog)
        self.continueBtn.clicked.connect(self.infoSave)
        self.continueBtn.setGeometry(QtCore.QRect(160, 160, 81, 31))
        self.continueBtn.setObjectName(_fromUtf8("continueBtn"))
        self.cancelBtn = QtGui.QPushButton(dialog)
        self.cancelBtn.clicked.connect(self.exit)
        self.cancelBtn.setGeometry(QtCore.QRect(270, 160, 81, 31))
        self.cancelBtn.setObjectName(_fromUtf8("cancelBtn"))

        self.retranslateUi(dialog)
        QtCore.QMetaObject.connectSlotsByName(dialog)

    def infoSave(self):  
        if self.ckeyEdit.text() != "" and self.csecretEdit.text() != "" and self.akeyEdit.text() != "" and self.asecretEdit.text() != "":
            self.pref.update_preferences({
                'twCKey':str(self.ckeyEdit.text()),
                'twCSecret':str(self.csecretEdit.text()),
                'twAKey':str(self.akeyEdit.text()),
                'twASecret':str(self.asecretEdit.text()),
                'twInfoEntered':True})

            self.sucess = True

            QtGui.QDialog.close(self.win)
        else:
            self.popMsg = QtGui.QMessageBox()
            self.popMsg.setWindowIcon(self.icon)
            self.popMsg.setWindowTitle("Invalid Information")
            self.popMsg.setText("Make sure you have filled in all boxes")
            self.popMsg.addButton(QtGui.QMessageBox.Ok)
            self.popMsg.addButton(QtGui.QMessageBox.Cancel)
            self.popMsg.setDefaultButton(QtGui.QMessageBox.Ok)

            self.popMsg.exec_()

    def exit(self):
        QtGui.QDialog.close(self.win)

    def retranslateUi(self, dialog):
        dialog.setWindowTitle(_translate("dialog", "Twitter ~ Shopify Destroyer", None))
        self.infoLabel.setText(_translate("dialog", "Follow the instructions provided in the ReadMe and input ALL information below", None))
        self.ckeyLabel.setText(_translate("dialog", "Consumer Key", None))
        self.csecretLabel.setText(_translate("dialog", "Consumer Secret", None))
        self.akeyLabel.setText(_translate("dialog", "Access Key", None))
        self.asecretLabel.setText(_translate("dialog", "Access Secret", None))
        self.continueBtn.setText(_translate("dialog", "Continue", None))
        self.cancelBtn.setText(_translate("dialog", "Cancel", None))