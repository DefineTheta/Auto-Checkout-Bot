from PyQt4 import QtCore, QtGui
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

class addProxy(object):
    def initUI(self, dialog):
    	self.win = dialog
    	dialog.setWindowTitle("Add Proxies ~ Shopify Destroyer")
    	dialog.setFixedSize(593, 354)

        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        dialog.setWindowIcon(self.icon) 

        self.font = QtGui.QFont()
        self.font.setFamily(_fromUtf8("Roboto Medium"))
        self.font.setPointSize(10)
        self.font.setBold(False)
        self.font.setWeight(50)
        dialog.setFont(self.font)

        self.dialogButtonBox = QtGui.QDialogButtonBox(dialog)
        self.dialogButtonBox.setGeometry(QtCore.QRect(220, 320, 161, 22))       
        self.dialogButtonBox.setFont(self.font)
        self.dialogButtonBox.setOrientation(QtCore.Qt.Horizontal)
        self.dialogButtonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)

        self.proxyTextEdit = QtGui.QTextEdit(dialog)
        self.proxyTextEdit.setGeometry(QtCore.QRect(10, 35, 571, 271))        
        self.proxyTextEdit.setFont(self.font)

        self.infoLabel = QtGui.QLabel(dialog)
        self.infoLabel.setGeometry(QtCore.QRect(10, 0, 481, 31))
        self.font.setPointSize(12)
        self.infoLabel.setFont(self.font)
        self.infoLabel.setText("Add all the proxies in the text area below: (ip:port:user:pass)")

        QtCore.QObject.connect(self.dialogButtonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), dialog.accept)
        QtCore.QObject.connect(self.dialogButtonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), dialog.reject)
        QtCore.QMetaObject.connectSlotsByName(dialog)
