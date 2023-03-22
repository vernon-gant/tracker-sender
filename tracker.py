import email
import imaplib
import logging.handlers
import os
import re
import smtplib
import ssl
import sys
from collections import namedtuple
from email.message import Message, EmailMessage

import prestashop_orders_client.exceptions as presta_exceptions
import pytesseract
from decouple import AutoConfig
from pdf2image import convert_from_path
from prestashop_orders_client import PrestaShopOrderClient
from prestashop_orders_client.utils import Order

config = AutoConfig(search_path=".env")

OFFICE_EMAIL = config('OFFICE_EMAIL', default='')
OFFICE_PASSWORD = config('OFFICE_PASSWORD', default='')
TARGET_EMAIL = config('TARGET_EMAIL', default='')
API_KEY = config('API_KEY', default='')
TESSERACT_PATH = config('TESSERACT_PATH', default='')
POPPLER_PATH = config('POPPLER_PATH', default='')

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

logger = logging.getLogger("tracker")
logger.setLevel(logging.INFO)
log_format = logging.Formatter(u'%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(lineno)d - %(message)s')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

CARGO_EMAIL = ("cargo@hunters.at", "pux@hunters.at")
SHIPPING_COMPANY_DETAILS = {"TNT": {
    "link": "https://www.tnt.com/express/de_at/site/home.html",
    "tracking_pattern": "(\\d{9,})",
    "verify_pattern": "Con No. Service"
}, "KURIER": {
    "link": "https://derkurier.de/sendungsverfolgung/?d-pt-state=search",
    "tracking_pattern": "Sendungsnummer: (\\d{11})",
    "verify_pattern": "\\|KURIER\\|"
}
}


def fetch_order(input_order_number: int) -> Order:
    order_client = PrestaShopOrderClient("shop.levus.co/LVS", API_KEY)
    try:
        result_order = order_client.get_order(input_order_number)
        logger.info(f"Found order {input_order_number} - {result_order}")
        return result_order
    except presta_exceptions.PrestaShopConnectionError:
        logger.exception("Connection failed")
        raise ConnectionError


def find_customers_label(order: dict):
    # this is done to make SSL connection with GMAIL
    imap_session = imaplib.IMAP4_SSL("imap.gmail.com")
    # logging the user in
    imap_session.login(OFFICE_EMAIL, OFFICE_PASSWORD)
    # calling function to check for email under this label
    imap_session.select('Inbox')
    logger.info("Started searching email with label...")
    result = find_label_text(imap_session, order)
    imap_session.close()
    imap_session.logout()
    return result


def find_label_text(imap_session: imaplib.IMAP4_SSL, order_data: Order) -> str:
    for cargo_email in CARGO_EMAIL:
        all_email_ids = search('FROM', cargo_email, imap_session)
        email_id_search_pool = str(all_email_ids[0]).removeprefix("b'").removesuffix("'").split()[::-1]  # [0:16]
        # Iterating over all emails
        for email_id in email_id_search_pool:
            typ, email_parts = imap_session.fetch(email_id, '(RFC822)')
            email_body = email_parts[0][1]
            email_body_content = email.message_from_bytes(email_body)
            for part in email_body_content.walk():
                if valid_label(part):
                    file_name = part.get_filename()
                    with open(file_name, "wb") as f:
                        f.write(part.get_payload(decode=True))
                    text = extract_text_from_label(file_name)
                    os.remove(file_name)
                    if is_customers_label(order_data, text):
                        logger.info("Label for order " + str(order_data) + " found!")
                        return text
    logger.info("Label for user " + str(order_data) + " not found...")
    return None


def search(key, value, imap_session: imaplib.IMAP4_SSL) -> tuple:
    result, data = imap_session.search(None, key, '"{}"'.format(value))
    return data


def valid_label(part: Message):
    return part.get('Content-Type').find("pdf") != -1 and \
           (part.get_filename().lower().startswith("cargo@hunters.at") or
            part.get_filename().lower().find("levus") != -1)


def is_customers_label(order: Order, text: str) -> bool:
    return sum(list(map(lambda value: 1 if text.find(str(value)) != -1 else 0, order._asdict().values()))) > 3


def extract_text_from_label(file_name: str) -> str:
    converted_pdf = convert_from_path(file_name, 500, poppler_path=POPPLER_PATH).pop(0)
    return pytesseract.image_to_string(converted_pdf)


def process_label(label: str) -> namedtuple:
    ShippingInfo = namedtuple("ShippingInfo", "company tracking link")
    company, tracking, link = "", "", ""
    if re.search(SHIPPING_COMPANY_DETAILS['KURIER']['verify_pattern'], label):
        company = "KURIER"
    elif re.search(SHIPPING_COMPANY_DETAILS['TNT']['verify_pattern'], label):
        company = "TNT"
    match company:
        case "TNT":
            tracking = re.search(SHIPPING_COMPANY_DETAILS['TNT']['tracking_pattern'], label).group(1)
            link = SHIPPING_COMPANY_DETAILS['TNT']['link']
        case "KURIER":
            tracking = re.search(SHIPPING_COMPANY_DETAILS['KURIER']['tracking_pattern'], label).group(1)
            link = SHIPPING_COMPANY_DETAILS['KURIER']['link']
    result = ShippingInfo(company, tracking, link)
    logger.info("Label info : " + str(result))
    return result


def send_email(order: Order, shipping_details: namedtuple, email_to_send: str):
    logger.info(f"Started computing email for {order}")
    email_text = f'Dear {order.first_name},\n\n' \
                 f'A great big thank you for your recent purchase!\n\n' \
                 f'Your order has been already handed over to our delivery partner - {shipping_details.company}! ' \
                 f'You can track your parcel at : {shipping_details.link}\n\n' \
                 f'Tracking ID:  {shipping_details.tracking}\n\n' \
                 f'We hope you enjoy your new item!\n\n' \
                 f'Best wishes,\n\n' \
                 f'Levus Team\n\n' \
                 f'{order.email}'
    try:
        em = EmailMessage()
        em['From'], em['To'], em['Subject'] = OFFICE_EMAIL, email_to_send, "Levus parcel tracking"
        em.set_content(email_text)
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(OFFICE_EMAIL, OFFICE_PASSWORD)
            smtp.sendmail(OFFICE_EMAIL, email_to_send, em.as_string())
        logger.info("Email sent!")
    except smtplib.SMTPException:
        logger.info("Email not sent...")


def send_tracking(order_number: int, target_email: str) -> str:
    order = fetch_order(order_number)
    shipping_label = find_customers_label(order)
    if shipping_label:
        shipping_info = process_label(shipping_label)
        send_email(order, shipping_info, target_email)
    else:
        logger.info("Label not found...")


def read_order_numbers_from_user():
    order_numbers = []
    while True:
        order_number = input("Enter order number: ")
        if order_number == "":
            break
        order_numbers.append(int(order_number))
    return order_numbers


if __name__ == '__main__':
    order_number = read_order_numbers_from_user()
    for order in order_number:
        send_tracking(order, TARGET_EMAIL)
