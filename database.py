import sqlite3
import os
# import random # Убрали, так как random пока не используется в этом файле

# --- Базовые данные (Описания, Фото) ---

hotel_descriptions = {
    # --- Описания для Нячанга (Ваши оригинальные) ---
    "Adamas Boutique Hotel 5 stars":
        "✨ Что включено в ваш тур ✨\n\n"
        "🛏 Проживание в номере категории Deluxe\n"
        "🍽 Завтрак 'шведский стол' (07:00-11:00)\n"
        "📶 Бесплатный Wi-Fi на всей территории\n"
        "🏊 Доступ в бассейн и SPA-зону\n"
        "🚗 Трансфер из аэропорта (встреча с табличкой)\n"
        "🛎 Ежедневная уборка номера\n"
        "🍹 Приветственный коктейль\n"
        "👶 Детская кроватка по запросу",
    "Alibu Resort Nha Trang 5 stars":
        "🌟 Премиум пакет услуг 🌟\n\n"
        "🌊 Люкс с панорамным видом на море\n"
        "🍾 Система 'Все включено' (питание + напитки)\n"
        "💆 2 бесплатных массажа (60 мин каждый)\n"
        "⛵ Экскурсия на острова (групповая)\n"
        "🎪 Детский клуб с аниматорами\n"
        "🏋‍♂ Современный фитнес-центр\n"
        "🎭 Вечерние шоу программы\n"
        "🛒 10% скидка в сувенирных магазинах",
    "Alma Resort Cam Ranh 5 stars":
        "💎 VIP-обслуживание 💎\n\n"
        "🏡 Вилла с приватным бассейном (50 м²)\n"
        "🍴 Полный пансион (завтрак, обед, ужин)\n"
        "🧖 СПА процедуры на выбор (2 сеанса)\n"
        "🚤 Аренда катера на 2 часа\n"
        "🎤 Вечерняя развлекательная программа\n"
        "👔 Персональный консьерж-сервис\n"
        "🧺 Прачечная (до 5 кг белья)\n"
        "🍉 Фруктовая корзина в номере",
    "Bonjour Nha Trang Hotel 4 stars":
        "🏝 Стандартный пакет услуг 🏝\n\n"
        "🛌 Стандартный номер (25 м²)\n"
        "☕ Континентальный завтрак\n"
        "💪 Фитнес-центр (06:00-22:00)\n"
        "🏖 1 экскурсия на выбор (город или острова)\n"
        "📶 Бесплатный Wi-Fi\n"
        "🚌 Трансфер до пляжа (по расписанию)\n"
        "🛒 5% скидка в ресторанах отеля",
    "Daphovina Hotel 4 stars":
        "🌆 Комфорт-тур 🌆\n\n"
        "🏙 Номер с видом на город\n"
        "🍳 2-разовое питание (завтрак+ужин)\n"
        "💦 Бассейн и сауна (08:00-20:00)\n"
        "🚐 Трансфер до пляжа (каждые 2 часа)\n"
        "🧒 Детская площадка\n"
        "🛌 Ежедневная уборка\n"
        "🍹 Бесплатный сок при заселении",
    "DB Hotel Nha Trang 3 stars":
        "💰 Эконом-вариант 💰\n\n"
        "🛏 Эконом номер (18 м²)\n"
        "🍞 Только завтрак (07:00-09:00)\n"
        "❄ Общий холодильник на этаже\n"
        "🍳 Общая кухня (посуда залог 100.000 VND)\n"
        "🧺 Прачечная самообслуживания\n"
        "🚍 Автобусная остановка рядом\n"
        "💵 Дешевые экскурсии от местных гидов",

    # --- Сгенерированные описания для Дананга ---
    "Bellerive Hoi An Resort & Spa 5 stars":
        "🌟 Элегантный отдых в Bellerive Hoi An 5 stars 🌟\n\n" # ИСПРАВЛЕНО * на stars
        "🛌 Просторный номер Deluxe с балконом\n"
        "🍽 Изысканный завтрак 'шведский стол'\n"
        "💆 Доступ в роскошный SPA-центр (процедуры за доп. плату)\n"
        "🏊 Большой инфинити-бассейн с видом\n"
        "📶 Высокоскоростной Wi-Fi бесплатно\n"
        "🛎 Консьерж-сервис для ваших пожеланий\n"
        "✨ Приветственный напиток по прибытии",
    "Centre Point Hotel & Residence Danang 5 stars":
        "🏙 Панорамный Дананг из Centre Point 5 stars 🏙\n\n" # ИСПРАВЛЕНО * на stars
        "🌇 Номер 'Premier' с видом на город или реку\n"
        "🍳 Завтрак в ресторане отеля\n"
        "🏋‍♂ Доступ в современный фитнес-зал\n"
        "🏊 Бассейн на крыше с потрясающим видом\n"
        "📶 Бесплатный Wi-Fi во всех зонах\n"
        "🛎 Круглосуточная стойка регистрации\n"
        "🅿️ Возможна парковка (по запросу)",
    "Da Nang Marriott Resort & Spa 5 stars":
        "💎 Премиум Релакс в Da Nang Marriott 5 stars 💎\n\n" # ИСПРАВЛЕНО * на stars
        "🌊 Шикарный номер с прямым выходом к бассейну или видом на море\n"
        "🍴 Завтрак 'шведский стол' с международными блюдами\n"
        "🧖 Посещение термальной зоны SPA (сауна, хаммам)\n"
        "🌴 Несколько бассейнов на территории, включая детский\n"
        "🎾 Теннисные корты и водные виды спорта (за доп. плату)\n"
        "📶 Wi-Fi на всей территории резорта\n"
        "🍉 Корзина сезонных фруктов в номер",
    "Da Nang Han River Hotel 4 stars":
        "🌉 Уют у реки Хан в Han River Hotel 4 stars 🌉\n\n" # ИСПРАВЛЕНО * на stars
        "🛌 Комфортабельный номер Standard\n"
        "☕ Завтрак включен\n"
        "💪 Небольшой тренажерный зал\n"
        "📶 Бесплатный Wi-Fi\n"
        "🛎 Ежедневная уборка\n"
        "🗺 Помощь в организации экскурсий\n"
        "✨ Удобное расположение для прогулок по набережной",
    "Diamond Sea Hotel 4 stars":
        "🏖 Морской бриз в Diamond Sea 4 stars 🏖\n\n" # ИСПРАВЛЕНО * на stars
        "🛌 Номер Superior с частичным видом на море\n"
        "🍳 Вкусный завтрак\n"
        "🏊 Бассейн на крыше с баром\n"
        "📶 Бесплатный Wi-Fi\n"
        "🚶 Прямой доступ к пляжу Микхе\n"
        "🛎 Круглосуточное обслуживание номеров\n"
        "🍹 Приветственный напиток",
    "Aria Grand Hotel & Spa 3 stars":
        "🏨 Комфорт и СПА в Aria Grand 3 stars 🏨\n\n" # ИСПРАВЛЕНО * на stars
        "🛏 Уютный стандартный номер\n"
        "🍞 Завтрак (может быть континентальный)\n"
        "💆 Возможность посетить СПА (услуги за доп. плату)\n"
        "📶 Wi-Fi в номере и лобби\n"
        "🛎 Дружелюбный персонал\n"
        "📍 Недалеко от пляжа и местных кафе\n"
        "✨ Хорошее соотношение цена/качество",

    # --- Сгенерированные описания для Фукуока ---
    "Melia Vinpearl Phu Quoc 5 stars":
        "🏝 Роскошная Вилла в Melia Vinpearl 5 stars 🏝\n\n" # ИСПРАВЛЕНО * на stars
        "🏡 Проживание на приватной вилле с бассейном\n"
        "🍽 Питание 'Полный пансион' или 'Все включено' (на выбор)\n"
        "🎢 Бесплатный доступ в парк развлечений VinWonders и Сафари (уточняйте условия тура)\n"
        "🏖 Собственный оборудованный пляж\n"
        "🏊 Несколько общих бассейнов и аквапарк\n"
        "📶 Wi-Fi на всей территории\n"
        "✨ Трансфер из/в аэропорт Фукуока",
    "Premier Village Phu Quoc 5 stars":
        "💎 Эксклюзивные Виллы в Premier Village 5 stars 💎\n\n" # ИСПРАВЛЕНО * на stars
        "🌊 Вилла на воде или с видом на океан с личным бассейном\n"
        "🍴 Завтрак 'шведский стол' в ресторане мирового класса\n"
        "🏖 Уникальное расположение между двумя пляжами\n"
        "🧖 Роскошный спа-центр Plumeria\n"
        "🛶 Бесплатные каяки и сапборды\n"
        "📶 Wi-Fi премиум-класса\n"
        "✨ Персональный сервис и багги для передвижения",
    "Radisson Blu Resort Phu Quoc 5 stars":
        "🌊 Современный шик в Radisson Blu 5 stars 🌊\n\n" # ИСПРАВЛЕНО * на stars
        "🛌 Стильный номер Deluxe с балконом\n"
        "🍳 Богатый завтрак 'шведский стол'\n"
        "🏊 Огромный бассейн-лагуна\n"
        "🎰 Доступ в казино Corona (для желающих, 21+)\n"
        "🏋‍♂ Фитнес-центр и спа-услуги\n"
        "📶 Бесплатный Wi-Fi\n"
        "🚌 Бесплатный шаттл до города Дуонг Донг (по расписанию)",
    "M Village Tropical 4 stars":
        "🌴 Тропический Оазис M Village 4 stars 🌴\n\n" # ИСПРАВЛЕНО * на stars
        "🛖 Уютное бунгало в окружении зелени\n"
        "☕ Завтрак в ресторане отеля\n"
        "🏊 Бассейн в саду\n"
        "📶 Wi-Fi на территории\n"
        "🛵 Возможность аренды скутера\n"
        "🏖 Недалеко от пляжа Онг Ланг\n"
        "✨ Спокойная и расслабляющая атмосфера",
    "JM Casa Villa Retreat 4 stars":
        "🏡 Виллы для Уединения JM Casa Villa 4 stars 🏡\n\n" # ИСПРАВЛЕНО * на stars
        "🛌 Просторная вилла с собственной кухней\n"
        "🍳 Возможность готовить самостоятельно или заказать завтрак\n"
        "🏊 Приватный бассейн для каждой виллы\n"
        "📶 Бесплатный Wi-Fi\n"
        "🌿 Тихий район, идеально для спокойного отдыха\n"
        "🛎 Персонализированный сервис\n"
        "✨ Идеально для семей или пар",
    "Hien Minh Bungalow 3 stars":
        "🌿 Сад и Пляж в Hien Minh 3 stars 🌿\n\n" # ИСПРАВЛЕНО * на stars
        "🛖 Комфортное бунгало в саду\n"
        "🍞 Простой завтрак включен\n"
        "🏖 Близкое расположение к пляжу Long Beach\n"
        "📶 Wi-Fi доступен\n"
        "🌴 Зеленая территория\n"
        "🛎 Помощь в бронировании туров\n"
        "💰 Отличный бюджетный вариант",
}


