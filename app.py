import base64
from io import BytesIO
from typing import TYPE_CHECKING

from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from config.openai_client import client, generate_response, generate_transcription
from config.telegram_bot import application
from exceptions.bad_argument_error import BadArgumentError
from exceptions.bad_choice_error import BadChoiceError
from utils.helpers import check_user_settings

if TYPE_CHECKING:
    from openai.types.chat.chat_completion import ChatCompletion

# Define states
(
    TASK_CHOICE,
    KNOWLEDGE_GAIN,
    INTERVIEW_PREP,
    PROBLEM_SOL,
    CODE_EXPL,
    CODE_WRITING,
    PROBLEM_HELP,
    EDA,
    MEME_EXPL,
    USER_SETTINGS,
    INTERVIEW_HARD,
    QUESTIONS_HARD,
    INTERN,
    JUNIOR,
    MIDDLE,
    SENIOR,
    EASY,
    MEDIUM,
    HARD,
    ALGO_TASK,
    ML_TASK,
    USER_REPLY,
) = range(22)

CALLBACK_QUERY_ARG = "update.callback_query"
MESSAGE_ARG = "update.message"


async def start(update: Update, _: CallbackContext) -> int:
    """Начальный хэндлер дерева команд."""
    keyboard = [
        [InlineKeyboardButton("Прокачка знаний", callback_data="KNOWLEDGE_GAIN")],
        [InlineKeyboardButton("Помоги решить задачу", callback_data="PROBLEM_SOL")],
        [InlineKeyboardButton("Oбъясни IT мем", callback_data="MEME_EXPL")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.message:  # When /start command is used
        await update.message.reply_text("Выберите задачу:", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text("Please choose:", reply_markup=reply_markup)
    return TASK_CHOICE


async def task_choice(update: Update, _: CallbackContext) -> int:
    """хэндлер выбора базовой группы задач."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data

    if choice == "KNOWLEDGE_GAIN":
        keyboard = [
            [InlineKeyboardButton("Подготовка к собесу", callback_data="INTERVIEW_PREP")],
            [InlineKeyboardButton("Задача по алгоритмам", callback_data="ALGO_TASK")],
            [InlineKeyboardButton("Задача по Ml", callback_data="ML_TASK")],
            [InlineKeyboardButton("Настройки пользователя", callback_data="USER_SETTINGS")],
            [InlineKeyboardButton("Назад", callback_data="BACK")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Ты выбрал прокачку знаний:", reply_markup=reply_markup)
        return KNOWLEDGE_GAIN
    if choice == "PROBLEM_SOL":
        keyboard = [
            [InlineKeyboardButton("Объясни код", callback_data="CODE_EXPL")],
            [InlineKeyboardButton("Напиши код", callback_data="CODE_WRITING")],
            [InlineKeyboardButton("Помоги решить задачу", callback_data="PROBLEM_HELP")],
            [InlineKeyboardButton("EDA датасета", callback_data="EDA")],
            [InlineKeyboardButton("Назад", callback_data="BACK")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Помощь в решении задачи:", reply_markup=reply_markup)
        return PROBLEM_SOL
    if choice == "MEME_EXPL":
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        keyboard = [
            [InlineKeyboardButton("Отмена", callback_data="CANCEL")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Отправьте мем одним изображением", reply_markup=reply_markup)
        return MEME_EXPL
    raise BadChoiceError(choice)  # type: ignore  # noqa: PGH003


async def knowledge_gain(update: Update, context: CallbackContext) -> int:
    """хэндлер выбора прокачки знаний."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data
    if choice == "INTERVIEW_PREP" and check_user_settings(
        context,
    ):
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(
            text="Please send a voice message or text reply.",
        )
        return USER_REPLY
    if choice == "ALGO_TASK" and check_user_settings(context):
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(
            text="Please send a voice message or text reply.",
        )
        return USER_REPLY
    if choice == "ML_TASK" and check_user_settings(context):
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(
            text="Please send a voice message or text reply.",
        )
        return USER_REPLY
    if choice == "USER_SETTINGS":
        keyboard = [
            [InlineKeyboardButton("Уровень подготовки", callback_data="INTERVIEW_HARD")],
            [InlineKeyboardButton("Сложность заданий", callback_data="QUESTIONS_HARD")],
            [InlineKeyboardButton("BACK", callback_data="BACK")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Настройки:", reply_markup=reply_markup)
        return USER_SETTINGS
    if choice == "BACK":
        return await start(update, context)
    raise BadChoiceError(choice)  # type: ignore  # noqa: PGH003


async def problem_solving(update: Update, context: CallbackContext) -> int:
    """хэндлер выбора помощи в решении задач."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data
    if choice == "CODE_EXPL":
        await code_explanation(update, context)
    if choice == "CODE_WRITING":
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(text="Скоро мы научимся писать код. Беседа завершена.")
        return ConversationHandler.END
    if choice == "PROBLEM_HELP":
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(
            text="Скоро мы научимся помогать в решении задач. Беседа завершена.",
        )
        return ConversationHandler.END
    if choice == "EDA":
        if update.callback_query is None:
            raise BadArgumentError(CALLBACK_QUERY_ARG)
        await update.callback_query.edit_message_text(text="Скоро мы научимся EDA. Беседа завершена.")
        return ConversationHandler.END
    if choice == "BACK":
        return await start(update, context)
    raise BadChoiceError(choice)  # type: ignore  # noqa: PGH003


async def code_explanation(update: Update, _: CallbackContext) -> int:
    """Хэндлер выбора объяснения кода."""
    if update.callback_query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await update.callback_query.edit_message_text(text="Скоро мы научимся объяснять код. Беседа завершена.")
    return ConversationHandler.END


async def user_settings(update: Update, context: CallbackContext) -> int:
    """Хэндлер выбора настроек пользоватея."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data
    if choice == "INTERVIEW_HARD":
        keyboard = [
            [InlineKeyboardButton("Intern", callback_data="INTERN")],
            [InlineKeyboardButton("Junior", callback_data="JUNIOR")],
            [InlineKeyboardButton("Middle", callback_data="MIDDLE")],
            [InlineKeyboardButton("Senior", callback_data="SENIOR")],
            [InlineKeyboardButton("BACK", callback_data="BACK")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Настройки:", reply_markup=reply_markup)
        return INTERVIEW_HARD
    if choice == "QUESTIONS_HARD":
        keyboard = [
            [InlineKeyboardButton("easy", callback_data="EASY")],
            [InlineKeyboardButton("medium", callback_data="MEDIUM")],
            [InlineKeyboardButton("hard", callback_data="HARD")],
            [InlineKeyboardButton("BACK", callback_data="BACK")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text="Настройки:", reply_markup=reply_markup)
        return QUESTIONS_HARD
    if choice == "BACK":
        return await start(update, context)
    raise BadChoiceError(choice)  # type: ignore  # noqa: PGH003


async def interview_hard(update: Update, context: CallbackContext) -> int:
    """Хэндлер выбора уровня знаний."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data
    if choice == "INTERN":
        context.user_data["questions_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "JUNIOR":
        context.user_data["questions_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "MIDDLE":
        context.user_data["questions_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "SENIOR":
        context.user_data["questions_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "BACK":
        pass
    keyboard = [
        [InlineKeyboardButton("Уровень подготовки", callback_data="INTERVIEW_HARD")],
        [InlineKeyboardButton("Сложность заданий", callback_data="QUESTIONS_HARD")],
        [InlineKeyboardButton("BACK", callback_data="BACK")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Настройки:", reply_markup=reply_markup)
    return USER_SETTINGS


async def questions_hard(update: Update, context: CallbackContext) -> int:
    """Хэндлер выбора сложности вопросов."""
    query = update.callback_query
    if query is None:
        raise BadArgumentError(CALLBACK_QUERY_ARG)
    await query.answer()
    choice = query.data
    if choice == "EASY":
        context.user_data["interview_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "MEDIUM":
        context.user_data["interview_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "HARD":
        context.user_data["interview_hard"] = choice  # type: ignore  # noqa: PGH003
    if choice == "BACK":
        pass
    keyboard = [
        [InlineKeyboardButton("Уровень подготовки", callback_data="INTERVIEW_HARD")],
        [InlineKeyboardButton("Сложность заданий", callback_data="QUESTIONS_HARD")],
        [InlineKeyboardButton("BACK", callback_data="BACK")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text="Настройки:", reply_markup=reply_markup)
    return USER_SETTINGS


async def meme_explanation(update: Update, context: CallbackContext) -> int:
    """Хэндлер диалога объяснения IT мема."""
    query = update.callback_query
    if query and query.data == "CANCEL":
        return await start(update, context)
    if update.message is None:
        raise BadArgumentError(MESSAGE_ARG)
    file = await update.message.photo[-1].get_file()
    data = await file.download_as_bytearray()
    explanation = explain_meme(data)
    await update.message.reply_text(text=f"{explanation}")
    return await start(update, context)


def explain_meme(data: bytearray) -> str:
    """Отправить мем в ChatGPT и получить его строковое описание."""
    bytes_data = bytes(data)
    base64_encoded = base64.b64encode(bytes_data)
    base64_string = base64_encoded.decode("utf-8")
    response: ChatCompletion = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        # TODO @ntrubkin: написать промт на объяснение IT мема
                        "text": "Что на изображении?",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_string}",
                        },
                    },
                ],
            },
        ],
        max_tokens=1024,
        temperature=0.5,
    )
    content = response.choices[0].message.content
    if content is None:
        logger.error("OpenAI содержит пустой ответ")
        return ""
    return content.strip()


async def cancel(update: Update, _: CallbackContext) -> int:
    """Завершает беседу."""
    if update.message is None:
        raise BadArgumentError(MESSAGE_ARG)
    await update.message.reply_text("Беседа завершена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def handle_user_reply(update: Update, context: CallbackContext) -> None:
    """обработка  ответа от пользователя."""
    if update.message is None:
        raise BadArgumentError(MESSAGE_ARG)
    if update.message.voice:

        audio_file = await context.bot.get_file(update.message.voice.file_id)

        audio_bytes = BytesIO(await audio_file.download_as_bytearray())

        transcription = generate_transcription(audio_bytes)

        reply = generate_response(transcription)
        await update.message.reply_text(reply)

        logger.info("user:", audio_file.file_path)
        logger.info("transcription:", transcription)
        logger.info("assistant:", reply)

    if update.message.text:
        reply = generate_response(update.message.text)
        await update.message.reply_text(reply)


"""Run the bot."""
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        TASK_CHOICE: [CallbackQueryHandler(task_choice)],
        KNOWLEDGE_GAIN: [CallbackQueryHandler(knowledge_gain)],
        PROBLEM_SOL: [CallbackQueryHandler(problem_solving)],
        USER_SETTINGS: [CallbackQueryHandler(user_settings)],
        INTERVIEW_HARD: [CallbackQueryHandler(interview_hard)],
        QUESTIONS_HARD: [CallbackQueryHandler(questions_hard)],
        USER_REPLY: [MessageHandler(filters.VOICE | filters.TEXT, handle_user_reply)],
        MEME_EXPL: [CallbackQueryHandler(meme_explanation), MessageHandler(filters.PHOTO, meme_explanation)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

application.add_handler(conv_handler)
application.add_handler(CommandHandler("start", start))

# Запуск бота
application.run_polling()
