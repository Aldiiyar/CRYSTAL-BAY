import asyncio
import os
import aiosqlite
import contextlib
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
# import datetime # <-- Раскомментируйте, если нужно для проверки високосного года позже

# --- Конфигурация ---
# !!! ВАЖНО: Убедитесь, что токен и имя БД верны !!!
BOT_TOKEN = '8168035111:AAH89w2v-QowtdKaCqemOcgCIgaaqi8Yjzk' # Используйте ваш реальный токен
DB_NAME = 'tours.db'

logging.basicConfig(level=logging.INFO) # Настройка логирования

if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN':
    raise ValueError("Не найден токен бота или используется токен по умолчанию. "
                     "Установите переменную BOT_TOKEN с вашим реальным токеном Telegram бота.")

# --- Проверка базы данных ---
if not os.path.exists(DB_NAME):
    raise FileNotFoundError(f"Файл базы данных '{DB_NAME}' не найден. "
                            f"Пожалуйста, сначала запустите скрипт настройки базы данных.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Состояния FSM ---
class UserState(StatesGroup):
    # --- Исходный поток выбора тура ---
    destination = State()     # Направление выбрано ('Все туры')
    departure = State()       # Вылет выбран (после направления в 'Все туры')

    # --- Поток горящих туров ---
    selecting_departure_for_random = State() # Выбор вылета после выбора случайного горящего тура

    # --- Общие состояния (используются несколькими потоками, включая фильтр) ---
    hotel_selected = State()  # Описание отеля показано, готов к выбору людей/фото/вылета(фильтр)
    people = State()          # Количество людей выбрано, готов к выбору месяца
    month = State()           # Месяц выбран, готов к выбору дня
    day = State()             # День выбран, готов к финальному итогу
    viewing_photos = State()  # Пользователь просматривает фото отеля

# --- НОВЫЕ СОСТОЯНИЯ для Фильтрации ---
class FilterState(StatesGroup):
    choosing_filter = State()               # Главный экран выбора фильтров
    choosing_budget = State()               # Выбор диапазона бюджета
    choosing_duration = State()             # Выбор длительности тура
    choosing_stars = State()                # Выбор звездности отеля
    showing_results = State()               # Отображение списка отфильтрованных результатов
    filtered_tour_selected = State()        # Показано описание отфильтрованного тура
    choosing_departure_for_filtered = State() # Выбор вылета после выбора отфильтрованного тура

# --- Вспомогательные функции для работы с БД ---

async def fetch_one(query, params=()):
    """Извлекает одну строку из базы данных."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row # Доступ к столбцам по имени
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()
    except aiosqlite.Error as e:
        logging.error(f"Ошибка БД fetch_one: {e}\nЗапрос: {query}\nПараметры: {params}")
        return None

async def fetch_all(query, params=()):
    """Извлекает все строки из базы данных."""
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()
    except aiosqlite.Error as e:
        logging.error(f"Ошибка БД fetch_all: {e}\nЗапрос: {query}\nПараметры: {params}")
        return [] # Возвращаем пустой список при ошибке


# --- Обработчики бота ---

@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    """Обработчик команды /start, показывает главное меню."""
    await state.clear() # Очищаем любое предыдущее состояние
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='🌍 Все туры', callback_data='all_tours'),
        types.InlineKeyboardButton(text='🔥 Горящие туры', callback_data='hot_tours'),
        types.InlineKeyboardButton(text='👨‍💼 Менеджеры', callback_data='managers'),
        types.InlineKeyboardButton(text='🔍 Найти тур', callback_data='find_tours_start') # Измененный callback
    )
    builder.adjust(2)

    await message.answer(
        '🌴 Приветствуем в CrystalBay! 🌴\n\n'
        'Ваш персональный гид по незабываемым путешествиям во Вьетнам!✨\n\n'
        'Мы подберем для вас лучшие туры, выгодные предложения и самые захватывающие маршруты. 🏝🏯🍜',
        reply_markup=builder.as_markup()
    )

# --- Навигация по главному меню ---

@dp.callback_query(F.data == 'start')
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню."""
    await state.clear() # Очищаем состояние при возврате в главное меню
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='🌍 Все туры', callback_data='all_tours'),
        types.InlineKeyboardButton(text='🔥 Горящие туры', callback_data='hot_tours'),
        types.InlineKeyboardButton(text='👨‍💼 Менеджеры', callback_data='managers'),
        types.InlineKeyboardButton(text='🔍 Найти тур', callback_data='find_tours_start')
    )
    builder.adjust(2)
    try:
        # Пытаемся отредактировать существующее сообщение
        await callback.message.edit_text(
            '🌴 Приветствуем в CrystalBay! 🌴\n\n'
            'Ваш персональный гид по незабываемым путешествиям во Вьетнам!✨\n\n'
            'Мы подберем для вас лучшие туры, выгодные предложения и самые захватывающие маршруты. 🏝🏯🍜',
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения в back_to_main: {e}")
        # Запасной вариант: Отправляем новое сообщение, если редактирование не удалось
        try:
            await callback.message.delete() # Пытаемся сначала удалить старое
        except Exception as del_e:
            logging.error(f"Ошибка удаления сообщения в back_to_main (запасной вариант): {del_e}")
        await callback.message.answer(
             '🌴 Приветствуем в CrystalBay! 🌴\n\n'
             'Ваш персональный гид по незабываемым путешествиям во Вьетнам!✨\n\n'
             'Мы подберем для вас лучшие туры, выгодные предложения и самые захватывающие маршруты. 🏝🏯🍜',
             reply_markup=builder.as_markup()
             )

    await callback.answer()

# ========================= ПОТОК "ВСЕ ТУРЫ" =========================

@dp.callback_query(F.data == 'all_tours')
async def all_tours(callback: types.CallbackQuery, state: FSMContext):
    """Отображает список городов для выбора."""
    # Сохраняем тип потока
    await state.update_data(is_hot=False, flow_type='all') # Указываем, что это поток "Все туры"

    # Сбрасываем состояние перед показом городов (исправление для "Назад к выбору города")
    await state.set_state(None)

    builder = InlineKeyboardBuilder()

    # Получаем список направлений из БД
    destinations = await fetch_all("SELECT destination_id, name FROM destinations ORDER BY name")

    if not destinations:
        await callback.answer("Направления не найдены в базе данных.", show_alert=True)
        return

    # Создаем кнопки для каждого направления
    emoji_map = {"Нячанг": "🌊", "Фукуок": "🏝", "Дананг": "🌅"}
    for dest in destinations:
        emoji = emoji_map.get(dest['name'], '📍')
        builder.add(
            types.InlineKeyboardButton(
                text=f"{emoji} {dest['name']}",
                callback_data=f"city_{dest['destination_id']}_{dest['name']}" # Передаем ID и Имя
            )
        )

    builder.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data='start')) # Кнопка Назад в главное меню
    builder.adjust(1) # Кнопки в один столбец

    try:
        # Редактируем сообщение, показывая список городов
        await callback.message.edit_text(
            'Выберите город, чтобы узнать подробности о турах 🏖:',
            reply_markup=builder.as_markup()
        )
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения в all_tours: {e}")
        # Запасной вариант, если редактирование не удалось
        try:
            await callback.message.delete()
        except Exception as del_e:
            logging.error(f"Ошибка удаления сообщения в all_tours (запасной вариант): {del_e}")
        await callback.message.answer(
            'Выберите город, чтобы узнать подробности о турах 🏖:',
            reply_markup=builder.as_markup()
        )

    await callback.answer() # Отвечаем на callback

# Разрешаем срабатывать из StateFilter(None) ИЛИ UserState.departure
# Это нужно, чтобы кнопка "Назад к выбору вылета" из списка отелей работала.
@dp.callback_query(F.data.startswith('city_'), StateFilter(None, UserState.departure))
async def city_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города и показывает выбор города вылета."""
    parts = callback.data.split('_')
    try:
        destination_id = int(parts[1])
        # Обрабатываем названия городов, которые могут содержать '_'
        destination_name = '_'.join(parts[2:])
        if not destination_name: raise ValueError("Имя направления пустое")
    except (ValueError, IndexError) as e:
        logging.error(f"Не удалось разобрать данные города из callback_data: {callback.data}, ошибка: {e}")
        await callback.answer("Ошибка при выборе города.", show_alert=True)
        return

    # Получаем текущие данные state, чтобы не перезаписать существующие нужные данные,
    # если мы пришли сюда через кнопку "Назад к выбору вылета"
    current_data = await state.get_data()
    current_data.update({
        'destination_id': destination_id,
        'destination_name': destination_name,
        'is_hot': False, # Убеждаемся, что флаг горящего тура сброшен для этого потока
        'flow_type': 'all'  # Убеждаемся, что тип потока правильный ('all')
    })

    # Обновляем состояние FSM
    await state.set_data(current_data) # Записываем обновленные данные
    await state.set_state(UserState.destination) # Устанавливаем состояние "направление выбрано"

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='🏙 Астана', callback_data=f'departure_Астана'),
        types.InlineKeyboardButton(text='🌄 Алматы', callback_data=f'departure_Алматы'),
        types.InlineKeyboardButton(text='🏔 Шымкент', callback_data=f'departure_Шымкент'),
    )
    # Кнопка "Назад к выбору города" по-прежнему ведет в all_tours
    builder.add(types.InlineKeyboardButton(text='⬅ Назад к выбору города', callback_data='all_tours'))
    builder.adjust(1)

    await callback.message.edit_text(
        f"✈️ Вы выбрали направление: {destination_name}\n\n"
        "Теперь выберите город отправления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# ####################################################################################### #
# ### ИЗМЕНЕНИЕ: Разрешаем срабатывать из StateFilter(UserState.destination) ИЛИ UserState.hotel_selected ### #
# ####################################################################################### #
# Это нужно, чтобы кнопка "Назад к выбору отеля" из описания отеля работала.
@dp.callback_query(F.data.startswith('departure_'), StateFilter(UserState.destination, UserState.hotel_selected))
async def departure_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города вылета и показывает список отелей."""
    # Извлекаем город вылета из callback_data
    departure_city = callback.data.split('_')[1]

    # Получаем нужные данные из state
    user_data = await state.get_data()
    destination_id = user_data.get('destination_id')
    destination_name = user_data.get('destination_name')
    flow_type = user_data.get('flow_type') # Получаем тип потока

    # Проверка, что нужные данные есть в состоянии
    if not destination_id or not destination_name or not flow_type:
        logging.error(f"Отсутствуют данные направления/потока в состоянии (departure_choice): {user_data}")
        await callback.message.edit_text("Ошибка: Не удалось определить направление. Попробуйте снова /start.")
        await callback.answer("Ошибка состояния", show_alert=True)
        await state.clear()
        return

    # Обновляем город вылета в state (если пришли из hotel_selected, он уже может быть там, но перезапись не повредит)
    # и устанавливаем правильное состояние
    await state.update_data(departure=departure_city)
    await state.set_state(UserState.departure) # Устанавливаем состояние "вылет выбран"

    # Запрос туров для выбранного направления
    query = """
        SELECT
            t.tour_id, t.price_per_person, t.hot_tour_discount_multiplier,
            h.hotel_id, h.display_name, h.stars
        FROM tours t
        JOIN hotels h ON t.hotel_id = h.hotel_id
        WHERE t.destination_id = ?
        ORDER BY h.stars DESC, h.display_name;
    """
    params = (destination_id,)
    available_tours = await fetch_all(query, params)

    # Если туры не найдены
    if not available_tours:
        back_builder = InlineKeyboardBuilder()
        # Кнопка назад к выбору вылета - callback теперь city_{id}_{name}
        back_builder.add(types.InlineKeyboardButton(
            text='⬅ Назад к выбору вылета',
            callback_data=f'city_{destination_id}_{destination_name}' # Используем сохраненные ID и имя
        ))
        await callback.message.edit_text(
             f"Извините, туры для направления '{destination_name}' не найдены.",
             reply_markup=back_builder.as_markup()
        )
        await callback.answer("Туры не найдены", show_alert=True)
        return

    # Создаем кнопки для каждого тура/отеля
    builder = InlineKeyboardBuilder()
    for tour in available_tours:
        base_price = tour['price_per_person'] # Базовая цена за человека
        display_name = tour['display_name']
        hotel_id = tour['hotel_id']
        discount_multiplier = tour['hot_tour_discount_multiplier']

        # ================== ИЗМЕНЕНИЕ ЛОГИКИ СКИДКИ В КНОПКЕ ==================
        # В потоке "Все туры" показываем только базовую цену в кнопке.
        # Для других потоков (если бы они сюда попали) оставляем логику скидки.
        # Однако, этот обработчик сейчас вызывается только из потока 'all'.
        # Поэтому можно просто убрать зачеркивание для всех случаев здесь.

        button_text = f"🏨 {display_name} - {base_price}₸"
        # Если это горящий тур (даже во "Всех турах"), добавим огонек для индикации
        if discount_multiplier < 1.0:
            button_text += " 🔥"

        # Старая логика (закомментирована):
        # if discount_multiplier < 1.0:
        #     discounted_price = round(base_price * discount_multiplier)
        #     discount_percent = int((1 - discount_multiplier) * 100)
        #     button_text = f"🏨 {display_name} - {discounted_price}₸ (<s>{base_price}₸</s> -{discount_percent}%)🔥"
        # else:
        #     button_text = f"🏨 {display_name} - {base_price}₸"
        # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ СКИДКИ В КНОПКЕ ==================

        builder.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f'hotel_{hotel_id}' # Передаем hotel_id
        ))

    # Кнопка назад к выбору вылета - callback теперь city_{id}_{name}
    # Эта кнопка будет вызывать обработчик city_choice
    builder.add(types.InlineKeyboardButton(
        text='⬅ Назад к выбору вылета',
        callback_data=f'city_{destination_id}_{destination_name}'
    ))
    builder.adjust(1)

    await callback.message.edit_text(
        f"🌍 Туры в {destination_name} (вылет из {departure_city}):\n\nВыберите отель:",
        reply_markup=builder.as_markup(),
        parse_mode='HTML' # Оставляем HTML на случай, если решим вернуть теги или для 🔥
    )
    await callback.answer()