hotel_photos = {
    "Adamas Boutique Hotel 5 stars": [
        "https://placehold.co/600x400/000000/FFFFFF/png?text=Adamas+Photo+1",
        "https://placehold.co/600x400/1E90FF/FFFFFF/png?text=Adamas+Photo+2",
        "https://placehold.co/600x400/FF6347/FFFFFF/png?text=Adamas+Photo+3"
    ],
    "Alibu Resort Nha Trang 5 stars": [
        "https://placehold.co/600x400/32CD32/FFFFFF/png?text=Alibu+Photo+1",
        "https://placehold.co/600x400/FFD700/FFFFFF/png?text=Alibu+Photo+2",
        "https://placehold.co/600x400/8A2BE2/FFFFFF/png?text=Alibu+Photo+3"
    ],
    "Alma Resort Cam Ranh 5 stars": [
        "https://placehold.co/600x400/FF4500/FFFFFF/png?text=Alma+Photo+1",
        "https://placehold.co/600x400/191970/FFFFFF/png?text=Alma+Photo+2",
        "https://placehold.co/600x400/2E8B57/FFFFFF/png?text=Alma+Photo+3"
    ],
    "Bonjour Nha Trang Hotel 4 stars": [
        "https://placehold.co/600x400/DC143C/FFFFFF/png?text=Bonjour+Photo+1",
        "https://placehold.co/600x400/00CED1/FFFFFF/png?text=Bonjour+Photo+2",
        "https://placehold.co/600x400/9932CC/FFFFFF/png?text=Bonjour+Photo+3"
    ],
    "Daphovina Hotel 4 stars": [
        "https://placehold.co/600x400/FF8C00/FFFFFF/png?text=Daphovina+1",
        "https://placehold.co/600x400/4682B4/FFFFFF/png?text=Daphovina+2",
        "https://placehold.co/600x400/3CB371/FFFFFF/png?text=Daphovina+3"
    ],
    "DB Hotel Nha Trang 3 stars": [
        "https://placehold.co/600x400/696969/FFFFFF/png?text=DB+Hotel+1",
        "https://placehold.co/600x400/BDB76B/FFFFFF/png?text=DB+Hotel+2",
        "https://placehold.co/600x400/778899/FFFFFF/png?text=DB+Hotel+3"
    ],
    "Bellerive Hoi An Resort & Spa 5 stars": [
        "https://placehold.co/600x400/f28b82/FFFFFF/png?text=Bellerive+1",
        "https://placehold.co/600x400/f28b82/000000/png?text=Bellerive+2"
        ],
    "Centre Point Hotel & Residence Danang 5 stars": [
        "https://placehold.co/600x400/fbbc04/FFFFFF/png?text=CentrePoint+1",
        "https://placehold.co/600x400/fbbc04/000000/png?text=CentrePoint+2"
        ],
    "Da Nang Marriott Resort & Spa 5 stars": [
        "https://placehold.co/600x400/fff475/FFFFFF/png?text=Marriott+Danang+1",
        "https://placehold.co/600x400/fff475/000000/png?text=Marriott+Danang+2"
        ],
    "Da Nang Han River Hotel 4 stars": [
        "https://placehold.co/600x400/ccff90/FFFFFF/png?text=HanRiver+1",
        "https://placehold.co/600x400/ccff90/000000/png?text=HanRiver+2"
        ],
    "Diamond Sea Hotel 4 stars": [
        "https://placehold.co/600x400/a7ffeb/FFFFFF/png?text=DiamondSea+1",
        "https://placehold.co/600x400/a7ffeb/000000/png?text=DiamondSea+2"
        ],
    "Aria Grand Hotel & Spa 3 stars": [
        "https://placehold.co/600x400/cbf0f8/FFFFFF/png?text=AriaGrand+1",
        "https://placehold.co/600x400/cbf0f8/000000/png?text=AriaGrand+2"
        ],
    "Melia Vinpearl Phu Quoc 5 stars": [
        "https://placehold.co/600x400/aecbfa/FFFFFF/png?text=MeliaVinpearl+1",
        "https://placehold.co/600x400/aecbfa/000000/png?text=MeliaVinpearl+2"
        ],
    "Premier Village Phu Quoc 5 stars": [
        "https://placehold.co/600x400/d7aefb/FFFFFF/png?text=PremierVillage+1",
        "https://placehold.co/600x400/d7aefb/000000/png?text=PremierVillage+2"
        ],
    "Radisson Blu Resort Phu Quoc 5 stars": [
        "https://placehold.co/600x400/fdcfe8/FFFFFF/png?text=RadissonBlu+1",
        "https://placehold.co/600x400/fdcfe8/000000/png?text=RadissonBlu+2"
        ],
    "M Village Tropical 4 stars": [
        "https://placehold.co/600x400/e6c9a8/FFFFFF/png?text=MVillage+1",
        "https://placehold.co/600x400/e6c9a8/000000/png?text=MVillage+2"
        ],
    "JM Casa Villa Retreat 4 stars": [
        "https://placehold.co/600x400/e8eaed/FFFFFF/png?text=JMCasa+1",
        "https://placehold.co/600x400/e8eaed/000000/png?text=JMCasa+2"
        ],
    "Hien Minh Bungalow 3 stars": [
        "https://placehold.co/600x400/ccbbb0/FFFFFF/png?text=HienMinh+1",
        "https://placehold.co/600x400/ccbbb0/000000/png?text=HienMinh+2"
        ],
}

