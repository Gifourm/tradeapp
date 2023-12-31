from requests import post


def send_telegram(chat_id: int, message: str) -> None:
    token = "my_token"
    telegram_url = f"https://api.telegram.org/bot{token}/sendMessage"
    request = post(telegram_url, data={
        "chat_id": chat_id,
        "text": message
    })

    if request.status_code != 200:
        raise Exception("post_text error")
