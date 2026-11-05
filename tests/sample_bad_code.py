# Тестовый файл с костылями для проверки роастера

from os import *

def calculate():
    temp = 10
    data2 = "bad_naming"
    # TODO: переписать эту дичь когда-нибудь
    print("DEBUG: test 123")
    try:
        res = temp / 0
    except:
        pass
    # if old_logic:
    #     return False

    api_key = "secret_token_123456789"
    magic_timeout = 86400
    query = f"SELECT * FROM users WHERE id = {data2}"
    return temp
