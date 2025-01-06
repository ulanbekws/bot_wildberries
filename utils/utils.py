import logging
import json

from typing import Dict, Any

import requests

logging.basicConfig(level=logging.INFO)

CONFIG_FILE = "config.json"


def validate_api_key(api_key: str) -> Dict[str, Any]:
    url = f"https://common-api.wildberries.ru/ping"
    headers = {"Authorization": f"Bearer {api_key}"}  # production
    print("valid_api_key_input", api_key)
    response_data = {}
    try:
        response = requests.get(url, headers=headers)
        response_data["status_code"] = response.status_code

        if response.status_code == 200:
            response_data["message"] = "Ok"
        elif response.status_code == 401:
            response_data["message"] = "Не получилось авторизоваться, у вас неправильный токен!"
        elif response.status_code == 429:
            response_data["message"] = "Слишком много запросов"
    except requests.RequestException as e:
        logging.error(f"Ошибка при проверке API ключа в валид: {e}")
        response_data["message"] = f"Ошибка подключения {e}"
        response_data["status_code"] = 500

    return response_data


def load_config():
    try:
        with open(CONFIG_FILE, 'r') as file:
            data = json.load(file)
            if isinstance(data, list) and all(isinstance(shop, dict) and "api_key" in shop and "name_shop" in shop for shop in data):
                return data
            else:
                print("Ошибка: Данные в config.json имеют неправильный формат.")
                return []
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print("Ошибка: Некорректный формат JSON.")
        return []


def save_config(data):
    config_list = load_config()


    if isinstance(data, dict):
        if any(shop.get("api_key") == data["api_key"] for shop in config_list):
            print(f"Магазин с API ключом {data['api_key']} уже существует.")
            return 409
        config_list.append(data)
    if isinstance(data, list):
        config_list = data

    with open(CONFIG_FILE, 'w') as file:
        json.dump(config_list, file, indent=4)

