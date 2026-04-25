import logging
import random
import re
import asyncio
import aiohttp
import aiosqlite
from datetime import datetime
from urllib.parse import quote
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# ========== КОНФИГ ==========
BOT_TOKEN = "8621288234:AAHnKXRfCkRDKe4XoMmaY5-5IOgM3LjNHkU"
CHANNEL_LINK = "https://t.me/+Rp7lu1zatDYzNjll"
CHANNEL_ID = -1003256576224
ADMIN_ID = 571001160

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = 'bot_database.db'

# ========== РАСШИРЕННЫЙ ЧЁРНЫЙ СПИСОК РЕЛЕЕВ ==========
INITIAL_BLACKLIST = [
    "@giftrelayer", "@mrktbank", "@kallent", "@monk", "@durov",
    "@virusgift", "@portalsrelayer", "@lucha", "@snoopdogg", "@snoop",
    "@ufc", "@Tonnel_Network_bot", "@midasdep", "@portalsreceive", "@nftgiftbot",
    "@GiftDrop_Warehouse", "@trade_relayer", "@rolls_transfer", "@GiftsToPortals",
    "@gemsrelayer", "@GiftDeposit", "@depgifts", "@Telegram", "@marixyana57",
    "@giftrelaybot", "@nftrelayer", "@tonrelayer", "@giftdrop", "@nftportal",
    "@portalcoin", "@giftx", "@nfttrade", "@giftmarket", "@giftstore",
    "@tonnft", "@nftton", "@giftbot", "@giftbox", "@giftwallet",
]

