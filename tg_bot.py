import os
import asyncio
import random
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from telegram.constants import ChatType
from datetime import date
from collections import defaultdict
from geopy.geocoders import Nominatim
import json
import os
from telegram import (
	Update,
	InlineKeyboardButton,
	InlineKeyboardMarkup,
	constants as tg_const,
)
from telegram.ext import (
	Application,
	CommandHandler,
	CallbackQueryHandler,
	MessageHandler,
	ContextTypes,
	filters,
)

BOT_TOKEN = os.getenv("TG_TOKEN")

STATS_FILE = "pidor_stats.json"


# ────────────────── Обширный список русских ругательств ──────────────────────
RUSSIAN_SWEARS = [
	# Старинные русские ругательства
	"ащеул", "баба-ветрогонка", "баляба", "баламошка", "балахвост", "басалай",
	"безпелюха", "безсоромна баба", "белебеня", "бзыря", "бобыня", "божевольный",
	"божедурье", "болдырь", "блудоум", "блудяшка", "бредкий", "брыдлый",
	"буня", "буслай", "валандай", "вертопрах", "визгопряха", "волочайка",
	"вымесок", "выпороток", "вяжихвостка", "глазопялка", "глуподырый",
	"глупендяй", "глупеня", "грабастик", "гузыня", "гульня", "дитка",
	"дроволом", "дурка", "елдыга", "еропка", "ерохвост", "ерпыль",
	"ёнда", "ёра", "жиздор", "загузастка", "задор-баба", "заовинник",
	"затетёха", "захухря", "кащей", "киселяй", "колоброд", "коломес",
	"колотовка", "колупай", "печегнёт", "печная ездова", "плеха", "попрешница",
	"потатуй", "похабник", "пресноплюй", "псоватый", "пустобрёх", "пустошный",
	"пыня", "пятигуз", "развисляй", "разлямзя", "разноголовый", "разтетёха",
	"растопча", "расщеколда", "рахубник", "рюма", "свербигузка", "сдёргоумка",
	"сиволап", "скапыжный", "скоблёное рыло", "скаред", "сквернавец", "сняголовь",
	"стерва", "страмец", "страхолюд", "суемудр", "тартыга", "телеух", "тетёшка",
	"титёшница", "трупёрда", "трясся", "туес", "тьмонеистовый", "тюрюхайло",
	"углан", "урюпа", "фетюк", "фофан", "фуфлыга", "халдей", "хандрыга",
	"хмыстень", "хохрик", "хобяка", "чёрт верёвочный", "чужеяд", "шаврик",

	# Животные
	"козел", "коза драная", "баран тупой", "свинья грязная", "кабан жирный",
	"осел упрямый", "мул", "пес смердящий", "сука", "шавка", "дворняга",
	"кот драный", "крыса серая", "мышь", "корова", "бык", "петух",
	"курица безмозглая", "гусь", "утка", "индюк напыщенный", "змея подколодная",
	"гадюка", "жаба", "лягушка", "червяк", "слизняк", "паук", "таракан",
	"муха назойливая", "комар", "клоп", "блоха", "вошь", "гнида",
	"гиена", "шакал", "волк", "лиса хитрая", "медведь", "заяц трусливый",
	"обезьяна", "мартышка", "горилла", "павиан", "хорек мерзкий",

	# Характеристики личности
	"дурак", "дура", "дебил", "идиот", "кретин", "олигофрен", "тупица",
	"дубина", "болван", "остолоп", "остолбень", "околотень", "телеух",
	"фофан", "толоконный лоб", "дубоголовый", "тупоголовый", "бестолочь",
	"тормоз", "недоумок", "полудурок", "придурок", "невежда", "неуч",
	"безграмотный", "некультурный", "дикарь", "варвар", "хам", "быдло",
	"мужлан", "деревенщина", "лапоть", "валенок", "пень", "чурбан",
	"бревно", "колода", "дуб", "балда",

	# Поведенческие характеристики
	"нахал", "хабал", "хулиган", "безобразник", "наглец", "подлец", "негодяй",
	"мерзавец", "гад", "сволочь", "паскуда", "мразь", "тварь", "урод",
	"ублюдок", "выродок", "отморозок", "психопат", "дегенерат", "извращенец",
	"маньяк", "садист", "деспот", "тиран", "агрессор", "насильник",
	"убийца", "палач", "мясник", "живодер", "бандит", "головорез",

	# Социальные роли
	"проститутка", "шлюха", "потаскуха", "развратница", "гулящая", "мошенник",
	"вор", "жулик", "плут", "аферист", "обманщик", "лжец", "врун", "лицемер",
	"двуличный", "предатель", "изменник", "трус", "шантажист", "вымогатель",
	"коррупционер", "казнокрад", "взяточник", "хапуга", "мздолюбец","барыга" 

	# Физические характеристики
	"урод", "уродина", "страшила", "чучело", "пугало", "монстр", "мутант",
	"калека", "карлик", "гигант", "толстяк", "жиртрест", "дистрофик",
	"скелет", "доходяга", "заморыш", "коротышка", "лилипут", "дрыщ",
	"слабак", "размазня", "тряпка", "лапша", "вонючка", "смердящий",
	"грязнуля", "неряха", "замарашка", "оборванец",


	# Современные сленговые
	"лох", "чмо", "чмошник", "лузер", "неудачник", "зануда", "нытик",
	"пессимист", "брюзга", "ворчун", "критикан", "демагог", "популист",
	"карьерист", "интриган", "подхалим", "лизоблюд", "подлиза", "холуй",
	"прислужник", "раб","пердун"

	# Составные оскорбления
	"дурак набитый", "осёл упрямый", "баран тупорылый", "козёл вонючий",
	"пень обросший", "дуб стоялый", "болван чучельный", "кретин дремучий",
	"идиот законченный", "дебил натуральный", "придурок конченый",
	"психопат клинический", "мерзавец отпетый", "негодяй последний",
	"подлец конченый", "паскуда редкостная", "сволочь отборная",
	"мразь человеческая", "тварь дрожащая", "ничтожество полное",
	"убожество жалкое", "посредственность серая", "бездарность природная",
	"неудачник прирожденный", "лузер пожизненный", "горе-человек",
	"недочеловек", "псевдочеловек", "существо жалкое", "создание убогое",
	"личность ущербная", "особь дефективная", "экземпляр бракованный",
	"индивид неполноценный", "субъект сомнительный", "объект презрения", "пердун старый"
	"пердун вонючий", "пидор вонючий", "пидорас вонючий", "пидорас вонючий",
	"пидорас вонючий", "пидорас вонючий", "пидорас вонючий", "пидорас вонючий",

    # Животные
    "козел", "коза драная", "баран тупой", "свинья грязная", "кабан жирный",
    "осел упрямый", "мул", "пес смердящий", "сука", "шавка", "дворняга",
    "кот драный", "крыса серая", "мышь", "корова", "бык", "петух",
    "курица безмозглая", "гусь", "утка", "индюк напыщенный", "змея подколодная",
    "гадюка", "жаба", "лягушка", "червяк", "слизняк", "паук", "таракан",
    "муха назойливая", "комар", "клоп", "блоха", "вошь", "гнида",
    "гиена", "шакал", "волк", "лиса хитрая", "медведь", "заяц трусливый",
    "обезьяна", "мартышка", "горилла", "павиан", "хорек мерзкий",


	# Дополнительные варианты
	"баклан", "балбес", "банан", "бревенчатый", "бубен", "буржуй", "бык",
	"вафлер", "ворон", "гавкало", "галимый", "гандон", "гниловатый",
	"головастик", "голубчик", "гопник", "грибок", "дармоед", "деревяшка",
	"дикобраз", "долбанутый", "дубовый", "дыня", "жижа", "забулдыга",
	"загогулина", "задрот", "зануда", "зараза", "зверюга", "идольный",
	"индюшка", "йогурт", "кабанчик", "кактус", "калоша", "каракули",
	"корнишон", "крендель", "кривуля", "кукушка", "лабуда", "лебеда",
	"леший", "лимон", "лопух", "лузга",
	"мелочь", "мерзавчик", "милашка", "мокрица", "морковка", "мумия",
	"мурло", "навозник", "нахлебник", "недоросль", "нелепица", "обжора",
	"огурец", "одуванчик", "олух", "опарыш", "паразит", "пенек",
	"пепелац", "перец", "пескарь", "петушок", "пижон", "пират", "плесень",


	# Философские оскорбления
	"ничтожество", "никчемность", "убожество", "жалость", "презрение",
	"отвращение", "мерзость", "гадость", "пакость", "поганость", "нечисть",
	"нежить", "упырь", "вампир", "вурдалак", "оборотень", "чудовище",
	"исчадие", "порождение", "отродье", "выкидыш", "недоносок", "ошибка природы",
	"брак эволюции", "тупик развития", "деградант", "регрессор", "примитив",
	"архаизм", "атавизм", "рудимент", "реликт", "анахронизм", "пережиток",



	# Предметные сравнения
	"швабра", "веник", "метла", "тряпка", "мочалка", "губка", "щетка",
	"скребок", "совок", "ведро", "таз", "корыто", "лохань", "бочка",
	"кадка", "чан", "котел", "кастрюля", "сковородка", "миска", "тарелка",


	# Инструментальные
	"молоток", "кувалда", "топор", "пила", "рубанок", "стамеска", "долото",
	"сверло", "бур", "коловорот", "дрель", "перфоратор", "отбойник",
	"лом", "лопата", "кирка", "мотыга", "тяпка", "грабли", "вилы",
	"коса", "серп", "секатор", "ножницы", "кусачки", "плоскогубцы"
]