# --- Детали отелей (для отображения и звездности) ---
# ИСПРАВЛЕНО: Звезды в display_name для Дананга и Фукуока
all_hotel_details = {
    # Нячанг
    "Adamas Boutique Hotel 5 stars": {"display_name": "🏨 Adamas Boutique Hotel 5 stars", "stars": 5},
    "Alibu Resort Nha Trang 5 stars": {"display_name": "🏨 Alibu Resort Nha Trang 5 stars", "stars": 5},
    "Alma Resort Cam Ranh 5 stars": {"display_name": "🏨 Alma Resort Cam Ranh 5 stars", "stars": 5},
    "Bonjour Nha Trang Hotel 4 stars": {"display_name": "🏨 Bonjour Nha Trang Hotel 4 stars", "stars": 4},
    "Daphovina Hotel 4 stars": {"display_name": "🏨 Daphovina Hotel 4 stars", "stars": 4},
    "DB Hotel Nha Trang 3 stars": {"display_name": "🏨 DB Hotel Nha Trang 3 stars", "stars": 3},
    # Дананг (ИСПРАВЛЕНО)
    "Bellerive Hoi An Resort & Spa 5 stars": {"display_name": "🏨 Bellerive Hoi An Resort & Spa 5 stars", "stars": 5},
    "Centre Point Hotel & Residence Danang 5 stars": {"display_name": "🏨 Centre Point Hotel & Residence Danang 5 stars", "stars": 5},
    "Da Nang Marriott Resort & Spa 5 stars": {"display_name": "🏨 Da Nang Marriott Resort & Spa 5 stars", "stars": 5},
    "Da Nang Han River Hotel 4 stars": {"display_name": "🏨 Da Nang Han River Hotel 4 stars", "stars": 4},
    "Diamond Sea Hotel 4 stars": {"display_name": "🏨 Diamond Sea Hotel 4 stars", "stars": 4},
    "Aria Grand Hotel & Spa 3 stars": {"display_name": "🏨 Aria Grand Hotel & Spa 3 stars", "stars": 3},
    # Фукуок (ИСПРАВЛЕНО)
    "Melia Vinpearl Phu Quoc 5 stars": {"display_name": "🏨 Melia Vinpearl Phu Quoc 5 stars", "stars": 5},
    "Premier Village Phu Quoc 5 stars": {"display_name": "🏨 Premier Village Phu Quoc 5 stars", "stars": 5},
    "Radisson Blu Resort Phu Quoc 5 stars": {"display_name": "🏨 Radisson Blu Resort Phu Quoc 5 stars", "stars": 5},
    "M Village Tropical 4 stars": {"display_name": "🏨 M Village Tropical 4 stars", "stars": 4},
    "JM Casa Villa Retreat 4 stars": {"display_name": "🏨 JM Casa Villa Retreat 4 stars", "stars": 4},
    "Hien Minh Bungalow 3 stars": {"display_name": "🏨 Hien Minh Bungalow 3 stars", "stars": 3},
}