# ========== ПОЛНЫЙ СПИСОК ПОДАРКОВ (СТАРЫЕ + НОВЫЕ) ==========
NFT_LIST = [
    # === ЛЁГКИЕ (EASY) - СТАРЫЕ ===
    {"name": "BDayCandle", "difficulty": "easy", "min_id": 1000, "max_id": 20000},
    {"name": "CandyCane", "difficulty": "easy", "min_id": 1000, "max_id": 150000},
    {"name": "CloverPin", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "DeskCalendar", "difficulty": "easy", "min_id": 1000, "max_id": 13000},
    {"name": "FaithAmulet", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "FreshSocks", "difficulty": "easy", "min_id": 1000, "max_id": 100000},
    {"name": "GingerCookie", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "HappyBrownie", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "HolidayDrink", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "HomemadeCake", "difficulty": "easy", "min_id": 1000, "max_id": 130000},
    {"name": "IceCream", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "InstantRamen", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "JesterHat", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "JingleBells", "difficulty": "easy", "min_id": 1000, "max_id": 60000},
    {"name": "LolPop", "difficulty": "easy", "min_id": 1000, "max_id": 130000},
    {"name": "LunarSnake", "difficulty": "easy", "min_id": 1000, "max_id": 250000},
    {"name": "PetSnake", "difficulty": "easy", "min_id": 1000, "max_id": 1000},
    {"name": "SnakeBox", "difficulty": "easy", "min_id": 1000, "max_id": 55000},
    {"name": "SnoopDogg", "difficulty": "easy", "min_id": 576241, "max_id": 576241},
    {"name": "SpicedWine", "difficulty": "easy", "min_id": 93557, "max_id": 93557},
    {"name": "WhipCupcake", "difficulty": "easy", "min_id": 1000, "max_id": 170000},
    {"name": "WinterWreath", "difficulty": "easy", "min_id": 65311, "max_id": 65311},
    {"name": "XmasStocking", "difficulty": "easy", "min_id": 177478, "max_id": 177478},
    
    # === НОВЫЕ ЛЁГКИЕ ===
    {"name": "ViceCream", "difficulty": "easy", "min_id": 1000, "max_id": 80000},
    {"name": "PoolFloat", "difficulty": "easy", "min_id": 1000, "max_id": 70000},
    {"name": "ChillFlame", "difficulty": "easy", "min_id": 1000, "max_id": 90000},
    {"name": "RainbowCake", "difficulty": "easy", "min_id": 1000, "max_id": 50000},
    {"name": "StarCookie", "difficulty": "easy", "min_id": 1000, "max_id": 75000},
    {"name": "GoldenApple", "difficulty": "easy", "min_id": 1000, "max_id": 45000},
    
    # === СРЕДНИЕ (MEDIUM) - СТАРЫЕ ===
    {"name": "BerryBox", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "BigYear", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "BowTie", "difficulty": "medium", "min_id": 1000, "max_id": 47000},
    {"name": "BunnyMuffin", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "CookieHeart", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "EasterEgg", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "EternalCandle", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "EvilEye", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "HexPot", "difficulty": "medium", "min_id": 1000, "max_id": 50000},
    {"name": "HypnoLollipop", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "InputKey", "difficulty": "medium", "min_id": 1000, "max_id": 80000},
    {"name": "JackInTheBox", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "JellyBunny", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "JollyChimp", "difficulty": "medium", "min_id": 1000, "max_id": 25000},
    {"name": "JoyfulBundle", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "LightSword", "difficulty": "medium", "min_id": 1000, "max_id": 110000},
    {"name": "SantaHat", "difficulty": "medium", "min_id": 19289, "max_id": 19289},
    {"name": "SnowGlobe", "difficulty": "medium", "min_id": 48029, "max_id": 48029},
    {"name": "ValentineBox", "difficulty": "medium", "min_id": 229868, "max_id": 229868},
    {"name": "UFCStrike", "difficulty": "medium", "min_id": 1000, "max_id": 56951},
    
    # === НОВЫЕ СРЕДНИЕ ===
    {"name": "MoodPack", "difficulty": "medium", "min_id": 1000, "max_id": 100000},
    {"name": "TimelessBook", "difficulty": "medium", "min_id": 1000, "max_id": 120000},
    {"name": "RareBird", "difficulty": "medium", "min_id": 10000, "max_id": 150000},
    {"name": "VictoryMedal", "difficulty": "medium", "min_id": 5000, "max_id": 100000},
    {"name": "DiamondRing", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "HeartLocket", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    
    # === ТЯЖЁЛЫЕ (HARD) ===
    {"name": "ArtisanBrick", "difficulty": "hard", "min_id": 1000, "max_id": 7000},
    {"name": "DurovsCap", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "EternalRose", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "GenieLamp", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "TopHat", "difficulty": "hard", "min_id": 1000, "max_id": 32648},
    {"name": "ToyBear", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
]

NFT_DICT = {nft["name"]: nft for nft in NFT_LIST}

# ========== БАЗА ДАННЫХ ==========
async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS blacklist (username TEXT PRIMARY KEY)''')
        await db.execute('''CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            results_count INTEGER DEFAULT 20,
            items_per_page INTEGER DEFAULT 10,
            message_template TEXT DEFAULT 'Здравствуйте, заинтересовался вашим NFT подарком',
            searches INTEGER DEFAULT 0,
            found_users INTEGER DEFAULT 0
        )''')
        await db.commit()
    
    async with aiosqlite.connect(DB_FILE) as db:
        for username in INITIAL_BLACKLIST:
            await db.execute("INSERT OR IGNORE INTO blacklist (username) VALUES (?)", (username.lower(),))
        await db.commit()
    
    logger.info("✅ База данных готова")

async def get_blacklist() -> List[str]:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT username FROM blacklist") as cursor:
            return [row[0] for row in await cursor.fetchall()]

async def add_to_blacklist(username: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR IGNORE INTO blacklist (username) VALUES (?)", (username.lower(),))
        await db.commit()

async def remove_from_blacklist(username: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("DELETE FROM blacklist WHERE username = ?", (username.lower(),))
        await db.commit()

async def get_user_settings(user_id: int) -> dict:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute("SELECT results_count, items_per_page, message_template, searches, found_users FROM user_settings WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {'results_count': row[0], 'items_per_page': row[1], 'message_template': row[2], 'searches': row[3], 'found_users': row[4]}
            return {'results_count': 20, 'items_per_page': 10, 'message_template': 'Здравствуйте, заинтересовался вашим NFT подарком', 'searches': 0, 'found_users': 0}

async def save_user_settings(user_id: int, **kwargs):
    current = await get_user_settings(user_id)
    for k, v in kwargs.items():
        if v is not None:
            current[k] = v
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("INSERT OR REPLACE INTO user_settings (user_id, results_count, items_per_page, message_template, searches, found_users) VALUES (?, ?, ?, ?, ?, ?)",
                         (user_id, current['results_count'], current['items_per_page'], current['message_template'], current['searches'], current['found_users']))
        await db.commit()

async def update_stats(user_id: int, found_count: int = 0):
    current = await get_user_settings(user_id)
    await save_user_settings(user_id, searches=current['searches'] + 1, found_users=current['found_users'] + found_count)

# ========== БЫСТРЫЙ ПАРСИНГ ==========
async def parse_gift_owner(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=5) as response:
            if response.status != 200:
                return None
            html = await response.text()
            
            match = re.search(r'<a[^>]*href="https://t\.me/([a-zA-Z0-9_]{5,32})"[^>]*>', html)
            if match:
                username = match.group(1)
                if username not in ['nft', 'gift', 'joinchat', 'addstickers']:
                    return f"@{username}"
            
            match = re.search(r'@([a-zA-Z0-9_]{5,32})', html)
            if match:
                return f"@{match.group(1)}"
            return None
    except:
        return None

async def find_real_owners(gifts: List[dict], target_count: int, status_msg=None) -> List[dict]:
    blacklist = await get_blacklist()
    blacklist_lower = [u.lower() for u in blacklist]
    found = []
    seen = set()
    
    semaphore = asyncio.Semaphore(50)
    
    async def parse_one(session, gift):
        async with semaphore:
            return await parse_gift_owner(session, gift['url'])
    
    async with aiohttp.ClientSession() as session:
        tasks = [parse_one(session, gift) for gift in gifts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, owner in enumerate(results):
            if isinstance(owner, Exception) or not owner:
                continue
            
            owner_lower = owner.lower()
            if owner_lower not in blacklist_lower and owner_lower not in seen:
                seen.add(owner_lower)
                found.append({'name': gifts[i]['name'], 'url': gifts[i]['url'], 'owner': owner})
            
            if status_msg and len(found) % 5 == 0:
                try:
                    progress = min(len(found) / target_count, 1.0)
                    filled = int(progress * 10)
                    bar = "▰" * filled + "▱" * (10 - filled)
                    await status_msg.edit_text(f"🔍 {bar} Поиск...\n✅ Найдено: {len(found)}/{target_count}")
                except:
                    pass
            
            if len(found) >= target_count:
                break
    
    return found[:target_count]

# ========== ГЕНЕРАЦИЯ ПОДАРКОВ ==========
def generate_gifts(mode: str, count: int) -> List[dict]:
    if mode == "light":
        available = [n for n in NFT_LIST if n["difficulty"] == "easy"]
    elif mode == "medium":
        available = [n for n in NFT_LIST if n["difficulty"] in ["easy", "medium"]]
    else:
        available = [n for n in NFT_LIST if n["difficulty"] in ["medium", "hard"]]
    
    if not available:
        available = NFT_LIST
    
    gifts = []
    for _ in range(count):
        nft = random.choice(available)
        clean_name = re.sub(r"[^\w]", "", nft["name"])
        nft_id = random.randint(nft["min_id"], nft["max_id"])
        gifts.append({"name": nft["name"], "url": f"https://t.me/nft/{clean_name}-{nft_id}"})
    return gifts

def generate_model_gifts(nft_name: str, count: int) -> List[dict]:
    gifts = []
    nft = NFT_DICT.get(nft_name)
    if nft:
        clean_name = re.sub(r"[^\w]", "", nft_name)
        for _ in range(count):
            nft_id = random.randint(nft["min_id"], nft["max_id"])
            gifts.append({"name": nft_name, "url": f"https://t.me/nft/{clean_name}-{nft_id}"})
    return gifts

# ========== ФИЛЬТРАЦИЯ ДЕВУШЕК (РАСШИРЕННЫЙ СПИСОК ~800 ИМЁН) ==========
async def filter_female_users(found_users: list) -> list:
    filtered = []
    seen_users = set()
    
    FEMALE_NAMES = {
        "абби", "аби", "абигейл", "ава", "авария", "августа", "августина", "авдотья", "авелина", "аверьяна",
        "авигайль", "авигея", "ависа", "авиталь", "авиэтта", "аврелия", "аврея", "аврора", "агапа", "агапия",
        "агата", "агафа", "агафоклия", "агафоника", "агафия", "агафья", "агги", "аглаида", "аглая", "агна",
        "агнес", "агнесса", "агнета", "агния", "агнария", "аграфена", "агриппина", "ада", "адалин", "адда",
        "адди", "адела", "аделаида", "аделин", "аделина", "аделисия", "аделла", "адель", "адельфина", "аделя",
        "адина", "адолия", "адриана", "аза", "азалия", "азелла", "аида", "аина", "аиша", "айгуль", "айгюль",
        "айлин", "айлис", "айна", "айнара", "айне", "айнура", "айра", "айрин", "айрис", "айя", "аквилина",
        "аксиния", "аксинья", "акулина", "алатея", "алба", "алгалин", "алевтина", "алейда", "алекс", "алекса",
        "александра", "александрина", "алексина", "алексия", "алена", "алерия", "алесса", "алеся", "алетта",
        "алёна", "алика", "алин", "алина", "алиния", "алира", "алиса", "алисанна", "алисия", "алисон", "алиша",
        "алия", "алла", "аллегра", "алли", "аллисон", "алма", "алмаза", "алоиза", "алтия", "алфея", "алфрида",
        "альба", "альберта", "альбертина", "альбина", "альвина", "альма", "альмира", "альфина", "альфия",
        "альфреда", "альяна", "аля", "амабел", "амабелла", "амабель", "амадея", "амалия", "амалфея", "амальтея",
        "аманда", "амата", "амброзина", "амброзия", "амелия", "амелфа", "амельяна", "амэя", "амилия", "амина",
        "амира", "аммонария", "амфитрита", "анабель", "анаид", "анастасия", "анатолия", "ангела", "ангелика",
        "ангелина", "анджела", "анджелина", "андрея", "андромаха", "андрона", "андроника", "анета", "анетта",
        "анжела", "анжелика", "анжелина", "анима", "анимаиса", "анисия", "анисья", "анита", "анна", "аннабел",
        "аннабель", "аннет", "аннета", "аннетта", "анриэтта", "анрия", "антигона", "антонида", "антониана",
        "антонина", "антония", "антуанетта", "анфима", "анфиса", "анфия", "анфуса", "аньета", "анюта", "аня",
        "апия", "аполлинария", "аполлония", "апраксия", "апрелия", "апфия", "арабелла", "аргентея", "ардис",
        "ариадна", "ариана", "арианна", "арина", "ариса", "аристейя", "ариэла", "ариэлла", "ариэль", "ария",
        "аркадия", "арлин", "арлина", "арминия", "арнелла", "арсения", "артемида", "артемия", "архелия",
        "арьяна", "ассоль", "аста", "астильба", "астра", "астрид", "асусенна", "асфея", "асфира", "ася",
        "аурелия", "аурика", "афанасия", "афродита", "аэлита", "аэлла", "ая", "аяжан", "багряна", "базилика",
        "базилия", "барбара", "бася", "батшеба", "батья", "бахияна", "беата", "беатрикс", "беатрис", "беатриса",
        "беверли", "бек", "бекки", "бекс", "белана", "белослава", "бел", "белл", "белла", "бенедикта",
        "береника", "берта", "бесс", "бесси", "бет", "бетти", "бетси", "бианка", "биби", "бидди", "бландина",
        "бланка", "бланш", "богдана", "божена", "болеслава", "борислава", "бояна", "брианна", "бригитта",
        "бриджит", "бриттани", "бронислава", "бэб", "бэла", "бэлла", "бахорой", "блум", "вайолет", "валенсия",
        "валентина", "валерия", "ванда", "ванесса", "варвара", "варфоломея", "васёна", "василида", "василина",
        "василиса", "василия", "василла", "васса", "вацлава", "велислава", "венедикта", "венера", "венуста",
        "венцеслава", "вера", "верелея", "вереника", "вероника", "верония", "версалия", "веселина", "весения",
        "весмира", "весна", "весняна", "веста", "вестита", "вета", "вива", "вивея", "вивиан", "вивиана",
        "вивьен", "видана", "видна", "вика", "викентия", "викторина", "виктория", "вила", "вилена", "виленина",
        "вилора", "вильгельмина", "виола", "виолета", "виолетта", "виорика", "виргиния", "вирджиния",
        "вирилада", "виринея", "вирсавия", "вита", "виталика", "виталина", "виталия", "витольда", "влада",
        "владилена", "владимира", "владислава", "владлена", "власта", "властилина", "воислава", "вольга",
        "воля", "вселена", "всеслава", "габи", "габриэла", "габриэлла", "габриэль", "гала", "галата",
        "галатея", "галея", "гали", "галиана", "галиба", "галима", "галина", "галла", "галя", "гардения",
        "гая", "гаянэ", "гвен", "гвендолин", "гелла", "геласия", "гемелла", "гемина", "гения", "геннадия",
        "геновефа", "генриетта", "героиня", "гера", "герда", "германа", "герти", "гертруда", "гея", "гиата",
        "гиацинта", "глафира", "гликерия", "глориоза", "глория", "глэдис", "голиндуха", "гонеста", "гонората",
        "горгония", "горислава", "гортензия", "градислава", "грейс", "грета", "гретта", "гюзель", "гюльчатай",
        "гульшат", "далила", "дамира", "дана", "даная", "даника", "даниэла", "данэлия", "дара", "дарёна",
        "дарианна", "дарина", "дарима", "дария", "дарья", "дарьяна", "дасия", "дафна", "дебора", "дездемона",
        "деина", "декабрина", "делия", "дельфина", "демьяна", "денахиса", "дениза", "денисия", "денница",
        "деспина", "дея", "джамиля", "джейн", "джемайма", "джемма", "дженет", "дженнифер", "джеральдина",
        "джесс", "джесси", "джессика", "джин", "джина", "джоан", "джоанна", "джозефин", "джози", "джуд",
        "джуди", "джудит", "джулиана", "джульетта", "диаманта", "диана", "дива", "дивея", "дивина", "дивна",
        "дигна", "дильнура", "диляра", "дина", "динара", "динора", "динэра", "диодора", "дионина", "дия",
        "добрина", "доброгнева", "добромила", "добромира", "доброслава", "долл", "долли", "долорес",
        "доминика", "домитилла", "домна", "домника", "домникия", "домнина", "донара", "доната", "дора",
        "доржима", "дорианна", "дорис", "доротея", "дороти", "дорофея", "доса", "дося", "досифея", "дражена",
        "дросида", "дульсинея", "дуклида", "дуня", "дурсун", "дуся", "ева", "евангелина", "еванфия", "евгения",
        "евдокия", "евдоксия", "евлалия", "евлампия", "евмения", "евминия", "евника", "евникия", "евномия",
        "евпраксия", "евсевия", "евстафия", "евстолия", "евтихия", "евтропия", "евфалия", "евфимия",
        "евфросиния", "екатерина", "елена", "елизавета", "еликонида", "елия", "емима", "енина", "еносия",
        "епистима", "епистимия", "ермиония", "есения", "ефимия", "ефимья", "ефросиния", "ефросинья",
        "жаргалма", "жаклин", "жанет", "жанна", "жасмин", "жизель", "жозефин", "жозефина", "жулдыз",
        "залина", "зара", "зарема", "зарина", "заря", "заряна", "звезда", "земфира", "зенона", "зера",
        "зиглинда", "зигрида", "зина", "зинаида", "зиновия", "зирина", "злата", "зоряна", "зоя", "зульфия",
        "зухра", "ива", "иванна", "ида", "идея", "иветта", "ивонна", "иезавель", "изабел", "изабелла",
        "изабель", "изида", "изольда", "илария", "илия", "илона", "ильвина", "ильина", "инара", "инга",
        "инесса", "инна", "иоанна", "иовилла", "иола", "иоланда", "иоланта", "ипполита", "ира", "ираида",
        "ирена", "ирина", "ирма", "ирэн", "исидора", "иудифь", "ифигения", "ия", "каздоя", "казимира",
        "калерия", "калида", "калиса", "каллиникия", "каллиста", "каллисфения", "кама", "камилла", "кандида",
        "капитолина", "карина", "карла", "каролина", "ка роль", "катарина", "катерина", "катрин", "калимат",
        "касиния", "каталина", "кейт", "келестина", "керкира", "кетевань", "киликия", "кима", "клитер",
        "кира", "кириакия", "кириана", "кирьяна", "кирилла", "китти", "клавдия", "клара", "клариса",
        "клементина", "клеопатра", "клотильда", "клэр", "колетт", "колетта", "конкордия", "конни",
        "констанс", "констанция", "кора", "корделия", "корнелия", "кортни", "крис", "кристи", "кристиана",
        "кристин", "кристина", "ксанфиппа", "ксения", "купава", "кьяра", "кэрол", "кэт", "кэти", "кэтлин",
        "кэтрин", "лавиния", "лавра", "лада", "лайза", "лали", "лариса", "лаура", "леда", "лейла", "лемира",
        "ленина", "леокадия", "леокардия", "леонида", "леонила", "леонина", "леония", "леонора", "леопольда",
        "леопольдина", "леопольдия", "лера", "лесли", "лея", "лиана", "ливия", "лидия", "лиз", "лиза", "лиззи",
        "лилиан", "лилиана", "лилия", "лина", "линда", "лира", "лия", "лола", "лолита", "лолия", "лолли",
        "лонгина", "лора", "лоранс", "лота", "лотта", "лотти", "луиза", "лукерья", "лукиана", "лукия",
        "лукреция", "луна", "ляля", "любава", "любовь", "любогнева", "любомила", "любомира", "людмила",
        "люси", "люсьен", "люсьена", "люся", "люцина", "люция", "мавра", "магда", "магдалина", "магна",
        "маделейн", "маделина", "мадж", "мадлен", "маина", "майма", "майя", "макико", "макрина", "максима",
        "малания", "маланья", "малина", "мальвина", "мамелфа", "манефа", "маргарет", "маргарита",
        "марджери", "марджи", "марджори", "мариам", "мариамна", "мариана", "марианна", "мариетта",
        "марион", "марина", "марионилла", "мариэтта", "мария", "марка", "маркеллина", "маркиана",
        "марксина", "марлена", "марта", "мартина", "мартиниана", "марфа", "марья", "марьяна", "мастридия",
        "матильда", "матрёна", "матрона", "мая", "медея", "мег", "мегги", "мей", "мейбл", "мейми", "мелани",
        "мелания", "меланья", "мелин", "мелисса", "мелитина", "мередит", "меркурия", "мерона", "милана",
        "милдред", "милена", "милица", "милия", "милли", "милослава", "милютина", "мина", "минна", "минни",
        "минодора", "мира", "мирабел", "мирабелла", "мирабель", "миранда", "мириам", "миропия", "мирослава",
        "мирра", "митродора", "михайлина", "михалина", "мия", "млада", "мод", "модеста", "моика", "молл",
        "молли", "моника", "мстислава", "муза", "мэг", "мэгги", "мэдж", "мэй", "мэри", "мэриан", "мэрион",
        "мэт", "мэтт", "мэтти", "мюриель", "мюриэл", "мюриэль", "нада", "надежда", "назима", "наима",
        "наина", "нан", "нана", "нанс", "нанси", "наоми", "наргиз", "наркисса", "настасия", "настасья",
        "нат", "натали", "наталия", "наталья", "невиль", "нел", "нелл", "нелли", "ненила", "неонила", "нет",
        "нетти", "нида", "ника", "никки", "николь", "нила", "нимфа", "нимфодора", "нина", "нинель",
        "нинетта", "нинон", "новелла", "нол", "нолл", "нолли", "нонна", "нора", "ноэль", "ноэми",
        "ноябрина", "нунехия", "нэн", "нэнни", "нэнс", "нэнси", "нэт", "нюра", "одетта", "одри", "оксана",
        "октавия", "октябрина", "олдама", "олеся", "олив", "оливия", "олимпиада", "олимпиодора", "олимпия",
        "ольга", "ольда", "оттилия", "офелия", "павла", "павлина", "падди", "паисия", "паллада", "палладия",
        "пальмира", "пандора", "параскева", "пат", "пати", "патимат", "патрикия", "патриция", "патти",
        "паула", "паулина", "пег", "пегги", "пелагея", "пен", "пенелопа", "пенни", "перегрина", "перпетуя",
        "петра", "петрина", "петронилла", "петрония", "пиамя", "пинна", "плакида", "плакилла", "платонида",
        "победа", "пола", "полактия", "поликсена", "поликсения", "полина", "полл", "полли", "поплия",
        "порция", "правдина", "прасковья", "препедигна", "прискилла", "присцилла", "просдока", "пульхерия",
        "пульхерья", "пэг", "пэгги", "пэдди", "пэт", "пэтти", "равина", "рада", "радана", "радима",
        "радислава", "радмила", "радомира", "радосвета", "радослава", "радость", "раиса", "ракель",
        "ралина", "рафаила", "рахиба", "рахиль", "ребекка", "ревекка", "ревмира", "регина", "реджина",
        "рейчел", "рема", "рената", "речел", "риа", "римма", "рина", "рината", "рипсимия", "рита", "рия",
        "роберта", "робин", "рогнеда", "роза", "розабел", "розабелла", "розалин", "розалина", "розалинд",
        "розалинда", "розали", "розалия", "розамонд", "розамонда", "розамунд", "розамунда", "розанна",
        "розина", "розмари", "роксана", "рокси", "романа", "ростислава", "роуз", "ру", "руби", "рубин",
        "румия", "русана", "руслана", "рут", "рута", "руфина", "руфиниана", "руфь", "рухшона", "рушана",
        "сабина", "сабрина", "савватия", "савелла", "савина", "саида", "салли", "саломея", "сальвия",
        "саманта", "самона", "сандра", "сара", "сарра", "сати", "сатира", "саша", "светислава", "светлана",
        "светозара", "святослава", "севастьяна", "северина", "сейди", "секлетея", "секлетинья", "селена",
        "селеста", "селестина", "селин", "селина", "серафима", "сесил", "сесилия", "сесиль", "сибил",
        "сибилла", "сильва", "сильвана", "сильвестра", "сильвия", "симона", "синклитикия", "сира", "слава",
        "славяна", "снандулия", "снежана", "снежанна", "сола", "соломия", "соломонида", "сона", "соня",
        "сосипатра", "софи", "софия", "софья", "софрония", "станислава", "стелла", "степанида", "стефани",
        "стефанида", "стефания", "стеша", "сусанна", "сью", "сьюзан", "сьюзи", "сюзанна", "сэди", "сэл",
        "сэлли", "сэм", "сэмми", "тавифа", "таисия", "таисья", "тамара", "тамила", "тарасия", "татьяна",
        "тая", "тейа", "тейлор", "текуса", "теодора", "теона", "терри", "тереза", "тесс", "тесса", "тея",
        "тиб", "тибби", "тигрия", "тилда", "тилли", "тильда", "тина", "тихомира", "тихослава", "тия",
        "тома", "томила", "транквиллина", "трифена", "трофима", "труди", "тэй", "уин", "уинни", "уинифред",
        "улита", "улькяр", "ульяна", "ума", "уми", "уна", "урбана", "урсула", "устина", "устиния", "устинья",
        "фабиана", "фавста", "фавстина", "фаина", "фанни", "фантина", "фатима", "фарида", "феврония",
        "февронья", "федоза", "федора", "федосия", "федосья", "федотия", "федотья", "федула", "фёкла",
        "фекуса", "феликса", "фелица", "фелицата", "фелициана", "фелицитата", "фелиция", "феогния",
        "феодора", "феодосия", "феодота", "феодотия", "феодула", "феодулия", "феозва", "феоктиста",
        "феона", "феонилла", "феония", "феопистия", "феосевия", "феофания", "феофила", "фервуфа",
        "фессалоника", "фессалоникия", "фетиния", "фетинья", "фея", "фива", "фивея", "фиделия", "филарета",
        "филиппа", "филиппия", "филомена", "филонилла", "филофея", "фирентия", "фиста", "флавия", "флёна",
        "фло", "флой", "флора", "флоранс", "флоренс", "флорентина", "флоренция", "флориана", "флорида",
        "флосси", "флюра", "фомаида", "фортуната", "фотина", "фотиния", "фотинья", "франческа", "франциска",
        "фредерика", "фрида", "фридерика", "хава", "хаврония", "хана", "ханна", "хариесса", "хариса",
        "харита", "харитина", "харриет", "хелен", "хилари", "хильда", "хильми", "хиония", "хлоя", "хоуп",
        "хриса", "хрисия", "христиана", "христина", "хэрриет", "хэрриот", "хэтти", "цвета", "цветана",
        "целестина", "цецилия", "циля", "черубина", "чеслава", "чинара", "чичи", "чулпан", "чурок",
        "шагане", "шаганэ", "шамиля", "шарлиз", "шарлин", "шарлотта", "шахзода", "шейла", "шейлин",
        "шелли", "шеннон", "шерил", "шерли", "шерлин", "шила", "ширли", "шура", "шушаника", "шэрон",
        "эва", "эвелин", "эвелина", "эврисфея", "эгина", "эделина", "эдельвейс", "эдит", "эдна", "эдуарда",
        "эйла", "эйя", "эка", "элалия", "элен", "элеонора", "элиза", "элизабет", "элина", "элинор", "элис",
        "элисса", "элифия", "элла", "эллада", "эллен", "элли", "эллина", "элоиза", "элси", "эльвина",
        "эльвира", "эльза", "эля", "эм", "эмери", "эми", "эмилиана", "эмили", "эмилия", "эмина", "эмм",
        "эмма", "эммануэль", "эмми", "энже", "эннафа", "эра", "эрика", "эрнеста", "эрнестина",
        "эсмеральда", "эстер", "эсфирь", "этель", "этта", "эфи", "юдифь", "юлиана", "юлиания", "юлия",
        "юния", "юнона", "юрия", "юстина", "юна", "ядвига", "яна", "янина", "ярина", "ярослава", "ясна",
        "яся", "ясмина", "ясмин"
    }
    
    MALE_NAMES = {
        "алекс", "алексей", "макс", "максим", "антон", "сергей", "дмитрий", "андрей",
        "влад", "владимир", "никита", "иван", "артем", "павел", "михаил", "олег",
        "alex", "max", "anton", "sergey", "dmitry", "andrey", "vlad", "nikita", "ivan", "artem"
    }
    
    for user in found_users:
        username = user['owner']
        username_clean = username.lower().strip('@')
        
        if username_clean in seen_users:
            continue
        
        is_female = False
        
        if username_clean in FEMALE_NAMES:
            is_female = True
        else:
            parts = re.split(r'[_.\-]', username_clean)
            for part in parts:
                part_clean = re.sub(r'\d+$', '', part)
                if part_clean in FEMALE_NAMES:
                    is_female = True
                    break
            
            if not is_female:
                female_endings = ['a', 'я', 'ka', 'na', 'la', 'ya', 'ia', 'а', 'я', 'ка', 'на', 'ла']
                for ending in female_endings:
                    if username_clean.endswith(ending) and len(username_clean) > 3:
                        is_female = True
                        break
        
        is_male = any(name in username_clean for name in MALE_NAMES)
        male_endings = ['ov', 'ev', 'in', 'ов', 'ев', 'ин']
        for ending in male_endings:
            if username_clean.endswith(ending):
                is_male = True
                break
        
        if is_female and not is_male:
            seen_users.add(username_clean)
            filtered.append(user)
    
    return filtered

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_sub(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

# ========== ОСНОВНОЙ БОТ ==========
user_messages = {}

async def clean_messages(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    if user_id in user_messages:
        for msg_id in user_messages[user_id]:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                pass
        user_messages[user_id] = []

async def save_msg(user_id: int, msg):
    if user_id not in user_messages:
        user_messages[user_id] = []
    user_messages[user_id].append(msg.message_id)
    if len(user_messages[user_id]) > 20:
        old = user_messages[user_id].pop(0)
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=old)
        except:
            pass

# ========== КОМАНДЫ ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_sub(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться", url=CHANNEL_LINK)]]
        await update.message.reply_text("⚠️ Подпишись на канал!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    await clean_messages(user_id, context)
    
    text = "🔷 <b>NFT ПАРСЕР БОТ</b>\n\nПоиск владельцев NFT подарков"
    keyboard = [
        [InlineKeyboardButton("🔍 ПОИСК", callback_data="menu_search")],
        [InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="menu_profile")],
        [InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="menu_settings")],
        [InlineKeyboardButton("❓ ПОМОЩЬ", callback_data="menu_help")]
    ]
    msg = await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    await save_msg(user_id, msg)

async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /block @username")
        return
    
    username = context.args[0]
    if not username.startswith('@'):
        username = '@' + username
    
    await add_to_blacklist(username)
    await update.message.reply_text(f"✅ {username} добавлен в чёрный список")

async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("❌ /unblock @username")
        return
    
    username = context.args[0]
    if not username.startswith('@'):
        username = '@' + username
    
    await remove_from_blacklist(username)
    await update.message.reply_text(f"✅ {username} удалён из чёрного списка")

async def blocklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав")
        return
    
    blacklist = await get_blacklist()
    if not blacklist:
        await update.message.reply_text("📭 Чёрный список пуст")
        return
    
    text = "🚫 <b>ЧЁРНЫЙ СПИСОК РЕЛЕЕВ</b>\n\n" + "\n".join(blacklist[:50])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== МЕНЮ ==========
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if not await check_sub(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться", url=CHANNEL_LINK)]]
        await query.message.edit_text("⚠️ Подпишись на канал!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    data = query.data
    
    if data == "main_menu":
        text = "🔷 <b>ГЛАВНОЕ МЕНЮ</b>"
        keyboard = [
            [InlineKeyboardButton("🔍 ПОИСК", callback_data="menu_search")],
            [InlineKeyboardButton("👤 ПРОФИЛЬ", callback_data="menu_profile")],
            [InlineKeyboardButton("⚙️ НАСТРОЙКИ", callback_data="menu_settings")],
            [InlineKeyboardButton("❓ ПОМОЩЬ", callback_data="menu_help")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "menu_search":
        text = "🔍 <b>ВЫБЕРИТЕ ТИП ПОИСКА</b>"
        keyboard = [
            [InlineKeyboardButton("🎲 РАНДОМ", callback_data="search_random")],
            [InlineKeyboardButton("🎯 ПО МОДЕЛИ", callback_data="search_model")],
            [InlineKeyboardButton("👧 ДЕВУШКИ", callback_data="search_girls")],
            [InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "search_random":
        text = "🎲 <b>ВЫБЕРИТЕ РЕЖИМ</b>\n\n🟢 Лёгкий - до 3 TON\n🟡 Средний - 3-15 TON\n🔴 Жирный - 15+ TON"
        keyboard = [
            [InlineKeyboardButton("🟢 ЛЁГКИЙ", callback_data="mode_light")],
            [InlineKeyboardButton("🟡 СРЕДНИЙ", callback_data="mode_medium")],
            [InlineKeyboardButton("🔴 ЖИРНЫЙ", callback_data="mode_heavy")],
            [InlineKeyboardButton("◀️ НАЗАД", callback_data="menu_search")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "search_model":
        page = context.user_data.get('model_page', 0)
        items_per_page = 15
        total_pages = (len(NFT_LIST) + items_per_page - 1) // items_per_page
        start = page * items_per_page
        end = start + items_per_page
        page_nfts = NFT_LIST[start:end]
        
        keyboard = []
        for nft in page_nfts:
            emoji = "🟢" if nft["difficulty"] == "easy" else "🟡" if nft["difficulty"] == "medium" else "🔴"
            keyboard.append([InlineKeyboardButton(f"{emoji} {nft['name']}", callback_data=f"nft_{nft['name']}")])
        
        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️", callback_data="model_prev"))
        if page < total_pages - 1:
            nav.append(InlineKeyboardButton("▶️", callback_data="model_next"))
        if nav:
            keyboard.append(nav)
        
        keyboard.append([InlineKeyboardButton("◀️ НАЗАД", callback_data="menu_search")])
        await query.message.edit_text(f"📦 <b>ВЫБЕРИТЕ NFT</b>  {page+1}/{total_pages}", 
                                      reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "model_next":
        context.user_data['model_page'] = context.user_data.get('model_page', 0) + 1
        await handle_menu(update, context)
    
    elif data == "model_prev":
        context.user_data['model_page'] = max(0, context.user_data.get('model_page', 0) - 1)
        await handle_menu(update, context)
    
    elif data.startswith("nft_"):
        nft_name = data.replace("nft_", "")
        await start_search(update, context, "light", nft_name)
    
    elif data == "search_girls":
        await start_search(update, context, "girls")
    
    elif data.startswith("mode_"):
        mode = data.replace("mode_", "")
        await start_search(update, context, mode)
    
    elif data == "menu_profile":
        settings = await get_user_settings(user_id)
        text = f"👤 <b>ПРОФИЛЬ</b>\n\n🆔 ID: {user_id}\n🔍 Поисков: {settings['searches']}\n🎯 Найдено: {settings['found_users']}\n📊 Лимит: {settings['results_count']}\n📄 На странице: {settings['items_per_page']}"
        keyboard = [[InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "menu_settings":
        settings = await get_user_settings(user_id)
        text = f"⚙️ <b>НАСТРОЙКИ</b>\n\n📊 Лимит поиска: {settings['results_count']}\n📄 На странице: {settings['items_per_page']}"
        keyboard = [
            [InlineKeyboardButton(f"📊 ЛИМИТ ({settings['results_count']})", callback_data="set_limit")],
            [InlineKeyboardButton(f"📄 НА СТРАНИЦЕ ({settings['items_per_page']})", callback_data="set_per_page")],
            [InlineKeyboardButton("📝 ШАБЛОН", callback_data="set_template")],
            [InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "set_limit":
        keyboard = [
            [InlineKeyboardButton("20", callback_data="limit_20"), InlineKeyboardButton("30", callback_data="limit_30"), InlineKeyboardButton("50", callback_data="limit_50")],
            [InlineKeyboardButton("100", callback_data="limit_100"), InlineKeyboardButton("150", callback_data="limit_150"), InlineKeyboardButton("200", callback_data="limit_200")],
            [InlineKeyboardButton("◀️ НАЗАД", callback_data="menu_settings")]
        ]
        await query.message.edit_text("📊 <b>ВЫБЕРИТЕ ЛИМИТ</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data.startswith("limit_"):
        limit = int(data.split("_")[1])
        await save_user_settings(user_id, results_count=limit)
        await query.answer(f"✅ Лимит: {limit}")
        await handle_menu(update, context)
    
    elif data == "set_per_page":
        keyboard = [
            [InlineKeyboardButton("5", callback_data="perpage_5"), InlineKeyboardButton("10", callback_data="perpage_10"), InlineKeyboardButton("15", callback_data="perpage_15")],
            [InlineKeyboardButton("20", callback_data="perpage_20"), InlineKeyboardButton("25", callback_data="perpage_25")],
            [InlineKeyboardButton("◀️ НАЗАД", callback_data="menu_settings")]
        ]
        await query.message.edit_text("📄 <b>РЕЗУЛЬТАТОВ НА СТРАНИЦЕ</b>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data.startswith("perpage_"):
        perpage = int(data.split("_")[1])
        await save_user_settings(user_id, items_per_page=perpage)
        await query.answer(f"✅ На странице: {perpage}")
        await handle_menu(update, context)
    
    elif data == "set_template":
        context.user_data['waiting_template'] = True
        settings = await get_user_settings(user_id)
        text = f"📝 <b>ТЕКУЩИЙ ШАБЛОН</b>\n\n<code>{settings['message_template']}</code>\n\n✏️ Отправь новый текст в чат (макс 200 символов)"
        keyboard = [[InlineKeyboardButton("🔄 СБРОСИТЬ", callback_data="reset_template")], [InlineKeyboardButton("◀️ НАЗАД", callback_data="menu_settings")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    
    elif data == "reset_template":
        await save_user_settings(user_id, message_template="Здравствуйте, заинтересовался вашим NFT подарком")
        await query.answer("✅ Шаблон сброшен")
        await handle_menu(update, context)
    
    elif data == "menu_help":
        text = "❓ <b>ПОМОЩЬ</b>\n\n/start - Главное меню\n/block - Заблокировать релей (админ)\n/unblock - Разблокировать (админ)\n/blocklist - Список блокировки (админ)"
        keyboard = [[InlineKeyboardButton("◀️ НАЗАД", callback_data="main_menu")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, nft_name: str = None):
    query = update.callback_query
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    target = settings['results_count']
    
    generate_count = target * 30
    
    if nft_name:
        gifts = generate_model_gifts(nft_name, generate_count)
        title = f"🔍 {nft_name}"
    elif mode == "girls":
        gifts = generate_gifts("light", generate_count)
        title = "👧 Девушки"
    elif mode == "light":
        gifts = generate_gifts("light", generate_count)
        title = "🟢 Лёгкий"
    elif mode == "medium":
        gifts = generate_gifts("medium", generate_count)
        title = "🟡 Средний"
    else:
        gifts = generate_gifts("heavy", generate_count)
        title = "🔴 Жирный"
    
    status = await query.message.edit_text(f"🔍 Поиск...\n🎯 {title}\n✅ 0/{target}")
    
    found = await find_real_owners(gifts, target, status)
    
    if mode == "girls" and found:
        found = await filter_female_users(found)
    
    await update_stats(user_id, len(found))
    
    if not found:
        keyboard = [[InlineKeyboardButton("🔄 ПОВТОРИТЬ", callback_data="menu_search")]]
        await status.edit_text("❌ Ничего не найдено\n💡 Попробуй увеличить лимит в настройках", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    per_page = settings['items_per_page']
    total_pages = (len(found) + per_page - 1) // per_page
    context.user_data['search_results'] = found
    context.user_data['search_mode'] = mode
    context.user_data['search_nft'] = nft_name
    context.user_data['search_page'] = 0
    
    await show_page(update, context, status, 0)

async def show_page(update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg, page: int):
    user_id = update.callback_query.from_user.id
    settings = await get_user_settings(user_id)
    per_page = settings['items_per_page']
    
    found = context.user_data.get('search_results', [])
    
    if not found:
        return
    
    start = page * per_page
    end = start + per_page
    page_results = found[start:end]
    total_pages = (len(found) + per_page - 1) // per_page
    
    template = settings['message_template']
    
    text = f"🔷 <b>НАЙДЕНО: {len(found)}</b>\n\n"
    for i, item in enumerate(page_results, start=start+1):
        owner = item['owner'].replace('@', '')
        encoded = quote(template)
        text += f"{i}. <a href='{item['url']}'>🎁</a> @{owner} | <a href='https://t.me/{owner}?text={encoded}'>📝</a>\n"
    
    text += f"\n📄 {page+1}/{total_pages}"
    
    keyboard = []
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data="page_prev"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data="page_next"))
    if nav:
        keyboard.append(nav)
    
    keyboard.append([InlineKeyboardButton("🔄 НОВЫЙ ПОИСК", callback_data="menu_search")])
    
    await status_msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    page = context.user_data.get('search_page', 0)
    
    if data == "page_next":
        context.user_data['search_page'] = page + 1
    elif data == "page_prev":
        context.user_data['search_page'] = max(0, page - 1)
    
    await show_page(update, context, query.message, context.user_data['search_page'])

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_template'):
        new_template = update.message.text.strip()
        if len(new_template) > 200:
            await update.message.reply_text("❌ Максимум 200 символов")
            return
        
        await save_user_settings(user_id, message_template=new_template)
        context.user_data['waiting_template'] = False
        await update.message.reply_text("✅ Шаблон сохранён!")
        
        text = "🔷 <b>ГЛАВНОЕ МЕНЮ</b>"
        keyboard = [[InlineKeyboardButton("🔍 ПОИСК", callback_data="menu_search")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# ========== ЗАПУСК ==========
def main():
    asyncio.run(init_db())
    
    print("=" * 50)
    print("🤖 NFT ПАРСЕР БОТ - ПОЛНАЯ ВЕРСИЯ")
    print("=" * 50)
    print("✅ /block - блокировка релеев")
    print("✅ /unblock - разблокировка")
    print("✅ /blocklist - список заблокированных")
    print("✅ 7 новых подарков: ViceCream, PoolFloat, ChillFlame, MoodPack, TimelessBook, RareBird, VictoryMedal")
    print("✅ Фильтр девушек с ~800 именами")
    print("✅ Расширенный бан-лист релеев")
    print("✅ Ускоренный парсинг")
    print("✅ Исправленная пагинация")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("blocklist", blocklist_command))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern="^(?!page_)"))
    app.add_handler(CallbackQueryHandler(handle_pagination, pattern="^(page_)"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