# ────────────────────── НОВЫЙ: Случайный выбор ругательств ────────────────────

# Загрузка и сохранение статистики
def load_pidor_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, encoding="utf-8") as f:
                stats = json.load(f)
                return (
                    stats.get("storage", {}),
                    # для stats — defaultdict на два уровня!
                    defaultdict(
                        lambda: defaultdict(int), 
                        {
                            int(k): defaultdict(int, {int(uid): c for uid, c in v.items()})
                            for k, v in stats.get("stats", {}).items()
                        }
                    ),
                    defaultdict(dict, {int(k): v for k, v in stats.get("names", {}).items()}),
                    defaultdict(dict, {int(k): v for k, v in stats.get("participants", {}).items()})
                )
        except Exception as e:
            print(f"Не удалось загрузить pidor_stats.json: {e}. Инициализация с нуля.")
            return {}, defaultdict(lambda: defaultdict(int)), defaultdict(dict), defaultdict(dict)
    return {}, defaultdict(lambda: defaultdict(int)), defaultdict(dict), defaultdict(dict)

def save_pidor_stats():
    out = {
        "storage": PIDOR_DAY_STORAGE,
        "stats": {str(k): v for k, v in PIDOR_DAY_STATS.items()},
        "names": {str(k): v for k, v in PIDOR_DAY_NAMES.items()},
        "participants": {str(k): v for k, v in GROUP_PARTICIPANTS.items()}
    }
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)

