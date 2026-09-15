import os
import random
import sqlite3
import asyncio
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = os.environ["BOT_TOKEN"]

BASE = Path(__file__).parent
DB = BASE / "stats.db"

# Видео броска
HEADS_VIDEO = BASE / "assets" / "heads.mp4"
TAILS_VIDEO = BASE / "assets" / "tails.mp4"

# Финальные изображения
HEADS_FINAL = BASE / "assets" / "heads.jpg"
TAILS_FINAL = BASE / "assets" / "tails.jpg"

# Длительность видео в секундах.
# Потом выставим точно под наши MP4.
VIDEO_DURATION = 3.0


def init_db():
    with sqlite3.connect(DB) as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS stats (
                chat_id TEXT PRIMARY KEY,
                heads INTEGER DEFAULT 0,
                tails INTEGER DEFAULT 0
            )
            """
        )


def get_stats(chat_id):
    with sqlite3.connect(DB) as c:
        c.execute(
            """
            INSERT OR IGNORE INTO stats(chat_id, heads, tails)
            VALUES (?, 0, 0)
            """,
            (str(chat_id),),
        )

        row = c.execute(
            """
            SELECT heads, tails
            FROM stats
            WHERE chat_id=?
            """,
            (str(chat_id),),
        ).fetchone()

    return row or (0, 0)


def add_result(chat_id, side):
    with sqlite3.connect(DB) as c:
        c.execute(
            """
            INSERT OR IGNORE INTO stats(chat_id, heads, tails)
            VALUES (?, 0, 0)
            """,
            (str(chat_id),),
        )

        if side == "heads":
            c.execute(
                """
                UPDATE stats
                SET heads = heads + 1
                WHERE chat_id=?
                """,
                (str(chat_id),),
            )
        else:
            c.execute(
                """
                UPDATE stats
                SET tails = tails + 1
                WHERE chat_id=?
                """,
                (str(chat_id),),
            )

    return get_stats(chat_id)


def reset_stats(chat_id):
    with sqlite3.connect(DB) as c:
        c.execute(
            """
            INSERT OR IGNORE INTO stats(chat_id, heads, tails)
            VALUES (?, 0, 0)
            """,
            (str(chat_id),),
        )

        c.execute(
            """
            UPDATE stats
            SET heads=0, tails=0
            WHERE chat_id=?
            """,
            (str(chat_id),),
        )


def keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🪙 ПОДБРОСИТЬ",
                    callback_data="flip",
                )
            ],
            [
                InlineKeyboardButton(
                    "🔄 СБРОСИТЬ СЧЁТ",
                    callback_data="reset",
                )
            ],
        ]
    )


def stats_text(heads, tails, result=None):
    total = heads + tails

    if result == "heads":
        title = "🦅 ОРЁЛ!"
    elif result == "tails":
        title = "👑 РЕШКА!"
    else:
        title = "🪙 Орёл или Решка?"

    return (
        f"{title}\n\n"
        f"📊 Всего бросков: {total}\n"
        f"🦅 Орёл — {heads}\n"
        f"👑 Решка — {tails}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    heads, tails = get_stats(chat_id)

    await update.message.reply_text(
        stats_text(heads, tails),
        reply_markup=keyboard(),
    )


async def do_flip(chat_id, bot):
    # Случайно выбираем сторону
    side = random.choice(["heads", "tails"])

    # Записываем результат в статистику
    heads, tails = add_result(chat_id, side)

    if side == "heads":
        video_file = HEADS_VIDEO
        final_image = HEADS_FINAL
    else:
        video_file = TAILS_VIDEO
        final_image = TAILS_FINAL

    # Отправляем видео броска монеты
    with open(video_file, "rb") as video:
        animation_message = await bot.send_animation(
            chat_id=chat_id,
            animation=video,
        )

    # Ждём окончания одного броска
    await asyncio.sleep(VIDEO_DURATION)

    # Удаляем видео, чтобы оно не продолжало крутиться
    try:
        await animation_message.delete()
    except Exception:
        pass

    # Показываем окончательный результат
    with open(final_image, "rb") as photo:
        await bot.send_photo(
            chat_id=chat_id,
            photo=photo,
            caption=stats_text(heads, tails, side),
            reply_markup=keyboard(),
        )


async def coin_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    await do_flip(
        update.effective_chat.id,
        context.bot,
    )


async def reset_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat_id = update.effective_chat.id

    reset_stats(chat_id)

    await update.message.reply_text(
        stats_text(0, 0),
        reply_markup=keyboard(),
    )


async def buttons(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    await query.answer()

    chat_id = update.effective_chat.id

    if query.data == "flip":
        await do_flip(
            chat_id,
            context.bot,
        )

    elif query.data == "reset":
        reset_stats(chat_id)

        try:
            await query.edit_message_caption(
                caption=stats_text(0, 0),
                reply_markup=keyboard(),
            )

        except Exception:
            try:
                await query.edit_message_text(
                    text=stats_text(0, 0),
                    reply_markup=keyboard(),
                )

            except Exception:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=stats_text(0, 0),
                    reply_markup=keyboard(),
                )


def main():
    init_db()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    app.add_handler(
        CommandHandler(
            "coin",
            coin_command,
        )
    )

    app.add_handler(
        CommandHandler(
            "reset",
            reset_command,
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            buttons,
        )
    )

    print(
        "BOT STARTED",
        flush=True,
    )

    app.run_polling(
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
