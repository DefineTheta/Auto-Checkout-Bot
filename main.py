from PyQt4 import QtCore, QtGui
import time
import webbrowser
import os
import tweepy
import sys
from turboactivate import TurboActivate
from functools import partial
from lxml import etree
from pyperclip import copy
from pypref import Preferences

import requests

from twitter import twitterDetail
from checkout import checkoutDetail, autoCheckout
from add_links import addLinks
from add_proxy import addProxy
from show_details import showDetail

try:
	_fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
	def _fromUtf8(s):
		return s

def resource_path(relative):
	if hasattr(sys, "_MEIPASS"):
		return os.path.join(sys._MEIPASS, relative)
	return os.path.join(os.path.abspath("."), relative)

ta = TurboActivate(resource_path('Data\AppData.dat'), "3edaca455978b6feefc1a0.09222620")

class collectData(QtCore.QThread):
	def __init__(self, scraper, url, keywords, proxy):
		QtCore.QThread.__init__(self)		
		self.inputDate = str(scraper.dateEdit.date().toPyDate())
		self.checkDate = scraper.dateCheck.isChecked()
		self.url = url
		self.keywords = keywords
		self.scraper = scraper
		if proxy != None:
			self.proxy = {'http':'http://'+proxy}
		else:
			self.proxy = proxy

	def __del__(self):
		self.wait()

	def run(self):
		try:
			data = requests.request('GET', self.url, proxies=self.proxy).content
		except requests.exceptions.ProxyError:
			self.scraper.logItems.append('{} - Proxy Error - {} - {}'.format(time.strftime("%m/%d/%Y %I:%M %p"), self.proxy, self.url))

		try:
			self.rootElement = etree.fromstring(data)
		except etree.XMLSyntaxError:
			self.scraper.logItems.append('{} - IP temporarily blocked. Increase repeat time or use more proxies. - {}'.format(time.strftime("%m/%d/%Y %I:%M %p"), self.url))

		for item in self.rootElement.getchildren():
			url = item[0].text
			date = item[1].text[:10]

			if url not in self.scraper.productUrls:
				for keyword in self.keywords:
					if keyword in url:
						if self.checkDate and date == self.inputDate:
							self.scraper.productUrls.append(url)
							self.emit(QtCore.SIGNAL('insertRow(PyQt_PyObject, PyQt_PyObject)'), url, keyword)
						elif not self.checkDate:
							self.scraper.productUrls.append(url)
							self.emit(QtCore.SIGNAL('insertRow(PyQt_PyObject, PyQt_PyObject)'), url, keyword)

		self.scraper.logItems.append(time.strftime("%m/%d/%Y %I:%M %p") + " - Finished scraping - " + self.url)

class monitorItem(QtCore.QThread):
	def __init__(self, task, row):
		QtCore.QThread.__init__(self)
		self.url = "https://kith.com/products/" + task['item_name'] + ".json"
		self.size = task['size']
		self.bill_name = task['billing_profile']
		self.row = row
		self.repeatCount = 0

	def __del__(self):
		self.wait()

	def run(self):
		try:
			self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "Starting... " + str(self.repeatCount))
			jsonData = requests.get(self.url).json()
			variants = jsonData['product']['variants']

			self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "Item Found")

			for variant in variants:
				variantName = variant.get('title')

				if variantName == self.size:
					variantID = str(variant.get('id'))

					self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "Checking Out...")

					aCheckout = autoCheckout('https://kith.com/cart/{}:1'.format(variantID), self.bill_name)
					aCheckout.start()

					while(aCheckout.finished == False):
						time.sleep(10)

					if aCheckout.sucess == True:	
						self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "Checkout Sucessful")
					else:
						self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "An Error Occured")
						time.sleep(20)
						self.repeatCount += 1
						self.run()
		except:
			self.emit(QtCore.SIGNAL('updateStatus(PyQt_PyObject, PyQt_PyObject)'), self.row, "An Error Occured")
			time.sleep(20)
			self.repeatCount += 1
			self.run()

class printLog(QtCore.QThread):
	def __init__(self, scraper):
		QtCore.QThread.__init__(self)
		self.scraper = scraper

	def __del__(self):
		self.wait()

	def run(self):
		for item in self.scraper.logItems:
			self.emit(QtCore.SIGNAL('log(PyQt_PyObject)'), item)
			time.sleep(0.2)

		self.scraper.logItems = []
		self.scraper.logQueued = False

class tweetLink(QtCore.QThread):
	def __init__(self, scraper):
		self.scraper = scraper
		QtCore.QThread.__init__(self)

		if self.scraper.pref.get('twInfoEntered'):
			auth = tweepy.OAuthHandler(self.scraper.pref.get('twCKey'), self.scraper.pref.get('twCSecret'))
			auth.set_access_token(self.scraper.pref.get('twAKey'), self.scraper.pref.get('twASecret'))

			self.twitterAPI = tweepy.API(auth)

	def __del__(self):
		self.wait()

	def run(self):
		for item in self.scraper.tweetItems:
			self.twitterAPI.update_status(item)

		self.scraper.tweetItems = []
		self.scraper.tweetQueued = False

