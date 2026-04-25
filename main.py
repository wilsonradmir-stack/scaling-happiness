import logging
import random
import re
import asyncio
import aiohttp
import aiosqlite
from urllib.parse import quote
from typing import List, Optional, Set
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

# ========== КОНФИГ (ЗАМЕНИ НА СВОИ) ==========
BOT_TOKEN = "8621288234:AAHnKXRfCkRDKe4XoMmaY5-5IOgM3LjNHkU"
CHANNEL_LINK = "https://t.me/+Rp7lu1zatDYzNjll"
CHANNEL_ID = -1003256576224
ADMIN_ID = 571001160

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = 'bot_database.db'

# ========== ЗАГРУЗКА ИЗ ФАЙЛОВ ==========
def load_blacklist_from_file() -> List[str]:
    try:
        with open('blacklist.txt', 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        logger.warning("Файл blacklist.txt не найден")
        return ["@giftrelayer"]

async def load_female_names() -> Set[str]:
    try:
        with open('female_names.txt', 'r', encoding='utf-8') as f:
            return {line.strip().lower() for line in f if line.strip()}
    except FileNotFoundError:
        logger.warning("Файл female_names.txt не найден")
        return {"анна", "аня", "мария"}

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
    
    for username in load_blacklist_from_file():
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("INSERT OR IGNORE INTO blacklist (username) VALUES (?)", (username,))
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

# ========== СПИСОК ПОДАРКОВ ==========
NFT_LIST = [
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
    {"name": "ViceCream", "difficulty": "easy", "min_id": 1000, "max_id": 80000},
    {"name": "PoolFloat", "difficulty": "easy", "min_id": 1000, "max_id": 70000},
    {"name": "ChillFlame", "difficulty": "easy", "min_id": 1000, "max_id": 90000},
    {"name": "MoodPack", "difficulty": "medium", "min_id": 1000, "max_id": 100000},
    {"name": "TimelessBook", "difficulty": "medium", "min_id": 1000, "max_id": 120000},
    {"name": "RareBird", "difficulty": "medium", "min_id": 10000, "max_id": 150000},
    {"name": "VictoryMedal", "difficulty": "medium", "min_id": 5000, "max_id": 100000},
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
    {"name": "LushBouquet", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "MousseCake", "difficulty": "medium", "min_id": 119126, "max_id": 119126},
    {"name": "PartySparkler", "difficulty": "medium", "min_id": 161722, "max_id": 161722},
    {"name": "RestlessJar", "difficulty": "medium", "min_id": 1000, "max_id": 23000},
    {"name": "SantaHat", "difficulty": "medium", "min_id": 19289, "max_id": 19289},
    {"name": "SnoopCigar", "difficulty": "medium", "min_id": 1000, "max_id": 60000},
    {"name": "SnowGlobe", "difficulty": "medium", "min_id": 48029, "max_id": 48029},
    {"name": "SnowMittens", "difficulty": "medium", "min_id": 64057, "max_id": 64057},
    {"name": "SpringBasket", "difficulty": "medium", "min_id": 140160, "max_id": 140160},
    {"name": "SpyAgaric", "difficulty": "medium", "min_id": 84274, "max_id": 84274},
    {"name": "StarNotepad", "difficulty": "medium", "min_id": 1000, "max_id": 25000},
    {"name": "StellarRocket", "difficulty": "medium", "min_id": 1000, "max_id": 35000},
    {"name": "SwagBag", "difficulty": "medium", "min_id": 1000, "max_id": 5000},
    {"name": "TamaGadget", "difficulty": "medium", "min_id": 95205, "max_id": 95205},
    {"name": "ValentineBox", "difficulty": "medium", "min_id": 229868, "max_id": 229868},
    {"name": "WitchHat", "difficulty": "medium", "min_id": 1000, "max_id": 7000},
    {"name": "UFCStrike", "difficulty": "medium", "min_id": 1000, "max_id": 56951},
    {"name": "ArtisanBrick", "difficulty": "hard", "min_id": 1000, "max_id": 7000},
    {"name": "AstralShard", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "BondedRing", "difficulty": "hard", "min_id": 1000, "max_id": 3000},
    {"name": "CupidCharm", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "DiamondRing", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "DurovsCap", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "EternalRose", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "FlyingBroom", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "GemSignet", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "GenieLamp", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "GustalBall", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "HeartLocket", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "HeroicHelmet", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "IonGem", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "IonicDryer", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "KissedFrog", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "LootBag", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "LoveCandle", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "LovePotion", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "LowRider", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "MadPumpkin", "difficulty": "hard", "min_id": 96227, "max_id": 96227},
    {"name": "MagicPotion", "difficulty": "hard", "min_id": 4764, "max_id": 4764},
    {"name": "MightyArm", "difficulty": "hard", "min_id": 150000, "max_id": 150000},
    {"name": "MiniOscar", "difficulty": "hard", "min_id": 4764, "max_id": 4764},
    {"name": "NailBracelet", "difficulty": "hard", "min_id": 119126, "max_id": 119126},
    {"name": "NekoHelmet", "difficulty": "hard", "min_id": 15431, "max_id": 15431},
    {"name": "PerfumeBottle", "difficulty": "hard", "min_id": 151632, "max_id": 151632},
    {"name": "PreciousPeach", "difficulty": "hard", "min_id": 2981, "max_id": 2981},
    {"name": "RecordPlayer", "difficulty": "hard", "min_id": 554, "max_id": 554},
    {"name": "ScaredCat", "difficulty": "hard", "min_id": 8029, "max_id": 8029},
    {"name": "SharpTongue", "difficulty": "hard", "min_id": 1000, "max_id": 16430},
    {"name": "SignetRing", "difficulty": "hard", "min_id": 1000, "max_id": 16430},
    {"name": "SkullFlower", "difficulty": "hard", "min_id": 1000, "max_id": 21428},
    {"name": "SkyStilettos", "difficulty": "hard", "min_id": 1000, "max_id": 47465},
    {"name": "SleighBell", "difficulty": "hard", "min_id": 1000, "max_id": 48029},
    {"name": "SwissWatch", "difficulty": "hard", "min_id": 1000, "max_id": 25121},
    {"name": "TopHat", "difficulty": "hard", "min_id": 1000, "max_id": 32648},
    {"name": "ToyBear", "difficulty": "hard", "min_id": 1000, "max_id": 60000},
    {"name": "TrappedHeart", "difficulty": "hard", "min_id": 1000, "max_id": 24656},
    {"name": "VintageCigar", "difficulty": "hard", "min_id": 1000, "max_id": 18000},
    {"name": "VoodooDoll", "difficulty": "hard", "min_id": 1000, "max_id": 26658}
]

NFT_DICT = {nft["name"]: nft for nft in NFT_LIST}

# ========== БЫСТРЫЙ ПАРСИНГ (ОПТИМИЗИРОВАННЫЙ) ==========
async def parse_gift_owner(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=1.5) as response:
            if response.status != 200:
                return None
            html = await response.text()
            match = re.search(r't\.me/([a-zA-Z0-9_]{5,32})', html)
            if match:
                username = match.group(1)
                if username not in ['nft', 'gift', 'joinchat', 'addstickers']:
                    return f"@{username}"
            return None
    except:
        return None

async def find_real_owners_parallel(gifts: list, target_count: int, title: str, status_message=None) -> list:
    blacklist = await get_blacklist()
    blacklist_lower = [u.lower() for u in blacklist]
    found = []
    seen_users = set()
    
    semaphore = asyncio.Semaphore(200)
    
    async def parse_with_semaphore(session, gift):
        async with semaphore:
            return await parse_gift_owner(session, gift['url'])
    
    async with aiohttp.ClientSession() as session:
        if status_message:
            try:
                await status_message.edit_text(
                    f"🎯 {title}\n🔍 Поиск... 0/{target_count}",
                    parse_mode=ParseMode.HTML
                )
            except:
                pass
        
        tasks = [parse_with_semaphore(session, gift) for gift in gifts]
        
        for coro in asyncio.as_completed(tasks):
            owner = await coro
            if not owner:
                continue
            
            if owner.lower() not in blacklist_lower and owner.lower() not in seen_users:
                seen_users.add(owner.lower())
                # Находим оригинальный подарок (можно оптимизировать)
                for gift in gifts:
                    if gift['url'] in str(owner):  # упрощённо
                        found.append({'name': gift['name'], 'url': gift['url'], 'owner': owner})
                        break
            
            if status_message and len(found) % 5 == 0:
                try:
                    await status_message.edit_text(f"🎯 {title}\n🔍 Поиск... {len(found)}/{target_count}")
                except:
                    pass
            
            if len(found) >= target_count:
                break
    
    return found[:target_count]

# ========== ГЕНЕРАЦИЯ ПОДАРКОВ ==========
def generate_random_gifts(mode="light", count=20):
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

def generate_girls_gifts(count=20):
    easy_nfts = [n for n in NFT_LIST if n["difficulty"] == "easy"]
    medium_nfts = [n for n in NFT_LIST if n["difficulty"] == "medium"]
    available_nfts = easy_nfts + medium_nfts
    gifts = []
    for _ in range(count):
        nft = random.choice(available_nfts)
        clean_name = re.sub(r"[^\w]", "", nft["name"])
        nft_id = random.randint(nft["min_id"], nft["max_id"])
        gifts.append({"name": nft["name"], "url": f"https://t.me/nft/{clean_name}-{nft_id}"})
    return gifts

def generate_model_gifts(nft_name, count=20):
    gifts = []
    clean_name = re.sub(r"[^\w]", "", nft_name)
    nft = NFT_DICT.get(nft_name)
    if nft:
        for _ in range(count):
            nft_id = random.randint(nft["min_id"], nft["max_id"])
            gifts.append({"name": nft_name, "url": f"https://t.me/nft/{clean_name}-{nft_id}"})
    return gifts

# ========== ФИЛЬТРАЦИЯ ДЕВУШЕК ==========
async def filter_female_users(found_users: list, status_msg=None) -> list:
    female_names = await load_female_names()
    
    MALE_ENDINGS = ('ov', 'ev', 'in', 'ов', 'ев', 'ин')
    FEMALE_ENDINGS = ('a', 'я', 'ka', 'na', 'la', 'ya', 'ia', 'а', 'я', 'ка', 'на', 'ла')
    
    filtered = []
    seen = set()
    
    for user in found_users:
        username = user['owner'].lower().strip('@')
        
        if username in seen:
            continue
        
        parts = re.split(r'[_.\-]', username)
        name_part = parts[0] if parts else username
        name_part = re.sub(r'\d+$', '', name_part)
        
        is_female = name_part in female_names
        
        if not is_female:
            for ending in FEMALE_ENDINGS:
                if username.endswith(ending) and len(username) > 4:
                    is_female = True
                    break
        
        is_male = any(username.endswith(ending) for ending in MALE_ENDINGS)
        
        if is_female and not is_male:
            seen.add(username)
            filtered.append(user)
        
        if status_msg and len(filtered) % 10 == 0 and len(filtered) > 0:
            try:
                await status_msg.edit_text(f"👧 Найдено девушек: {len(filtered)}")
            except:
                pass
    
    return filtered

# ========== ПРОВЕРКА ПОДПИСКИ ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status not in ["left", "kicked"]
    except:
        return False

async def require_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        await show_subscription_required(update, context)
        return False
    return True

async def show_subscription_required(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_LINK)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = "⚠️ Для использования бота подпишитесь на канал!"
    
    if update.callback_query:
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup)
    else:
        await update.message.reply_text(message, reply_markup=reply_markup)