# --- Данные по турам (цены, скидки, ДЛИТЕЛЬНОСТЬ) ---
# !!! ВАЖНО: Длительность (duration) уже добавлена !!!
tour_specific_data = {
    "Нячанг": {
        "Adamas Boutique Hotel 5 stars": {"price": 500000, "hot_discount": 0.9, "duration": 7},
        "Alibu Resort Nha Trang 5 stars": {"price": 600000, "hot_discount": 0.85, "duration": 10},
        "Alma Resort Cam Ranh 5 stars": {"price": 700000, "hot_discount": 0.8, "duration": 14},
        "Bonjour Nha Trang Hotel 4 stars": {"price": 400000, "hot_discount": 1.0, "duration": 7},
        "Daphovina Hotel 4 stars": {"price": 350000, "hot_discount": 1.0, "duration": 7},
        "DB Hotel Nha Trang 3 stars": {"price": 300000, "hot_discount": 1.0, "duration": 7},
    },
    "Дананг": {
        "Bellerive Hoi An Resort & Spa 5 stars": {"price": 350000, "hot_discount": 1.0, "duration": 7},
        "Centre Point Hotel & Residence Danang 5 stars": {"price": 320000, "hot_discount": 1.0, "duration": 7},
        "Da Nang Marriott Resort & Spa 5 stars": {"price": 450000, "hot_discount": 0.9, "duration": 10},
        "Da Nang Han River Hotel 4 stars": {"price": 250000, "hot_discount": 1.0, "duration": 7},
        "Diamond Sea Hotel 4 stars": {"price": 260000, "hot_discount": 1.0, "duration": 7},
        "Aria Grand Hotel & Spa 3 stars": {"price": 180000, "hot_discount": 1.0, "duration": 7},
    },
    "Фукуок": {
        "Melia Vinpearl Phu Quoc 5 stars": {"price": 420000, "hot_discount": 1.0, "duration": 10},
        "Premier Village Phu Quoc 5 stars": {"price": 500000, "hot_discount": 0.85, "duration": 14},
        "Radisson Blu Resort Phu Quoc 5 stars": {"price": 390000, "hot_discount": 1.0, "duration": 7},
        "M Village Tropical 4 stars": {"price": 240000, "hot_discount": 1.0, "duration": 7},
        "JM Casa Villa Retreat 4 stars": {"price": 230000, "hot_discount": 1.0, "duration": 10},
        "Hien Minh Bungalow 3 stars": {"price": 150000, "hot_discount": 1.0, "duration": 7},
    }
}