# ===================== ПОТОК "ГОРЯЩИЕ ТУРЫ" =====================
# (Без изменений в этой секции - ОСТАВЛЯЕМ зачеркивание)
@dp.callback_query(F.data == 'hot_tours')
async def hot_tours_random_offers(callback: types.CallbackQuery, state: FSMContext):
    """Показывает случайные горящие предложения."""
    # Сохраняем тип потока
    await state.update_data(is_hot=True, flow_type='hot_random') # Тип потока 'hot_random'
    builder = InlineKeyboardBuilder()

    # Определяем ID целевых направлений
    target_cities = ['Нячанг', 'Фукуок', 'Дананг']
    placeholders = ','.join('?' for city in target_cities)
    query_dest_ids = f"SELECT destination_id, name FROM destinations WHERE name IN ({placeholders})"
    dest_rows = await fetch_all(query_dest_ids, target_cities)
    destination_map = {row['name']: row['destination_id'] for row in dest_rows}
    if len(destination_map) != len(target_cities):
        logging.warning(f"Не удалось найти ID для всех целевых городов: {target_cities}. Найдено: {destination_map.keys()}")

    # Запрос всех актуальных горящих туров (со скидкой)
    # Используем price_per_person
    query_hot_tours = """
        SELECT
            t.tour_id, t.destination_id, t.hotel_id, t.price_per_person,
            t.hot_tour_discount_multiplier,
            h.display_name AS hotel_name, d.name AS destination_name
        FROM tours t
        JOIN hotels h ON t.hotel_id = h.hotel_id
        JOIN destinations d ON t.destination_id = d.destination_id
        WHERE t.hot_tour_discount_multiplier < 1.0 -- Только туры со скидкой
        ORDER BY d.name, h.display_name;
    """
    all_hot_tours = await fetch_all(query_hot_tours)

    # Если горящих туров нет
    if not all_hot_tours:
        builder.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data='start'))
        await callback.message.edit_text(
             "🔥 К сожалению, сейчас нет активных горящих туров.",
             reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    # Группируем туры по направлению
    tours_by_destination = {}
    for tour in all_hot_tours:
        dest_id = tour['destination_id']
        if dest_id not in tours_by_destination:
            tours_by_destination[dest_id] = []
        tours_by_destination[dest_id].append(tour)

    # Выбираем по одному случайному туру для каждого целевого направления, если там есть туры
    selected_random_tours = []
    target_destination_ids = [destination_map.get(city) for city in target_cities if destination_map.get(city)]

    for dest_id in target_destination_ids:
        if dest_id in tours_by_destination and tours_by_destination[dest_id]:
            try:
                chosen_tour = random.choice(tours_by_destination[dest_id])
                selected_random_tours.append(chosen_tour)
                # Опционально: Удалить выбранный тур, чтобы избежать дубликатов, если нужно
                # tours_by_destination[dest_id].remove(chosen_tour)
            except IndexError: # Не должно произойти, если список не пуст, но для безопасности
                 logging.warning(f"IndexError при выборе случайного тура для dest_id {dest_id}, список мог быть неожиданно пуст.")

    # Если не удалось выбрать ни одного случайного тура (например, все скидки не в целевых городах)
    if not selected_random_tours:
        builder.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data='start'))
        await callback.message.edit_text(
             f"🔥 К сожалению, сейчас нет горящих туров в Нячанге, Фукуоке или Дананге.",
             reply_markup=builder.as_markup()
        )
        await callback.answer()
        return

    # Формируем текст и кнопки для выбранных предложений
    offer_texts = ["🔥 <b>Случайные горящие предложения:</b>\n"]
    emoji_map = {"Нячанг": "🌊", "Фукуок": "🏝", "Дананг": "🌅"}

    for tour in selected_random_tours:
        base_price = tour['price_per_person'] # Используем price_per_person
        discount_multiplier = tour['hot_tour_discount_multiplier']
        discounted_price = round(base_price * discount_multiplier)
        discount_percent = int((1 - discount_multiplier) * 100)
        dest_name = tour['destination_name']
        hotel_name = tour['hotel_name']
        emoji = emoji_map.get(dest_name, '📍')

        # Текст для кнопки
        button_text = (f"{emoji} {hotel_name} ({dest_name})\n"
                       f"~{discounted_price}₸ (-{discount_percent}%)")
        # Текст для общего описания (ЗДЕСЬ ОСТАВЛЯЕМ ЗАЧЕРКИВАНИЕ <s>)
        offer_texts.append(f"• {hotel_name} ({dest_name}): <s>{base_price}₸</s> {discounted_price}₸ (-{discount_percent}%)")

        builder.add(types.InlineKeyboardButton(
            text=button_text,
            callback_data=f"randomhot_{tour['tour_id']}" # Используем tour_id
        ))

    builder.add(types.InlineKeyboardButton(text='⬅ Назад', callback_data='start'))
    builder.adjust(1)

    final_text = "\n".join(offer_texts) + "\n\nВыберите одно из предложений, чтобы продолжить:"

    await callback.message.edit_text(
        final_text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML' # HTML нужен для <s> и <b>
    )
    await callback.answer()


@dp.callback_query(F.data.startswith('randomhot_'))
async def random_hot_tour_selected(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор случайного горящего тура, запрашивает город вылета."""
    try:
        tour_id = int(callback.data.split('_')[1])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать tour_id из randomhot callback: {callback.data}")
        await callback.answer("Ошибка при выборе предложения.", show_alert=True)
        return

    # Сохраняем ID оригинального тура для кнопки "Назад"
    await state.update_data(selected_tour_id_origin=tour_id)
    await state.set_state(UserState.selecting_departure_for_random) # Состояние выбора вылета для случайного тура

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='🏙 Астана', callback_data=f'departure_for_random_{tour_id}_Астана'),
        types.InlineKeyboardButton(text='🌄 Алматы', callback_data=f'departure_for_random_{tour_id}_Алматы'),
        types.InlineKeyboardButton(text='🏔 Шымкент', callback_data=f'departure_for_random_{tour_id}_Шымкент'),
    )
    # Кнопка назад к списку спецпредложений
    builder.add(types.InlineKeyboardButton(text='⬅ Назад к спецпредложениям', callback_data='hot_tours'))
    builder.adjust(1)

    await callback.message.edit_text(
        f"🔥 Отличное предложение!\n\n"
        "✈️ Теперь выберите город отправления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith('departure_for_random_'), StateFilter(UserState.selecting_departure_for_random))
async def departure_for_random_tour_chosen(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор города вылета для случайного горящего тура и показывает описание отеля."""
    try:
        parts = callback.data.split('_')
        tour_id = int(parts[3])
        departure_city = parts[4]
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать данные из departure_for_random callback: {callback.data}")
        await callback.answer("Ошибка при выборе города вылета.", show_alert=True)
        return

    # Запрашиваем детали тура по tour_id
    # Используем price_per_person
    query = """
        SELECT
            t.price_per_person, t.hot_tour_discount_multiplier, t.destination_id, t.hotel_id,
            h.display_name AS hotel_display_name, h.description AS hotel_description,
            d.name AS destination_name
        FROM tours t
        JOIN hotels h ON t.hotel_id = h.hotel_id
        JOIN destinations d ON t.destination_id = d.destination_id
        WHERE t.tour_id = ?
    """
    tour_details = await fetch_one(query, (tour_id,))

    if not tour_details:
        logging.error(f"Не удалось получить детали для tour_id {tour_id} после случайного выбора.")
        await callback.message.edit_text("Произошла ошибка при загрузке деталей тура. Попробуйте снова.",
                                         reply_markup=InlineKeyboardBuilder().add(
                                             types.InlineKeyboardButton(text='⬅ Назад', callback_data='hot_tours')
                                         ).as_markup())
        await state.clear() # Сбрасываем состояние при ошибке
        await callback.answer("Ошибка загрузки тура", show_alert=True)
        return

    # Рассчитываем цену (ЗДЕСЬ ОСТАВЛЯЕМ ЗАЧЕРКИВАНИЕ <s>)
    base_price = tour_details['price_per_person'] # Базовая цена
    hot_discount_multiplier = tour_details['hot_tour_discount_multiplier']
    final_discount_multiplier = hot_discount_multiplier # В этом потоке скидка всегда есть
    discounted_price = round(base_price * final_discount_multiplier)
    discount_percent = int((1 - final_discount_multiplier) * 100)
    price_text = f"🔥 <s>{base_price}₸</s> {discounted_price}₸ (-{discount_percent}%)"

    # Сохраняем все необходимые данные в state
    # flow_type='hot_random' и is_hot=True уже установлены
    # selected_tour_id_origin уже установлен
    await state.update_data(
        departure=departure_city,
        hotel_id=tour_details['hotel_id'],
        hotel_display_name=tour_details['hotel_display_name'],
        # Сохраняем описание, чтобы не запрашивать снова при возврате
        description=tour_details['hotel_description'],
        base_price=base_price, # Сохраняем базовую цену (price_per_person)
        hot_discount_multiplier=hot_discount_multiplier, # Сохраняем множитель скидки
        final_discount_multiplier=final_discount_multiplier, # Сохраняем итоговый множитель
        destination_id=tour_details['destination_id'],
        destination_name=tour_details['destination_name'],
        # Добавляем is_hot=True здесь, т.к. это горящий тур
        is_hot=True
    )
    await state.set_state(UserState.hotel_selected) # Переход к общему состоянию показа отеля

    # --- Кнопки ---
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='👥 Выбрать количество людей', callback_data='choose_people'),
        types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{tour_details["hotel_id"]}'),
        # Кнопка "Назад" должна вернуть к выбору города вылета для ЭТОГО тура
        types.InlineKeyboardButton(
            text='⬅ Назад (выбор вылета)',
            # Используем оригинальный tour_id, сохраненный ранее
            callback_data=f'randomhot_{tour_id}'
        )
    )
    builder.adjust(1)

    # --- Отображение информации об отеле ---
    display_name = tour_details['hotel_display_name']
    description = tour_details['hotel_description']

    await callback.message.edit_text(
        f"🏨 <b>{display_name}</b>\n"
        f"📍 {tour_details['destination_name']} (Вылет из {departure_city})\n\n"
        f"{description or 'Описание недоступно.'}\n\n"
        f"💰 <b>Цена за 1 человека:</b> {price_text}", # Используем price_text с зачеркиванием
        parse_mode='HTML', # HTML нужен для <s> и <b>
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# ================== ПОТОК ФИЛЬТРАЦИИ ("НАЙТИ ТУР") ==================
# (Без изменений в этой секции - ОСТАВЛЯЕМ зачеркивание, если тур со скидкой)

async def show_main_filter_menu(message_or_callback: types.Message | types.CallbackQuery, state: FSMContext, is_edit: bool = True):
    """Отображает главное меню фильтра с текущими выбранными параметрами."""
    message = message_or_callback if isinstance(message_or_callback, types.Message) else message_or_callback.message

    user_data = await state.get_data()
    selected_filters = user_data.get('selected_filters', {'budget': None, 'duration': None, 'stars': None})

    # --- Форматируем текст кнопок с учетом текущего выбора ---
    budget_text = "💰 Фильтр по Бюджету"
    if selected_filters.get('budget'):
        b_filter = selected_filters['budget']
        if b_filter == '0-300000': budget_text += " (<300k)"
        elif b_filter == '300000-500000': budget_text += " (300-500k)"
        elif b_filter == '500000-inf': budget_text += " (500k+)"

    duration_text = "⏳ Фильтр по Длительности"
    if selected_filters.get('duration'):
        duration_text += f" ({selected_filters['duration']} дн.)"

    stars_text = "⭐ Фильтр по Звездам"
    if selected_filters.get('stars'):
        stars_text += f" ({selected_filters['stars']}★)"

    # --- Собираем клавиатуру ---
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text=budget_text, callback_data='filter_budget'))
    builder.row(types.InlineKeyboardButton(text=duration_text, callback_data='filter_duration'))
    builder.row(types.InlineKeyboardButton(text=stars_text, callback_data='filter_stars'))
    builder.row(
        types.InlineKeyboardButton(text='✅ Показать туры', callback_data='filter_show'),
        types.InlineKeyboardButton(text='🔄 Сбросить', callback_data='filter_reset')
    )
    builder.row(types.InlineKeyboardButton(text='⬅ Назад в меню', callback_data='start'))

    # --- Текст сообщения ---
    current_filters_text = "Текущие фильтры:\n"
    has_filters = False
    if selected_filters.get('budget'):
        # Извлекаем текст в скобках для отображения
        current_filters_text += f" - Бюджет: {budget_text.split('(')[1][:-1]}\n"
        has_filters = True
    if selected_filters.get('duration'):
        current_filters_text += f" - Длительность: {selected_filters['duration']} дн.\n"
        has_filters = True
    if selected_filters.get('stars'):
        current_filters_text += f" - Звезды: {selected_filters['stars']}★\n"
        has_filters = True

    if not has_filters:
        current_filters_text = "Фильтры не выбраны.\n"

    final_text = f"🔍 <b>Поиск тура по параметрам</b>\n\n{current_filters_text}\nВыберите фильтр для настройки или нажмите 'Показать туры'."

    # --- Отправляем или редактируем сообщение ---
    if is_edit:
        try:
            await message.edit_text(final_text, reply_markup=builder.as_markup(), parse_mode='HTML')
        except Exception as e:
            logging.error(f"Ошибка редактирования сообщения в show_main_filter_menu: {e}")
            # Запасной вариант: отправляем новое сообщение
            await message.answer(final_text, reply_markup=builder.as_markup(), parse_mode='HTML')
            # Попытка удалить старое сообщение callback'а, если возможно
            if isinstance(message_or_callback, types.CallbackQuery):
                 with contextlib.suppress(Exception): await message_or_callback.message.delete()
    else:
        await message.answer(final_text, reply_markup=builder.as_markup(), parse_mode='HTML')

    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.answer()


