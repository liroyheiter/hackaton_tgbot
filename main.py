import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

API_TOKEN = "7255790527:AAFWVcX7hzSEXVMQg4uo8AxKPjtxciulPC4"  # Замените на ваш токен
ADMIN_CHAT_ID = "890235087"  # Айди администратора для отправки данных

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher()

# Состояния для FSM
class Form(StatesGroup):
    role = State()
    full_name = State()
    phone_number = State()
    specialization = State()
    certificate = State()
    schedule = State()  # Новое состояние для указания расписания

# Кнопки выбора роли (обычные кнопки)
role_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Ментор")],
        [KeyboardButton(text="Психолог")]
    ],
    resize_keyboard=True
)

# Кнопки для указания дней недели (Inline)
days_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=day, callback_data=f"day_{day}") for day in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]],
    [InlineKeyboardButton(text="Завершить выбор дней", callback_data="finish_days")]
])

# Кнопки для указания часов приема
time_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text=f"{hour} a.m.", callback_data=f"time_{hour} a.m.") for hour in range(6, 12)],
    [InlineKeyboardButton(text=f"{hour - 12} p.m.", callback_data=f"time_{hour} p.m.") for hour in range(12, 23)],
    [InlineKeyboardButton(text="Завершить выбор времени", callback_data="finish_time")]
])

# Inline-кнопки для одобрения и отклонения заявки
approve_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Одобрить", callback_data="approve")],
    [InlineKeyboardButton(text="Отклонить", callback_data="reject")]
])

# Списки для хранения выбранных дней и часов
selected_days = set()
selected_times = set()

@dp.message(Command("get_chat_id"))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id  # Получаем ID чата
    await message.answer(f"Ваш ID чата: {chat_id}")  # Отправляем ID пользователю

# Хендлер на команду /start
@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    await message.answer("Привет! Пожалуйста, выбери свою роль:", reply_markup=role_kb)
    await state.set_state(Form.role)

# Хендлер на выбор роли (по кнопке)
@dp.message(Form.role)
async def choose_role(message: types.Message, state: FSMContext):
    if message.text not in ["Ментор", "Психолог"]:
        await message.answer("Пожалуйста, выбери роль, нажав на кнопку.")
        return

    await state.update_data(role=message.text)
    await message.answer("Пожалуйста, укажите ваше ФИО.")
    await state.set_state(Form.full_name)

# Запрос ФИО
@dp.message(Form.full_name)
async def full_name(message: types.Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await message.answer("Введите ваш номер телефона.")
    await state.set_state(Form.phone_number)

# Запрос номера телефона
@dp.message(Form.phone_number)
async def phone_number(message: types.Message, state: FSMContext):
    await state.update_data(phone_number=message.text)
    await message.answer("Укажите вашу специализацию.")
    await state.set_state(Form.specialization)

# Запрос специализации
@dp.message(Form.specialization)
async def specialization(message: types.Message, state: FSMContext):
    await state.update_data(specialization=message.text)
    await message.answer("Отправьте сертификат (файл).")
    await state.set_state(Form.certificate)

# Запрос сертификата (только документы)
@dp.message(Form.certificate)
async def certificate(message: types.Message, state: FSMContext):
    if not message.document:
        await message.answer("Пожалуйста, отправьте сертификат в виде файла.")
        return

    certificate_file_id = message.document.file_id
    await state.update_data(certificate=certificate_file_id)

    # Отправляем данные администратору
    user_data = await state.get_data()
    text = (
        f"Новая заявка:\n"
        f"Роль: {user_data['role']}\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Телефон: {user_data['phone_number']}\n"
        f"Специализация: {user_data['specialization']}\n"
    )
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, reply_markup=approve_kb)
    if 'certificate' in user_data:
        certificate_file_id = user_data['certificate']
    await bot.send_document(chat_id=ADMIN_CHAT_ID, document=certificate_file_id)
    await message.answer("Ваши данные отправлены на проверку. Пожалуйста, дождитесь одобрения.")
    await state.set_state(Form.schedule)

# Одобрение/отклонение заявки
@dp.callback_query(lambda c: c.data in ["approve", "reject"])
async def process_application(callback_query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    if callback_query.data == "approve":
        # Обработаем одобрение заявки
        await bot.send_message(callback_query.from_user.id, "Заявка одобрена!")
        
        # Запрашиваем расписание после одобрения
        await bot.send_message(callback_query.from_user.id, 
                                 "Пожалуйста, выберите дни недели, когда вы можете вести прием:", 
                                 reply_markup=days_kb)
        
    elif callback_query.data == "reject":
        # Обработаем отклонение заявки
        await bot.send_message(callback_query.from_user.id, "Заявка отклонена.")
    
    # Удаляем сообщение с кнопками у администратора
    await callback_query.message.delete()

# Запрос расписания
@dp.callback_query(lambda c: c.data.startswith("day_"))
async def select_day(callback_query: CallbackQuery):
    day = callback_query.data.split("_")[1]
    if day in selected_days:
        selected_days.remove(day)
        await callback_query.answer(f"{day} удален из выбора.")
    else:
        selected_days.add(day)
        await callback_query.answer(f"{day} добавлен в выбор.")

    # Отправляем текущее состояние выбора
    await bot.send_message(callback_query.from_user.id, "Выберите дни недели:", reply_markup=days_kb)

# Запрос времени
@dp.callback_query(lambda c: c.data.startswith("time_"))
async def select_time(callback_query: CallbackQuery):
    time = callback_query.data.split("_")[1]
    if time in selected_times:
        selected_times.remove(time)
        await callback_query.answer(f"{time} удалено из выбора.")
    else:
        selected_times.add(time)
        await callback_query.answer(f"{time} добавлено в выбор.")

    # Отправляем текущее состояние выбора
    await bot.send_message(callback_query.from_user.id, "Выберите часы приема:", reply_markup=time_kb)

# Завершение выбора дней
@dp.callback_query(lambda c: c.data == "finish_days")
async def finish_days(callback_query: CallbackQuery):
    await callback_query.answer("Выбор дней завершен. Теперь выберите время.")
    await bot.send_message(callback_query.from_user.id, "Пожалуйста, выберите часы приема:", reply_markup=time_kb)

# Завершение выбора времени и отправка данных администратору
@dp.callback_query(lambda c: c.data == "finish_time")
async def finish_time(callback_query: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()

    # Формируем текст для администратора
    text = (
        f"Роль: {user_data['role']}\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Телефон: {user_data['phone_number']}\n"
        f"Специализация: {user_data['specialization']}\n"
        f"Часы приема: {', '.join(selected_times)}\n"
        f"Дни недели: {', '.join(selected_days)}\n"
    )
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text)

    await bot.send_message(callback_query.from_user.id, "Ваши данные успешно отправлены администратору!")

if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