DB_NAME = 'tours.db'

def create_connection(db_file):
    """ Создает соединение с базой данных SQLite """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        # print(f"SQLite version: {sqlite3.sqlite_version}") # Можно раскомментировать для отладки
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database {db_file}: {e}")
    return conn

def create_table(conn, create_table_sql):
    """ Создает таблицу по запросу create_table_sql """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except sqlite3.Error as e:
        print(f"Error creating table: {e}")

def setup_database():
    """ Создает/обновляет базу данных и таблицы, заполняет их данными """
    # Проверяем существование файла БД
    # if os.path.exists(DB_NAME):
    #     # Решите, нужно ли удалять старую БД при каждом запуске
    #     # os.remove(DB_NAME)
    #     # print(f"Removed existing database: {DB_NAME}")
    #     print(f"Database {DB_NAME} already exists. Will try to add/update data.")
    # else:
    #     print(f"Database {DB_NAME} not found. Creating new one.")


    conn = create_connection(DB_NAME)

    if conn is not None:
        print("Database connection established.")
        # --- SQL для создания таблиц (IF NOT EXISTS) ---
        # Таблица отелей (звезды уже здесь)
        sql_create_hotels_table = """ CREATE TABLE IF NOT EXISTS hotels (
                                            hotel_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            internal_key TEXT NOT NULL UNIQUE,
                                            display_name TEXT NOT NULL,
                                            description TEXT,
                                            stars INTEGER  -- Поле для фильтра по звездам
                                        ); """
        # Таблица фото
        sql_create_photos_table = """CREATE TABLE IF NOT EXISTS hotel_photos (
                                        photo_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        hotel_id INTEGER NOT NULL,
                                        photo_url TEXT NOT NULL,
                                        order_index INTEGER DEFAULT 0,
                                        FOREIGN KEY (hotel_id) REFERENCES hotels (hotel_id)
                                    );"""
        # Таблица направлений
        sql_create_destinations_table = """CREATE TABLE IF NOT EXISTS destinations (
                                                destination_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                                name TEXT NOT NULL UNIQUE
                                            );"""
        # --- ИЗМЕНЕНО: Таблица туров ---
        sql_create_tours_table = """ CREATE TABLE IF NOT EXISTS tours (
                                            tour_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            destination_id INTEGER NOT NULL,
                                            hotel_id INTEGER NOT NULL,
                                            price_per_person INTEGER NOT NULL, -- Переименовано из base_price, для фильтра по бюджету
                                            duration_days INTEGER NOT NULL,    -- Новое поле для фильтра по длительности
                                            departure_dates TEXT,              /* Пока не используется */
                                            standard_discount_multiplier REAL DEFAULT 1.0, /* Пока не используется активно */
                                            hot_tour_discount_multiplier REAL DEFAULT 1.0,
                                            FOREIGN KEY (destination_id) REFERENCES destinations (destination_id),
                                            FOREIGN KEY (hotel_id) REFERENCES hotels (hotel_id),
                                            UNIQUE(destination_id, hotel_id) /* Гарантирует уникальность тура */
                                        ); """

        # Создаем таблицы
        create_table(conn, sql_create_hotels_table)
        print("Table 'hotels' checked/created.")
        create_table(conn, sql_create_photos_table)
        print("Table 'hotel_photos' checked/created.")
        create_table(conn, sql_create_destinations_table)
        print("Table 'destinations' checked/created.")
        create_table(conn, sql_create_tours_table)
        print("Table 'tours' checked/created (with price_per_person, duration_days).")

        cursor = conn.cursor()

        # --- Заполнение/Обновление отелей и фото ---
        hotel_key_to_id = {}
        print("\nPopulating/Updating hotels and photos...")
        for internal_key, details in all_hotel_details.items():
            display_name = details["display_name"] # Используем исправленное имя
            stars = details["stars"] # Получаем звезды из деталей отеля
            description = hotel_descriptions.get(internal_key, f"Стандартное описание для {internal_key}")

            try:
                cursor.execute("""
                    INSERT INTO hotels (internal_key, display_name, description, stars)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(internal_key) DO UPDATE SET
                        display_name=excluded.display_name,
                        description=excluded.description,
                        stars=excluded.stars;
                """, (internal_key, display_name, description, stars))

                cursor.execute("SELECT hotel_id FROM hotels WHERE internal_key = ?", (internal_key,))
                result = cursor.fetchone()
                if result:
                    hotel_id = result[0]
                    hotel_key_to_id[internal_key] = hotel_id
                    # print(f"  Processed hotel: {display_name} (ID: {hotel_id}, Stars: {stars})") # Отладка

                    if internal_key in hotel_photos:
                        photo_count = 0
                        # Сначала удалим старые фото для этого отеля, чтобы избежать дубликатов при обновлении
                        cursor.execute("DELETE FROM hotel_photos WHERE hotel_id = ?", (hotel_id,))
                        # Затем вставим актуальные
                        for index, photo_url in enumerate(hotel_photos[internal_key]):
                             cursor.execute("INSERT INTO hotel_photos (hotel_id, photo_url, order_index) VALUES (?, ?, ?)",
                                               (hotel_id, photo_url, index))
                             photo_count += 1
                        # if photo_count > 0: # Отладка
                        #     print(f"    Added/Updated {photo_count} photos for {display_name}")
                else:
                    print(f"  Error retrieving hotel_id for {internal_key} after insert/update.")

            except sqlite3.Error as e:
                print(f"  Error processing hotel {internal_key}: {e}")
        print("Finished processing hotels and photos.")

        # --- Заполнение/Обновление направлений ---
        destination_name_to_id = {}
        print("\nPopulating/Updating destinations...")
        all_destination_names = tour_specific_data.keys()
        for dest_name in all_destination_names:
            try:
                cursor.execute("INSERT OR IGNORE INTO destinations (name) VALUES (?)", (dest_name,))
                cursor.execute("SELECT destination_id FROM destinations WHERE name = ?", (dest_name,))
                result = cursor.fetchone()
                if result:
                    destination_name_to_id[dest_name] = result[0]
                    # print(f"  Processed destination: {dest_name} (ID: {result[0]})") # Отладка
                else:
                    print(f"  Error retrieving destination_id for {dest_name} after insert/ignore.")
            except sqlite3.Error as e:
                print(f"  Error processing destination {dest_name}: {e}")
        print("Finished processing destinations.")


        # --- ИЗМЕНЕНО: Заполнение/Обновление туров ---
        print("\nPopulating/Updating tours (linking destinations and hotels)...")
        processed_tours = 0
        updated_tours = 0 # Не используется, но оставил для возможного разделения подсчета
        skipped_tours = 0
        for dest_name, hotels_in_dest in tour_specific_data.items():
            if dest_name not in destination_name_to_id:
                print(f"  Warning: Destination ID for '{dest_name}' not found. Skipping tours for this destination.")
                skipped_tours += len(hotels_in_dest)
                continue
            dest_id = destination_name_to_id[dest_name]

            for hotel_key, tour_data in hotels_in_dest.items():
                if hotel_key not in hotel_key_to_id:
                    print(f"  Warning: Hotel ID for key '{hotel_key}' in destination '{dest_name}' not found. Skipping this tour.")
                    skipped_tours += 1
                    continue
                hotel_id = hotel_key_to_id[hotel_key]

                # Получаем данные тура, включая новые поля
                price_per_person = tour_data.get('price') # Используем .get() для безопасности
                hot_discount = tour_data.get('hot_discount', 1.0) # Значение по умолчанию, если нет
                duration = tour_data.get('duration') # Новое поле длительности

                # Проверка, что основные данные есть
                if price_per_person is None or duration is None:
                    print(f"  Warning: Missing 'price' or 'duration' for tour {dest_name} - {hotel_key}. Skipping.")
                    skipped_tours += 1
                    continue

                try:
                    # Используем INSERT ... ON CONFLICT для вставки или обновления
                    cursor.execute("""
                        INSERT INTO tours (destination_id, hotel_id, price_per_person, duration_days, departure_dates, standard_discount_multiplier, hot_tour_discount_multiplier)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(destination_id, hotel_id) DO UPDATE SET
                            price_per_person=excluded.price_per_person,
                            duration_days=excluded.duration_days, -- Обновляем длительность
                            hot_tour_discount_multiplier=excluded.hot_tour_discount_multiplier,
                            -- Добавьте сюда другие поля для обновления, если нужно
                            departure_dates=excluded.departure_dates,
                            standard_discount_multiplier=excluded.standard_discount_multiplier;
                    """, (dest_id, hotel_id, price_per_person, duration, None, 1.0, hot_discount))

                    # cursor.rowcount вернет 1 для INSERT и 1 для UPDATE (в SQLite, если не использовать RETURNING)
                    # Более надежный способ - проверить был ли UPDATE:
                    # if cursor.lastrowid == 0: # Это не надежно для ON CONFLICT DO UPDATE
                    #     # Альтернативно, можно сначала SELECT, потом UPDATE/INSERT, но ON CONFLICT проще
                    #     # print(f"  Processed tour (Update/Insert): {dest_name} -> {hotel_key}") # Отладка
                    #     pass # Просто считаем обработанным
                    processed_tours += 1 # Считаем общее количество обработанных (вставленных/обновленных)

                except sqlite3.Error as e:
                    print(f"  Error processing tour link for {dest_name} - {hotel_key}: {e}")
                    skipped_tours += 1

        print(f"\nFinished processing tours. Processed (Inserted/Updated): {processed_tours}, Skipped: {skipped_tours}")

        # Сохраняем изменения в базе данных
        conn.commit()
        print("\nDatabase update/population complete. Changes committed.")
        # Закрываем соединение
        conn.close()
        print("Database connection closed.")
    else:
        print("Error! Cannot create the database connection.")