# --- Запуск потока фильтрации ---
@dp.callback_query(F.data == 'find_tours_start')
async def find_tours_start(callback: types.CallbackQuery, state: FSMContext):
    """Начинает процесс фильтрации туров."""
    # Инициализируем фильтры и устанавливаем тип потока
    await state.update_data(selected_filters={}, flow_type='filter') # Тип потока 'filter'
    await state.set_state(FilterState.choosing_filter) # Устанавливаем состояние выбора фильтра
    # Показываем главное меню фильтра
    await show_main_filter_menu(callback, state, is_edit=True)
    # await callback.answer() # answer вызывается внутри show_main_filter_menu

# --- Обработчики кнопок выбора типа фильтра ---
@dp.callback_query(F.data == 'filter_budget', StateFilter(FilterState.choosing_filter))
async def filter_budget_options(callback: types.CallbackQuery, state: FSMContext):
    """Показывает опции для фильтра по бюджету."""
    await state.set_state(FilterState.choosing_budget) # Устанавливаем состояние выбора бюджета
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="До 300 000 ₸", callback_data="budget_0-300000"))
    builder.row(types.InlineKeyboardButton(text="300 000 - 500 000 ₸", callback_data="budget_300000-500000"))
    builder.row(types.InlineKeyboardButton(text="Более 500 000 ₸", callback_data="budget_500000-inf"))
    builder.row(types.InlineKeyboardButton(text="Любой бюджет", callback_data="budget_any")) # Сброс фильтра
    builder.row(types.InlineKeyboardButton(text="⬅ Назад к фильтрам", callback_data="back_to_main_filter"))
    await callback.message.edit_text("💰 Выберите ценовой диапазон (на человека):", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == 'filter_duration', StateFilter(FilterState.choosing_filter))
