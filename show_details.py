from PyQt4 import QtCore, QtGui
from checkout import autoCheckout, checkoutDetail
from pypref import Preferences

import requests
import webbrowser
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

class showDetail(object):
    def __init__(self, url, baseUrl):
        self.url = url
        self.baseUrl = baseUrl

        self.pref = Preferences(directory=os.path.join(os.environ['APPDATA'], 'Shopify Destroyer'), filename='bot_pref.py')

    def initUI(self, dialog):
    	self.win = dialog
    	dialog.setWindowTitle("Item Details ~ Shopify Destroyer")
    	dialog.setFixedSize(1160, 300)

        self.icon = QtGui.QIcon()
        self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        dialog.setWindowIcon(self.icon)

        self.font = QtGui.QFont()
        self.font.setFamily(_fromUtf8("Roboto Medium"))
        self.font.setPointSize(10)
        self.font.setBold(False)
        self.font.setWeight(50)
        dialog.setFont(self.font)

        self.itemDetailContainer = QtGui.QGroupBox(dialog)
        self.itemDetailContainer.setGeometry(QtCore.QRect(5, 0, 1150, 290))
        self.itemDetailContainer.setFont(self.font)
        self.itemDetailContainer.setTitle("Item Detail")

        self.itemTable = QtGui.QTableWidget(self.itemDetailContainer)
        self.itemTable.setGeometry(QtCore.QRect(10, 20, 860, 260))
        self.itemTable.setRowCount(0)

        self.itemTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
        self.itemTable.setFrameShape(QtGui.QFrame.StyledPanel)
        self.itemTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
        self.itemTable.setGridStyle(QtCore.Qt.SolidLine)

        self.itemTable.setShowGrid(False)
        self.itemTable.setSortingEnabled(True)
        self.itemTable.setWordWrap(True)
        self.itemTable.setCornerButtonEnabled(False)

        item = QtGui.QTableWidgetItem()
        self.itemTable.setColumnCount(7)
        self.itemTable.setColumnWidth(1, 130)
        self.itemTable.setColumnWidth(2, 100)
        self.itemTable.setColumnWidth(3, 80)
        self.itemTable.setColumnWidth(5, 20)
        self.itemTable.setColumnWidth(6, 25)

        self.itemTable.verticalHeader().setVisible(False)

        item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

        item = QtGui.QTableWidgetItem()
        item.setText("Name")
        self.itemTable.setHorizontalHeaderItem(0, item)

        item = QtGui.QTableWidgetItem()
        item.setText("ID")
        self.itemTable.setHorizontalHeaderItem(1, item)

        item = QtGui.QTableWidgetItem()
        item.setText("Public Title")
        self.itemTable.setHorizontalHeaderItem(2, item)

        item = QtGui.QTableWidgetItem()
        item.setText("Stock")
        self.itemTable.setHorizontalHeaderItem(3, item)

        item = QtGui.QTableWidgetItem()
        item.setText("Price")
        self.itemTable.setHorizontalHeaderItem(4, item)

        item = QtGui.QTableWidgetItem()
        item.setText("")
        self.itemTable.setHorizontalHeaderItem(5, item)

        item = QtGui.QTableWidgetItem()
        item.setText("")
        self.itemTable.setHorizontalHeaderItem(6, item)

        self.itemTable.horizontalHeader().setVisible(True)
        self.itemTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

        self.collectData()


    def collectData(self):
        url = self.url + '.json'
        jsonData = requests.get(url).json()
        variants = jsonData['product']['variants']
        imageUrl = jsonData['product']['image'].get('src')

        name = jsonData['product'].get('title')

        for variant in variants:
            variantName = variant.get('title')
            stock = variant.get('inventory_quantity')

            if stock == None:
                stock = '-'

            rowPosition = self.itemTable.rowCount()
            self.itemTable.insertRow(rowPosition)

            self.itemTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem(name + ' - ' + variantName))
            self.itemTable.setItem(rowPosition, 1, QtGui.QTableWidgetItem(str(variant.get('id'))))
            self.itemTable.setItem(rowPosition, 2, QtGui.QTableWidgetItem(variantName))
            self.itemTable.setItem(rowPosition, 3, QtGui.QTableWidgetItem(str(stock)))
            self.itemTable.setItem(rowPosition, 4, QtGui.QTableWidgetItem('$' + variant.get('price')))

            self.insertCartLink(str(variant.get('id')), rowPosition)

            for i in range(5):
                self.itemTable.item(rowPosition, i).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

        QtCore.QCoreApplication.processEvents()

        imageLabel = QtGui.QLabel(self.itemDetailContainer)
        image = QtGui.QPixmap()
        image.loadFromData(requests.request('GET', imageUrl).content)
        imageLabel.setPixmap(image.scaledToWidth(250))
        imageLabel.setGeometry(QtCore.QRect(885, 20, 1050, 270))

    def insertCartLink(self, variantID, rowPos):
        linkPic = QtGui.QLabel()
        linkPic.setPixmap(QtGui.QPixmap(resource_path('Data\linkImg.png')).scaledToWidth(15))
        linkPic.mousePressEvent = lambda event:webbrowser.open(self.baseUrl+'/cart/{}:1'.format(variantID))
        self.itemTable.setCellWidget(rowPos, 5, linkPic)

        cartPic = QtGui.QLabel()
        cartPic.setPixmap(QtGui.QPixmap(resource_path('Data\cartImg.png')).scaledToWidth(20))
        cartPic.mousePressEvent = lambda event:self.checkout(self.baseUrl+'/cart/{}:1'.format(variantID))
        self.itemTable.setCellWidget(rowPos, 6, cartPic)

    def checkout(self, url):
        if self.pref.get('checkoutDetailEntered') == True:
            aCheckout = autoCheckout(url)
            aCheckout.start()
        else:
            checkoutWin = QtGui.QDialog(self.win)
            checkout = checkoutDetail()
            checkout.initUI(checkoutWin)
            checkoutWin.exec_()