# Глобальные хранилища для статистики
PIDOR_DAY_STORAGE: Dict[int, Dict] = {}
PIDOR_DAY_STATS: Dict[int, Dict[int, int]] = {}
PIDOR_DAY_NAMES: Dict[int, Dict[int, str]] = {}
GROUP_PARTICIPANTS: Dict[int, Dict[int, str]] = {}

# Инициализация при запуске
PIDOR_DAY_STORAGE, PIDOR_DAY_STATS, PIDOR_DAY_NAMES, GROUP_PARTICIPANTS = load_pidor_stats()

# Обработчик автоинсульта (и сбор участников!)
async def insult_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    chat = update.effective_chat
    user = update.effective_user
    # Запоминаем всех, кто не бот
    GROUP_PARTICIPANTS[chat.id][user.id] = user.username
    print('PIDOR_DAY_STORAGE', PIDOR_DAY_STORAGE)
    print('PIDOR_DAY_STATS', PIDOR_DAY_STATS)
    print('PIDOR_DAY_NAMES', PIDOR_DAY_NAMES)
    print('GROUP_PARTICIPANTS', GROUP_PARTICIPANTS)

    text_lower = update.message.text.lower()
    # Измените (and/or) по желанию
    if "е" in text_lower or "й" in text_lower:
        user_name = user.first_name or "друг"
        random_swear = random.choice(RUSSIAN_SWEARS)
        response = f"ты {random_swear}, {user_name} епта"
        await context.bot.send_message(chat.id, response)

# Команда "пидор дня"
async def pidor_of_the_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat.type not in ['group', 'supergroup']:
        await update.message.reply_text("Эта команда работает только в группах!")
        return
    today = date.today().isoformat()
    chat_id = chat.id
    current_entry = PIDOR_DAY_STORAGE.get(chat_id)
    if current_entry and current_entry["date"] == today:
        winner_name = current_entry["name"]
        await update.message.reply_text(f"🏆 Пидор дня — {winner_name} (выбран ранее сегодня)")
        return
    members = list(GROUP_PARTICIPANTS.get(chat_id, {}).items())
    if not members:
        await update.message.reply_text("Не удалось найти кандидатов в пидоры. Пусть сначала кто-нибудь напишет!")
        return
    no_winner = 202356111
    possible_members = [m for m in members if m[0] != no_winner]
    if not possible_members:
        await update.message.reply_text("Нет возможных кандидатов для выбора.")
        return
    winner_id, winner_name = random.choice(possible_members)
    PIDOR_DAY_STATS[chat_id][winner_id] += 1
    PIDOR_DAY_NAMES[chat_id][winner_id] = winner_name
    PIDOR_DAY_STORAGE[chat_id] = {"date": today, "user_id": winner_id, "name": winner_name}
    save_pidor_stats()
    await update.message.reply_text(f"🎉 Сегодня пидор дня — {winner_name}! Поздравляем! 🎉")

# Команда статистики
async def pidor_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    chat_id = chat.id
    stats = PIDOR_DAY_STATS.get(chat_id, {})
    names = PIDOR_DAY_NAMES.get(chat_id, {})
    if not stats:
        await update.message.reply_text("Пока никто не был избран пидором в этом чате.")
        return
    lines = []
    for user_id, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        name = names.get(str(user_id))
        lines.append(f"{name}: {count}")
    result = "📊 Статистика выбора пидора дня:\n" + "\n".join(lines)
    await update.message.reply_text(result)

# Стартовая команда с кнопкой
async def start_hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👋 Скажи привет", callback_data="say_hello")]])
    await update.message.reply_text("Нажми кнопку, чтобы получить привет!", reply_markup=kb)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    if q.data == "say_hello":
        await context.bot.send_message(q.message.chat_id, "привет")

def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("sayhello", start_hello))
    app.add_handler(CommandHandler("whoispidor", pidor_of_the_day))
    app.add_handler(CommandHandler("pidarstat", pidor_stats))
    app.add_handler(CallbackQueryHandler(button_click, pattern="^say_hello$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, insult_user))
    app.run_polling()

if __name__ == "__main__":
    main()