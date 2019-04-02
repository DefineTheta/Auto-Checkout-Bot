from PyQt4 import QtCore, QtGui
from functools import partial
from pypref import Preferences
import time
import sys
import os

from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)

class checkoutDetail(object):
	def __init__(self):
		self.pref = Preferences(directory=os.path.join(os.environ['APPDATA'], 'Shopify Destroyer'), filename='bot_pref.py')

	def initUI(self, dialog):
		self.editedBoxes = [False, False, False, False, False, False, False, False, False, False, False, False, False]
		self.sucess = False

		self.win = dialog
		dialog.setWindowTitle("Checkout Detail ~ Shopify Destroyer")
		dialog.setFixedSize(531, 589)
		self.font = QtGui.QFont()
		self.font.setPointSize(10)

		self.icon = QtGui.QIcon()
		self.icon.addPixmap(QtGui.QPixmap(_fromUtf8(str(resource_path("Data\icon.png")))), QtGui.QIcon.Normal, QtGui.QIcon.Off)
		dialog.setWindowIcon(self.icon)

		self.checkoutDetailContainer = QtGui.QGroupBox(dialog)
		self.checkoutDetailContainer.setGeometry(QtCore.QRect(0, 0, 531, 411))
		self.checkoutDetailContainer.setTitle("Checkout Detail")

		self.emailEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.emailEdit.setGeometry(QtCore.QRect(20, 20, 491, 31))
		self.emailEdit.setFont(self.font)
		self.emailEdit.setText("Email Address")
		self.emailEdit.textChanged.connect(partial(self.edited, 0))

		self.fNameEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.fNameEdit.setGeometry(QtCore.QRect(20, 70, 231, 31))
		self.fNameEdit.setFont(self.font)
		self.fNameEdit.setText("First Name")
		self.fNameEdit.textChanged.connect(partial(self.edited, 1))

		self.lNameEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.lNameEdit.setGeometry(QtCore.QRect(280, 70, 231, 31))
		self.lNameEdit.setFont(self.font)
		self.lNameEdit.setText("Last Name")
		self.lNameEdit.textChanged.connect(partial(self.edited, 2))

		self.companyEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.companyEdit.setGeometry(QtCore.QRect(20, 120, 491, 31))
		self.companyEdit.setFont(self.font)
		self.companyEdit.setText("Company (Optional)")

		self.addEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.addEdit.setGeometry(QtCore.QRect(20, 170, 351, 31))
		self.addEdit.setFont(self.font)
		self.addEdit.setText("Address")
		self.addEdit.textChanged.connect(partial(self.edited, 3))

		self.aptEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.aptEdit.setGeometry(QtCore.QRect(400, 170, 111, 31))
		self.aptEdit.setFont(self.font)
		self.aptEdit.setText("Apt (Optional)")

		self.cityEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.cityEdit.setGeometry(QtCore.QRect(20, 220, 491, 31))
		self.cityEdit.setFont(self.font)
		self.cityEdit.setText("City")
		self.cityEdit.textChanged.connect(partial(self.edited, 4))

		self.countryEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.countryEdit.setGeometry(QtCore.QRect(20, 270, 171, 31))
		self.countryEdit.setFont(self.font)
		self.countryEdit.setText("Country")
		self.countryEdit.textChanged.connect(partial(self.edited, 5))

		self.stateEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.stateEdit.setGeometry(QtCore.QRect(210, 270, 171, 31))
		self.stateEdit.setFont(self.font)
		self.stateEdit.setText("State")
		self.stateEdit.textChanged.connect(partial(self.edited, 6))

		self.pCodeEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.pCodeEdit.setGeometry(QtCore.QRect(400, 270, 111, 31))
		self.pCodeEdit.setFont(self.font)
		self.pCodeEdit.setText("Postcode")
		self.pCodeEdit.textChanged.connect(partial(self.edited, 7))

		self.phoneEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.phoneEdit.setGeometry(QtCore.QRect(20, 320, 491, 31))
		self.phoneEdit.setFont(self.font)
		self.phoneEdit.setText("Phone")
		self.phoneEdit.textChanged.connect(partial(self.edited, 8))

		self.discountEdit = QtGui.QLineEdit(self.checkoutDetailContainer)
		self.discountEdit.setGeometry(QtCore.QRect(20, 370, 491, 31))
		self.discountEdit.setFont(self.font)
		self.discountEdit.setText("Gift Card or Discount Code (Optional)")

		self.ccDetailContainer = QtGui.QGroupBox(dialog)
		self.ccDetailContainer.setGeometry(QtCore.QRect(0, 420, 531, 171))
		self.ccDetailContainer.setTitle("Credit Card Detail")

		self.ccNumberEdit = QtGui.QLineEdit(self.ccDetailContainer)
		self.ccNumberEdit.setGeometry(QtCore.QRect(20, 20, 491, 31))
		self.ccNumberEdit.setFont(self.font)
		self.ccNumberEdit.setText("Card Number")
		self.ccNumberEdit.textChanged.connect(partial(self.edited, 9))

		self.ccNameEdit = QtGui.QLineEdit(self.ccDetailContainer)
		self.ccNameEdit.setGeometry(QtCore.QRect(20, 70, 241, 31))
		self.ccNameEdit.setFont(self.font)
		self.ccNameEdit.setText("Name On Card")
		self.ccNameEdit.textChanged.connect(partial(self.edited, 10))

		self.ccExpiryEdit = QtGui.QLineEdit(self.ccDetailContainer)
		self.ccExpiryEdit.setGeometry(QtCore.QRect(280, 70, 131, 31))
		self.ccExpiryEdit.setFont(self.font)
		self.ccExpiryEdit.setText("MM/YYYY")
		self.ccExpiryEdit.textChanged.connect(partial(self.edited, 11))

		self.ccSecurityEdit = QtGui.QLineEdit(self.ccDetailContainer)
		self.ccSecurityEdit.setGeometry(QtCore.QRect(430, 70, 81, 31))
		self.ccSecurityEdit.setFont(self.font)
		self.ccSecurityEdit.setText("CVV")
		self.ccSecurityEdit.textChanged.connect(partial(self.edited, 12))

		self.font.setPointSize(12)

		self.contBtn = QtGui.QPushButton(self.ccDetailContainer)
		self.contBtn.setGeometry(QtCore.QRect(48, 120, 171, 41))
		self.contBtn.setFont(self.font)
		self.contBtn.setText("Continue")
		self.contBtn.clicked.connect(self.cont)

		self.cancelBtn = QtGui.QPushButton(self.ccDetailContainer)
		self.cancelBtn.setGeometry(QtCore.QRect(313, 120, 171, 41))
		self.cancelBtn.setFont(self.font)
		self.cancelBtn.setText("Cancel")
		self.cancelBtn.clicked.connect(self.canc)
	
	def edited(self, pos):
		self.editedBoxes[pos] = True

	def canc(self):
		self.sucess = False
		QtGui.QDialog.close(self.win)				

	def cont(self):
		if all(box == True for box in self.editedBoxes):
			self.pref.update_preferences({
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
				'coPhone':str(self.pCodeEdit.text()),
				'coDiscount':str(self.discountEdit.text()),
				'coCCNum':str(self.ccNumberEdit.text()),
				'coCCName':str(self.ccNameEdit.text()),
				'coCCExpiry':str(self.ccExpiryEdit.text()),
				'coCCSNum':str(self.ccSecurityEdit.text())})

			self.pref.update_preferences({'checkoutDetailEntered':True})

			QtGui.QDialog.close(self.win)
		else:
			self.popMsg = QtGui.QMessageBox()
			self.popMsg.setWindowIcon(self.icon)
			self.popMsg.setWindowTitle("Invalid Inputs!")
			self.popMsg.setText("Please fill in all the required information")
			self.popMsg.addButton(QtGui.QMessageBox.Ok)
			self.popMsg.addButton(QtGui.QMessageBox.Cancel)
			self.popMsg.setDefaultButton(QtGui.QMessageBox.Ok)

			self.popMsg.exec_()