# --- НОВАЯ ЧАСТЬ: Пример функции для извлечения и отображения данных ---
# --- Адаптируйте ЭТУ ЧАСТЬ под вашу логику отображения ---

def display_tours_for_destination(destination_name):
    """
    Пример функции для извлечения и 'чистого' отображения туров
    для заданного направления из базы данных.
    Именно в подобной функции (в вашем коде) нужно искать
    и исправлять добавление тега '<s> Цена </s>'.
    """
    print(f"\n--- Туры для направления: {destination_name} ---")
    conn = create_connection(DB_NAME)
    if conn is None:
        print("Не удалось подключиться к БД для отображения.")
        return

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT
                h.display_name,
                h.stars,
                t.price_per_person,
                t.duration_days,
                t.hot_tour_discount_multiplier,
                h.description
            FROM tours t
            JOIN hotels h ON t.hotel_id = h.hotel_id
            JOIN destinations d ON t.destination_id = d.destination_id
            WHERE d.name = ?
            ORDER BY h.stars DESC, t.price_per_person ASC
        """, (destination_name,))

        results = cursor.fetchall()

        if not results:
            print("Туры для этого направления не найдены.")
        else:
            for row in results:
                display_name, stars, price, duration, discount, description = row

                final_price = int(price * discount)
                discount_info = ""
                if discount < 1.0:
                    discount_percent = int((1 - discount) * 100)
                    discount_info = f" 🔥 Скидка {discount_percent}%! Старая цена: {price:,} ₽" # Пример формата вывода скидки

                # ВЫВОД БЕЗ ЛИШНИХ ТЕГОВ:
                print(f"\n🏨 Отель: {display_name}") # Имя уже содержит "stars"
                print(f"⭐ Звезд: {stars}")
                print(f"⏳ Дни: {duration}")
                # Пример корректного вывода цены
                print(f"💰 Цена на человека: {final_price:,} ₽{discount_info}")
                # print(f"\n{description}\n") # Можно раскомментировать для вывода описания

                # ПРОВЕРЬТЕ ВАШ КОД: Ищите место, где к строке с ценой
                # добавляется "<s> Цена </s>" и удалите это добавление.
                # Возможно, это выглядело примерно так (НЕПРАВИЛЬНО):
                # print(f"<s> Цена </s> {final_price:,} ₽") # <-- ИСПРАВИТЬ НА КОРРЕКТНЫЙ ВЫВОД

    except sqlite3.Error as e:
        print(f"Ошибка при извлечении данных: {e}")
    finally:
        conn.close()
        # print(f"Соединение с БД закрыто после отображения для {destination_name}.")


if __name__ == '__main__':
    # 1. Обновляем/создаем базу данных
    print("Starting database setup...")
    setup_database()
    print("Database setup finished.")

    # 2. Пример отображения данных (БЕЗ ОШИБОК ФОРМАТИРОВАНИЯ)
    # Вызовите эту функцию (или адаптируйте свою) для нужных направлений
    display_tours_for_destination("Дананг")
    display_tours_for_destination("Фукуок")
    # display_tours_for_destination("Нячанг") # Для проверки