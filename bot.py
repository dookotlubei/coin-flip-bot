import os, random, sqlite3, asyncio
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN=os.environ['BOT_TOKEN']
BASE=Path(__file__).parent
DB=os.getenv('DB_PATH', str(BASE/'stats.db'))
HEADS=BASE/'assets'/'heads.jpg'; TAILS=BASE/'assets'/'tails.jpg'

def init_db():
    with sqlite3.connect(DB) as c:
        c.execute('CREATE TABLE IF NOT EXISTS stats (scope TEXT PRIMARY KEY, heads INTEGER NOT NULL DEFAULT 0, tails INTEGER NOT NULL DEFAULT 0)')

def scope(update):
    chat=update.effective_chat
    return f'chat:{chat.id}' if chat.type in ('group','supergroup') else f'user:{update.effective_user.id}'

def get_stats(s):
    with sqlite3.connect(DB) as c:
        row=c.execute('SELECT heads,tails FROM stats WHERE scope=?',(s,)).fetchone()
        return row or (0,0)

def add(s, side):
    with sqlite3.connect(DB) as c:
        c.execute('INSERT OR IGNORE INTO stats(scope,heads,tails) VALUES(?,0,0)',(s,))
        c.execute(f'UPDATE stats SET {side}={side}+1 WHERE scope=?',(s,))
    return get_stats(s)

def reset(s):
    with sqlite3.connect(DB) as c:
        c.execute('INSERT OR REPLACE INTO stats(scope,heads,tails) VALUES(?,0,0)',(s,))

def keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton('🪙 ПОДБРОСИТЬ',callback_data='flip')],[InlineKeyboardButton('🔄 СБРОСИТЬ СЧЁТ',callback_data='reset')]])

def text(h,t,result=None):
    top=f'🎯 Результат: {result}\n\n' if result else '🪙 Орёл или Решка?\n\n'
    return f'{top}📊 Всего бросков: {h+t}\n🦅 Орёл — {h}\n👑 Решка — {t}'

async def start(update:Update, context:ContextTypes.DEFAULT_TYPE):
    h,t=get_stats(scope(update))
    await update.message.reply_text(text(h,t),reply_markup=keyboard())

async def flip(q, s):
    # lightweight Telegram-side animation while the result is being chosen
    await q.edit_message_text('🪙 Подбрасываю монетку…')
    await asyncio.sleep(.55)
    await q.edit_message_text('🪙  ◐  Вращается…')
    await asyncio.sleep(.55)
    await q.edit_message_text('🪙  ◑  Вращается…')
    await asyncio.sleep(.55)
    side='heads' if random.SystemRandom().randrange(2)==0 else 'tails'
    h,t=add(s,side)
    result='🦅 ОРЁЛ' if side=='heads' else '👑 РЕШКА'
    photo=HEADS if side=='heads' else TAILS
    await q.message.reply_photo(photo=photo.open('rb'),caption=text(h,t,result),reply_markup=keyboard())
    try: await q.message.delete()
    except Exception: pass

async def buttons(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query; await q.answer(); s=scope(update)
    if q.data=='flip': await flip(q,s)
    elif q.data=='reset':
        reset(s)
        try: await q.edit_message_caption(caption=text(0,0),reply_markup=keyboard())
        except Exception: await q.edit_message_text(text(0,0),reply_markup=keyboard())

async def reset_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    reset(scope(update)); await update.message.reply_text(text(0,0),reply_markup=keyboard())

def main():
    init_db(); app=Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler('start',start)); app.add_handler(CommandHandler('coin',start)); app.add_handler(CommandHandler('reset',reset_cmd)); app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling(drop_pending_updates=True)

if __name__=='__main__': main()
