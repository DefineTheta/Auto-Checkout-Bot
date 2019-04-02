import requests, sys, time, re
from datetime import datetime
from bs4 import BeautifulSoup
from urlparse import urlparse


s = requests.session()

def UTCtoEST():
    current=datetime.now()
    return str(current) + ' EST'

home = 'kithnyc'
###Get Session Id###
session = s.get('https://www.'+home+'.com/cart.js').json()
sessionID = session['token']
print('SessionID:', sessionID)

###ATC###
print(UTCtoEST(), 'Adding item....')
atcdata = {
    'id': '34575821767',
    'quantity': '1'
}
for atcurlRetry in range(1):
    atcURL = s.post('https://www.'+home+'.com/cart/add.js', data=atcdata, allow_redirects=True)
    match = re.findall('"quantity":1', atcURL.text)
    if match:
        print(UTCtoEST(), 'ATC successful....')
        break
    print(UTCtoEST(), 'Trying to ATC....')
    time.sleep(0)
else:
    print(UTCtoEST(), 'Could not ATC after ' + ' retries, therefore exiting the bot.')
    sys.exit(1)

###Going to Checkout Page###
for cartRetry in range(1):
    cartdata = {
        'updates[]': 1,
        'note': '',
        'checkout': 'Check Out'
    }
    atc = s.post('https://www.'+home+'.com/cart', data=cartdata, allow_redirects=True)
###Parsing URL###
    parse = urlparse(atc.url)
    storeID = parse.path.split('/')[1]
    checkoutID = parse.path.split('checkouts/')[1]
    print('Checkout Session Id:', checkoutID)
###Get Token###
    soup = BeautifulSoup(atc.text, 'lxml')
    input = soup.find_all('input')[2]
    auth_token = input.get('value')
    print('Auth_token:', auth_token)
###Get Contact info###
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Host': 'checkout.shopify.com',
        'Referer': 'https: //checkout.shopify.com/'+storeID+'/checkouts/'+checkoutID+'?step=contact_information',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    qs = {
        '_method': 'patch',
        'authenticity_token': auth_token,
        'previous_step': 'contact_information',
        'checkout[email]': 'email',
        'checkout[shipping_address][first_name]': 'First',
        'checkout[shipping_address][last_name]': 'Last',
        'checkout[shipping_address][company]': '',
        'checkout[shipping_address][address1]': 'Address 1',
        'checkout[shipping_address][address2]': '',
        'checkout[shipping_address][city]': 'City',
        'checkout[shipping_address][country]': 'United States',
        'checkout[shipping_address][province]': '',
        'checkout[shipping_address][province]': '',
        'checkout[shipping_address][province]': 'New York',
        'checkout[shipping_address][zip]': 'Zip',
        'checkout[shipping_address][phone]': 'Phone',
        'checkout[remember_me]': '',
        'checkout[remember_me]': '0',
        'checkout[client_details][browser_width]': '979',
        'checkout[client_details][browser_height]': '631',
        'checkout[client_details][javascript_enabled]': '1',
        'step': 'contact_information'
    }
    GETcontact = s.get(atc.url, data=qs, headers=headers, allow_redirects=True)
    print atc.url

