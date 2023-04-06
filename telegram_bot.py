from config import TG_TOKEN
import logging
from datetime import date
from gpt_calories import meal_calories
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, \
    PicklePersistence

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

START, SEX, WEIGHT, HEIGHT, AGE, LIFESTYLE, BASIC_METABOLISM, AIM, MEAL, CHANGE_WEIGHT, WEIGHT_HANDLER = range(11)
BMR_AMR = {
    'Низкая': 1.2,
    'Средняя': 1.375,
    'Высокая': 1.55,
    'Спортсмен': 1.725
}
AIMS = {
    'Похудеть': 0.9,
    'Сохранить вес': 1,
    'Набрать массу': 1.1
}


async def start(update, context):
    user = update.effective_user
    logger.info('%s стартанул бота', user.first_name)
    await update.message.reply_text(
        f"Здавствуйте, {user.first_name}!\n\n"
        f"Добро пожаловать в Калькулятор калорий!\n"
        f"С его помощью можно с легкостью вести дневник питания за день.\n"
        f"Пишите о приемах пищи в свободной манере и не мучайтесь с сложными приложениями!"
        , reply_markup=ReplyKeyboardMarkup([['Понятно!']], resize_keyboard=True))
    return SEX


async def sex(update, context):
    reply_keyboard = [['Мужчина', 'Женщина']]
    await update.message.reply_text(
        f"Для начала оценим ваш базовый обмен"
    )
    await update.message.reply_text(
        f"Ваш пол:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return WEIGHT


async def weight(update, context):
    user_sex = update.message.text
    context.user_data['sex'] = user_sex
    logger.info('%s выбрал пол %s', update.message.from_user.first_name, user_sex)
    await update.message.reply_text(
        f"Ваш вес в килограммах:",
        reply_markup=ReplyKeyboardRemove()
    )
    return HEIGHT


async def height(update, context):
    user_weight = update.message.text
    user_weight = user_weight.replace(',', '.')
    context.user_data['weight'] = round(float(user_weight), 1)
    logger.info('%s указал вес %s', update.message.from_user.first_name, user_weight)
    await update.message.reply_text(
        f"Введите Ваш рост в сантиметрах:"
    )
    return AGE


async def height_wrong_weight(update, context):
    logger.info('%s указал странный вес %s', update.message.from_user.first_name, update.message.text)
    await _wrong_info_message(update)
    await update.message.reply_text(
        f"Введите Ваш вес в килограммах:",
    )
    return HEIGHT


async def age(update, context):
    user_height = update.message.text
    context.user_data['height'] = int(user_height)
    logger.info('%s указал рост %s', update.message.from_user.first_name, user_height)
    await update.message.reply_text(
        f"Введите Ваш возраст:"
    )
    return LIFESTYLE


async def age_wrong_height(update, context):
    logger.info('%s указал странный рост %s', update.message.from_user.first_name, update.message.text)
    await _wrong_info_message(update)
    await update.message.reply_text(
        f"Введите Ваш рост в сантиметрах:",
    )
    return AGE


async def _wrong_info_message(update):
    await update.message.reply_text(
        f"Кажется, вы ввели некорректные данные. 🤡🤡🤡"
    )


async def lifestyle(update, context):
    user_age = update.message.text
    context.user_data['age'] = int(user_age)
    logger.info('%s указал возраст %s', update.message.from_user.first_name, user_age)
    reply_keyboard = [['Низкая', 'Средняя', 'Высокая', 'Спортсмен']]
    await update.message.reply_text(
        f"Оцените вашу физическую активность:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return BASIC_METABOLISM


async def lifestyle_wrong_age(update, context):
    logger.info('%s указал странный возраст %s', update.message.from_user.first_name, update.message.text)
    await _wrong_info_message(update)
    await update.message.reply_text(
        f"Введите Ваш возраст:",
    )
    return LIFESTYLE


async def basic_metabolism(update, context):
    user_lifestyle = update.message.text
    context.user_data['lifestyle'] = user_lifestyle
    logger.info('%s указал активность %s', update.message.from_user.first_name, user_lifestyle)
    user = context.user_data
    bmr = await _bmr_calculator(user)
    amr = int(bmr * BMR_AMR[user['lifestyle']])
    user['amr'] = amr
    await update.message.reply_text(
        f"Ваш базовый обмен равен {amr} калорий"
    )
    reply_keyboard = [['Похудеть', 'Сохранить вес', 'Набрать массу']]
    await update.message.reply_text(
        f"Какую цель вы преследуете?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    return AIM


async def _bmr_calculator(user):
    if user['sex'] == 'Мужчина':
        bmr = 88.362 + (13.397 * user['weight']) + (4.799 * user['height']) - (5.677 * user['age'])
    else:
        bmr = 447.593 + (9.247 * user['weight']) + (3.098 * user['height']) - (3.098 * user['age'])
    return int(bmr)


async def aim(update, context):
    user_aim = update.message.text
    context.user_data['aim'] = user_aim
    user = context.user_data
    user['calories_goal'] = int(AIMS[user_aim] * user['amr'])
    user['days'] = {}
    user['days'][date.today()] = 0
    logger.info('%s указал целью %s. Имеет основной обмен %s, нужно тратить %s в день',
                update.message.from_user.first_name, user_aim, user['amr'], user['calories_goal'])
    await update.message.reply_text(
        f"Отлично. Ваша цель: {user_aim}.\n"
        f"Для этого ежедневно нужно употреблять {user['calories_goal']} калорий",
        reply_markup=ReplyKeyboardRemove()
    )
    await _ask_for_request(update)
    return MEAL


async def meal(update, context):
    meal_info = update.message.text
    user = context.user_data
    resp_text, resp_number = meal_calories(meal_info)
    logger.info('%s сделал запрос %s и получил ответ %s (%s)',
                update.message.from_user.first_name, meal_info, resp_number, resp_text)
    today = await _date_update(user)
    if resp_number:
        user['days'][today] += resp_number
        await update.message.reply_text(
            f"Вы употребили в пищу {resp_number} калорий.\n"
            f"Суммарно за сегодня {user['days'][today]}\n"
            f"Осталось употребить {max(user['calories_goal'] - user['days'][today], 0)}",
        )
        logger.info('Удачный запрос %s', user)
    else:
        await update.message.reply_text(
            f"К сожалению по данному запросу не получилось посчитать калории",
        )
        logger.info('Неудачный запрос %s', user)
    await _ask_for_request(update)
    return MEAL


async def _ask_for_request(update):
    await update.message.reply_text(
        f"Расскажите, что вы ели. Я посчитаю калории за вас.",
    )


async def _date_update(user):
    today = date.today()
    if today not in user['days']:
        user['days'][today] = 0
    return today


async def report(update, context):
    report_message = []
    users_days = context.user_data['days']
    user = context.user_data
    report_message.append(f"Ваша цель: {user['aim']}\n"
                          f"Необходимо употреблять {user['calories_goal']} калорий.")
    users_days_ordered = dict(reversed(list(users_days.items())))
    calories_goal = user['calories_goal']
    goal = user['aim']
    for day, calories in users_days_ordered.items():
        if goal == 'Похудеть' and calories <= user['calories_goal'] or \
                goal == 'Набрать массу' and calories >= calories_goal or \
                goal == 'Сохранить вес' and calories_goal * 0.9 < calories < calories_goal * 1.1:
            report_message.append(f'👍 {day} вы употребили {calories}')
        else:
            report_message.append(f'👎 {day} вы употребили {calories}.')
    await update.message.reply_text(
        '\n\n'.join(report_message)
    )
    await _ask_for_request(update)
    return MEAL


async def change_weight_command(update, context):
    user = update.effective_user
    logger.info('%s меняет вес', user.first_name)
    await update.message.reply_text('Укажите ваш текущий вес в килограммах')
    return CHANGE_WEIGHT


async def change_weight(update, context):
    user_weight = update.message.text
    user_weight = user_weight.replace(',', '.')
    user = context.user_data
    user['weight'] = round(float(user_weight), 1)
    user['bmr'] = await _bmr_calculator(user)
    user['amr'] = int(user['bmr'] * BMR_AMR[user['lifestyle']])
    user['calories_goal'] = int(AIMS[user['aim']] * user['amr'])
    logger.info('%s изменил вес %s. Новый обмен %s, новая цель %s',
                update.message.from_user.first_name, user_weight, user['amr'], user['calories_goal'])
    await update.message.reply_text(
        f"Установлен новый вес {user['weight']} кг. Ваш базовый обмен {user['amr']}. "
        f"Необходимо потреблять {user['calories_goal']} калорий"
    )
    await _ask_for_request(update)

    return MEAL


async def change_weight_wrong(update, context):
    await _wrong_info_message(update)
    await update.message.reply_text('Укажите ваш текущий вес:')
    logger.info('%s указал странный вес', update.message.from_user.first_name)

    return CHANGE_WEIGHT


def main():
    persistence = PicklePersistence(filepath="conversationbot")
    application = Application.builder().token(TG_TOKEN).persistence(persistence).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.TEXT, start)
        ],
        states={
            SEX: [MessageHandler(filters.TEXT, sex)],
            WEIGHT: [MessageHandler(filters.Regex("^(Мужчина|Женщина)$"), weight)],
            HEIGHT: [MessageHandler(filters.Regex("^([3-9][0-9]|1[0-9][0-9])((\.|\,)[1-9])?$"), height),
                     MessageHandler(filters.TEXT & ~filters.COMMAND, height_wrong_weight)
                     ],
            AGE: [MessageHandler(filters.Regex("^(1[0-9][0-9]|2[0-4][0-9])$"), age),
                  MessageHandler(filters.TEXT & ~filters.COMMAND, age_wrong_height)
                  ],
            LIFESTYLE: [MessageHandler(filters.Regex("^([0-9][0-9]|1[0-2][0-9])$"), lifestyle),
                        MessageHandler(filters.TEXT & ~filters.COMMAND, lifestyle_wrong_age)
                        ],
            BASIC_METABOLISM: [MessageHandler(filters.Regex("^(Низкая|Средняя|Высокая|Спортсмен)$"), basic_metabolism)],
            AIM: [MessageHandler(filters.Regex("^(Похудеть|Сохранить вес|Набрать массу)$"), aim)],
            MEAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, meal),
                   CommandHandler("report", report),
                   CommandHandler("change_weight", change_weight_command)],
            CHANGE_WEIGHT: [MessageHandler(filters.Regex("^([3-9][0-9]|1[0-9][0-9])((\.|\,)[1-9])?$"), change_weight),
                            MessageHandler(filters.TEXT & ~filters.COMMAND, change_weight_wrong)
                            ],
        },
        fallbacks=[CommandHandler("start", start),
                   CommandHandler("report", report),
                   CommandHandler("change_weight", change_weight_command)],
        name="my_conversation",
        persistent=True,
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