async def filter_duration_options(callback: types.CallbackQuery, state: FSMContext):
    """Показывает опции для фильтра по длительности."""
    await state.set_state(FilterState.choosing_duration) # Устанавливаем состояние выбора длительности
    # Вариант 1: Заранее заданные значения
    durations = [7, 10, 14]
    # Вариант 2: Получить уникальные значения из БД (может быть медленно при больших данных)
    # distinct_durations = await fetch_all("SELECT DISTINCT duration_days FROM tours ORDER BY duration_days")
    # durations = [d['duration_days'] for d in distinct_durations if d['duration_days']]

    builder = InlineKeyboardBuilder()
    buttons = [types.InlineKeyboardButton(text=f"{d} дней", callback_data=f"duration_{d}") for d in durations]
    # Можно расположить в несколько рядов, если много опций
    if len(buttons) <= 3:
        builder.row(*buttons)
    else:
        builder.row(*buttons[:len(buttons)//2])
        builder.row(*buttons[len(buttons)//2:])

    builder.row(types.InlineKeyboardButton(text="Любая", callback_data="duration_any")) # Сброс фильтра
    builder.row(types.InlineKeyboardButton(text="⬅ Назад к фильтрам", callback_data="back_to_main_filter"))
    await callback.message.edit_text("⏳ Выберите продолжительность тура:", reply_markup=builder.as_markup())
    await callback.answer()

@dp.callback_query(F.data == 'filter_stars', StateFilter(FilterState.choosing_filter))
async def filter_stars_options(callback: types.CallbackQuery, state: FSMContext):
    """Показывает опции для фильтра по звездности отеля."""
    await state.set_state(FilterState.choosing_stars) # Устанавливаем состояние выбора звезд
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="3 ★", callback_data="stars_3"),
        types.InlineKeyboardButton(text="4 ★", callback_data="stars_4"),
        types.InlineKeyboardButton(text="5 ★", callback_data="stars_5")
    )
    builder.row(types.InlineKeyboardButton(text="Любые звезды", callback_data="stars_any")) # Сброс фильтра
    builder.row(types.InlineKeyboardButton(text="⬅ Назад к фильтрам", callback_data="back_to_main_filter"))
    await callback.message.edit_text("⭐ Выберите категорию отеля:", reply_markup=builder.as_markup())
    await callback.answer()

# --- Обработчик для возврата к главному меню фильтра ---
# Срабатывает из состояний выбора конкретного параметра фильтра
@dp.callback_query(F.data == 'back_to_main_filter', StateFilter(
    FilterState.choosing_budget,
    FilterState.choosing_duration,
    FilterState.choosing_stars
))
async def back_to_main_filter_handler(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает пользователя к главному меню фильтрации."""
    await state.set_state(FilterState.choosing_filter) # Возвращаем в состояние выбора фильтра
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем меню
    # await callback.answer() # answer вызывается внутри show_main_filter_menu

# --- Обработчики выбора конкретных значений фильтров ---
@dp.callback_query(F.data.startswith('budget_'), StateFilter(FilterState.choosing_budget))
async def set_budget_filter(callback: types.CallbackQuery, state: FSMContext):
    """Устанавливает значение фильтра по бюджету и возвращает в главное меню фильтра."""
    budget_value = callback.data.split('_')[1]
    user_data = await state.get_data()
    selected_filters = user_data.get('selected_filters', {})
    if budget_value == 'any':
        selected_filters['budget'] = None # Убираем фильтр
    else:
        selected_filters['budget'] = budget_value # Устанавливаем значение
    await state.update_data(selected_filters=selected_filters) # Сохраняем в FSM
    await state.set_state(FilterState.choosing_filter) # Возвращаем в состояние выбора фильтра
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем обновленное меню
    await callback.answer("Бюджет выбран") # Краткое уведомление

@dp.callback_query(F.data.startswith('duration_'), StateFilter(FilterState.choosing_duration))
async def set_duration_filter(callback: types.CallbackQuery, state: FSMContext):
    """Устанавливает значение фильтра по длительности и возвращает в главное меню фильтра."""
    duration_value = callback.data.split('_')[1]
    user_data = await state.get_data()
    selected_filters = user_data.get('selected_filters', {})
    if duration_value == 'any':
        selected_filters['duration'] = None # Убираем фильтр
    else:
        try:
            selected_filters['duration'] = int(duration_value) # Устанавливаем значение (число)
        except ValueError:
            logging.error(f"Неверное значение длительности: {duration_value}")
            await callback.answer("Неверное значение длительности.", show_alert=True)
            return # Остаемся в том же состоянии выбора длительности
    await state.update_data(selected_filters=selected_filters) # Сохраняем в FSM
    await state.set_state(FilterState.choosing_filter) # Возвращаем в состояние выбора фильтра
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем обновленное меню
    await callback.answer("Длительность выбрана") # Краткое уведомление

@dp.callback_query(F.data.startswith('stars_'), StateFilter(FilterState.choosing_stars))
async def set_stars_filter(callback: types.CallbackQuery, state: FSMContext):
    """Устанавливает значение фильтра по звездам и возвращает в главное меню фильтра."""
    stars_value = callback.data.split('_')[1]
    user_data = await state.get_data()
    selected_filters = user_data.get('selected_filters', {})
    if stars_value == 'any':
        selected_filters['stars'] = None # Убираем фильтр
    else:
        try:
            selected_filters['stars'] = int(stars_value) # Устанавливаем значение (число)
        except ValueError:
            logging.error(f"Неверное значение звезд: {stars_value}")
            await callback.answer("Неверное значение звезд.", show_alert=True)
            return # Остаемся в том же состоянии выбора звезд
    await state.update_data(selected_filters=selected_filters) # Сохраняем в FSM
    await state.set_state(FilterState.choosing_filter) # Возвращаем в состояние выбора фильтра
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем обновленное меню
    await callback.answer("Звезды выбраны") # Краткое уведомление

# --- Обработчик сброса фильтров ---
@dp.callback_query(F.data == 'filter_reset', StateFilter(FilterState.choosing_filter))
async def reset_filters(callback: types.CallbackQuery, state: FSMContext):
    """Сбрасывает все выбранные фильтры."""
    await state.update_data(selected_filters={}) # Очищаем словарь фильтров в FSM
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем меню без фильтров
    await callback.answer("Фильтры сброшены")

# --- Вспомогательная функция для построения SQL-запроса на основе фильтров ---
def build_filter_query(filters: dict):
    """Строит SQL-запрос и параметры на основе выбранных фильтров."""
    # Базовый запрос для выборки туров с информацией об отелях и направлениях
    base_query = """
        SELECT
            t.tour_id, t.price_per_person, t.duration_days,
            t.hot_tour_discount_multiplier, t.destination_id, t.hotel_id,
            h.display_name, h.stars, d.name as destination_name
        FROM tours t
        JOIN hotels h ON t.hotel_id = h.hotel_id
        JOIN destinations d ON t.destination_id = d.destination_id
    """
    where_clauses = [] # Список условий WHERE
    params = []        # Список параметров для запроса

    # Фильтр по Бюджету (price_per_person)
    budget = filters.get('budget')
    if budget:
        if budget == '0-300000':
            where_clauses.append("t.price_per_person < ?")
            params.append(300000)
        elif budget == '300000-500000':
            where_clauses.append("t.price_per_person >= ? AND t.price_per_person <= ?")
            params.extend([300000, 500000])
        elif budget == '500000-inf':
            where_clauses.append("t.price_per_person > ?")
            params.append(500000)
        # 'any' бюджет не требует условия

    # Фильтр по Длительности (duration_days)
    duration = filters.get('duration')
    if duration: # duration уже int, если не None
        where_clauses.append("t.duration_days = ?")
        params.append(duration)

    # Фильтр по Звездам (h.stars)
    stars = filters.get('stars')
    if stars: # stars уже int, если не None
        where_clauses.append("h.stars = ?")
        params.append(stars)

    # Собираем итоговый запрос
    query = base_query
    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses) # Добавляем условия через AND

    query += " ORDER BY d.name, h.stars DESC, t.price_per_person;" # Сортировка по умолчанию

    return query, tuple(params) # Возвращаем запрос и кортеж параметров

# --- Обработчик кнопки "Показать туры" ---
@dp.callback_query(F.data == 'filter_show', StateFilter(FilterState.choosing_filter))
async def show_filtered_tours(callback: types.CallbackQuery, state: FSMContext):
    """Показывает список туров, отфильтрованных по заданным критериям."""
    user_data = await state.get_data()
    selected_filters = user_data.get('selected_filters', {})

    # Строим и выполняем запрос к БД
    query, params = build_filter_query(selected_filters)
    logging.info(f"Выполнение запроса фильтра: {query} с параметрами: {params}")
    results = await fetch_all(query, params)

    builder = InlineKeyboardBuilder()

    # Если туры не найдены
    if not results:
        await callback.answer("Туры по вашим критериям не найдены.", show_alert=True)
        # Остаемся в том же состоянии `choosing_filter`, чтобы пользователь мог изменить фильтры.
        # Не меняем сообщение, чтобы пользователь видел свои фильтры и понял, что ничего не найдено.
        return # Просто выходим, сообщение не меняем

    # --- Отображение результатов ---
    results_text = "🔍 <b>Результаты поиска:</b>\n\n"
    emoji_map = {"Нячанг": "🌊", "Фукуок": "🏝", "Дананг": "🌅"}
    count = 0
    for tour in results:
        count += 1
        base_price = tour['price_per_person']
        discount_multiplier = tour['hot_tour_discount_multiplier']
        dest_name = tour['destination_name']
        hotel_name = tour['display_name']
        stars = tour['stars']
        duration = tour['duration_days']
        emoji = emoji_map.get(dest_name, '📍')

        # Форматируем цену с учетом возможной скидки (ЗДЕСЬ ОСТАВЛЯЕМ ЗАЧЕРКИВАНИЕ <s>)
        price_str = f"{base_price}₸"
        if discount_multiplier < 1.0:
            discounted_price = round(base_price * discount_multiplier)
            discount_percent = int((1 - discount_multiplier) * 100)
            price_str = f"<s>{base_price}</s> {discounted_price}₸ 🔥(-{discount_percent}%)"

        # Добавляем информацию о туре в текст
        results_text += (f"{count}. {emoji}<b>{hotel_name} ({stars}★)</b> - {dest_name}\n"
                         f"    ⏳ {duration} дн. | 💰 ~{price_str} / чел.\n\n")

        # Добавляем кнопку для выбора этого тура
        builder.add(types.InlineKeyboardButton(
            text=f"{count}. {hotel_name}",
            callback_data=f"filtered_tour_{tour['tour_id']}" # Передаем ID тура
        ))

    # Добавляем кнопку Назад к Фильтрам
    builder.row(types.InlineKeyboardButton(text="⬅ Назад к фильтрам", callback_data="back_to_filters"))
    builder.adjust(1) # Каждая кнопка тура на своей строке

    await callback.message.edit_text(
        results_text,
        reply_markup=builder.as_markup(),
        parse_mode='HTML' # HTML нужен для <s> и <b>
    )
    await state.set_state(FilterState.showing_results) # Устанавливаем состояние показа результатов
    await callback.answer(f"Найдено туров: {len(results)}")

# --- Обработчик возврата к фильтрам из списка результатов ---
@dp.callback_query(F.data == 'back_to_filters', StateFilter(FilterState.showing_results))
async def back_to_filters_from_results(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает пользователя из списка результатов к главному меню фильтра."""
    await state.set_state(FilterState.choosing_filter) # Возвращаем в состояние выбора фильтра
    await show_main_filter_menu(callback, state, is_edit=True) # Показываем главное меню фильтра
    # await callback.answer() # answer вызывается внутри show_main_filter_menu

# --- Обработчик выбора конкретного тура из отфильтрованного списка ---
@dp.callback_query(F.data.startswith('filtered_tour_'), StateFilter(FilterState.showing_results))
async def select_filtered_tour(callback: types.CallbackQuery, state: FSMContext):
    """Показывает детальное описание выбранного отфильтрованного тура."""
    try:
        tour_id = int(callback.data.split('_')[2])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать tour_id из filtered_tour callback: {callback.data}")
        await callback.answer("Ошибка при выборе тура.", show_alert=True)
        return

    # Запрашиваем полные детали для этого конкретного тура по tour_id
    # Используем price_per_person, duration_days
    query = """
        SELECT
            t.price_per_person, t.duration_days, t.hot_tour_discount_multiplier,
            t.destination_id, t.hotel_id,
            h.display_name AS hotel_display_name, h.description AS hotel_description, h.stars,
            d.name AS destination_name
        FROM tours t
        JOIN hotels h ON t.hotel_id = h.hotel_id
        JOIN destinations d ON t.destination_id = d.destination_id
        WHERE t.tour_id = ?
    """
    tour_details = await fetch_one(query, (tour_id,))

    if not tour_details:
        logging.error(f"Не удалось получить детали для отфильтрованного tour_id {tour_id}.")
        # Кнопка Назад теперь ведет к фильтрам, а не результатам, т.к. мы не смогли загрузить тур
        await callback.message.edit_text("Произошла ошибка при загрузке деталей тура. Попробуйте снова.",
                                         reply_markup=InlineKeyboardBuilder().add(
                                             types.InlineKeyboardButton(text='⬅ Назад к фильтрам', callback_data='back_to_filters')
                                         ).as_markup())
        # Возвращаемся в состояние выбора фильтров
        await state.set_state(FilterState.choosing_filter)
        await callback.answer("Ошибка загрузки тура", show_alert=True)
        return

    # --- Рассчитываем цену (ЗДЕСЬ ОСТАВЛЯЕМ ЗАЧЕРКИВАНИЕ <s>, если есть скидка) ---
    base_price = tour_details['price_per_person']
    hot_discount_multiplier = tour_details['hot_tour_discount_multiplier']
    # Даже отфильтрованный тур может иметь скидку
    final_discount_multiplier = hot_discount_multiplier if hot_discount_multiplier < 1.0 else 1.0
    price_per_person_final = round(base_price * final_discount_multiplier)

    price_text = f"{price_per_person_final}₸"
    if final_discount_multiplier < 1.0:
        discount_percent = int((1 - final_discount_multiplier) * 100)
        price_text = f"🔥 <s>{base_price}₸</s> {price_per_person_final}₸ (-{discount_percent}%)"

    # --- Обновляем состояние (основная информация о туре) ---
    # flow_type='filter' уже установлен
    await state.update_data(
        # departure=None, # Город вылета ЕЩЕ НЕ выбран
        hotel_id=tour_details['hotel_id'],
        hotel_display_name=tour_details['hotel_display_name'],
        description=tour_details['hotel_description'], # Сохраняем описание
        base_price=base_price,
        hot_discount_multiplier=hot_discount_multiplier,
        final_discount_multiplier=final_discount_multiplier,
        destination_id=tour_details['destination_id'],
        destination_name=tour_details['destination_name'],
        duration_days=tour_details['duration_days'], # Сохраняем длительность
        is_hot=(final_discount_multiplier < 1.0) # Устанавливаем флаг горящего тура
    )
    await state.set_state(FilterState.filtered_tour_selected) # Новое состояние: выбран отфильтрованный тур

    # --- Собираем кнопки ---
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='✈️ Выбрать город вылета', callback_data='choose_departure_filtered'),
        types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{tour_details["hotel_id"]}'),
        # Новая кнопка "Назад" для возврата к списку результатов
        types.InlineKeyboardButton(text='⬅ Назад к результатам', callback_data='back_to_results_from_desc')
    )
    builder.adjust(1)

    # --- Отображаем информацию ---
    display_name = tour_details['hotel_display_name']
    description = tour_details['hotel_description']
    destination_name = tour_details['destination_name']
    duration = tour_details['duration_days']

    await callback.message.edit_text(
        f"🏨 <b>{display_name}</b>\n"
        f"📍 {destination_name} | ⏳ {duration} дн.\n\n" # Показываем длительность
        f"{description or 'Описание недоступно.'}\n\n"
        f"💰 <b>Цена за 1 человека:</b> {price_text}", # Используем price_text с возможным зачеркиванием
        parse_mode='HTML', # HTML нужен для <s> и <b>
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# --- Обработчик: Назад к результатам из описания отфильтрованного тура ---
@dp.callback_query(F.data == 'back_to_results_from_desc', StateFilter(FilterState.filtered_tour_selected))
async def back_to_results_list(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает пользователя из описания тура обратно к списку результатов фильтрации."""
    # Нам нужно заново выполнить запрос фильтра и показать результаты.
    # Функция `show_filtered_tours` ожидает состояние `choosing_filter`, установим его.
    await state.set_state(FilterState.choosing_filter)
    # Вызываем функцию, которая строит и показывает список результатов
    await show_filtered_tours(callback, state)
    # Ответ на callback обрабатывается внутри show_filtered_tours

# --- Обработчик: Кнопка "Выбрать город вылета" для отфильтрованного тура ---
@dp.callback_query(F.data == 'choose_departure_filtered', StateFilter(FilterState.filtered_tour_selected))
async def choose_departure_for_filtered_tour(callback: types.CallbackQuery, state: FSMContext):
    """Показывает кнопки выбора города вылета для отфильтрованного тура."""
    await state.set_state(FilterState.choosing_departure_for_filtered) # Состояние выбора вылета для фильтра

    user_data = await state.get_data()
    hotel_id = user_data.get('hotel_id') # Нужен для кнопки "Назад"

    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='🏙 Астана', callback_data=f'filtered_departure_Астана'),
        types.InlineKeyboardButton(text='🌄 Алматы', callback_data=f'filtered_departure_Алматы'),
        types.InlineKeyboardButton(text='🏔 Шымкент', callback_data=f'filtered_departure_Шымкент'),
    )
    # Кнопка "Назад" должна возвращать к описанию этого же тура
    builder.add(types.InlineKeyboardButton(
        text='⬅ Назад к описанию тура',
        callback_data=f'back_to_filtered_desc_{hotel_id}' # Передаем hotel_id в callback
        ))
    builder.adjust(1)

    await callback.message.edit_text(
        "✈️ Выберите город отправления:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# --- Обработчик: Назад к описанию отфильтрованного тура из выбора вылета ---
@dp.callback_query(F.data.startswith('back_to_filtered_desc_'), StateFilter(FilterState.choosing_departure_for_filtered))
async def back_to_filtered_description_handler(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к экрану описания тура из экрана выбора города вылета (для фильтра)."""
    try:
        # Извлекаем hotel_id из callback_data
        hotel_id = int(callback.data.split('_')[4])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать hotel_id из back_to_filtered_desc callback: {callback.data}")
        await callback.answer("Ошибка при возврате.", show_alert=True)
        return

    # Восстанавливаем вид описания, используя данные из state
    user_data = await state.get_data()
    display_name = user_data.get('hotel_display_name')
    description = user_data.get('description')
    base_price = user_data.get('base_price')
    final_discount_multiplier = user_data.get('final_discount_multiplier')
    destination_name = user_data.get('destination_name')
    duration = user_data.get('duration_days')
    flow_type = user_data.get('flow_type') # Получаем тип потока

    # Проверка наличия всех необходимых данных
    if not all([display_name, description, base_price is not None, final_discount_multiplier is not None, destination_name, duration is not None, flow_type]):
        logging.error(f"Неполные данные состояния для back_to_filtered_description_handler отель {hotel_id}: {user_data}")
        await callback.message.edit_text("Ошибка данных. Начните поиск заново /start.")
        await state.clear()
        await callback.answer("Ошибка данных", show_alert=True)
        return

    # --- Восстанавливаем цену (ЗДЕСЬ ОСТАВЛЯЕМ ЗАЧЕРКИВАНИЕ <s>, т.к. это поток Фильтра) ---
    price_per_person_final = round(base_price * final_discount_multiplier)
    price_text = f"{price_per_person_final}₸"
    if final_discount_multiplier < 1.0:
        discount_percent = int((1 - final_discount_multiplier) * 100)
        price_text = f"🔥 <s>{base_price}₸</s> {price_per_person_final}₸ (-{discount_percent}%)"

    # Восстанавливаем текст сообщения
    final_text = (
        f"🏨 <b>{display_name}</b>\n"
        f"📍 {destination_name} | ⏳ {duration} дн.\n\n"
        f"{description}\n\n"
        f"💰 <b>Цена за 1 человека:</b> {price_text}" # Используем price_text с возможным зачеркиванием
    )

    # Восстанавливаем кнопки (как в select_filtered_tour)
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='✈️ Выбрать город вылета', callback_data='choose_departure_filtered'),
        types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{hotel_id}'),
        types.InlineKeyboardButton(text='⬅ Назад к результатам', callback_data='back_to_results_from_desc')
    )
    builder.adjust(1)

    # Редактируем сообщение
    await callback.message.edit_text(final_text, parse_mode='HTML', reply_markup=builder.as_markup())
    # Возвращаем состояние к показу описания тура
    await state.set_state(FilterState.filtered_tour_selected)
    await callback.answer()


# --- Обработчик: Выбор города вылета для отфильтрованного тура и переход к выбору кол-ва людей ---
@dp.callback_query(F.data.startswith('filtered_departure_'), StateFilter(FilterState.choosing_departure_for_filtered))
async def set_departure_for_filtered_tour(callback: types.CallbackQuery, state: FSMContext):
    """Сохраняет выбранный город вылета и переходит к шагу выбора количества людей."""
    departure_city = callback.data.split('_')[2]
    await state.update_data(departure=departure_city)

    # Теперь у нас есть вся необходимая информация (отель, направление, вылет, цена и т.д.)
    # Переходим к состоянию, где выбирается количество людей.
    # Используем общее состояние UserState.hotel_selected, т.к. следующий шаг (выбор людей) общий.
    await state.set_state(UserState.hotel_selected)
    # Вызываем функцию, которая показывает экран выбора количества людей
    await choose_people_prompt(callback, state)
    # Ответ на callback обрабатывается внутри choose_people_prompt

# ================== ОБЩИЕ ЧАСТИ ПОТОКОВ ==================

# --- Выбор отеля (общий обработчик из потока "Все туры") ---
# Срабатывает только из состояния UserState.departure (после выбора вылета в потоке "Все туры")
@dp.callback_query(F.data.startswith('hotel_'), StateFilter(UserState.departure))
async def hotel_choice(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает выбор отеля в потоке 'Все туры' и показывает его описание."""
    try:
        hotel_id = int(callback.data.split('_')[1])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать hotel_id из callback_data: {callback.data}")
        await callback.answer("Ошибка при выборе отеля.", show_alert=True)
        return

    user_data = await state.get_data()
    destination_id = user_data.get('destination_id')
    departure_city = user_data.get('departure')
    flow_type = user_data.get('flow_type') # Получаем тип потока ('all')

    # --- Проверка наличия критически важных данных ---
    if not destination_id or not departure_city or flow_type != 'all':
        logging.error(f"Некорректные/отсутствующие данные dest/departure/flow_type в состоянии для hotel_choice: {user_data}")
        await callback.message.edit_text("Ошибка: Не удалось определить предыдущий шаг. Попробуйте снова /start.")
        await callback.answer("Ошибка состояния", show_alert=True)
        await state.clear()
        return

    # --- Получаем детали отеля и тура ---
    # Используем price_per_person
    hotel_info = await fetch_one("SELECT display_name, description FROM hotels WHERE hotel_id = ?", (hotel_id,))
    # Ищем тур по отелю И направлению
    tour_info = await fetch_one(
        "SELECT price_per_person, hot_tour_discount_multiplier FROM tours WHERE hotel_id = ? AND destination_id = ?",
        (hotel_id, destination_id)
    )

    if not hotel_info or not tour_info:
        logging.error(f"Не удалось найти информацию об отеле ({hotel_id}) или туре ({destination_id}) в hotel_choice")
        back_builder = InlineKeyboardBuilder()
        back_builder.add(types.InlineKeyboardButton(text='⬅ Назад к выбору отеля', callback_data=f'departure_{departure_city}'))
        await callback.message.edit_text("Ошибка: информация об отеле или туре не найдена.", reply_markup=back_builder.as_markup())
        await callback.answer("Отель/Тур не найден", show_alert=True)
        return

    display_name = hotel_info['display_name']
    description = hotel_info['description']
    base_price = tour_info['price_per_person'] # Базовая цена
    hot_discount_multiplier = tour_info['hot_tour_discount_multiplier']

    # --- Рассчитываем итоговую цену и множитель для сохранения ---
    # ================== ИЗМЕНЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================
    # В потоке "Все туры" (flow_type == 'all') показываем только базовую цену
    price_text = f"{base_price}₸"
    final_discount_multiplier_for_state = 1.0 # Изначально считаем, что скидки нет
    is_hot_for_state = False

    if hot_discount_multiplier < 1.0:
        # Даже если множитель < 1.0, в потоке 'all' мы не показываем зачеркивание.
        # Но сохраняем факт наличия скидки и сам множитель в state!
        final_discount_multiplier_for_state = hot_discount_multiplier
        is_hot_for_state = True # Этот конкретный тур - горящий
        # Можно добавить текстовый индикатор, если хотите
        # price_text += " 🔥 (Горящий тур!)"
    # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================

    # --- Обновляем состояние ---
    # flow_type='all' уже установлен
    await state.update_data(
        hotel_id=hotel_id,
        hotel_display_name=display_name,
        description=description, # Сохраняем описание
        base_price=base_price,
        hot_discount_multiplier=hot_discount_multiplier, # Сохраняем исходный множитель
        final_discount_multiplier=final_discount_multiplier_for_state, # Сохраняем фактический множитель
        is_hot=is_hot_for_state # Устанавливаем флаг горящего тура (даже если цена не зачеркнута)
        # departure, destination_id, destination_name уже есть в state
    )
    await state.set_state(UserState.hotel_selected) # КРИТИЧЕСКИЙ ПЕРЕХОД СОСТОЯНИЯ

    # --- Собираем кнопки ---
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text='👥 Выбрать количество людей', callback_data='choose_people'),
        types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{hotel_id}'),
        types.InlineKeyboardButton(text='⬅ Назад к выбору отеля', callback_data=f'departure_{departure_city}')
    )
    builder.adjust(1)

    # --- Отображаем информацию об отеле ---
    await callback.message.edit_text(
        f"🏨 <b>{display_name}</b>\n\n"
        f"{description or 'Описание недоступно.'}\n\n"
        f"💰 <b>Цена за 1 человека:</b> {price_text}", # Показываем цену без зачеркивания
        parse_mode='HTML', # HTML нужен для <b> и 🔥 (если добавите)
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# --- Просмотр Фото (логика почти без изменений, но добавлены проверки состояний) ---

async def send_or_edit_photo(callback: types.CallbackQuery, state: FSMContext, hotel_id: int, photo_index: int):
    """Отправляет или редактирует сообщение с фотографией отеля."""
    # --- Получаем URL фото и название отеля ---
    photo_rows = await fetch_all("SELECT photo_url FROM hotel_photos WHERE hotel_id = ? ORDER BY order_index", (hotel_id,))
    hotel_info = await fetch_one("SELECT display_name FROM hotels WHERE hotel_id = ?", (hotel_id,))

    if not photo_rows or not hotel_info:
        await callback.answer("Фотографии или информация об отеле не найдены.", show_alert=True)
        try:
            # Пытаемся вернуться к описанию, если фото не найдены
            await show_description_by_id_from_photo_fallback(callback, state, hotel_id)
        except Exception as fallback_e:
            logging.error(f"Запасной вариант показа описания не удался после ошибки фото для отеля {hotel_id}: {fallback_e}")
        return

    photos = [row['photo_url'] for row in photo_rows]
    display_name = hotel_info['display_name']

    # Убеждаемся, что индекс фото в допустимых границах
    photo_index = max(0, min(photo_index, len(photos) - 1))
    current_photo_url = photos[photo_index]
    caption = f"🏨 {display_name} - фото {photo_index + 1}/{len(photos)}"

    # --- Собираем кнопки навигации ---
    builder = InlineKeyboardBuilder()
    nav_buttons = []
    if photo_index > 0: # Кнопка "Назад" по фото
        nav_buttons.append(types.InlineKeyboardButton(text='⬅️', callback_data=f'photo_{hotel_id}_{photo_index-1}'))
    # Кнопка возврата к текстовому описанию
    nav_buttons.append(types.InlineKeyboardButton(text='🔙 Описание', callback_data=f'show_description_{hotel_id}'))
    if photo_index < len(photos) - 1: # Кнопка "Вперед" по фото
        nav_buttons.append(types.InlineKeyboardButton(text='➡️', callback_data=f'photo_{hotel_id}_{photo_index+1}'))
    if nav_buttons:
        builder.row(*nav_buttons)

    try:
        current_state_str = await state.get_state() # Текущее состояние FSM
        user_data = await state.get_data()
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id

        # Создаем объект InputMediaPhoto для редактирования
        media = types.InputMediaPhoto(media=current_photo_url, caption=caption, parse_mode='HTML')

        # Определяем, нужно ли редактировать существующее сообщение или отправлять новое
        # Ожидаемые предыдущие состояния (когда переходим от текста к фото)
        expected_previous_states = [UserState.hotel_selected, FilterState.filtered_tour_selected]
        # ID сообщения с фото, которое мы редактируем (если оно есть)
        photo_message_id = user_data.get('photo_message_id')

        # Если мы переходим с текстового описания на фото, ИЛИ состояние потерялось, ИЛИ нет ID сообщения с фото
        if current_state_str in expected_previous_states or not photo_message_id:
            # Пытаемся отредактировать текущее сообщение (заменить текст на фото)
            await callback.message.edit_media(media=media, reply_markup=builder.as_markup())
            # Сохраняем ID отредактированного сообщения и текущий индекс фото
            await state.update_data(photo_message_id=message_id, current_photo_index=photo_index)
            # Устанавливаем общее состояние просмотра фото
            await state.set_state(UserState.viewing_photos)
        # Если мы уже просматриваем фото (состояние viewing_photos) и ID сообщения совпадает
        elif current_state_str == UserState.viewing_photos and photo_message_id == message_id:
             # Просто редактируем медиа (меняем фото и кнопки) в том же сообщении
             await bot.edit_message_media(
                 chat_id=chat_id,
                 message_id=message_id,
                 media=media,
                 reply_markup=builder.as_markup()
             )
             # Обновляем только индекс фото в состоянии
             await state.update_data(current_photo_index=photo_index)
        else:
            # Несоответствие состояния или ID сообщения - отправляем новое фото
            logging.warning(f"Несоответствие состояния или ID сообщения при навигации по фото. Состояние: {current_state_str}, Сохраненный ID: {photo_message_id}, Callback ID: {message_id}. Отправка нового фото.")
            sent_message = await bot.send_photo(chat_id=chat_id, photo=current_photo_url, caption=caption, reply_markup=builder.as_markup(), parse_mode='HTML')
            # Сохраняем ID нового сообщения и индекс
            await state.update_data(photo_message_id=sent_message.message_id, current_photo_index=photo_index)
            await state.set_state(UserState.viewing_photos) # Устанавливаем состояние просмотра
            with contextlib.suppress(Exception): await callback.message.delete() # Пытаемся удалить старое сообщение

    except Exception as e:
        logging.error(f"Ошибка отправки/редактирования фото для отеля {hotel_id}, индекс {photo_index}: {e}")
        await callback.answer("Не удалось обновить или показать фото.", show_alert=True)
        try:
            # Пытаемся показать текстовое описание как запасной вариант
            await show_description_by_id_from_photo_fallback(callback, state, hotel_id)
        except Exception as fallback_e:
            logging.error(f"Запасной вариант показа описания не удался после ошибки фото {hotel_id}: {fallback_e}")


# Запуск просмотра фото (с экрана описания)
# Состояния: UserState.hotel_selected (основные потоки), FilterState.filtered_tour_selected (поток фильтра)
@dp.callback_query(F.data.startswith('view_photos_'), StateFilter(UserState.hotel_selected, FilterState.filtered_tour_selected))
async def view_hotel_photos_start(callback: types.CallbackQuery, state: FSMContext):
    """Начинает просмотр фотографий отеля."""
    try:
        hotel_id = int(callback.data.split('_')[2])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать hotel_id из view_photos callback: {callback.data}")
        await callback.answer("Ошибка при попытке просмотра фото.", show_alert=True)
        return
    # Вызываем функцию показа фото с индексом 0 (первое фото)
    await send_or_edit_photo(callback, state, hotel_id, 0)
    await callback.answer()

# Навигация по фото (нажатие стрелок)
# Состояние: UserState.viewing_photos (когда фото уже отображается)
@dp.callback_query(F.data.startswith('photo_'), StateFilter(UserState.viewing_photos))
async def handle_photo_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопок навигации по фотографиям."""
    try:
        parts = callback.data.split('_')
        hotel_id = int(parts[1])
        photo_index = int(parts[2]) # Новый индекс фото для показа
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать данные навигации по фото: {callback.data}")
        await callback.answer("Ошибка навигации по фото.", show_alert=True)
        return
    # Вызываем функцию показа фото с новым индексом
    await send_or_edit_photo(callback, state, hotel_id, photo_index)
    await callback.answer()

# --- ВОЗВРАТ К ОПИСАНИЮ ИЗ ФОТО ---

# Общая функция для показа описания (удаляет фото, шлет текст)
async def show_description_by_id(callback_or_message: types.CallbackQuery | types.Message, state: FSMContext, hotel_id: int):
    """Удаляет сообщение с фото и отправляет новое сообщение с текстовым описанием отеля."""
    user_data = await state.get_data()
    message = callback_or_message.message if isinstance(callback_or_message, types.CallbackQuery) else callback_or_message
    chat_id = message.chat.id

    # Определяем ID сообщения с фото, которое нужно удалить
    message_id_to_delete = user_data.get('photo_message_id')
    # Если ID не найден в state (маловероятно, но возможно), пытаемся использовать ID сообщения из callback'а
    if not message_id_to_delete and isinstance(callback_or_message, types.CallbackQuery):
        message_id_to_delete = callback_or_message.message.message_id
        logging.warning(f"photo_message_id не найден. Используется ID сообщения callback'а {message_id_to_delete} для попытки удаления.")
    elif not message_id_to_delete:
        logging.error(f"Невозможно определить сообщение с фото для удаления (отель {hotel_id})")
        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.answer("Ошибка: Не удалось найти предыдущее сообщение.", show_alert=True)
        return # Не можем продолжить без ID

    # --- Восстанавливаем данные отеля из state ---
    # Используем данные из state, если они там есть и полные
    display_name = user_data.get('hotel_display_name')
    description = user_data.get('description')
    base_price = user_data.get('base_price')
    final_discount_multiplier = user_data.get('final_discount_multiplier')
    departure_city = user_data.get('departure') # Может быть None в потоке фильтра
    destination_name = user_data.get('destination_name')
    duration = user_data.get('duration_days') # Для потока фильтра
    flow_type = user_data.get('flow_type')

    # --- Проверяем наличие критически важных данных ---
    # Город вылета может отсутствовать на этом шаге в потоке фильтрации, это нормально
    if not all([display_name, description, base_price is not None, final_discount_multiplier is not None, destination_name, flow_type]):
        logging.error(f"Неполные данные состояния при возврате к описанию для отеля {hotel_id}: {user_data}")
        # Если основные данные отсутствуют, восстановление сложно. Проще отправить сообщение об ошибке.
        await bot.send_message(chat_id, "Произошла ошибка при возврате к описанию. Пожалуйста, начните поиск заново /start.")
        await state.clear()
        # Пытаемся удалить сообщение с фото, даже если произошла ошибка данных
        if message_id_to_delete:
             with contextlib.suppress(Exception): await bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
        return

    # --- Восстанавливаем текст цены (УЧИТЫВАЕМ flow_type) ---
    price_per_person_final = round(base_price * final_discount_multiplier) # Реальная цена
    # ================== ИЗМЕНЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================
    if flow_type == 'all':
        # В потоке "Все туры" показываем базовую цену без зачеркивания
        price_text = f"{base_price}₸"
        # Если тур горящий, можно добавить индикатор, но не зачеркивать
        # if final_discount_multiplier < 1.0:
        #     price_text += " 🔥"
    else: # Для потоков 'hot_random' и 'filter'
        # Оставляем логику с зачеркиванием, если есть скидка
        if final_discount_multiplier < 1.0:
            discount_percent = int((1 - final_discount_multiplier) * 100)
            price_text = f"🔥 <s>{base_price}₸</s> {price_per_person_final}₸ (-{discount_percent}%)"
        else:
            price_text = f"{price_per_person_final}₸" # Цена без скидки
    # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================

    # --- Восстанавливаем текст сообщения ---
    final_text = f"🏨 <b>{display_name}</b>\n"
    if destination_name:
        final_text += f"📍 {destination_name}"
        # Добавляем город вылета, если он известен
        if departure_city:
            final_text += f" (Вылет из {departure_city})"
        # Добавляем длительность, если известна (в потоке фильтра)
        if duration and flow_type == 'filter':
             final_text += f" | ⏳ {duration} дн."
        final_text += "\n\n"
    else: final_text += "\n" # Если нет имени направления, просто перенос строки

    final_text += (f"{description}\n\n"
                   f"💰 <b>Цена за 1 человека:</b> {price_text}") # Используем price_text (с/без зачеркивания)

    # --- Восстанавливаем кнопки ---
    builder = InlineKeyboardBuilder()
    # Определяем текст и callback для кнопки следующего шага
    next_step_callback = 'choose_people'
    next_step_text = '👥 Выбрать количество людей'
    # Если мы в потоке фильтра и город вылета еще не выбран
    if flow_type == 'filter' and not departure_city:
        next_step_callback = 'choose_departure_filtered'
        next_step_text = '✈️ Выбрать город вылета'

    builder.add(types.InlineKeyboardButton(text=next_step_text, callback_data=next_step_callback))
    # Кнопка просмотра фото всегда нужна здесь
    builder.add(types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{hotel_id}'))

    # --- Логика кнопки "Назад" в зависимости от потока ---
    back_callback_data = 'start' # Запасной вариант по умолчанию
    back_text = '⬅ Назад'
    original_tour_id = user_data.get('selected_tour_id_origin') # Для потока hot_random

    if flow_type == 'all' and departure_city:
        back_callback_data = f'departure_{departure_city}'
        back_text = '⬅ Назад к выбору отеля'
    elif flow_type == 'hot_random' and original_tour_id:
        # В потоке "Горящие туры" назад к выбору вылета для этого тура
        back_callback_data = f'randomhot_{original_tour_id}'
        back_text = '⬅ Назад (выбор вылета)'
    elif flow_type == 'filter':
        # В потоке "Фильтр" назад к списку результатов
        back_callback_data = 'back_to_results_from_desc'
        back_text = '⬅ Назад к результатам'
    else: # Запасной вариант, если flow_type неизвестен или данные отсутствуют
        logging.warning(f"Неожиданный flow_type или отсутствующие данные для кнопки Назад из описания. Поток: {flow_type}, Данные: {user_data}")

    builder.add(types.InlineKeyboardButton(text=back_text, callback_data=back_callback_data))
    builder.adjust(1)

    # --- Удаляем старое сообщение (с фото) и отправляем новое (с текстом) ---
    try:
        if message_id_to_delete:
            with contextlib.suppress(Exception): # Подавляем ошибки удаления
                await bot.delete_message(chat_id=chat_id, message_id=message_id_to_delete)
                logging.info(f"Успешно удалено сообщение с фото {message_id_to_delete} для отеля {hotel_id}")

        # Отправляем новое сообщение с текстом
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=final_text,
            parse_mode='HTML',
            reply_markup=builder.as_markup()
        )
        logging.info(f"Отправлено новое текстовое описание для отеля {hotel_id}")

        # Устанавливаем правильное состояние FSM в зависимости от потока и шага
        if flow_type == 'filter' and not departure_city:
            # Если в фильтре и вылет не выбран, остаемся в состоянии выбора вылета для фильтра
             await state.set_state(FilterState.filtered_tour_selected)
        else:
            # Во всех остальных случаях (вылет выбран или не требуется) переходим в общее состояние hotel_selected
             await state.set_state(UserState.hotel_selected)

        # Очищаем данные, связанные с просмотром фото, из состояния
        await state.update_data(photo_message_id=None, current_photo_index=None)

    except Exception as e:
        logging.error(f"Ошибка удаления/отправки сообщения в show_description_by_id для отеля {hotel_id}: {e}")
        if isinstance(callback_or_message, types.CallbackQuery):
            await callback_or_message.answer("Не удалось вернуться к описанию.", show_alert=True)


# Запасная функция для показа описания, если загрузка фото не удалась изначально
async def show_description_by_id_from_photo_fallback(callback: types.CallbackQuery, state: FSMContext, hotel_id: int):
    """Показывает текстовое описание, если фото не загрузились (отправляет новое сообщение)."""
    user_data = await state.get_data()
    chat_id = callback.message.chat.id

    # --- Восстанавливаем данные из state ---
    display_name = user_data.get('hotel_display_name')
    description = user_data.get('description')
    base_price = user_data.get('base_price')
    final_discount_multiplier = user_data.get('final_discount_multiplier')
    departure_city = user_data.get('departure')
    destination_name = user_data.get('destination_name')
    duration = user_data.get('duration_days')
    flow_type = user_data.get('flow_type')

    if not all([display_name, description, base_price is not None, final_discount_multiplier is not None, destination_name, flow_type]):
        logging.error(f"Неполные данные состояния для запасного описания отеля {hotel_id}: {user_data}")
        await callback.answer("Ошибка данных, не могу показать описание.", show_alert=True)
        return

    # --- Восстанавливаем текст цены (УЧИТЫВАЕМ flow_type) ---
    price_per_person_final = round(base_price * final_discount_multiplier)
    # ================== ИЗМЕНЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================
    if flow_type == 'all':
        price_text = f"{base_price}₸"
    else: # 'hot_random', 'filter'
        if final_discount_multiplier < 1.0:
            discount_percent = int((1 - final_discount_multiplier) * 100)
            price_text = f"🔥 <s>{base_price}₸</s> {price_per_person_final}₸ (-{discount_percent}%)"
        else:
            price_text = f"{price_per_person_final}₸"
    # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================

    # --- Восстанавливаем текст сообщения с пометкой об ошибке фото ---
    final_text = f"🏨 <b>{display_name}</b>\n"
    if destination_name:
        final_text += f"📍 {destination_name}"
        if departure_city: final_text += f" (Вылет из {departure_city})"
        if duration and flow_type == 'filter': final_text += f" | ⏳ {duration} дн."
        final_text += "\n\n"
    else: final_text += "\n"
    final_text += (f"{description}\n\n"
                   f"💰 <b>Цена за 1 человека:</b> {price_text}\n\n"
                   f"<i>Не удалось загрузить фото.</i>") # Добавляем пометку

    # --- Восстанавливаем кнопки (без кнопки фото) ---
    builder = InlineKeyboardBuilder()
    next_step_callback = 'choose_people'
    next_step_text = '👥 Выбрать количество людей'
    if flow_type == 'filter' and not departure_city:
        next_step_callback = 'choose_departure_filtered'
        next_step_text = '✈️ Выбрать город вылета'

    builder.add(types.InlineKeyboardButton(text=next_step_text, callback_data=next_step_callback))
    # Кнопки фото здесь нет, так как она не сработала

    # Логика кнопки "Назад" (такая же, как в show_description_by_id)
    back_callback_data = 'start'
    back_text = '⬅ Назад'
    original_tour_id = user_data.get('selected_tour_id_origin')
    if flow_type == 'all' and departure_city:
        back_callback_data = f'departure_{departure_city}'
        back_text = '⬅ Назад к выбору отеля'
    elif flow_type == 'hot_random' and original_tour_id:
        back_callback_data = f'randomhot_{original_tour_id}'
        back_text = '⬅ Назад (выбор вылета)'
    elif flow_type == 'filter':
        back_callback_data = 'back_to_results_from_desc'
        back_text = '⬅ Назад к результатам'

    builder.add(types.InlineKeyboardButton(text=back_text, callback_data=back_callback_data))
    builder.adjust(1)

    try:
        # Отправляем описание как новое сообщение
        await bot.send_message(
            chat_id=chat_id,
            text=final_text,
            parse_mode='HTML',
            reply_markup=builder.as_markup()
        )
        # Пытаемся удалить исходное сообщение (которое могло быть текстом до попытки показать фото)
        with contextlib.suppress(Exception): await callback.message.delete()

        # Устанавливаем правильное состояние
        if flow_type == 'filter' and not departure_city:
             await state.set_state(FilterState.filtered_tour_selected)
        else:
             await state.set_state(UserState.hotel_selected)
        # Очищаем состояние фото
        await state.update_data(photo_message_id=None, current_photo_index=None)

    except Exception as e:
        logging.error(f"Ошибка отправки запасного описания для отеля {hotel_id}: {e}")
        await callback.answer("Произошла ошибка при отображении описания.", show_alert=True)


# Вызов возврата к описанию из фото (нажатие кнопки "Описание")
# Состояние: UserState.viewing_photos
@dp.callback_query(F.data.startswith('show_description_'), StateFilter(UserState.viewing_photos))
async def show_description_from_photo(callback: types.CallbackQuery, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Описание' во время просмотра фото."""
    try:
        hotel_id = int(callback.data.split('_')[2])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать hotel_id из show_description callback: {callback.data}")
        await callback.answer("Ошибка при возврате к описанию.", show_alert=True)
        return
    # Вызываем общую функцию для показа описания
    await show_description_by_id(callback, state, hotel_id)
    # await callback.answer() # Ответ обрабатывается неявно отправкой нового сообщения


# --- Выбор количества людей и Даты (логика в основном общая) ---

# Запуск выбора количества людей (из состояния UserState.hotel_selected)
@dp.callback_query(F.data == 'choose_people', StateFilter(UserState.hotel_selected))
async def choose_people_prompt(callback: types.CallbackQuery, state: FSMContext):
    """Показывает кнопки для выбора количества человек."""
    builder = InlineKeyboardBuilder()
    buttons = [types.InlineKeyboardButton(text=f'{i}', callback_data=f'people_{i}') for i in range(1, 7)] # Кнопки 1-6
    builder.row(*buttons[:3]) # Ряд 1: 1, 2, 3
    builder.row(*buttons[3:]) # Ряд 2: 4, 5, 6

    user_data = await state.get_data()
    hotel_id = user_data.get('hotel_id')
    # flow_type = user_data.get('flow_type') # Не используется напрямую здесь, но есть в state

    # --- Логика кнопки "Назад" ---
    back_callback_data = None
    back_text = '⬅ Назад к описанию'
    if hotel_id:
        # Используем специальный callback для возврата к описанию через РЕДАКТИРОВАНИЕ сообщения
        back_callback_data = f'back_to_description_edit_{hotel_id}'
    else: # Запасной вариант, если ID отеля потерялся
        logging.warning("hotel_id отсутствует в состоянии при вызове choose_people_prompt")
        back_callback_data = 'start' # Безопасный возврат в главное меню

    builder.row(types.InlineKeyboardButton(text=back_text, callback_data=back_callback_data))

    # Редактируем текущее сообщение
    await callback.message.edit_text(
        text="👥 Выберите количество человек:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()


# НОВЫЙ ОБРАБОТЧИК: Возврат к описанию (редактирование) с экрана выбора людей
# Состояние: UserState.hotel_selected (так как мы возвращаемся из choose_people_prompt)
@dp.callback_query(F.data.startswith('back_to_description_edit_'), StateFilter(UserState.hotel_selected))
async def back_to_description_edit_from_people(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к описанию отеля, редактируя текущее сообщение (из выбора кол-ва людей)."""
    try:
        # Извлекаем hotel_id из callback_data
        hotel_id = int(callback.data.split('_')[4])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать hotel_id из back_to_description_edit callback: {callback.data}")
        await callback.answer("Ошибка при возврате.", show_alert=True)
        return

    # Восстанавливаем вид описания, РЕДАКТИРУЯ текущее сообщение
    user_data = await state.get_data()
    display_name = user_data.get('hotel_display_name')
    description = user_data.get('description')
    base_price = user_data.get('base_price')
    final_discount_multiplier = user_data.get('final_discount_multiplier')
    departure_city = user_data.get('departure') # Может быть None для фильтра
    destination_name = user_data.get('destination_name')
    duration = user_data.get('duration_days')
    flow_type = user_data.get('flow_type')

    # Проверка данных (как в show_description_by_id)
    if not all([display_name, description, base_price is not None, final_discount_multiplier is not None, destination_name, flow_type]):
        logging.error(f"Неполные данные состояния для back_to_description_edit отель {hotel_id}: {user_data}")
        await callback.message.edit_text("Ошибка данных. Начните поиск заново /start.")
        await state.clear()
        await callback.answer("Ошибка данных", show_alert=True)
        return

    # --- Восстанавливаем цену (УЧИТЫВАЕМ flow_type) ---
    price_per_person_final = round(base_price * final_discount_multiplier)
    # ================== ИЗМЕНЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================
    if flow_type == 'all':
        price_text = f"{base_price}₸"
    else: # 'hot_random', 'filter'
        if final_discount_multiplier < 1.0:
            discount_percent = int((1 - final_discount_multiplier) * 100)
            price_text = f"🔥 <s>{base_price}₸</s> {price_per_person_final}₸ (-{discount_percent}%)"
        else:
            price_text = f"{price_per_person_final}₸"
    # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================

    # Восстанавливаем текст
    final_text = f"🏨 <b>{display_name}</b>\n"
    if destination_name:
        final_text += f"📍 {destination_name}"
        if departure_city: final_text += f" (Вылет из {departure_city})"
        if duration and flow_type == 'filter': final_text += f" | ⏳ {duration} дн."
        final_text += "\n\n"
    else: final_text += "\n"
    final_text += (f"{description}\n\n"
                   f"💰 <b>Цена за 1 человека:</b> {price_text}") # Используем price_text

    # --- Восстанавливаем кнопки (как в show_description_by_id) ---
    builder = InlineKeyboardBuilder()
    next_step_callback = 'choose_people'
    next_step_text = '👥 Выбрать количество людей'
    # Проверяем, нужно ли показывать кнопку выбора вылета (для фильтра)
    if flow_type == 'filter' and not departure_city:
        next_step_callback = 'choose_departure_filtered'
        next_step_text = '✈️ Выбрать город вылета'

    builder.add(types.InlineKeyboardButton(text=next_step_text, callback_data=next_step_callback))
    builder.add(types.InlineKeyboardButton(text='📷 Посмотреть фото отеля', callback_data=f'view_photos_{hotel_id}'))

    # Логика кнопки "Назад" (как в show_description_by_id)
    back_callback_data = 'start'
    back_text = '⬅ Назад'
    original_tour_id = user_data.get('selected_tour_id_origin')
    if flow_type == 'all' and departure_city:
        back_callback_data = f'departure_{departure_city}'
        back_text = '⬅ Назад к выбору отеля'
    elif flow_type == 'hot_random' and original_tour_id:
        back_callback_data = f'randomhot_{original_tour_id}'
        back_text = '⬅ Назад (выбор вылета)'
    elif flow_type == 'filter':
        back_callback_data = 'back_to_results_from_desc'
        back_text = '⬅ Назад к результатам'

    builder.add(types.InlineKeyboardButton(text=back_text, callback_data=back_callback_data))
    builder.adjust(1)

    # --- Редактируем сообщение ---
    try:
        await callback.message.edit_text(
            final_text,
            parse_mode='HTML',
            reply_markup=builder.as_markup()
        )
        # Состояние остается UserState.hotel_selected
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка редактирования сообщения в back_to_description_edit_from_people для отеля {hotel_id}: {e}")
        await callback.answer("Не удалось вернуться к описанию.", show_alert=True)


# Обработка выбора количества людей (переход к выбору месяца)
# Состояние UserState.hotel_selected (из всех потоков, т.к. мы здесь после показа описания)
@dp.callback_query(F.data.startswith('people_'), StateFilter(UserState.hotel_selected))
async def people_choice(callback: types.CallbackQuery, state: FSMContext):
    """Сохраняет количество человек и переходит к выбору месяца."""
    try:
        people_count = int(callback.data.split('_')[1])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать people_count из callback_data: {callback.data}")
        await callback.answer("Ошибка при обработке количества человек.", show_alert=True)
        return

    await state.update_data(people=people_count)
    await state.set_state(UserState.people) # Переход к состоянию выбора месяца/даты
    # Вызов функции для отображения выбора месяца
    await choose_dates_prompt(callback, state)
    # Ответ на callback обрабатывается внутри choose_dates_prompt

# --- Обработчики для выбора Даты (логика не менялась) ---

async def choose_dates_prompt(callback_or_message: types.CallbackQuery | types.Message, state: FSMContext):
    """Показывает кнопки выбора месяца."""
    # Проверяем и при необходимости устанавливаем правильное состояние
    current_state = await state.get_state()
    if current_state != UserState.people:
        logging.warning(f"choose_dates_prompt вызван из неожиданного состояния: {current_state}. Принудительно ставим UserState.people")
        await state.set_state(UserState.people)

    message = callback_or_message.message if isinstance(callback_or_message, types.CallbackQuery) else callback_or_message

    # --- Собираем кнопки месяцев ---
    builder = InlineKeyboardBuilder()
    months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн',
              'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
    month_buttons = [
        types.InlineKeyboardButton(text=month, callback_data=f'month_{i+1}')
        for i, month in enumerate(months)
    ]
    # Располагаем кнопки по 3 в ряд
    builder.row(month_buttons[0], month_buttons[1], month_buttons[2])
    builder.row(month_buttons[3], month_buttons[4], month_buttons[5])
    builder.row(month_buttons[6], month_buttons[7], month_buttons[8])
    builder.row(month_buttons[9], month_buttons[10], month_buttons[11])

    # Кнопка "Назад" к выбору количества людей
    builder.row(types.InlineKeyboardButton(text='⬅ Назад к кол-ву людей', callback_data='back_to_people_selection'))

    # Редактируем сообщение
    await message.edit_text(
        text="📅 Выберите месяц поездки:",
        reply_markup=builder.as_markup()
    )
    # Отвечаем на callback, если он был
    if isinstance(callback_or_message, types.CallbackQuery):
        await callback_or_message.answer()

# Обработчик кнопки "Назад к кол-ву людей" из выбора месяца
@dp.callback_query(F.data == 'back_to_people_selection', StateFilter(UserState.people))
async def back_to_people_from_month(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к экрану выбора количества людей."""
    # Возвращаем состояние, которое было перед выбором людей
    await state.set_state(UserState.hotel_selected)
    # Вызываем функцию показа выбора людей (она отредактирует сообщение)
    await choose_people_prompt(callback, state)
    # Ответ на callback обрабатывается внутри choose_people_prompt

# Обработчик выбора месяца
# Может быть вызван из состояния people (первый раз) или day (при возврате с выбора дня)
@dp.callback_query(F.data.startswith('month_'), StateFilter(UserState.people, UserState.day))
async def month_choice(callback: types.CallbackQuery, state: FSMContext):
    """Сохраняет месяц и показывает кнопки выбора дня."""
    try:
        month_num = int(callback.data.split('_')[1])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать month_num из callback_data: {callback.data}")
        await callback.answer("Ошибка при обработке месяца.", show_alert=True)
        return

    months_full = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    if not (1 <= month_num <= 12):
        logging.error(f"Распарсен неверный номер месяца: {month_num}")
        await callback.answer("Некорректный номер месяца.", show_alert=True)
        return
    month_name = months_full[month_num - 1]

    # Определяем количество дней в месяце (упрощенно, без учета високосного года)
    if month_num in [1, 3, 5, 7, 8, 10, 12]: days_in_month = 31
    elif month_num in [4, 6, 9, 11]: days_in_month = 30
    elif month_num == 2: days_in_month = 28 # Упрощение для Февраля
    else: days_in_month = 30 # На всякий случай

    # Сохраняем месяц в state
    await state.update_data(month=month_num, month_name=month_name)
    # Устанавливаем состояние выбора дня
    await state.set_state(UserState.month)

    # --- Собираем кнопки дней ---
    builder = InlineKeyboardBuilder()
    day_buttons = [
        types.InlineKeyboardButton(text=str(day), callback_data=f'day_{day}')
        for day in range(1, days_in_month + 1)
    ]
    # Располагаем кнопки дней по 7 в ряд
    rows = [day_buttons[i:i + 7] for i in range(0, len(day_buttons), 7)]
    for row in rows:
        builder.row(*row)
    # Кнопка "Назад" к выбору месяца
    builder.row(types.InlineKeyboardButton(text='⬅ Назад к месяцам', callback_data='back_to_month_selection'))

    # Редактируем сообщение
    await callback.message.edit_text(
        text=f"📅 Выберите день поездки ({month_name}):",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

# Обработчик кнопки "Назад к месяцам" из выбора дня
@dp.callback_query(F.data == 'back_to_month_selection', StateFilter(UserState.month))
async def back_to_month_selection_handler(callback: types.CallbackQuery, state: FSMContext):
    """Возвращает к экрану выбора месяца."""
    # Возвращаем состояние, которое было перед выбором месяца
    await state.set_state(UserState.people)
    # Вызываем функцию показа выбора месяца (она отредактирует сообщение)
    await choose_dates_prompt(callback, state)
    # Ответ на callback обрабатывается внутри choose_dates_prompt

# --- Финальное Подтверждение ---
# Срабатывает после выбора дня (состояние UserState.month)
@dp.callback_query(F.data.startswith('day_'), StateFilter(UserState.month))
async def day_choice_final(callback: types.CallbackQuery, state: FSMContext):
    """Сохраняет день, формирует и показывает итоговое подтверждение тура."""
    try:
        day = int(callback.data.split('_')[1])
    except (ValueError, IndexError):
        logging.error(f"Не удалось разобрать день из callback_data: {callback.data}")
        await callback.answer("Ошибка при обработке дня.", show_alert=True)
        return

    await state.update_data(day=day)
    # Устанавливаем финальное состояние
    await state.set_state(UserState.day)

    data = await state.get_data()

    # --- Извлекаем все данные из state ---
    display_name = data.get('hotel_display_name')
    base_price = data.get('base_price') # Это price_per_person
    people_count = data.get('people')
    final_discount_multiplier = data.get('final_discount_multiplier')
    month_num_for_back = data.get("month") # Номер месяца для кнопки "Назад"
    month_name_final = data.get("month_name")
    departure_final = data.get("departure")
    destination_name_final = data.get("destination_name")
    duration_final = data.get("duration_days") # Получаем длительность, если есть
    is_hot_final = data.get('is_hot', False) # Флаг горящего тура
    flow_type = data.get('flow_type') # Тип потока

    # --- Проверяем наличие всех необходимых данных ---
    if not all([
        display_name, base_price is not None, people_count,
        final_discount_multiplier is not None, month_num_for_back,
        month_name_final, departure_final, destination_name_final, flow_type # Добавили flow_type
    ]):
        logging.error(f"Неполные данные состояния для финального итога: {data}")
        await callback.message.edit_text("Ошибка: Недостаточно данных для формирования итогов. Пожалуйста, начните заново /start.")
        await state.clear() # Очищаем состояние при критической ошибке
        await callback.answer("Ошибка данных.", show_alert=True)
        return

    # --- Рассчитываем финальную цену ---
    # Используем final_discount_multiplier, который был сохранен в state
    # Этот множитель будет 1.0 для потока 'all' (если тур не горящий),
    # и < 1.0 для 'hot_random' и 'filter' (если скидка есть)
    price_per_person_final = round(base_price * final_discount_multiplier)
    total_price = price_per_person_final * people_count

    # --- Формируем текст скидки и отображение цены за человека (УЧИТЫВАЕМ flow_type) ---
    discount_text = ""
    # ================== ИЗМЕНЕНИЕ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================
    if flow_type == 'all':
        # В потоке "Все туры" показываем базовую цену и не показываем скидку
        price_per_person_display = f"{base_price}₸"
        discount_text = "" # Убираем текст скидки
    else: # Для потоков 'hot_random' и 'filter'
        # Используем сохраненный final_discount_multiplier
        if final_discount_multiplier < 1.0:
            discount_percent = int((1 - final_discount_multiplier) * 100)
            discount_label = "Скидка (горящий тур)" if is_hot_final else "Скидка"
            discount_text = f"🎁 <b>{discount_label}:</b> {discount_percent}%\n"
            price_per_person_display = f"<s>{base_price}₸</s> {price_per_person_final}₸"
        else:
            # Если скидки нет (даже в потоках hot/filter), показываем обычную цену
            price_per_person_display = f"{price_per_person_final}₸"
            discount_text = ""
    # ================== КОНЕЦ ИЗМЕНЕНИЯ ЛОГИКИ ОТОБРАЖЕНИЯ ЦЕНЫ ==================

    # --- Собираем итоговый текст ---
    summary_text = (
        f"🎉 <b>Ваш выбор подтвержден:</b>\n\n"
        f"✈️ <b>Вылет из:</b> {departure_final}\n"
        f"🏝 <b>Направление:</b> {destination_name_final}\n"
        f"🏨 <b>Отель:</b> {display_name}\n"
        # Добавляем длительность, если она есть в state (особенно из потока фильтра)
        f"⏳ <b>Длительность:</b> {duration_final} дн.\n" if duration_final else ""
        f"👥 <b>Количество человек:</b> {people_count}\n"
        f"📅 <b>Примерная дата начала:</b> {day} {month_name_final}\n\n"
        f"💰 <b>Цена за 1 чел.:</b> {price_per_person_display}\n" # Используем display-цену
        f"{discount_text}" # Добавляем текст скидки (если нужно по логике flow_type)
        f"💲 <b>Итоговая цена ({people_count} чел.):</b> {total_price}₸\n\n" # Итоговая всегда правильная
        f"📞 <b>Для бронирования и уточнения деталей свяжитесь с нашим менеджером:</b>\n"
        "    • <a href='https://t.me/Ako_1307'>Алдияр</a>\n"
        "    • <a href='https://t.me/quinssoo'>Олжас</a>\n"
        "    • Общий телефон: +7 (777) 123-45-67\n\n"
        "<i>*Точные даты вылета и наличие мест будут подтверждены менеджером.</i>"
    )

    # --- Финальные кнопки ---
    builder = InlineKeyboardBuilder()
    # Кнопка для нового поиска (возврат в начало)
    builder.add(types.InlineKeyboardButton(text='🔍 Новый поиск', callback_data='start'))
    # Кнопка для изменения даты (возврат к выбору дня этого же месяца)
    builder.add(types.InlineKeyboardButton(text='⬅ Изменить дату', callback_data=f'month_{month_num_for_back}'))

    # Редактируем сообщение
    await callback.message.edit_text(
        text=summary_text,
        parse_mode='HTML', # HTML нужен для <b>, <a> и <s> (если есть)
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True # Отключаем предпросмотр ссылок
    )
    await callback.answer()
    # Состояние остается UserState.day, пользователь может изменить дату или начать новый поиск

# ==================== МЕНЕДЖЕРЫ (без изменений) ====================
@dp.callback_query(F.data == 'managers')
async def show_managers(callback: types.CallbackQuery):
    """Показывает информацию о менеджерах и контакты."""
    builder = InlineKeyboardBuilder()
    builder.add(
        types.InlineKeyboardButton(text="📞 Алдияр", url="https://t.me/Ako_1307"),
        types.InlineKeyboardButton(text="📞 Олжас", url="https://t.me/quinssoo"),
        types.InlineKeyboardButton(text="📞 Общий чат поддержки", url="https://t.me/crystalbay_support"), # Пример ссылки на чат
        types.InlineKeyboardButton(text="⬅ Назад", callback_data="start") # Назад в главное меню
    )
    builder.adjust(1) # Кнопки в один столбец
    await callback.message.edit_text(
        "👨‍💼 <b>Наши менеджеры</b> 👩‍💼\n\n"
        "Мы готовы помочь вам с выбором тура, ответить на вопросы и организовать ваше идеальное путешествие!\n\n"
        "📅 <b>График работы:</b> Пн-Пт 09:00-18:00, Сб-Вс 10:00-16:00\n"
        "📧 <b>Email:</b> info@crystalbay.kz\n"
        "📱 <b>Телефон:</b> +7 (777) 123-45-67\n\n"
        "Выберите менеджера или напишите в общий чат:",
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True # Отключаем предпросмотр ссылок
    )
    await callback.answer()

# --- Главная функция запуска бота ---
async def main():
    """Основная функция для запуска бота."""
    logging.info("Запуск бота...")

    # Проверка схемы базы данных при запуске
    try:
        async with aiosqlite.connect(DB_NAME) as db:
            # Проверяем наличие новых и старых полей во всех таблицах
            await db.execute("SELECT tour_id, destination_id, hotel_id, price_per_person, duration_days, hot_tour_discount_multiplier FROM tours LIMIT 1")
            await db.execute("SELECT hotel_id, display_name, description, stars FROM hotels LIMIT 1")
            await db.execute("SELECT destination_id, name FROM destinations LIMIT 1")
            await db.execute("SELECT photo_id, hotel_id, photo_url, order_index FROM hotel_photos LIMIT 1")
        logging.info("Подключение к БД и проверка схемы успешны.")
    except aiosqlite.Error as e:
        logging.critical(f"Ошибка БД при проверке на старте: {e}. Убедитесь, что '{DB_NAME}' существует, имеет корректную структуру (price_per_person, duration_days) и заполнена.")
        return # Предотвращаем запуск бота при ошибке БД

    # Запуск поллинга
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.critical(f"Ошибка поллинга бота: {e}")
    finally:
        # Корректное завершение работы
        logging.info("Остановка бота...")
        session = await bot.get_session()
        if session and not session.closed:
             await session.close()
             logging.info("Сессия бота закрыта.")

# --- Точка входа ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен вручную")