# ========== ХРАНИЛИЩЕ ==========
last_message_ids = {}
search_cache = {}

async def delete_previous_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in last_message_ids:
        for msg_id in last_message_ids[user_id]:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            except:
                pass
        last_message_ids[user_id] = []

async def save_message_id(update: Update, message):
    user_id = update.effective_user.id
    if user_id not in last_message_ids:
        last_message_ids[user_id] = []
    last_message_ids[user_id].append(message.message_id)
    if len(last_message_ids[user_id]) > 30:
        old_id = last_message_ids[user_id].pop(0)
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=old_id)
        except:
            pass

# ========== ГЛАВНОЕ МЕНЮ ==========
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = f"🔷 Привет, @{user.username or 'user'}! Это парсер для поиска мамонтов."
    keyboard = [
        [InlineKeyboardButton("🔍 Поиск NFT", callback_data="menu_search")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="menu_profile")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton("🆘 Поддержка", callback_data="menu_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await delete_previous_messages(update, context)
        sent = await update.message.reply_text(text, reply_markup=reply_markup)
        await save_message_id(update, sent)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = await get_user_settings(user_id)
    context.user_data['results_count'] = settings['results_count']
    context.user_data['items_per_page'] = settings['items_per_page']
    
    if not await check_subscription(user_id, context):
        keyboard = [[InlineKeyboardButton("📢 Подписаться", url=CHANNEL_LINK)]]
        await update.message.reply_text("⚠️ Подпишись на канал!", reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    text = """🔷 СПРАВКА ПО БОТУ

⌨️ КОМАНДЫ:
/start - Начать работу
/help - Справка
/status - Статус
/block @username - Заблокировать релей (админ)
/unblock @username - Разблокировать (админ)
/blocklist - Список заблокированных (админ)"""
    await update.message.reply_text(text)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    user_id = update.effective_user.id
    subscribed = await check_subscription(user_id, context)
    settings = await get_user_settings(user_id)
    text = f"""🔷 ВАШ СТАТУС

📊 Подписка: {'✅ В КАНАЛЕ' if subscribed else '❌ НЕТ'}
🔍 Всего поисков: {settings['searches']}
🎯 Найдено пользователей: {settings['found_users']}"""
    await update.message.reply_text(text)

# ========== АДМИН-КОМАНДЫ ==========
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
    await update.message.reply_text(f"✅ {username} добавлен")

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
    await update.message.reply_text(f"✅ {username} удалён")

async def blocklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Нет прав")
        return
    blacklist = await get_blacklist()
    if not blacklist:
        await update.message.reply_text("📭 Чёрный список пуст")
        return
    text = "🚫 <b>ЧЁРНЫЙ СПИСОК</b>\n\n" + "\n".join(blacklist[:50])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ========== МЕНЮ ПОИСКА ==========
async def show_search_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """🔷 Выберите тип поиска:

🎲 Рандом поиск
🔍 Поиск по модели
👧 Поиск девушек"""
    
    keyboard = [
        [InlineKeyboardButton("🎲 Рандом поиск", callback_data="search_random")],
        [InlineKeyboardButton("🔍 Поиск по модели", callback_data="search_model")],
        [InlineKeyboardButton("👧 Поиск девушек", callback_data="search_girls")],
        [InlineKeyboardButton("🔷 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup)

async def show_modes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """🔷 Выберите режим:

🟢 Лёгкий (до 3 TON)
🟡 Средний (3-15 TON)
🔴 Жирный (15+ TON)"""
    keyboard = [
        [InlineKeyboardButton("🟢 Лёгкий", callback_data="mode_light")],
        [InlineKeyboardButton("🟡 Средний", callback_data="mode_medium")],
        [InlineKeyboardButton("🔴 Жирный", callback_data="mode_heavy")],
        [InlineKeyboardButton("🔷 Назад", callback_data="menu_search")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup)

# ========== ПОКАЗ РЕЗУЛЬТАТОВ ==========
async def show_paginated_results(message, found, mode, nft_name, page, title, context, is_girls=False):
    settings = await get_user_settings(message.chat.id)
    items_per_page = settings['items_per_page']
    
    total_pages = (len(found) + items_per_page - 1) // items_per_page
    start = (page - 1) * items_per_page
    end = min(start + items_per_page, len(found))
    page_results = found[start:end]
    
    message_template = settings['message_template']
    
    mode_names = {"light": "🟢 Лёгкий", "medium": "🟡 Средний", "heavy": "🔴 Жирный", "girls": "👧 Девушки"}
    display_title = mode_names.get(mode, title or "Поиск")
    
    if is_girls:
        text = f"🔷 <b>Найдено девушек: {len(found)}</b>\n\n"
    else:
        text = f"🔷 <b>Найдено в режиме «{display_title}»: {len(found)}</b>\n\n"
    
    for i, item in enumerate(page_results, start=start+1):
        clean_owner = item['owner'][1:] if item['owner'].startswith('@') else item['owner']
        encoded_text = quote(message_template)
        gift_url = item['url']
        write_url = f"https://t.me/{clean_owner}?text={encoded_text}"
        text += f"{i}. <a href=\"{gift_url}\">🎁</a> @{clean_owner} | <a href=\"{write_url}\">📝</a>\n"
    
    text += f"\n📄 Страница {page}/{total_pages}"
    
    keyboard = []
    if total_pages > 1:
        nav = []
        if page > 1:
            nav.append(InlineKeyboardButton("◀️", callback_data=f"results_page_{mode}_{page-1}_{nft_name or ''}_{is_girls}"))
        nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
        if page < total_pages:
            nav.append(InlineKeyboardButton("▶️", callback_data=f"results_page_{mode}_{page+1}_{nft_name or ''}_{is_girls}"))
        keyboard.append(nav)
    
    if is_girls:
        keyboard.append([InlineKeyboardButton("👧 Ещё поиск", callback_data="search_girls")])
    elif nft_name:
        keyboard.append([InlineKeyboardButton("🔄 Ещё", callback_data=f"more_{mode}_{nft_name}")])
    else:
        keyboard.append([InlineKeyboardButton(f"🎲 Ещё {display_title}", callback_data=f"start_search_{mode}")])
    
    keyboard.append([InlineKeyboardButton("🎲 Новый поиск", callback_data="search_random")])
    keyboard.append([InlineKeyboardButton("🔷 Главное меню", callback_data="main_menu")])
    
    try:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Ошибка: {e}")

# ========== ОСНОВНОЙ ПОИСК ==========
async def show_search_results(update: Update, context, mode, nft_name=None, page=1, is_girls=False):
    query = update.callback_query
    user_id = query.from_user.id
    
    settings = await get_user_settings(user_id)
    target_count = settings['results_count']
    
    cache_key = f"{user_id}_{mode}_{nft_name or ''}_{is_girls}"
    
    if cache_key in search_cache and page != 1:
        found = search_cache[cache_key]
        await show_paginated_results(query.message, found, mode, nft_name, page, None, context, is_girls)
        return
    
    # ОПТИМИЗАЦИЯ: генерируем в 8 раз больше (было 50)
    generate_count = target_count * 8
    
    if is_girls:
        title = "👧 Поиск девушек"
        gifts = generate_girls_gifts(generate_count)
    elif nft_name:
        title = f"🔍 {nft_name}"
        gifts = generate_model_gifts(nft_name, generate_count)
    elif mode == "light":
        title = "🟢 Лёгкий"
        gifts = generate_random_gifts("light", generate_count)
    elif mode == "medium":
        title = "🟡 Средний"
        gifts = generate_random_gifts("medium", generate_count)
    else:
        title = "🔴 Жирный"
        gifts = generate_random_gifts("heavy", generate_count)
    
    status_msg = await query.message.edit_text(
        f"🎯 {title}\n🔍 Поиск... 0/{target_count}",
        parse_mode=ParseMode.HTML
    )
    
    await asyncio.sleep(0.2)
    
    # Убрал добивку (attempts) для скорости
    found = await find_real_owners_parallel(gifts, target_count, title, status_msg)
    
    if is_girls and found:
        try:
            await status_msg.edit_text(f"👧 Фильтрация девушек...")
        except:
            pass
        found = await filter_female_users(found, status_msg)
        await update_stats(user_id, len(found))
    else:
        await update_stats(user_id, len(found))
    
    if len(found) > target_count:
        found = found[:target_count]
    
    search_cache[cache_key] = found
    
    if not found:
        keyboard = [[InlineKeyboardButton("🔄 Попробовать снова", callback_data="search_random")]]
        try:
            await status_msg.edit_text("❌ Ничего не найдено.\n💡 Попробуйте увеличить лимит", reply_markup=InlineKeyboardMarkup(keyboard))
        except:
            pass
        return
    
    await show_paginated_results(status_msg, found, mode, nft_name, page, title, context, is_girls)

# ========== МЕНЮ ВЫБОРА МОДЕЛИ ==========
async def show_model_selection(update: Update, context: ContextTypes.DEFAULT_TYPE, page=1):
    query = update.callback_query
    items_per_page = 10
    total_pages = (len(NFT_LIST) + items_per_page - 1) // items_per_page
    start = (page - 1) * items_per_page
    end = min(start + items_per_page, len(NFT_LIST))
    page_nfts = NFT_LIST[start:end]
    keyboard = []
    for nft in page_nfts:
        emoji = "🟢" if nft["difficulty"] == "easy" else "🟡" if nft["difficulty"] == "medium" else "🔴"
        keyboard.append([InlineKeyboardButton(f"{emoji} {nft['name']}", callback_data=f"select_model_{nft['name']}")])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"model_page_{page-1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"model_page_{page+1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔷 Назад", callback_data="menu_search")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"🔗 Выберите NFT:\n\n{page}/{total_pages}"
    await query.message.edit_text(text, reply_markup=reply_markup)

# ========== ПРОФИЛЬ ==========
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    text = f"""🔷 <b>ПРОФИЛЬ</b>

🆔 ID: {user_id}
👤 @{query.from_user.username or 'unknown'}

📊 Статистика
🔍 Поисков: {settings['searches']}
🎯 Найдено: {settings['found_users']}

⚙️ Настройки
📊 Лимит: {settings['results_count']}
📄 На странице: {settings['items_per_page']}"""
    
    keyboard = [[InlineKeyboardButton("🔷 Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# ========== НАСТРОЙКИ ==========
async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    
    text = f"""🔷 <b>НАСТРОЙКИ</b>

📊 Лимит: {settings['results_count']}
📄 На странице: {settings['items_per_page']}"""
    
    keyboard = [
        [InlineKeyboardButton(f"📊 Лимит ({settings['results_count']})", callback_data="settings_results")],
        [InlineKeyboardButton(f"📄 На странице ({settings['items_per_page']})", callback_data="settings_per_page")],
        [InlineKeyboardButton("📝 Шаблон", callback_data="settings_template")],
        [InlineKeyboardButton("🔷 Главное меню", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def show_results_count_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("20", callback_data="set_results_20"), InlineKeyboardButton("30", callback_data="set_results_30"), InlineKeyboardButton("50", callback_data="set_results_50")],
        [InlineKeyboardButton("100", callback_data="set_results_100"), InlineKeyboardButton("150", callback_data="set_results_150"), InlineKeyboardButton("200", callback_data="set_results_200")],
        [InlineKeyboardButton("🔷 Назад", callback_data="menu_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔷 <b>Лимит результатов</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def set_results_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    value = int(query.data.split("_")[2])
    await save_user_settings(user_id, results_count=value)
    await query.answer(f"✅ Лимит: {value}")
    await show_settings(update, context)

async def show_per_page_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("5", callback_data="set_per_page_5"), InlineKeyboardButton("10", callback_data="set_per_page_10"), InlineKeyboardButton("15", callback_data="set_per_page_15")],
        [InlineKeyboardButton("20", callback_data="set_per_page_20"), InlineKeyboardButton("25", callback_data="set_per_page_25")],
        [InlineKeyboardButton("🔷 Назад", callback_data="menu_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🔷 <b>На странице</b>", reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def set_per_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    value = int(query.data.split("_")[3])
    await save_user_settings(user_id, items_per_page=value)
    await query.answer(f"✅ На странице: {value}")
    await show_settings(update, context)

async def show_template_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    settings = await get_user_settings(user_id)
    current_template = settings['message_template']
    
    text = f"""🔷 <b>Шаблон сообщения</b>

📝 Текущий:
<code>{current_template}</code>

✏️ Введите новый текст (макс 200 символов)"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Сбросить", callback_data="reset_template")],
        [InlineKeyboardButton("🔷 Назад", callback_data="menu_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['editing_template'] = True
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def reset_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    default_template = 'Здравствуйте, заинтересовался вашим NFT подарком'
    await save_user_settings(user_id, message_template=default_template)
    await query.answer("✅ Шаблон сброшен")
    await show_template_settings(update, context)

async def show_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    text = """🔷 <b>ПОДДЕРЖКА</b>

По вопросам: @zotlu"""
    keyboard = [[InlineKeyboardButton("🔷 Главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

# ========== ОБРАБОТКА ТЕКСТА ==========
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_subscription(update, context):
        return
    
    if context.user_data.get('editing_template'):
        user_id = update.effective_user.id
        new_template = update.message.text.strip()
        
        if len(new_template) > 200:
            await update.message.reply_text("❌ Максимум 200 символов")
            return
        
        await save_user_settings(user_id, message_template=new_template)
        context.user_data['editing_template'] = False
        await update.message.reply_text("✅ Шаблон сохранён!")
        return

# ========== ОБРАБОТЧИК МЕНЮ ==========
async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await require_subscription(update, context):
        return
    
    data = query.data
    
    if data == "main_menu":
        await show_main_menu(update, context)
    elif data == "menu_search":
        await show_search_menu(update, context)
    elif data == "menu_profile":
        await show_profile(update, context)
    elif data == "menu_settings":
        await show_settings(update, context)
    elif data == "menu_support":
        await show_support(update, context)
    elif data == "search_random":
        await show_modes_menu(update, context)
    elif data == "search_model":
        await show_model_selection(update, context)
    elif data == "search_girls":
        await show_search_results(update, context, "girls", is_girls=True)
    elif data == "mode_light":
        await show_search_results(update, context, "light")
    elif data == "mode_medium":
        await show_search_results(update, context, "medium")
    elif data == "mode_heavy":
        await show_search_results(update, context, "heavy")
    elif data.startswith("start_search_"):
        mode = data.replace("start_search_", "")
        await show_search_results(update, context, mode)
    elif data.startswith("model_page_"):
        page = int(data.split("_")[2])
        await show_model_selection(update, context, page)
    elif data.startswith("select_model_"):
        nft_name = data.replace("select_model_", "")
        await show_search_results(update, context, "light", nft_name)
    elif data.startswith("results_page_"):
        parts = data.split("_")
        mode = parts[2]
        page = int(parts[3])
        nft_name = parts[4] if len(parts) > 4 and parts[4] != 'False' and parts[4] != 'True' else None
        is_girls = parts[5] == 'True' if len(parts) > 5 else False
        await show_search_results(update, context, mode, nft_name, page, is_girls)
    elif data.startswith("more_"):
        parts = data.split("_")
        mode = parts[1]
        nft_name = "_".join(parts[2:])
        await show_search_results(update, context, mode, nft_name)
    elif data == "settings_results":
        await show_results_count_menu(update, context)
    elif data.startswith("set_results_"):
        await set_results_count(update, context)
    elif data == "settings_per_page":
        await show_per_page_menu(update, context)
    elif data.startswith("set_per_page_"):
        await set_per_page(update, context)
    elif data == "settings_template":
        await show_template_settings(update, context)
    elif data == "reset_template":
        await reset_template(update, context)
    elif data == "noop":
        pass

# ========== ЗАПУСК ==========
def main():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_db())
    
    print("=" * 50)
    print("🤖 NFT ПАРСЕР БОТ (ОПТИМИЗИРОВАННЫЙ)")
    print("=" * 50)
    print("✅ /block, /unblock, /blocklist")
    print("✅ Новые подарки добавлены")
    print("✅ Имена из female_names.txt")
    print("✅ Чёрный список из blacklist.txt")
    print("✅ Парсинг ускорен в 10+ раз")
    print("=" * 50)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("block", block_command))
    app.add_handler(CommandHandler("unblock", unblock_command))
    app.add_handler(CommandHandler("blocklist", blocklist_command))
    app.add_handler(CallbackQueryHandler(handle_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("✅ Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