class Scraper(object):
	def __init__(self, window):
		self.window = window

		self.checkedRows = []
		self.productUrls = []
		self.workerThreads = []
		self.logItems = []
		self.tweetItems = []

		self.continuous = False
		self.logQueued = False
		self.tweetQueued = False

		self.monitorTabRender = False
		self.taskTabRender = False
		self.cardTabRender = False
		self.scrapeTabRender = False
		self.settingsTabRender = False

		self.taskEdited = False

		self.logCount = 0
		self.repeatCount = 0

		self.currentTab = None
		self.currentStorePage = None
		self.currentCardPage = None

		self.pref = Preferences(directory=os.path.join(os.environ['APPDATA'], 'Shopify Destroyer'), filename='bot_pref.py')

		if self.pref.get('tasks') == None:
			self.pref.update_preferences({'tasks': []})

		if self.pref.get('billing_profile') == None:
			self.pref.update_preferences({'billing_profile': {}})

		if self.pref.get('shoe_size') == None:
			self.pref.update_preferences({'shoe_size': ['4', '4.5', '5', '5.5', '6', '6.5', '7', '7.5', '8', '8.5', '9', '9.5', '10', '10.5', '11', '11.5', '12', '12.5', '13', '13.5', '14', '14.5', '15']})

		self.tasks = self.pref.get('tasks')
		self.bill_profile = self.pref.get('billing_profile')
		self.proxies = self.pref.get('Proxies')

		self.repeatTimer = QtCore.QTimer()
		self.window.connect(self.repeatTimer, QtCore.SIGNAL('timeout()'), self.programStart)
		self.waitTimer = QtCore.QTimer()
		self.window.connect(self.waitTimer, QtCore.SIGNAL('timeout()'), self.programStart)

	def initUI(self):
		self.window.setWindowTitle("Shopify Destroyer")
		self.window.setFixedSize(800, 570)
		self.mainWidget = QtGui.QWidget(self.window)
		self.window.setCentralWidget(self.mainWidget)

		self.font = QtGui.QFont("Calibri", 11, 65)
		self.plainFont = QtGui.QFont()

		self.taskBarWidget = QtGui.QWidget(self.mainWidget)
		self.taskBarWidget.setGeometry(QtCore.QRect(0, 5, 810, 100))

		self.monitorTabLabel = QtGui.QLabel(self.taskBarWidget)
		self.monitorTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\clipboard.png')).scaledToWidth(80))
		self.monitorTabLabel.setGeometry(QtCore.QRect(80, 0, 80, 80))
		self.monitorTabLabel.mousePressEvent = lambda event:self.monitorTabGUI()
		self.monitorTabLabel.mouseReleaseEvent = lambda event:self.monitorTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\clipboard.png')).scaledToWidth(80))

		self.monitorTextLabel = QtGui.QLabel(self.taskBarWidget)
		self.monitorTextLabel.setGeometry(QtCore.QRect(95, 80, 70, 20))
		self.monitorTextLabel.setFont(self.font)
		self.monitorTextLabel.setText("Monitor")

		self.taskTabLabel = QtGui.QLabel(self.taskBarWidget)
		self.taskTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Tools-PNG-Image.png')).scaledToWidth(80))
		self.taskTabLabel.setGeometry(QtCore.QRect(220, 0, 80, 80))
		self.taskTabLabel.mousePressEvent = lambda event:self.taskTabGUI()
		self.taskTabLabel.mouseReleaseEvent = lambda event:self.taskTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Tools-PNG-Image.png')).scaledToWidth(80))

		self.taskTextLabel = QtGui.QLabel(self.taskBarWidget)
		self.taskTextLabel.setGeometry(QtCore.QRect(230, 80, 70, 20))
		self.taskTextLabel.setFont(self.font)
		self.taskTextLabel.setText("Add Task")

		self.cardTabLabel = QtGui.QLabel(self.taskBarWidget)
		self.cardTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\credit-card-1.png')).scaledToWidth(75))
		self.cardTabLabel.setGeometry(QtCore.QRect(370, 3, 75, 75))
		self.cardTabLabel.mousePressEvent = lambda event:self.cardTabGUI()
		self.cardTabLabel.mouseReleaseEvent = lambda event:self.cardTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\credit-card-1.png')).scaledToWidth(75))

		self.cardTextLabel = QtGui.QLabel(self.taskBarWidget)
		self.cardTextLabel.setGeometry(QtCore.QRect(360, 80, 110, 20))
		self.cardTextLabel.setFont(self.font)
		self.cardTextLabel.setText("Billing Profiles")

		self.scrapeTabLabel = QtGui.QLabel(self.taskBarWidget)
		self.scrapeTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\dsfsdf-dsf.png')).scaledToWidth(80))
		self.scrapeTabLabel.setGeometry(QtCore.QRect(500, 0, 80, 80))
		self.scrapeTabLabel.mousePressEvent = lambda event:self.scrapeTabGUI()
		self.scrapeTabLabel.mouseReleaseEvent = lambda event:self.scrapeTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\dsfsdf-dsf.png')).scaledToWidth(80))

		self.scrapeTextLabel = QtGui.QLabel(self.taskBarWidget)
		self.scrapeTextLabel.setGeometry(QtCore.QRect(515, 80, 70, 20))
		self.scrapeTextLabel.setFont(self.font)
		self.scrapeTextLabel.setText("Scrape")

		self.settingsTabLabel = QtGui.QLabel(self.taskBarWidget)
		self.settingsTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\gear-png-8.png')).scaledToWidth(75))
		self.settingsTabLabel.setGeometry(QtCore.QRect(640, 3, 75, 75))
		self.settingsTabLabel.mousePressEvent = lambda event:self.settingsTabGUI()
		self.settingsTabLabel.mouseReleaseEvent = lambda event:self.settingsTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\gear-png-8.png')).scaledToWidth(75))

		self.settingsTextLabel = QtGui.QLabel(self.taskBarWidget)
		self.settingsTextLabel.setGeometry(QtCore.QRect(653, 80, 70, 20))
		self.settingsTextLabel.setFont(self.font)
		self.settingsTextLabel.setText("Settings")

		self.monitorTabGUI()
		self.monitorTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\clipboard.png')).scaledToWidth(80))

		# QtGui.QApplication.setStyle(QtGui.QStyleFactory.create('windowsvista'))

		# # self.mainWidget.setAutoFillBackground(True)
		# # p = self.mainWidget.palette()
		# # p.setColor(self.mainWidget.backgroundRole(), QtGui.QColor(42,42,42))
		# # self.mainWidget.setPalette(p)

		self.icon = QtGui.QIcon()
		self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		self.window.setWindowIcon(self.icon)

		# self.font = QtGui.QFont("Calibri", 11, 75)
		# self.plainFont = QtGui.QFont()

		# self.inputPanelContainer = QtGui.QGroupBox(self.mainWidget)
		# self.inputPanelContainer.setGeometry(QtCore.QRect(0, 0, 421, 241))
		# self.inputPanelContainer.setTitle("Input Panel")

		# self.dateEdit = QtGui.QDateEdit(QtCore.QDate(int(time.strftime("%Y")), int(time.strftime("%m")), int(time.strftime("%d"))), self.inputPanelContainer)
		# self.dateEdit.setGeometry(QtCore.QRect(140, 210, 121, 22))
		# self.dateEdit.setDisplayFormat("dd/MM/yyyy")

		# self.targetLabel = QtGui.QLabel(self.inputPanelContainer)
		# self.targetLabel.setGeometry(QtCore.QRect(10, 15, 71, 21))
		# self.targetLabel.setFont(self.font)
		# self.targetLabel.setText("Target links")

		# self.loadBtn = QtGui.QPushButton(self.inputPanelContainer)        
		# self.loadBtn.setGeometry(QtCore.QRect(180, 10, 51, 26))
		# self.loadBtn.setText("Load")
		# self.loadBtn.clicked.connect(self.load_links)

		# self.addBtn = QtGui.QPushButton(self.inputPanelContainer)        
		# self.addBtn.setGeometry(QtCore.QRect(240, 10, 51, 26))
		# self.addBtn.setText("Add")
		# self.addBtn.clicked.connect(self.add_links)		

		# self.delBtn = QtGui.QPushButton(self.inputPanelContainer)        
		# self.delBtn.setGeometry(QtCore.QRect(300, 10, 51, 26))
		# self.delBtn.setText("Del")
		# self.delBtn.clicked.connect(self.del_links)

		# self.clearBtn = QtGui.QPushButton(self.inputPanelContainer)        
		# self.clearBtn.setGeometry(QtCore.QRect(360, 10, 51, 26))
		# self.clearBtn.setText("Clear")
		# self.clearBtn.clicked.connect(self.clear_links)

		# self.keyLabel = QtGui.QLabel(self.inputPanelContainer)
		# self.keyLabel.setGeometry(QtCore.QRect(10, 180, 61, 20))
		# self.keyLabel.setFont(self.font)
		# self.keyLabel.setText("Key word")

		# self.keywordInput = QtGui.QLineEdit(self.inputPanelContainer)
		# self.keywordInput.setGeometry(QtCore.QRect(110, 180, 301, 20))

		# self.dateLabel = QtGui.QLabel(self.inputPanelContainer)
		# self.dateLabel.setGeometry(QtCore.QRect(10, 210, 31, 20))
		# self.dateLabel.setFont(self.font)
		# self.dateLabel.setText("Date")

		# self.dateCheck = QtGui.QCheckBox(self.inputPanelContainer)
		# self.dateCheck.setGeometry(QtCore.QRect(110, 210, 21, 21))

		# self.linkTable = QtGui.QTableWidget(self.inputPanelContainer)
		# self.linkTable.setGeometry(QtCore.QRect(10, 40, 401, 131))
		# self.linkTable.setMinimumSize(QtCore.QSize(390, 0))

		# self.linkTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
		# self.linkTable.setFrameShape(QtGui.QFrame.StyledPanel)
		# self.linkTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
		# self.linkTable.setGridStyle(QtCore.Qt.SolidLine)

		# self.linkTable.setShowGrid(False)
		# self.linkTable.setSortingEnabled(True)
		# self.linkTable.setWordWrap(True)
		# self.linkTable.setCornerButtonEnabled(False)

		# self.linkTable.setColumnCount(2)
		# header = self.linkTable.horizontalHeader()
		# self.linkTable.setColumnWidth(0, 20)
		# header.setResizeMode(1, QtGui.QHeaderView.Stretch)
		# self.linkTable.verticalHeader().setVisible(False)
		# self.linkTable.horizontalHeader().setVisible(False)

		# self.linkTable.itemClicked.connect(self.itemClickedHandler)

		# self.schedulerContainer = QtGui.QGroupBox(self.mainWidget)
		# self.schedulerContainer.setGeometry(QtCore.QRect(240, 250, 181, 71))
		# self.schedulerContainer.setTitle("Scheduler")

		# self.plainFont.setPointSize(10)

		# self.schedulerCheck = QtGui.QCheckBox(self.schedulerContainer)
		# self.schedulerCheck.setGeometry(QtCore.QRect(10, 20, 70, 17))
		# self.schedulerCheck.setFont(self.plainFont)
		# self.schedulerCheck.setText("Enable")

		# self.minLabel = QtGui.QLabel(self.schedulerContainer)
		# self.minLabel.setGeometry(QtCore.QRect(10, 40, 101, 21))
		# self.minLabel.setFont(self.plainFont)
		# self.minLabel.setText("Repeat (minutes)")

		# self.plainFont.setPointSize(9)

		# self.waitMinBox = QtGui.QDoubleSpinBox(self.schedulerContainer)
		# self.waitMinBox.setGeometry(QtCore.QRect(115, 40, 51, 22))
		# self.waitMinBox.setDecimals(1)
		# self.waitMinBox.setSingleStep(0.1)
		# self.waitMinBox.setFont(self.plainFont)

		# self.twitterNotifContainer = QtGui.QGroupBox(self.mainWidget)
		# self.twitterNotifContainer.setGeometry(QtCore.QRect(0, 250, 231, 71))
		# self.twitterNotifContainer.setTitle("Twitter Notification")

		# self.plainFont.setPointSize(10)

		# self.tinfoLabel = QtGui.QLabel(self.twitterNotifContainer)
		# self.tinfoLabel.setGeometry(QtCore.QRect(10, 39, 80, 21))
		# self.tinfoLabel.setFont(self.plainFont)
		# self.tinfoLabel.setText("Information - ")

		# self.tinfoEnterLabel = QtGui.QLabel(self.twitterNotifContainer)
		# self.tinfoEnterLabel.setGeometry(QtCore.QRect(90, 40, 141, 20))
		# self.tinfoEnterLabel.setFont(self.plainFont)

		# palette = QtGui.QPalette()
		# if self.pref.get('twInfoEntered'):
		# 	self.tinfoEnterLabel.setText("Entered")
		# 	palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.green)
		# 	self.tinfoEnterLabel.setPalette(palette)
		# else:
		# 	self.tinfoEnterLabel.setText("Not Entered")
		# 	palette.setColor(QtGui.QPalette.Foreground,QtCore.Qt.red)
		# 	self.tinfoEnterLabel.setPalette(palette)

		# self.twitterCheck = QtGui.QCheckBox(self.twitterNotifContainer)
		# self.twitterCheck.setGeometry(QtCore.QRect(10, 20, 70, 17))
		# self.twitterCheck.setFont(self.plainFont)
		# self.twitterCheck.setText("Enable")
		# self.twitterCheck.clicked.connect(self.checkboxChecked)

		# self.resetBtn = QtGui.QPushButton(self.mainWidget)        
		# self.resetBtn.setGeometry(QtCore.QRect(171, 332, 80, 25))
		# self.resetBtn.setFont(self.plainFont)
		# self.resetBtn.setText("Reset")
		# self.resetBtn.clicked.connect(self.programReset)

		# self.stopBtn = QtGui.QPushButton(self.mainWidget)        
		# self.stopBtn.setGeometry(QtCore.QRect(255, 332, 80, 25))
		# self.stopBtn.setStyleSheet("background-color: #F07F7F")
		# self.stopBtn.setFont(self.plainFont)
		# self.stopBtn.setText("Stop")
		# self.stopBtn.clicked.connect(self.programStop)

		# self.runBtn = QtGui.QPushButton(self.mainWidget)        
		# self.runBtn.setGeometry(QtCore.QRect(340, 332, 80, 25))
		# self.runBtn.setStyleSheet("background-color: #3BB370")
		# self.runBtn.setFont(self.plainFont)
		# self.runBtn.setText("Run")
		# self.runBtn.clicked.connect(self.programStart)

		# self.printBtn = QtGui.QPushButton(self.mainWidget)        
		# self.printBtn.setGeometry(QtCore.QRect(10, 330, 60, 30))
		# self.printBtn.setText("Save")
		# self.printBtn.clicked.connect(self.print_log)

		# self.plainFont.setPointSize(9)

		# self.logContainer = QtGui.QGroupBox(self.mainWidget)
		# self.logContainer.setGeometry(QtCore.QRect(0, 360, 421, 241))
		# self.logContainer.setFont(self.plainFont)
		# self.logContainer.setTitle("Log")

		# self.logBrowser = QtGui.QTextBrowser(self.logContainer)
		# self.logBrowser.setGeometry(QtCore.QRect(10, 20, 401, 211))
		# self.logBrowser.setLineWrapMode(QtGui.QTextEdit.NoWrap)

		# self.outputContainer = QtGui.QGroupBox(self.mainWidget)
		# self.outputContainer.setGeometry(QtCore.QRect(430, 0, 620, 601))
		# self.outputContainer.setTitle("Output")

		# self.outputTable = QtGui.QTableWidget(self.outputContainer)
		# self.outputTable.setGeometry(QtCore.QRect(10, 20, 600, 571))
		# self.outputTable.setMinimumSize(QtCore.QSize(491, 0))

		# self.outputTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
		# self.outputTable.setFrameShape(QtGui.QFrame.StyledPanel)
		# self.outputTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
		# self.outputTable.setGridStyle(QtCore.Qt.SolidLine)

		# self.outputTable.setShowGrid(False)
		# self.outputTable.setSortingEnabled(True)
		# self.outputTable.setWordWrap(True)
		# self.outputTable.setCornerButtonEnabled(False)

		# item = QtGui.QTableWidgetItem()
		# self.outputTable.setColumnCount(5)
		# self.outputTable.setColumnWidth(1, 130)
		# self.outputTable.setColumnWidth(2, 100)
		# self.outputTable.setColumnWidth(3, 20)
		# self.outputTable.setColumnWidth(4, 20)
		# self.outputTable.verticalHeader().setVisible(False)

		# item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

		# item = QtGui.QTableWidgetItem()
		# item.setText("Link")
		# self.outputTable.setHorizontalHeaderItem(0, item)

		# item = QtGui.QTableWidgetItem()
		# item.setText("Date")
		# self.outputTable.setHorizontalHeaderItem(1, item)

		# item = QtGui.QTableWidgetItem()
		# item.setText("Keyword")
		# self.outputTable.setHorizontalHeaderItem(2, item)

		# item = QtGui.QTableWidgetItem()
		# item.setText("")
		# self.outputTable.setHorizontalHeaderItem(3, item)

		# item = QtGui.QTableWidgetItem()
		# item.setText("")
		# self.outputTable.setHorizontalHeaderItem(4, item)

		# self.outputTable.horizontalHeader().setVisible(True)
		# self.outputTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

		# self.menubar = QtGui.QMenuBar(self.window)
		# self.menubar.setGeometry(QtCore.QRect(0, 0, 1018, 21))
		# self.window.setMenuBar(self.menubar)

		# self.menuProgram = QtGui.QMenu(self.menubar)
		# self.menuProgram.setTitle("Program")

		# self.menuSetting = QtGui.QMenu(self.menubar)
		# self.menuSetting.setTitle("Setting")

		# self.actionTwitter = QtGui.QAction(self.window)
		# self.actionTwitter.setText("Twitter")
		# self.actionTwitter.triggered.connect(self.twitterDialog)

		# self.actionDeactivate = QtGui.QAction(self.window)
		# self.actionDeactivate.setText("Deactivate")
		# self.actionDeactivate.triggered.connect(self.deactivate)

		# self.actionCheckout = QtGui.QAction(self.window)
		# self.actionCheckout.setText("Checkout")
		# self.actionCheckout.triggered.connect(self.checkoutDialog)

		# self.actionProxy = QtGui.QAction(self.window)
		# self.actionProxy.setText("Proxy")
		# self.actionProxy.triggered.connect(self.proxyDialog)

		# self.menuProgram.addAction(self.actionDeactivate)

		# self.menuSetting.addAction(self.actionTwitter)
		# self.menuSetting.addAction(self.actionCheckout)
		# self.menuSetting.addAction(self.actionProxy)

		# self.menubar.addAction(self.menuProgram.menuAction())
		# self.menubar.addAction(self.menuSetting.menuAction())

	def monitorTabGUI(self):
		self.monitorTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\clipboard_click.png')).scaledToWidth(80))

		if self.currentTab != "Monitor":
			self.changeTab()
			self.currentTab = "Monitor"

			if self.monitorTabRender == False:
				self.monitorTabRender = True

				self.monitorTabWidget = QtGui.QWidget(self.mainWidget)
				self.monitorTabWidget.setGeometry(QtCore.QRect(0, 105, 800, 470))

				self.monitorTable = QtGui.QTableWidget(self.monitorTabWidget)
				self.monitorTable.setGeometry(QtCore.QRect(20, 10, 760, 400))

				self.monitorTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
				self.monitorTable.setFrameShape(QtGui.QFrame.StyledPanel)
				self.monitorTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
				self.monitorTable.setGridStyle(QtCore.Qt.SolidLine)

				self.monitorTable.setShowGrid(False)
				self.monitorTable.setSortingEnabled(True)
				self.monitorTable.setWordWrap(True)
				self.monitorTable.setCornerButtonEnabled(False)

				item = QtGui.QTableWidgetItem()
				self.monitorTable.setColumnCount(6)
				self.monitorTable.setColumnWidth(0, 20)
				self.monitorTable.setColumnWidth(1, 120)
				self.monitorTable.setColumnWidth(2, 200)
				self.monitorTable.setColumnWidth(3, 60)
				self.monitorTable.setColumnWidth(5, 80)
				self.monitorTable.verticalHeader().setVisible(False)

				item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

				item = QtGui.QTableWidgetItem()
				item.setText("")
				self.monitorTable.setHorizontalHeaderItem(0, item)

				item = QtGui.QTableWidgetItem()
				item.setText("Store")
				self.monitorTable.setHorizontalHeaderItem(1, item)
		 
				item = QtGui.QTableWidgetItem()
				item.setText("Item")
				self.monitorTable.setHorizontalHeaderItem(2, item)

				item = QtGui.QTableWidgetItem()
				item.setText("Size")
				self.monitorTable.setHorizontalHeaderItem(3, item)

				item = QtGui.QTableWidgetItem()
				item.setText("Profile")
				self.monitorTable.setHorizontalHeaderItem(4, item)

				item = QtGui.QTableWidgetItem()
				item.setText("Status")
				self.monitorTable.setHorizontalHeaderItem(5, item)

				self.monitorTable.horizontalHeader().setVisible(True)
				self.monitorTable.horizontalHeader().setResizeMode(5, QtGui.QHeaderView.Stretch)

				colour = False

				for i in range(15):
					rowPosition = self.monitorTable.rowCount()
					self.monitorTable.insertRow(rowPosition)
					self.monitorTable.setRowHeight(rowPosition, 25)
					
					for j in range(6):
						if i < len(self.tasks) and self.tasks != None:
							if j == 0:
								chkBoxItem = QtGui.QTableWidgetItem()
								chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
								chkBoxItem.setCheckState(QtCore.Qt.Unchecked)       
								self.monitorTable.setItem(rowPosition,j,chkBoxItem)
							else:
								if j == 1:
									info = self.tasks[i]['store_name']
								elif j == 2:
									info = self.tasks[i]['item_name']
								elif j == 3:
									info = self.tasks[i]['size']
								elif j == 4:
									info = self.tasks[i]['billing_profile']
								elif j == 5:
									info = 'Not Started'

								self.monitorTable.setItem(rowPosition, j, QtGui.QTableWidgetItem(info))
						else:
							self.monitorTable.setItem(rowPosition, j, QtGui.QTableWidgetItem())
						
						self.monitorTable.item(rowPosition, j).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

						if colour:
							self.monitorTable.item(rowPosition, j).setBackground(QtGui.QColor(0,130,15,50))

					if colour:
						colour = False
					else:
						colour = True

				self.monitorTable.itemClicked.connect(self.itemClickedHandler)

				self.startTaskLabel = QtGui.QLabel(self.monitorTabWidget)
				self.startTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfsdf.png')).scaledToWidth(30))
				self.startTaskLabel.setGeometry(QtCore.QRect(30, 420, 30, 30))
				self.startTaskLabel.mousePressEvent = lambda event:self.monitorStart()

				self.startTextLabel = QtGui.QLabel(self.monitorTabWidget)
				self.startTextLabel.setGeometry(QtCore.QRect(70, 425, 70, 20))
				self.startTextLabel.setFont(self.font)
				self.startTextLabel.setText("Start")
				self.startTaskLabel.mousePressEvent = lambda event:self.monitorStart()

				self.stopTaskLabel = QtGui.QLabel(self.monitorTabWidget)
				self.stopTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\stop.png')).scaledToWidth(30))
				self.stopTaskLabel.setGeometry(QtCore.QRect(130, 420, 30, 30))

				self.stopTextLabel = QtGui.QLabel(self.monitorTabWidget)
				self.stopTextLabel.setGeometry(QtCore.QRect(170, 425, 70, 20))
				self.stopTextLabel.setFont(self.font)
				self.stopTextLabel.setText("Stop")

				self.delTaskLabel = QtGui.QLabel(self.monitorTabWidget)
				self.delTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfsd-dfg.png')).scaledToWidth(30))
				self.delTaskLabel.setGeometry(QtCore.QRect(230, 420, 30, 30))

				self.delTextLabel = QtGui.QLabel(self.monitorTabWidget)
				self.delTextLabel.setGeometry(QtCore.QRect(270, 425, 70, 20))
				self.delTextLabel.setFont(self.font)
				self.delTextLabel.setText("Delete")
			else:
				if self.taskEdited:
					self.taskEdited = False
					for i in range(len(self.tasks)):
						for j in range(5):
							if j == 0:
								chkBoxItem = QtGui.QTableWidgetItem()
								chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
								chkBoxItem.setCheckState(QtCore.Qt.Unchecked)       
								self.monitorTable.setItem(i,j,chkBoxItem)
							else:
								if j == 1:
									info = self.tasks[i]['store_name']
								elif j == 2:
									info = self.tasks[i]['item_name']
								elif j == 3:
									info = self.tasks[i]['size']
								elif j == 4:
									info = self.tasks[i]['billing_profile']

								self.monitorTable.item(i, j).setText(info)

			self.monitorTabWidget.show()

	def taskTabGUI(self):
		self.taskTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Tools-PNG-Image_click.png')).scaledToWidth(80))

		if self.currentTab != "Add Task":
			self.changeTab()
			self.currentTab = "Add Task"

			if self.taskTabRender == False:
				self.taskTabRender = True

				self.taskTabWidget = QtGui.QWidget(self.mainWidget)
				self.taskTabWidget.setGeometry(QtCore.QRect(0, 105, 800, 470))

				self.taskOneTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskOneTextLabel.setGeometry(QtCore.QRect(175, 15, 100, 20))
				self.taskOneTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskOneTextLabel.setText("1. Task Name")

				self.taskNameInput = QtGui.QLineEdit(self.taskTabWidget)
				self.taskNameInput.setGeometry(QtCore.QRect(130, 35, 180, 25))

				self.taskTwoTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskTwoTextLabel.setGeometry(QtCore.QRect(160, 75, 120, 20))
				self.taskTwoTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskTwoTextLabel.setText("2. Select A Store")

				self.taskStoreSelect = QtGui.QComboBox(self.taskTabWidget)
				self.taskStoreSelect.setGeometry(QtCore.QRect(130, 95, 180, 25))
				self.taskStoreSelect.setEditable(True)
				self.taskStoreSelect.lineEdit().setReadOnly(True)
				self.taskStoreSelect.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
				self.taskStoreSelect.addItems(["Kith NYC"])

				for i in range(self.taskStoreSelect.count()):
					self.taskStoreSelect.setItemData(i, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

				self.taskThreeTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskThreeTextLabel.setGeometry(QtCore.QRect(150, 135, 140, 20))
				self.taskThreeTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskThreeTextLabel.setText("3. Enter Item Name")

				self.taskItemNameInput = QtGui.QLineEdit(self.taskTabWidget)
				self.taskItemNameInput.setGeometry(QtCore.QRect(130, 155, 180, 25))

				self.taskFourTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskFourTextLabel.setGeometry(QtCore.QRect(170, 195, 120, 20))
				self.taskFourTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskFourTextLabel.setText("4. Select Size")

				self.taskSizeSelect = QtGui.QComboBox(self.taskTabWidget)
				self.taskSizeSelect.setGeometry(QtCore.QRect(185, 215, 60, 25))
				self.taskSizeSelect.setEditable(True)
				self.taskSizeSelect.lineEdit().setReadOnly(True)
				self.taskSizeSelect.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
				self.taskSizeSelect.addItems(self.pref.get('shoe_size'))

				for i in range(self.taskSizeSelect.count()):
					self.taskSizeSelect.setItemData(i, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

				self.taskFiveTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskFiveTextLabel.setGeometry(QtCore.QRect(135, 255, 180, 20))
				self.taskFiveTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskFiveTextLabel.setText("5. Select A Billing Profile")

				self.taskBillSelect = QtGui.QComboBox(self.taskTabWidget)
				self.taskBillSelect.setGeometry(QtCore.QRect(130, 275, 180, 25))
				self.taskBillSelect.setEditable(True)
				self.taskBillSelect.lineEdit().setReadOnly(True)
				self.taskBillSelect.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
				self.taskBillSelect.addItems(["Profile 1", "Profile 2"])

				for i in range(self.taskBillSelect.count()):
					self.taskBillSelect.setItemData(i, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

				self.taskSixTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskSixTextLabel.setGeometry(QtCore.QRect(130, 315, 180, 20))
				self.taskSixTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskSixTextLabel.setText("6. Pick A Proxy (Optional)")

				self.taskProxySelect = QtGui.QComboBox(self.taskTabWidget)
				self.taskProxySelect.setGeometry(QtCore.QRect(130, 335, 180, 25))
				self.taskProxySelect.setEditable(True)
				self.taskProxySelect.lineEdit().setReadOnly(True)
				self.taskProxySelect.lineEdit().setAlignment(QtCore.Qt.AlignCenter)
				self.taskProxySelect.addItems(["122.23.41.2", "23.412.491.2"])

				for i in range(self.taskProxySelect.count()):
					self.taskProxySelect.setItemData(i, QtCore.Qt.AlignCenter, QtCore.Qt.TextAlignmentRole)

				self.taskSevenTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.taskSevenTextLabel.setGeometry(QtCore.QRect(105, 375, 230, 20))
				self.taskSevenTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.taskSevenTextLabel.setText("7. Turn on notification (Optional)")

				self.notifCheckbox = QtGui.QCheckBox("Yes", self.taskTabWidget)
				self.notifCheckbox.setGeometry(QtCore.QRect(190, 395, 50, 20))

				self.doneTaskLabel = QtGui.QLabel(self.taskTabWidget)
				self.doneTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\check.png')).scaledToWidth(30))
				self.doneTaskLabel.setGeometry(QtCore.QRect(170, 425, 30, 30))
				self.doneTaskLabel.mousePressEvent = lambda event:self.taskSave()

				self.doneTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.doneTextLabel.setGeometry(QtCore.QRect(205, 430, 70, 20))
				self.doneTextLabel.setFont(self.font)
				self.doneTextLabel.setText("Done")
				self.doneTextLabel.mousePressEvent = lambda event:self.taskSave()

				self.taskTabVerticalDivider = QtGui.QFrame(self.taskTabWidget)
				self.taskTabVerticalDivider.setGeometry(QtCore.QRect(380, 20, 20, 420))
				self.taskTabVerticalDivider.setFrameShape(QtGui.QFrame.VLine)
				self.taskTabVerticalDivider.setFrameShadow(QtGui.QFrame.Sunken)

				self.taskTable = QtGui.QTableWidget(self.taskTabWidget)
				self.taskTable.setGeometry(QtCore.QRect(470, 35, 250, 375))

				self.taskTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
				self.taskTable.setFrameShape(QtGui.QFrame.StyledPanel)
				self.taskTable.setGridStyle(QtCore.Qt.SolidLine)

				self.taskTable.setShowGrid(False)
				self.taskTable.setSortingEnabled(True)
				self.taskTable.setWordWrap(True)
				self.taskTable.setCornerButtonEnabled(False)

				item = QtGui.QTableWidgetItem()
				self.taskTable.setColumnCount(1)
				self.taskTable.verticalHeader().setVisible(False)

				item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

				item = QtGui.QTableWidgetItem()
				item.setFont(QtGui.QFont("Calibri", 10, 65))
				item.setText("Task Name")
				self.taskTable.setHorizontalHeaderItem(0, item)

				self.taskTable.horizontalHeader().setVisible(True)
				self.taskTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

				colour = False

				for i in range(14):
					rowPosition = self.taskTable.rowCount()
					self.taskTable.insertRow(rowPosition)
					self.taskTable.setRowHeight(rowPosition, 25)

					if i < len(self.tasks):
						self.taskTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem(self.tasks[i]['task_name']))
					else:
						self.taskTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem())

					self.taskTable.item(rowPosition, 0).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

					if colour:
						self.taskTable.item(rowPosition, 0).setBackground(QtGui.QColor(0,130,15,50))

					if colour:
						colour = False
					else:
						colour = True

				self.editTaskLabel = QtGui.QLabel(self.taskTabWidget)
				self.editTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\edit-editor-pen-pencil-write-icon--4.png')).scaledToWidth(30))
				self.editTaskLabel.setGeometry(QtCore.QRect(555, 425, 30, 30))
				self.editTaskLabel.mousePressEvent = lambda event:self.editTask()

				self.editTaskTextLabel = QtGui.QLabel(self.taskTabWidget)
				self.editTaskTextLabel.setGeometry(QtCore.QRect(595, 430, 70, 20))
				self.editTaskTextLabel.setFont(self.font)
				self.editTaskTextLabel.setText("Edit")
				self.editTaskTextLabel.mousePressEvent = lambda event:self.editTask()
			elif self.taskEdited:
				for i in range(len(self.tasks)):
					self.taskTable.item(i,0).setText(self.tasks[i]['task_name'])

			self.taskTabWidget.show()

	def cardTabGUI(self):
		self.cardTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\credit-card-1_click.png')).scaledToWidth(75))

		if self.currentTab != "Card":
			self.changeTab()
			self.currentTab = "Card"

			if self.cardTabRender == False:
				font = QtGui.QFont("Calibri", 10, 65)

				self.cardTabRender = True
				self.currentCardPage = "One"

				self.cardTabWidget = QtGui.QWidget(self.mainWidget)
				self.cardTabWidget.setGeometry(QtCore.QRect(0, 105, 800, 470))

				self.cardStepOneWidget = QtGui.QWidget(self.cardTabWidget)
				self.cardStepOneWidget.setGeometry(QtCore.QRect(0, 0, 450, 470))

				self.cardOneTextLabel = QtGui.QLabel(self.cardStepOneWidget)
				self.cardOneTextLabel.setGeometry(QtCore.QRect(50, 15, 200, 20))
				self.cardOneTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.cardOneTextLabel.setText("1. Billing Profile Name")

				self.cardNameInput = QtGui.QLineEdit(self.cardStepOneWidget)
				self.cardNameInput.setGeometry(QtCore.QRect(50, 40, 180, 25))

				self.cardTwoTextLabel = QtGui.QLabel(self.cardStepOneWidget)
				self.cardTwoTextLabel.setGeometry(QtCore.QRect(50, 75, 150, 20))
				self.cardTwoTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.cardTwoTextLabel.setText("2. Shipping Detail")

				self.emailEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.emailEdit.setGeometry(QtCore.QRect(50, 100, 350, 25))
				self.emailEdit.setFont(font)
				self.emailEdit.setText("Email Address")

				self.fNameEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.fNameEdit.setGeometry(QtCore.QRect(50, 140, 165, 25))
				self.fNameEdit.setFont(font)
				self.fNameEdit.setText("First Name")

				self.lNameEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.lNameEdit.setGeometry(QtCore.QRect(235, 140, 165, 25))
				self.lNameEdit.setFont(font)
				self.lNameEdit.setText("Last Name")

				self.companyEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.companyEdit.setGeometry(QtCore.QRect(50, 180, 230, 25))
				self.companyEdit.setFont(font)
				self.companyEdit.setText("Company (Optional)")

				self.aptEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.aptEdit.setGeometry(QtCore.QRect(300, 180, 100, 25))
				self.aptEdit.setFont(font)
				self.aptEdit.setText("Apt (Optional)")

				self.addEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.addEdit.setGeometry(QtCore.QRect(50, 220, 350, 25))
				self.addEdit.setFont(font)
				self.addEdit.setText("Address")

				self.countryEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.countryEdit.setGeometry(QtCore.QRect(50, 260, 165, 25))
				self.countryEdit.setFont(font)
				self.countryEdit.setText("Country")		

				self.cityEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.cityEdit.setGeometry(QtCore.QRect(235, 260, 165, 25))
				self.cityEdit.setFont(font)
				self.cityEdit.setText("City")				

				self.stateEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.stateEdit.setGeometry(QtCore.QRect(50, 300, 165, 25))
				self.stateEdit.setFont(font)
				self.stateEdit.setText("State")

				self.pCodeEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.pCodeEdit.setGeometry(QtCore.QRect(235, 300, 165, 25))
				self.pCodeEdit.setFont(font)
				self.pCodeEdit.setText("Postcode")

				self.phoneEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.phoneEdit.setGeometry(QtCore.QRect(50, 340, 350, 25))
				self.phoneEdit.setFont(font)
				self.phoneEdit.setText("Phone")

				self.discountEdit = QtGui.QLineEdit(self.cardStepOneWidget)
				self.discountEdit.setGeometry(QtCore.QRect(50, 380, 350, 25))
				self.discountEdit.setFont(font)
				self.discountEdit.setText("Gift Card or Discount Code (Optional)")

				self.nextTaskLabel = QtGui.QLabel(self.cardStepOneWidget)
				self.nextTaskLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfdfg-jksdfjk.png')).scaledToWidth(30))
				self.nextTaskLabel.setGeometry(QtCore.QRect(180, 425, 30, 30))
				self.nextTaskLabel.mousePressEvent = lambda event:self.changeCardTabGUIPage()

				self.nextTextLabel = QtGui.QLabel(self.cardStepOneWidget)
				self.nextTextLabel.setGeometry(QtCore.QRect(220, 430, 70, 20))
				self.nextTextLabel.setFont(self.font)
				self.nextTextLabel.setText("Next")
				self.nextTextLabel.mousePressEvent = lambda event:self.changeCardTabGUIPage()

				self.cardStepTwoWidget = QtGui.QWidget(self.cardTabWidget)
				self.cardStepTwoWidget.setGeometry(QtCore.QRect(0, 0, 450, 470))

				self.cardThreeTextLabel = QtGui.QLabel(self.cardStepTwoWidget)
				self.cardThreeTextLabel.setGeometry(QtCore.QRect(50, 15, 240, 20))
				self.cardThreeTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.cardThreeTextLabel.setText("3. Billing Detail (Not Functional)")

				self.fNameBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.fNameBillingEdit.setGeometry(QtCore.QRect(50, 40, 165, 25))
				self.fNameBillingEdit.setFont(font)
				self.fNameBillingEdit.setText("First Name")

				self.lNameBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.lNameBillingEdit.setGeometry(QtCore.QRect(235, 40, 165, 25))
				self.lNameBillingEdit.setFont(font)
				self.lNameBillingEdit.setText("Last Name")

				self.aptBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.aptBillingEdit.setGeometry(QtCore.QRect(300, 80, 100, 25))
				self.aptBillingEdit.setFont(font)
				self.aptBillingEdit.setText("Apt (Optional)")

				self.addBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.addBillingEdit.setGeometry(QtCore.QRect(50, 80, 230, 25))
				self.addBillingEdit.setFont(font)
				self.addBillingEdit.setText("Address")

				self.addBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.addBillingEdit.setGeometry(QtCore.QRect(50, 120, 165, 25))
				self.addBillingEdit.setFont(font)
				self.addBillingEdit.setText("Country")		

				self.cityBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.cityBillingEdit.setGeometry(QtCore.QRect(235, 120, 165, 25))
				self.cityBillingEdit.setFont(font)
				self.cityBillingEdit.setText("City")				

				self.stateBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.stateBillingEdit.setGeometry(QtCore.QRect(50, 160, 165, 25))
				self.stateBillingEdit.setFont(font)
				self.stateBillingEdit.setText("State")

				self.pCodeBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.pCodeBillingEdit.setGeometry(QtCore.QRect(235, 160, 165, 25))
				self.pCodeBillingEdit.setFont(font)
				self.pCodeBillingEdit.setText("Postcode")

				self.phoneBillingEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.phoneBillingEdit.setGeometry(QtCore.QRect(50, 200, 350, 25))
				self.phoneBillingEdit.setFont(font)
				self.phoneBillingEdit.setText("Phone")

				self.sameAddrCheckbox = QtGui.QCheckBox("Same as shipping", self.cardStepTwoWidget)
				self.sameAddrCheckbox.setGeometry(QtCore.QRect(50, 240, 150, 25))
				self.sameAddrCheckbox.setFont(font)

				self.cardFourTextLabel = QtGui.QLabel(self.cardStepTwoWidget)
				self.cardFourTextLabel.setGeometry(QtCore.QRect(50, 275, 150, 20))
				self.cardFourTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.cardFourTextLabel.setText("4. Credit Card Detail")

				self.ccNumberEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.ccNumberEdit.setGeometry(QtCore.QRect(50, 300, 350, 25))
				self.ccNumberEdit.setFont(font)
				self.ccNumberEdit.setText("Card Number")

				self.ccNameEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.ccNameEdit.setGeometry(QtCore.QRect(50, 340, 230, 25))
				self.ccNameEdit.setFont(font)
				self.ccNameEdit.setText("Name On Card")

				self.ccExpiryEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.ccExpiryEdit.setGeometry(QtCore.QRect(300, 340, 100, 25))
				self.ccExpiryEdit.setFont(font)
				self.ccExpiryEdit.setText("MM/YYYY")

				self.ccSecurityEdit = QtGui.QLineEdit(self.cardStepTwoWidget)
				self.ccSecurityEdit.setGeometry(QtCore.QRect(50, 380, 81, 25))
				self.ccSecurityEdit.setFont(font)
				self.ccSecurityEdit.setText("CVV")

				self.doneCardLabel = QtGui.QLabel(self.cardStepTwoWidget)
				self.doneCardLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\check.png')).scaledToWidth(30))
				self.doneCardLabel.setGeometry(QtCore.QRect(180, 425, 30, 30))
				self.doneCardLabel.mousePressEvent = lambda event:self.saveBillProfile()

				self.doneCardTextLabel = QtGui.QLabel(self.cardStepTwoWidget)
				self.doneCardTextLabel.setGeometry(QtCore.QRect(220, 430, 70, 20))
				self.doneCardTextLabel.setFont(self.font)
				self.doneCardTextLabel.setText("Done")
				self.doneCardTextLabel.mousePressEvent = lambda event:self.saveBillProfile()

				self.cardTabVerticalDivider = QtGui.QFrame(self.cardTabWidget)
				self.cardTabVerticalDivider.setGeometry(QtCore.QRect(455, 20, 20, 420))
				self.cardTabVerticalDivider.setFrameShape(QtGui.QFrame.VLine)
				self.cardTabVerticalDivider.setFrameShadow(QtGui.QFrame.Sunken)

				self.billingProfileTable = QtGui.QTableWidget(self.cardTabWidget)
				self.billingProfileTable.setGeometry(QtCore.QRect(530, 35, 180, 375))

				self.billingProfileTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
				self.billingProfileTable.setFrameShape(QtGui.QFrame.StyledPanel)
				self.billingProfileTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
				self.billingProfileTable.setGridStyle(QtCore.Qt.SolidLine)

				self.billingProfileTable.setShowGrid(False)
				self.billingProfileTable.setSortingEnabled(True)
				self.billingProfileTable.setWordWrap(True)
				self.billingProfileTable.setCornerButtonEnabled(False)

				item = QtGui.QTableWidgetItem()
				self.billingProfileTable.setColumnCount(1)
				self.billingProfileTable.verticalHeader().setVisible(False)

				item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

				item = QtGui.QTableWidgetItem()
				item.setFont(QtGui.QFont("Calibri", 10, 65))
				item.setText("Billing Profile Name")
				self.billingProfileTable.setHorizontalHeaderItem(0, item)

				self.billingProfileTable.horizontalHeader().setVisible(True)
				self.billingProfileTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

				colour = False

				bill_profile_name = self.bill_profile.keys()

				for i in range(14):
					rowPosition = self.billingProfileTable.rowCount()
					self.billingProfileTable.insertRow(rowPosition)
					self.billingProfileTable.setRowHeight(rowPosition, 25)

					if i < len(bill_profile_name):
						self.billingProfileTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem(bill_profile_name[i]))
					else:
						self.billingProfileTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem())

					self.billingProfileTable.item(rowPosition, 0).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

					if colour:
						self.billingProfileTable.item(rowPosition, 0).setBackground(QtGui.QColor(0,130,15,50))

					if colour:
						colour = False
					else:
						colour = True

				self.editProfileLabel = QtGui.QLabel(self.cardTabWidget)
				self.editProfileLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\edit-editor-pen-pencil-write-icon--4.png')).scaledToWidth(30))
				self.editProfileLabel.setGeometry(QtCore.QRect(580, 425, 30, 30))

				self.editProfileTextLabel = QtGui.QLabel(self.cardTabWidget)
				self.editProfileTextLabel.setGeometry(QtCore.QRect(620, 430, 70, 20))
				self.editProfileTextLabel.setFont(self.font)
				self.editProfileTextLabel.setText("Edit")

				self.cardStepTwoWidget.hide()

			self.cardTabWidget.show()

	def scrapeTabGUI(self):
		self.scrapeTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\dsfsdf-dsf_click.png')).scaledToWidth(80))

		if self.currentTab != "Scrape":
			self.changeTab()
			self.currentTab = "Scrape"

			if self.scrapeTabRender == False:
				font = QtGui.QFont("Calibri", 10, 65)

				self.scrapeTabRender = True
				self.currentStorePage = "One"

				self.scrapeInfoTabWidget = QtGui.QWidget(self.mainWidget)
				self.scrapeInfoTabWidget.setGeometry(QtCore.QRect(0, 105, 800, 470))

				self.scrapeOneTextLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.scrapeOneTextLabel.setGeometry(QtCore.QRect(30, 15, 200, 20))
				self.scrapeOneTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.scrapeOneTextLabel.setText("1. Select Stores")

				self.scrapePageOneWidget = QtGui.QWidget(self.scrapeInfoTabWidget)
				self.scrapePageOneWidget.setGeometry(QtCore.QRect(0, 20, 470, 450))

				self.shopOneLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopOneLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\Oneness287.png')).scaledToWidth(100))
				self.shopOneLabel.setGeometry(QtCore.QRect(30, 20, 100, 50))

				self.shopOneCheckbox = QtGui.QCheckBox("Oneness287", self.scrapePageOneWidget)
				self.shopOneCheckbox.setGeometry(QtCore.QRect(40, 70, 150, 25))
				self.shopOneCheckbox.setFont(font)

				self.shopTwoLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopTwoLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfsdf-kasd.png')).scaledToWidth(100))
				self.shopTwoLabel.setGeometry(QtCore.QRect(160, 30, 100, 25))

				self.shopTwoCheckbox = QtGui.QCheckBox("Notre-Shop", self.scrapePageOneWidget)
				self.shopTwoCheckbox.setGeometry(QtCore.QRect(170, 70, 150, 25))
				self.shopTwoCheckbox.setFont(font)

				self.shopThreeLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopThreeLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\PHARiTjo.png')).scaledToWidth(100))
				self.shopThreeLabel.setGeometry(QtCore.QRect(280, 20, 100, 50))

				self.shopThreeCheckbox = QtGui.QCheckBox("Bdgastore", self.scrapePageOneWidget)
				self.shopThreeCheckbox.setGeometry(QtCore.QRect(290, 70, 150, 25))
				self.shopThreeCheckbox.setFont(font)

				self.shopFourLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopFourLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfDASJ.png')).scaledToWidth(75))
				self.shopFourLabel.setGeometry(QtCore.QRect(390, 10, 100, 60))

				self.shopFourCheckbox = QtGui.QCheckBox("Rise45", self.scrapePageOneWidget)
				self.shopFourCheckbox.setGeometry(QtCore.QRect(400, 70, 100, 25))
				self.shopFourCheckbox.setFont(font)

				self.shopFiveLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopFiveLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\skfgjk-ery.png')).scaledToWidth(75))
				self.shopFiveLabel.setGeometry(QtCore.QRect(30, 95, 75, 75))

				self.shopFiveCheckbox = QtGui.QCheckBox("Octobersveryown", self.scrapePageOneWidget)
				self.shopFiveCheckbox.setGeometry(QtCore.QRect(10, 165, 120, 25))
				self.shopFiveCheckbox.setFont(QtGui.QFont("Calibri", 9, 65))

				self.shopSixLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopSixLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\p9LTUFig.png')).scaledToWidth(75))
				self.shopSixLabel.setGeometry(QtCore.QRect(120, 95, 75, 75))

				self.shopSixCheckbox = QtGui.QCheckBox("Cncpts", self.scrapePageOneWidget)
				self.shopSixCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(130, 165, 80, 25)))
				self.shopSixCheckbox.setFont(font)

				self.shopSevenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopSevenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sneajekf-policD.png')).scaledToWidth(60))
				self.shopSevenLabel.setGeometry(QtCore.QRect(215, 100, 60, 60))

				self.shopSevenCheckbox = QtGui.QCheckBox("Sneakerpolitics", self.scrapePageOneWidget)
				self.shopSevenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(195, 165, 120, 25)))
				self.shopSevenCheckbox.setFont(font)	

				self.shopEightLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopEightLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\8BFLZiVA.png')).scaledToWidth(60))
				self.shopEightLabel.setGeometry(QtCore.QRect(310, 100, 60, 60))

				self.shopEightCheckbox = QtGui.QCheckBox("Rockcitykicks", self.scrapePageOneWidget)
				self.shopEightCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(300, 165, 120, 25)))
				self.shopEightCheckbox.setFont(font)

				self.shopNineLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopNineLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdf-hsdh8.png')).scaledToWidth(60))
				self.shopNineLabel.setGeometry(QtCore.QRect(400, 95, 60, 70))

				self.shopNineCheckbox = QtGui.QCheckBox("Xhibition", self.scrapePageOneWidget)
				self.shopNineCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(400, 165, 120, 25)))
				self.shopNineCheckbox.setFont(font)

				self.shopTenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopTenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\shopnkicksef.png')).scaledToWidth(150))
				self.shopTenLabel.setGeometry(QtCore.QRect(30, 190, 150, 50))

				self.shopTenCheckbox = QtGui.QCheckBox("Shopnicekicks", self.scrapePageOneWidget)
				self.shopTenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(60, 230, 120, 25)))
				self.shopTenCheckbox.setFont(font)

				self.shopElevenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopElevenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\deadmeanthb.png')).scaledToWidth(150))
				self.shopElevenLabel.setGeometry(QtCore.QRect(195, 200, 150, 30))

				self.shopElevenCheckbox = QtGui.QCheckBox("Deadstock", self.scrapePageOneWidget)
				self.shopElevenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(230, 230, 120, 25)))
				self.shopElevenCheckbox.setFont(font)

				self.shopTwelveLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopTwelveLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\ghsd.png')).scaledToWidth(100))
				self.shopTwelveLabel.setGeometry(QtCore.QRect(360, 205, 100, 25))

				self.shopTwelveCheckbox = QtGui.QCheckBox("Exclucitylife", self.scrapePageOneWidget)
				self.shopTwelveCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(370, 230, 120, 25)))
				self.shopTwelveCheckbox.setFont(font)

				self.shopThirteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopThirteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\kithasd.png')).scaledToWidth(100))
				self.shopThirteenLabel.setGeometry(QtCore.QRect(20, 260, 100, 45))

				self.shopThirteenCheckbox = QtGui.QCheckBox("Kith NYC", self.scrapePageOneWidget)
				self.shopThirteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(30, 305, 80, 25)))
				self.shopThirteenCheckbox.setFont(font)

				self.shopFourteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopFourteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\extrabutterny_myshopify_com_logo.png')).scaledToWidth(80))
				self.shopFourteenLabel.setGeometry(QtCore.QRect(140, 260, 80, 50))

				self.shopFourteenCheckbox = QtGui.QCheckBox("Extrabutterny", self.scrapePageOneWidget)
				self.shopFourteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(130, 305, 100, 25)))
				self.shopFourteenCheckbox.setFont(font)

				self.shopFifteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopFifteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\pcshoes.png')).scaledToWidth(150))
				self.shopFifteenLabel.setGeometry(QtCore.QRect(230, 260, 150, 40))

				self.shopFifteenCheckbox = QtGui.QCheckBox("Packershoes", self.scrapePageOneWidget)
				self.shopFifteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(260, 305, 100, 25)))
				self.shopFifteenCheckbox.setFont(font)

				self.shopSixteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopSixteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfbn-vhsdhf.png')).scaledToWidth(80))
				self.shopSixteenLabel.setGeometry(QtCore.QRect(390, 260, 80, 40))

				self.shopSixteenCheckbox = QtGui.QCheckBox("Beatniconline", self.scrapePageOneWidget)
				self.shopSixteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(370, 305, 100, 25)))
				self.shopSixteenCheckbox.setFont(font)

				self.shopSeventeenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopSeventeenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfsedgherrgg.png')).scaledToWidth(100))
				self.shopSeventeenLabel.setGeometry(QtCore.QRect(20, 330, 100, 60))

				self.shopSeventeenCheckbox = QtGui.QCheckBox("Nojokicks", self.scrapePageOneWidget)
				self.shopSeventeenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(30, 390, 100, 25)))
				self.shopSeventeenCheckbox.setFont(font)

				self.shopEighteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopEighteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\crtdsjd.png')).scaledToWidth(150))
				self.shopEighteenLabel.setGeometry(QtCore.QRect(140, 340, 150, 40))

				self.shopEighteenCheckbox = QtGui.QCheckBox("Courtsidesneakers", self.scrapePageOneWidget)
				self.shopEighteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(150, 380, 120, 25)))
				self.shopEighteenCheckbox.setFont(font)

				self.shopNineteenLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.shopNineteenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdggher.png')).scaledToWidth(150))
				self.shopNineteenLabel.setGeometry(QtCore.QRect(310, 340, 150, 30))

				self.shopNineteenCheckbox = QtGui.QCheckBox("Bowsandarrowsberkeley", self.scrapePageOneWidget)
				self.shopNineteenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(305, 380, 160, 25)))
				self.shopNineteenCheckbox.setFont(font)

				self.moreScrapeStoreLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.moreScrapeStoreLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfdfg-jksdfjk.png')).scaledToWidth(30))
				self.moreScrapeStoreLabel.setGeometry(QtCore.QRect(160, 410, 30, 30))
				self.moreScrapeStoreLabel.mousePressEvent = lambda event:self.changeScrapeTabGUIPage()

				self.moreScrapeStoreTextLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.moreScrapeStoreTextLabel.setGeometry(QtCore.QRect(200, 415, 70, 20))
				self.moreScrapeStoreTextLabel.setFont(self.font)
				self.moreScrapeStoreTextLabel.setText("More")
				self.moreScrapeStoreTextLabel.mousePressEvent = lambda event:self.changeScrapeTabGUIPage()

				self.addShopLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.addShopLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfasd.png')).scaledToWidth(30))
				self.addShopLabel.setGeometry(QtCore.QRect(260, 410, 30, 30))

				self.addShopTextLabel = QtGui.QLabel(self.scrapePageOneWidget)
				self.addShopTextLabel.setGeometry(QtCore.QRect(300, 415, 70, 20))
				self.addShopTextLabel.setFont(self.font)
				self.addShopTextLabel.setText("Add")

				self.scrapePageTwoWidget = QtGui.QWidget(self.scrapeInfoTabWidget)
				self.scrapePageTwoWidget.setGeometry(QtCore.QRect(0, 20, 470, 450))

				self.shopTwentyLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\zfncl0xC.png')).scaledToWidth(80))
				self.shopTwentyLabel.setGeometry(QtCore.QRect(30, 10, 80, 80))

				self.shopTwentyCheckbox = QtGui.QCheckBox("Lapstoneandhammer", self.scrapePageTwoWidget)
				self.shopTwentyCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(10, 90, 140, 25)))
				self.shopTwentyCheckbox.setFont(QtGui.QFont("Calibri", 9, 65))

				self.shopTwentyOneLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyOneLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\kdf.png')).scaledToWidth(80))
				self.shopTwentyOneLabel.setGeometry(QtCore.QRect(140, 10, 80, 80))

				self.shopTwentyOneCheckbox = QtGui.QCheckBox("Cityblueshop", self.scrapePageTwoWidget)
				self.shopTwentyOneCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(140, 90, 100, 25)))
				self.shopTwentyOneCheckbox.setFont(font)

				self.shopTwentyTwoLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyTwoLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\Bape.png')).scaledToWidth(80))
				self.shopTwentyTwoLabel.setGeometry(QtCore.QRect(230, 10, 80, 80))

				self.shopTwentyTwoCheckbox = QtGui.QCheckBox("Bape", self.scrapePageTwoWidget)
				self.shopTwentyTwoCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(245, 90, 100, 25)))
				self.shopTwentyTwoCheckbox.setFont(font)

				self.shopTwentyThreeLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyThreeLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\Fb7lhS8R.png')).scaledToWidth(80))
				self.shopTwentyThreeLabel.setGeometry(QtCore.QRect(310, 10, 80, 80))

				self.shopTwentyThreeCheckbox = QtGui.QCheckBox("Soleclassics", self.scrapePageTwoWidget)
				self.shopTwentyThreeCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(310, 90, 100, 25)))
				self.shopTwentyThreeCheckbox.setFont(font)

				self.shopTwentyFourLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyFourLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sadfwertfdc.png')).scaledToWidth(80))
				self.shopTwentyFourLabel.setGeometry(QtCore.QRect(400, 10, 80, 80))

				self.shopTwentyFourCheckbox = QtGui.QCheckBox("Sneakerusa", self.scrapePageTwoWidget)
				self.shopTwentyFourCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(395, 90, 100, 25)))
				self.shopTwentyFourCheckbox.setFont(QtGui.QFont("Calibri", 9, 65))

				self.shopTwentyFiveLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyFiveLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdtgwfdvxce.png')).scaledToWidth(100))
				self.shopTwentyFiveLabel.setGeometry(QtCore.QRect(20, 110, 100, 45))

				self.shopTwentyFiveCheckbox = QtGui.QCheckBox("Rimenyc", self.scrapePageTwoWidget)
				self.shopTwentyFiveCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(35, 150, 100, 25)))
				self.shopTwentyFiveCheckbox.setFont(font)

				self.shopTwentySixLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentySixLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfkjduyw.png')).scaledToWidth(100))
				self.shopTwentySixLabel.setGeometry(QtCore.QRect(130, 115, 100, 45))

				self.shopTwentySixCheckbox = QtGui.QCheckBox("12amrun", self.scrapePageTwoWidget)
				self.shopTwentySixCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(145, 150, 100, 25)))
				self.shopTwentySixCheckbox.setFont(font)

				self.shopTwentySevenLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentySevenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\dfhgdfghdfngh.png')).scaledToWidth(80))
				self.shopTwentySevenLabel.setGeometry(QtCore.QRect(250, 115, 80, 40))

				self.shopTwentySevenCheckbox = QtGui.QCheckBox("Shoegallerymiami ", self.scrapePageTwoWidget)
				self.shopTwentySevenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(235, 150, 120, 25)))
				self.shopTwentySevenCheckbox.setFont(font)

				self.shopTwentyEightLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyEightLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdfgjnsd.png')).scaledToWidth(150))
				self.shopTwentyEightLabel.setGeometry(QtCore.QRect(350, 120, 150, 30))

				self.shopTwentyEightCheckbox = QtGui.QCheckBox("Bbbranded", self.scrapePageTwoWidget)
				self.shopTwentyEightCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(375, 150, 120, 25)))
				self.shopTwentyEightCheckbox.setFont(font)

				self.shopTwentyEightLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyEightLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sfshdfdfh.png')).scaledToWidth(80))
				self.shopTwentyEightLabel.setGeometry(QtCore.QRect(20, 175, 100, 55))

				self.shopTwentyEightCheckbox = QtGui.QCheckBox("Blendsus", self.scrapePageTwoWidget)
				self.shopTwentyEightCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(25, 230, 120, 25)))
				self.shopTwentyEightCheckbox.setFont(font)

				self.shopTwentyNineLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopTwentyNineLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\phulpbron.png')).scaledToWidth(150))
				self.shopTwentyNineLabel.setGeometry(QtCore.QRect(130, 180, 150, 50))

				self.shopTwentyNineCheckbox = QtGui.QCheckBox("Philipbrownemenswear", self.scrapePageTwoWidget)
				self.shopTwentyNineCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(125, 230, 160, 25)))
				self.shopTwentyNineCheckbox.setFont(font)

				self.shopThirtyLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sfheuik.png')).scaledToWidth(150))
				self.shopThirtyLabel.setGeometry(QtCore.QRect(300, 180, 150, 50))

				self.shopThirtyCheckbox = QtGui.QCheckBox("Addictmiami", self.scrapePageTwoWidget)
				self.shopThirtyCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(330, 230, 120, 25)))
				self.shopThirtyCheckbox.setFont(font)

				self.shopThirtyOneLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyOneLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdsdgijsdfui.png')).scaledToWidth(100))
				self.shopThirtyOneLabel.setGeometry(QtCore.QRect(10, 250, 100, 50))

				self.shopThirtyOneCheckbox = QtGui.QCheckBox("Wishatl", self.scrapePageTwoWidget)
				self.shopThirtyOneCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(25, 290, 120, 25)))
				self.shopThirtyOneCheckbox.setFont(font)

				self.shopThirtyTwoLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyTwoLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\jifv.png')).scaledToWidth(100))
				self.shopThirtyTwoLabel.setGeometry(QtCore.QRect(120, 250, 100, 50))

				self.shopThirtyTwoCheckbox = QtGui.QCheckBox("Burnrubbersneakers", self.scrapePageTwoWidget)
				self.shopThirtyTwoCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(105, 290, 140, 25)))
				self.shopThirtyTwoCheckbox.setFont(font)

				self.shopThirtyThreeLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyThreeLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\minimsdh.png')).scaledToWidth(100))
				self.shopThirtyThreeLabel.setGeometry(QtCore.QRect(240, 240, 100, 60))

				self.shopThirtyThreeCheckbox = QtGui.QCheckBox("Minishopmadrid", self.scrapePageTwoWidget)
				self.shopThirtyThreeCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(240, 290, 140, 25)))
				self.shopThirtyThreeCheckbox.setFont(font)

				self.shopThirtyFourLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyFourLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\soleplay.png')).scaledToWidth(150))
				self.shopThirtyFourLabel.setGeometry(QtCore.QRect(330, 260, 150, 25))

				self.shopThirtyFourCheckbox = QtGui.QCheckBox("Solefly", self.scrapePageTwoWidget)
				self.shopThirtyFourCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(380, 290, 80, 25)))
				self.shopThirtyFourCheckbox.setFont(font)

				self.shopThirtyFiveLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyFiveLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\smatabndj.png')).scaledToWidth(80))
				self.shopThirtyFiveLabel.setGeometry(QtCore.QRect(20, 315, 80, 80))

				self.shopThirtyFiveCheckbox = QtGui.QCheckBox("Samtabak", self.scrapePageTwoWidget)
				self.shopThirtyFiveCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(20, 390, 80, 25)))
				self.shopThirtyFiveCheckbox.setFont(font)

				self.shopThirtySixLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtySixLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\sdawfafs.png')).scaledToWidth(80))
				self.shopThirtySixLabel.setGeometry(QtCore.QRect(120, 315, 80, 80))

				self.shopThirtySixCheckbox = QtGui.QCheckBox("Capsuletoronto", self.scrapePageTwoWidget)
				self.shopThirtySixCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(110, 390, 120, 25)))
				self.shopThirtySixCheckbox.setFont(font)

				self.shopThirtySevenLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtySevenLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\zqh-SkaL_400x400.png')).scaledToWidth(80))
				self.shopThirtySevenLabel.setGeometry(QtCore.QRect(220, 315, 80, 80))

				self.shopThirtySevenCheckbox = QtGui.QCheckBox("Alumniofny", self.scrapePageTwoWidget)
				self.shopThirtySevenCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(220, 390, 120, 25)))
				self.shopThirtySevenCheckbox.setFont(font)

				self.shopThirtyEightLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.shopThirtyEightLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Shops\dripla.png')).scaledToWidth(150))
				self.shopThirtyEightLabel.setGeometry(QtCore.QRect(320, 330, 150, 50))

				self.shopThirtyEightCheckbox = QtGui.QCheckBox("Shopdripla", self.scrapePageTwoWidget)
				self.shopThirtyEightCheckbox.setGeometry(QtCore.QRect(QtCore.QRect(340, 390, 120, 25)))
				self.shopThirtyEightCheckbox.setFont(font)

				self.backShopPageLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.backShopPageLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sfdfger.png')).scaledToWidth(30))
				self.backShopPageLabel.setGeometry(QtCore.QRect(160, 410, 30, 30))
				self.backShopPageLabel.mousePressEvent = lambda event:self.changeScrapeTabGUIPage()

				self.backShopTextLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.backShopTextLabel.setGeometry(QtCore.QRect(200, 415, 70, 20))
				self.backShopTextLabel.setFont(self.font)
				self.backShopTextLabel.setText("Back")
				self.backShopTextLabel.mousePressEvent = lambda event:self.changeScrapeTabGUIPage()

				self.addShopLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.addShopLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfasd.png')).scaledToWidth(30))
				self.addShopLabel.setGeometry(QtCore.QRect(260, 410, 30, 30))

				self.addShopTextLabel = QtGui.QLabel(self.scrapePageTwoWidget)
				self.addShopTextLabel.setGeometry(QtCore.QRect(300, 415, 70, 20))
				self.addShopTextLabel.setFont(self.font)
				self.addShopTextLabel.setText("Add")

				self.scrapeTabVerticalDivider = QtGui.QFrame(self.scrapeInfoTabWidget)
				self.scrapeTabVerticalDivider.setGeometry(QtCore.QRect(490, 20, 20, 420))
				self.scrapeTabVerticalDivider.setFrameShape(QtGui.QFrame.VLine)
				self.scrapeTabVerticalDivider.setFrameShadow(QtGui.QFrame.Sunken)

				self.scrapeTwoTextLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.scrapeTwoTextLabel.setGeometry(QtCore.QRect(530, 15, 200, 20))
				self.scrapeTwoTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.scrapeTwoTextLabel.setText("2. Enter Keywords")

				self.scrapeKeywordTable = QtGui.QTableWidget(self.scrapeInfoTabWidget)
				self.scrapeKeywordTable.setGeometry(QtCore.QRect(530, 35, 240, 150))

				self.scrapeKeywordTable.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)       
				self.scrapeKeywordTable.setFrameShape(QtGui.QFrame.StyledPanel)
				self.scrapeKeywordTable.setSelectionMode(QtGui.QAbstractItemView.NoSelection)
				self.scrapeKeywordTable.setGridStyle(QtCore.Qt.SolidLine)

				self.scrapeKeywordTable.setShowGrid(False)
				self.scrapeKeywordTable.setSortingEnabled(True)
				self.scrapeKeywordTable.setWordWrap(True)
				self.scrapeKeywordTable.setCornerButtonEnabled(False)

				item = QtGui.QTableWidgetItem()
				self.scrapeKeywordTable.setColumnCount(1)
				self.scrapeKeywordTable.verticalHeader().setVisible(False)

				item.setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

				item = QtGui.QTableWidgetItem()
				item.setFont(QtGui.QFont("Calibri", 10, 65))
				item.setText("Keyword")
				self.scrapeKeywordTable.setHorizontalHeaderItem(0, item)

				self.scrapeKeywordTable.horizontalHeader().setVisible(True)
				self.scrapeKeywordTable.horizontalHeader().setResizeMode(0, QtGui.QHeaderView.Stretch)

				colour = False

				for i in range(5):
					rowPosition = self.scrapeKeywordTable.rowCount()
					self.scrapeKeywordTable.insertRow(rowPosition)
					self.scrapeKeywordTable.setRowHeight(rowPosition, 25)

					self.scrapeKeywordTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem())
					self.scrapeKeywordTable.item(rowPosition, 0).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

					if colour:
						self.scrapeKeywordTable.item(rowPosition, 0).setBackground(QtGui.QColor(0,130,15,50))

					if colour:
						colour = False
					else:
						colour = True

				self.scrapeKeywordInput = QtGui.QLineEdit(self.scrapeInfoTabWidget)
				self.scrapeKeywordInput.setGeometry(QtCore.QRect(530, 195, 185, 25))
				self.scrapeKeywordInput.setFont(font)
				self.scrapeKeywordInput.setText("Add Keyword")

				self.addKeywordLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.addKeywordLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfasd.png')).scaledToWidth(20))
				self.addKeywordLabel.setGeometry(QtCore.QRect(725, 195, 20, 20))

				self.delTKeywordLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.delTKeywordLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfsd-dfg.png')).scaledToWidth(20))
				self.delTKeywordLabel.setGeometry(QtCore.QRect(750, 195, 20, 20))

				self.scrapeThreeTextLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.scrapeThreeTextLabel.setGeometry(QtCore.QRect(530, 230, 200, 20))
				self.scrapeThreeTextLabel.setFont(QtGui.QFont("Calibri", 12, 65))
				self.scrapeThreeTextLabel.setText("3. Select A Date (Optional)")

				self.scrapeCalander = QtGui.QCalendarWidget(self.scrapeInfoTabWidget)
				self.scrapeCalander.setGeometry(QtCore.QRect(530, 260, 240, 160))

				self.startScrapeLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.startScrapeLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sdfsdf.png')).scaledToWidth(30))
				self.startScrapeLabel.setGeometry(QtCore.QRect(600, 425, 30, 30))

				self.startScrapeTextLabel = QtGui.QLabel(self.scrapeInfoTabWidget)
				self.startScrapeTextLabel.setGeometry(QtCore.QRect(640, 430, 70, 20))
				self.startScrapeTextLabel.setFont(self.font)
				self.startScrapeTextLabel.setText("Start")

				self.scrapePageTwoWidget.hide()

			self.scrapeInfoTabWidget.show()

	def settingsTabGUI(self):
		self.settingsTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\gear-png-8_click.png')).scaledToWidth(75))

		if self.currentTab != "Settings":
			self.changeTab()
			self.currentTab = "Settings"

			if self.scrapeTabRender == False:
				font = QtGui.QFont("Calibri", 10, 65)

				self.settingsTabRender = True

				self.settingsTabWidget = QtGui.QWidget(self.mainWidget)
				self.settingsTabWidget.setGeometry(QtCore.QRect(0, 105, 800, 470))

				self.deactivatePageLabel = QtGui.QLabel(self.settingsTabWidget)
				self.deactivatePageLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\sfdfger.png')).scaledToWidth(30))
				self.deactivatePageLabel.setGeometry(QtCore.QRect(160, 410, 30, 30))
				self.deactivatePageLabel.mousePressEvent = lambda event:self.deactivate()

				self.deactivateTextLabel = QtGui.QLabel(self.settingsTabWidget)
				self.deactivateTextLabel.setGeometry(QtCore.QRect(200, 415, 70, 20))
				self.deactivateTextLabel.setFont(self.font)
				self.deactivateTextLabel.setText("Deactivate")
				self.deactivateTextLabel.mousePressEvent = lambda event:self.deactivate()

			self.settingsTabWidget.show()

	def show(self):
		super(QtGui.QMainWindow, self).show()
		self.qtApp.exec_()

	def checkAddTask(self):
		self.pref.update_preferences({'Proxies': proxies})
		self.proxies = self.pref.get('Proxies')

	def editTask(self):
		row = self.taskTable.currentRow()

		for i in range(len(self.tasks)):
			task = self.tasks[i]

			if task['task_name'] == self.taskTable.item(row, 0).text():
				self.taskNameInput.setText(task['task_name'])
				self.taskNameInput.setReadOnly(True)
				self.taskStoreSelect.setCurrentIndex(self.taskStoreSelect.findText(task['store_name']))
				self.taskItemNameInput.setText(task['item_name'])
				self.taskSizeSelect.setCurrentIndex(self.taskSizeSelect.findText(task['size']))
				self.taskBillSelect.setCurrentIndex(self.taskBillSelect.findText(task['billing_profile']))
				self.taskProxySelect.setCurrentIndex(self.taskProxySelect.findText(task['task_proxy']))

				if task['notification']:
					self.notifCheckbox.setChecked(True)
				else:
					self.notifCheckbox.setChecked(False)

	def taskSave(self):
		self.taskEdited = True
		self.currentTab = None
		self.taskNameInput.setReadOnly(False)

		for i in range(len(self.tasks)):
			task = self.tasks[i]
			if task['task_name'] == str(self.taskNameInput.text()):
				task['store_name'] = str(self.taskStoreSelect.currentText())
				task['item_name'] = str(self.taskItemNameInput.text())
				task['size'] = str(self.taskSizeSelect.currentText())
				task['billing_profile'] = str(self.taskBillSelect.currentText())
				task['task_proxy'] = str(self.taskProxySelect.currentText())

				if self.notifCheckbox.isChecked():
					task['notification'] = True
				else:
					task['notification'] = False

				self.pref.update_preferences({'tasks': self.tasks})

				self.taskTabGUI()
				self.taskTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Tools-PNG-Image.png')).scaledToWidth(80))

				return None

		taskDict = {'task_name': str(self.taskNameInput.text()),
					'store_name': str(self.taskStoreSelect.currentText()),
					'item_name': str(self.taskItemNameInput.text()),
					'size': str(self.taskSizeSelect.currentText()),
					'billing_profile': str(self.taskBillSelect.currentText()),
					'task_proxy': str(self.taskProxySelect.currentText())}

		if self.notifCheckbox.isChecked():
			taskDict['notification'] = True
		else:
			taskDict['notification'] = False

		self.tasks.append(taskDict)
		self.pref.update_preferences({'tasks': self.tasks})

		self.taskTabGUI()
		self.taskTabLabel.setPixmap(QtGui.QPixmap(resource_path('Data\Image\Tools-PNG-Image.png')).scaledToWidth(80))

	def changeScrapeTabGUIPage(self):
		if self.currentStorePage == "One":
			self.scrapePageOneWidget.hide()
			self.scrapePageTwoWidget.show()

			self.currentStorePage = "Two"
		elif self.currentStorePage =="Two":
			self.scrapePageTwoWidget.hide()
			self.scrapePageOneWidget.show()

			self.currentStorePage = "One"

	def changeCardTabGUIPage(self):
		if self.currentCardPage == "One":
			self.cardStepOneWidget.hide()
			self.cardStepTwoWidget.show()

			self.currentCardPage = "Two"
		elif self.currentCardPage =="Two":
			self.cardStepTwoWidget.hide()
			self.cardStepOneWidget.show()

			self.currentCardPage = "One"

	def changeTab(self):
		if self.currentTab == "Monitor":
			self.monitorTabWidget.hide()
		elif self.currentTab == "Add Task":
			self.taskTabWidget.hide()
		elif self.currentTab == "Card":
			self.cardTabWidget.hide()
		elif self.currentTab == "Scrape":
			self.scrapeInfoTabWidget.hide()
		elif self.currentTab == "Settings":
			self.settingsTabWidget.hide()

	def saveBillProfile(self):
		billDict = {
		'coEmail':str(self.emailEdit.text()),
		'coFName':str(self.fNameEdit.text()),
		'coLName':str(self.lNameEdit.text()),
		'coCompName':str(self.companyEdit.text()),
		'coAddress':str(self.addEdit.text()),
		'coApt':str(self.aptEdit.text()),
		'coCity':str(self.cityEdit.text()),
		'coCountry':str(self.countryEdit.text()),
		'coState':str(self.stateEdit.text()),
		'coPostCode':str(self.pCodeEdit.text()),
		'coPhone':str(self.phoneEdit.text()),
		'coDiscount':str(self.discountEdit.text()),
		'coCCNum':str(self.ccNumberEdit.text()),
		'coCCName':str(self.ccNameEdit.text()),
		'coCCExpiry':str(self.ccExpiryEdit.text()),
		'coCCSNum':str(self.ccSecurityEdit.text())
		}

		self.bill_profile[str(self.cardNameInput.text())] = billDict

		self.pref.update_preferences({'billing_profile': self.bill_profile})

	def monitorStart(self):
		count = 0
		for row in self.checkedRows:
			self.monitorTable.item(row, 5).setText('Starting...')

			self.workerThreads.append(monitorItem(self.tasks[row], row))
			self.window.connect(self.workerThreads[count], QtCore.SIGNAL("updateStatus(PyQt_PyObject, PyQt_PyObject)"), self.updateStatus, QtCore.Qt.BlockingQueuedConnection)
			self.workerThreads[count].finished.connect(partial(self.printTes, "HI"))
			self.workerThreads[count].start()

			count += 1

	def printTes(self, word):
		print word

	def updateStatus(self, row, status):
		self.monitorTable.item(row, 5).setText(status)
		QtCore.QCoreApplication.processEvents() 

	def log(self, item):
		if self.logCount >= 250:
			self.logCount = 0
			self.logBrowser.clear()

		self.logBrowser.append(item)
		self.logCount += 1

	def clearOutput(self):
		self.productUrls = []
		self.outputTable.setRowCount(0)
		self.window.setFixedSize(1018, 627)      
		self.itemTable.setRowCount(0)

	def twitterDialog(self):
		twitterDialog = QtGui.QDialog(self.window)
		self.twitter = twitterDetail()
		self.twitter.setupUi(twitterDialog)
		twitterDialog.exec_()

	def proxyDialog(self):
		proxyDialog = QtGui.QDialog(self.window)
		self.proxy = addProxy()
		self.proxy.initUI(proxyDialog)
		proxyDialog.exec_()

		proxies = str(self.proxy.proxyTextEdit.toPlainText()).strip().splitlines()

		self.pref.update_preferences({'Proxies': proxies})
		self.proxies = proxies

	def checkboxChecked(self):
		if self.twitterCheck.isChecked():
			if not self.pref.get('twInfoEntered'):
				self.twitterCheck.setChecked(False)
				self.twitterDialog()

				if self.twitter.sucess:
					self.twitterCheck.setChecked(True)

	def deactivate(self):
		self.deactivateMsg = QtGui.QMessageBox()
		self.deactivateMsg.setWindowIcon(self.icon)
		self.deactivateMsg.setWindowTitle("Deactive Program")
		self.deactivateMsg.setText("Are you sure you want to deactivate?")
		self.deactivateMsg.addButton(QtGui.QMessageBox.Ok)
		self.deactivateMsg.addButton(QtGui.QMessageBox.Cancel)
		self.deactivateMsg.setDefaultButton(QtGui.QMessageBox.Cancel)

		if self.deactivateMsg.exec_() == QtGui.QMessageBox.Ok:
			ta.deactivate()
			sys.exit()

	def insertLink(self, link):
		rowPosition = self.linkTable.rowCount()
		self.linkTable.insertRow(rowPosition)
		self.linkTable.setRowHeight(rowPosition, 15)

		chkBoxItem = QtGui.QTableWidgetItem()
		chkBoxItem.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
		chkBoxItem.setCheckState(QtCore.Qt.Unchecked)       
		self.linkTable.setItem(rowPosition,0,chkBoxItem)

		self.linkTable.setItem(rowPosition, 1, QtGui.QTableWidgetItem(link))

	def load_links(self):
		fileName = QtGui.QFileDialog.getOpenFileName(self.window, 'Open File', '', 'Text Files (*.txt)')

		links = (line.rstrip('\n') for line in open(fileName))

		for link in links:
			self.insertLink(link)

	def add_links(self):
		addLinksWin = QtGui.QDialog(self.window)
		self.addLinks = addLinks()
		self.addLinks.initUI(addLinksWin)
		addLinksWin.exec_()

		links = str(self.addLinks.linkTextEdit.toPlainText()).strip().splitlines()

		for link in links:
			self.insertLink(link)

	def itemClickedHandler(self, item):
		if item.checkState() == QtCore.Qt.Checked:
			if item.row() not in self.checkedRows:
				self.checkedRows.append(item.row())
		elif item.column() == 0:
			if item.row() in self.checkedRows:
				self.checkedRows.remove(item.row())

	def del_links(self):
		self.mainWidget.hide()
		self.checkedLinkRows.sort()
		removeCount = 0

		for row in self.checkedLinkRows:
			self.linkTable.removeRow(row - removeCount)
			removeCount += 1

		self.checkedLinkRows = []

	def clear_links(self): 
		self.mainWidget.show()
		self.linkTable.setRowCount(0)
		self.checkedLinkRows = []

		self.popUp("Links Cleared!", "All links have been cleared from crawling")

	def print_log(self):
		log = self.logBrowser.toPlainText()
		
		script_dir = os.path.dirname(__file__)
		rel_path = "log.txt"
		abs_file_path = os.path.join(script_dir, rel_path)

		file = open(abs_file_path, 'a+')
		file.write(log)
		file.close()

		self.popUp("Log Saved!", "Log has been saved to log.txt")	

	def insertRow(self, url, keyword):
		rowPosition = self.outputTable.rowCount()
		self.outputTable.insertRow(rowPosition)
		self.outputTable.setRowHeight(rowPosition, 35)

		currentTime = time.strftime("%d/%m/%Y %I:%M %p")

		self.outputTable.setItem(rowPosition, 0, QtGui.QTableWidgetItem(url))
		self.outputTable.setItem(rowPosition, 1, QtGui.QTableWidgetItem(currentTime))
		self.outputTable.setItem(rowPosition, 2, QtGui.QTableWidgetItem(keyword))

		linkPic = QtGui.QLabel()
		linkPic.setPixmap(QtGui.QPixmap(resource_path('Data\linkImg.png')).scaledToWidth(15))
		linkPic.mousePressEvent = lambda event:webbrowser.open(url)
		self.outputTable.setCellWidget(rowPosition, 3, linkPic)

		detailPic = QtGui.QLabel()
		detailPic.setPixmap(QtGui.QPixmap(resource_path('Data\detailImg.png')).scaledToWidth(15))
		detailPic.mousePressEvent = lambda event:self.showItemDetail(url, '/'.join(url.split('/')[:3]))
		self.outputTable.setCellWidget(rowPosition, 4, detailPic)		

		for i in range(3):
			self.outputTable.item(rowPosition, i).setTextAlignment(QtCore.Qt.AlignHCenter|QtCore.Qt.AlignVCenter|QtCore.Qt.AlignCenter)

		if self.twitterCheck.isChecked():
			itemTitle = url.split('/')[4].replace('-', ' ')
			self.tweetItems.append('{0} || {1} is now available! {2}'.format(time.strftime("%I:%M:%S %p"), itemTitle, url))

			if not self.tweetQueued:
				self.tweetQueued = True

				self.tweetQueue = tweetLink(self)
				self.tweetQueue.start()

		QtCore.QCoreApplication.processEvents() 
		
	def showItemDetail(self, url, baseUrl):
		self.showDetailWin = QtGui.QDialog(self.window)
		self.showDetail = showDetail(url, baseUrl)
		self.showDetail.initUI(self.showDetailWin)
		self.showDetailWin.exec_()    

	def runThread(self, keywords):
		if self.linkCount < self.linkTable.rowCount() and not self.stopped:
			time.sleep(0.05)

			if self.proxy != None:
				self.logItems.append('{} - Using Proxy {} - Started scraping - {}'.format(time.strftime("%m/%d/%Y %I:%M %p"), self.proxy, self.linkTable.item(self.linkCount, 1).text()))
			else:
				self.logItems.append('{} - Started scraping - {}'.format(time.strftime("%m/%d/%Y %I:%M %p"), self.linkTable.item(self.linkCount, 1).text()))

			if not self.logQueued:
				self.logQueued = True
				self.logQueue = printLog(self)
				self.window.connect(self.logQueue, QtCore.SIGNAL("log(PyQt_PyObject)"), self.log)
				self.logQueue.start()

			self.workerThreads.append(collectData(self, self.linkTable.item(self.linkCount, 1).text(), keywords, self.proxy))
			self.window.connect(self.workerThreads[self.linkCount], QtCore.SIGNAL("insertRow(PyQt_PyObject, PyQt_PyObject)"), self.insertRow, QtCore.Qt.BlockingQueuedConnection)
			self.workerThreads[self.linkCount].finished.connect(partial(self.runThread, keywords))
			self.workerThreads[self.linkCount].start()

			self.linkCount += 1
		elif all(thread.isRunning() == False for thread in self.workerThreads):
			self.workerThreads = []

			print "My program took", time.time() - self.start_time, "to run"

			if self.continuous and not self.stopped:
				self.programStart()

			if not self.repeatTimer.isActive() and not self.continuous:				
				self.runBtn.setEnabled(True)
				self.resetBtn.setEnabled(True)

	def checkoutDialog(self):
		self.checkoutWin = QtGui.QDialog(self.window)
		self.checkout = checkoutDetail()
		self.checkout.initUI(self.checkoutWin)
		self.checkoutWin.exec_()		

	def programStart(self):
		if all(thread.isRunning() == False for thread in self.workerThreads):
			if self.waitTimer.isActive():
				self.waitTimer.stop()

			if self.repeatCount == 0:
				self.proxy = None
			elif self.repeatCount > len(self.proxies):
				self.repeatCount = 0
				self.proxy = None
			else:
				self.proxy = self.proxies[self.repeatCount-1]

			self.repeatCount += 1

			self.start_time = time.time()

			if not self.repeatTimer.isActive() and self.schedulerCheck.isChecked() and not self.continuous:
				if self.waitMinBox.value() != 0.0:
					self.repeatTimer.start(self.waitMinBox.value() * 60000)
				else:
					self.continuous = True

			self.linkCount = 0
			self.stopped = False
			self.runBtn.setEnabled(False)
			self.resetBtn.setEnabled(False)

			keywords = str(self.keywordInput.text()).lower().replace('+', '-').replace(' ', '-').split(',')

			if self.linkTable.rowCount() < 10:
				self.speed = self.linkTable.rowCount()
			else:
				self.speed = 10

			for i in range(self.speed):
				self.runThread(keywords)
		else:
			self.logItems.append('{} - Repeat time is too low. Stop the program and increase the time interval. We recommend 1 min. '.format(time.strftime("%m/%d/%Y %I:%M %p")))
			self.waitTimer.start(6000)

	def programStop(self):
		if self.repeatTimer.isActive():
			self.repeatTimer.stop()

		if self.waitTimer.isActive():
			self.waitTimer.stop()

		self.runBtn.setEnabled(True)
		self.resetBtn.setEnabled(True)
		self.stopped = True
		self.continuous = False

		self.linkCount = 0
		self.repeatCount = 0

		self.productUrls = []
		self.workerThreads = []
		self.checkedLinkRows = []

	def programReset(self):
		self.keywordInput.clear()
		self.logBrowser.clear()

		if self.schedulerCheck.isChecked():
			self.schedulerCheck.setChecked(False)

		if self.twitterCheck.isChecked():
			self.twitterCheck.setChecked(False)

		if self.dateCheck.isChecked():
			self.dateCheck.setChecked(False)		

		self.outputTable.setRowCount(0)
		self.linkTable.setRowCount(0)

		self.programStop()

		self.popUp("Program Reset!", "Program has reset")

	def popUp(self, title, msg):
		self.popMsg = QtGui.QMessageBox()
		self.popMsg.setWindowIcon(self.icon)
		self.popMsg.setWindowTitle(title)
		self.popMsg.setText(msg)
		self.popMsg.addButton(QtGui.QMessageBox.Ok)
		self.popMsg.addButton(QtGui.QMessageBox.Cancel)
		self.popMsg.setDefaultButton(QtGui.QMessageBox.Ok)

		self.popMsg.exec_()