###Post Contact Info###
    headers1 = {
        'Origin': 'https://checkout.shopify.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Referer': 'https://checkout.shopify.com/'+storeID+'/checkouts/'+checkoutID,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    formData = {
        '_method': 'patch',
        'authenticity_token': auth_token,
        'button': '',
        'checkout[email]': 'Email',
        'checkout[shipping_address][first_name]': 'First',
        'checkout[shipping_address][last_name]': 'Last',
        'checkout[shipping_address][address1]': 'Address 1',
        'checkout[shipping_address][address2]': '',
        'checkout[shipping_address][city]': 'City',
        'checkout[shipping_address][country]': 'United States',
        'checkout[shipping_address][province]': 'New York',
        'checkout[shipping_address][zip]': 'Zip',
        'checkout[shipping_address][phone]': '0430 027 546',
        'checkout[remember_me]': '0',
        'checkout[client_details][browser_width]': '979',
        'checkout[client_details][browser_height]': '631',
        'checkout[client_details][javascript_enabled]': '1',
        'previous_step': 'contact_information',
        'step': 'shipping_method'
    }
    POSTcontact = s.post(atc.url, data=formData, headers=headers1, allow_redirects=True)
    ###Parsing Shipping Method###
    soup = BeautifulSoup(POSTcontact.text, 'html.parser')
    file = open('text.html', 'w+')
    file.write(POSTcontact.text.encode('utf8'))
    file.close()
    shipping = soup.find(attrs={'class': 'radio-wrapper'})
    shipping_method = shipping.get('data-shipping-method')

###Submitting Shipping Data###
    headers2 = {
        'Origin': 'https://checkout.shopify.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Referer': 'https://checkout.shopify.com/'+storeID+'/checkouts/'+checkoutID,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    ShipformData = {
        '_method': 'patch',
        'authenticity_token': auth_token,
        'previous_step': 'shipping_method',
        'step': 'payment_method',
        'checkout[shipping_rate][id]': shipping_method,
        'button': '',
        'checkout[client_details][browser_width]': '1280',
        'checkout[client_details][browser_height]': '368',
        'checkout[client_details][javascript_enabled]': '1'
    }
    shippingmethod = s.post(atc.url, data=ShipformData, headers=headers2, allow_redirects=True)
    ###Parsing payment_gateaway###
    soup = BeautifulSoup(shippingmethod.text, 'html.parser')    
    ul = soup.find(attrs={'class': 'radio-wrapper content-box__row '})
    payment_gateaway = ul.get('data-select-gateway')

###submitting payment info###
    CCheaders = {
        'accept': 'application/json',
        'Origin': 'https://checkout.shopifycs.com',
        'Accept-Language': 'en-US,en;q=0.8',
        'Host': 'elb.deposit.shopifycs.com',
        'content-type': 'application/json',
        'Referer': 'https://checkout.shopifycs.com/number?identifier='+checkoutID+'&location=3A%2F%2Fcheckout.shopify.com%2F'+storeID+'%2Fcheckouts%2F'+checkoutID+'%3Fpreviousstep%3Dshipping_method%26step%3Dpayment_method',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    ccinfo = {
        'number': "0000 0000 0000 0000",
        'name': "First Last",
        'month': 5,
        'year': 2020,
        'verification_value': "000"
    }
    creditcard = s.post('https://elb.deposit.shopifycs.com/sessions', json=ccinfo, headers=CCheaders, allow_redirects=True)
    cc_verify = creditcard.json()
    cc_verify_id = cc_verify['id']

###submitting credit card info##
    paymentheaders = {
        'Origin': 'https://checkout.shopify.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.8',
        'Referer': 'https://checkout.shopify.com/'+storeID+'/checkouts/'+checkoutID,
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98 Safari/537.36'
    }
    paymentdata = {
        '_method': 'patch',
        'authenticity_token': auth_token,
        'checkout[buyer_accepts_marketing]': '1',
        'checkout[client_details][browser_height]': '979',
        'checkout[client_details][browser_width]': '631',
        'checkout[client_details][javascript_enabled]': '1',
        'checkout[credit_card][vault]': 'false',
        'checkout[different_billing_address]': 'false',
        'checkout[payment_gateway]': payment_gateaway,
        'checkout[total_price]': '1199',
        'complete': '1',
        'previous_step': 'payment_method',
        's': cc_verify_id,
        'step': '',
      }
    submitpayment = s.post(atc.url, data=paymentdata, headers=paymentheaders, allow_redirects=True)
    print(UTCtoEST(), submitpayment.status_code, submitpayment.url)