class autoCheckout(QtCore.QThread):
	def __init__(self, url, billing_name):
		QtCore.QThread.__init__(self)
		self.url = url
		self.finished = False
		self.sucess = False

		self.pref = Preferences(directory=os.path.join(os.environ['APPDATA'], 'Shopify Destroyer'), filename='bot_pref.py')

		self.billingProfile = self.pref.get('billing_profile')[billing_name] 
		self.email = self.billingProfile['coEmail']
		self.fName = self.billingProfile['coFName']
		self.lName = self.billingProfile['coLName']
		self.company = self.billingProfile['coCompName']
		self.address = self.billingProfile['coAddress']
		self.apt = self.billingProfile['coApt']
		self.city = self.billingProfile['coCity']
		self.country = self.billingProfile['coCountry']
		self.state = self.billingProfile['coState']
		self.pCode = self.billingProfile['coPostCode']
		self.phone = self.billingProfile['coPhone']
		self.discount = self.billingProfile['coDiscount']
		self.ccInfo = [self.billingProfile['coCCNum'],
				self.billingProfile['coCCName'],
				self.billingProfile['coCCExpiry'],
				self.billingProfile['coCCSNum']]

	def __del__(self):
		self.wait()

	def run(self):
		self.wdriver = webdriver.Chrome(resource_path('Data\chromedriver.exe'))
		self.wdriver.get(self.url)

		inputForm = WebDriverWait(self.wdriver, 20).until(
					EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div/form"))
					)

		emailInput = inputForm.find_element_by_id('checkout_email')
		emailInput.send_keys(self.email)

		fNameInput = inputForm.find_element_by_id('checkout_shipping_address_first_name')
		fNameInput.send_keys(self.fName)

		lNameInput = inputForm.find_element_by_id('checkout_shipping_address_last_name')
		lNameInput.send_keys(self.lName)

		if self.company != "Company (Optional)":
			try:
				companyInput = inputForm.find_element_by_id('checkout_shipping_address_company')
				companyInput.send_keys(self.company)
			except:
				pass

		addInput = inputForm.find_element_by_id('checkout_shipping_address_address1')
		addInput.send_keys(self.address)

		if self.apt != "Apt (Optional)":
			aptInput = inputForm.find_element_by_id('checkout_shipping_address_address2')
			aptInput.send_keys(self.apt)

		cityInput = inputForm.find_element_by_id('checkout_shipping_address_city')
		cityInput.send_keys(self.city)

		countrySelect = Select(inputForm.find_element_by_id('checkout_shipping_address_country'))
		countrySelect.select_by_visible_text(self.country)

		stateSelect = Select(inputForm.find_element_by_id('checkout_shipping_address_province'))
		stateSelect.select_by_visible_text(self.state)

		pCodeInput = inputForm.find_element_by_id('checkout_shipping_address_zip')
		pCodeInput.send_keys(self.pCode)

		try:
			phoneInput = inputForm.find_element_by_id('checkout_shipping_address_phone')
			phoneInput.send_keys(self.phone)
		except NoSuchElementException:
			pass

		contBtn = inputForm.find_element_by_name('button')
		contBtn.click()

		time.sleep(5)

		paymentBtn = WebDriverWait(self.wdriver, 20).until(
					EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div/div[2]/div[2]/div/form/div[2]/button"))
					)
		paymentBtn.click()

		frame = WebDriverWait(self.wdriver, 20).until(
					EC.presence_of_element_located((By.TAG_NAME, "iframe"))
					)

		iframes = self.wdriver.find_elements_by_tag_name('iframe')  

		inputIDs = ["/html/body/form/input[1]", "/html/body/form/input[2]", "/html/body/form/input[5]", "/html/body/form/input[6]"]

		time.sleep(5)

		for i in range(4):
			self.wdriver.switch_to_frame(iframes[i])

			inputBox = self.wdriver.find_element_by_xpath(inputIDs[i])

			if i == 0:
				for j in range(len(self.ccInfo[i])):
					if j%4 == 0:
						time.sleep(0.5)
					inputBox.send_keys(self.ccInfo[i][j])
			elif i == 2:
				date = self.ccInfo[i].split('/')

				inputBox.send_keys(date[0])
				time.sleep(1)
				inputBox.send_keys(date[1])
			else:
				inputBox.send_keys(self.ccInfo[i])

			self.wdriver.switch_to_default_content()

		if self.discount != "Gift Card or Discount Code (Optional)":
			discountInput = self.wdriver.find_element_by_id('checkout_reduction_code')
			discountInput.send_keys(self.discount)

		# sameShipAddBtn = self.wdriver.find_element_by_id('checkout_different_billing_address_false')
		# sameShipAddBtn.click()

		completeBtn = self.wdriver.find_element_by_name('button')
		completeBtn.click()

		sucessMsg = WebDriverWait(self.wdriver, 20).until(
					EC.presence_of_element_located((By.CLASS_NAME, "notice__text"))
					)

		self.finished = True