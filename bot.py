import asyncio
import os
import re
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import instaloader
import requests
import yt_dlp
from youtube_search import YoutubeSearch
from io import BytesIO

BOT_TOKEN = "8823632699:AAERZ0B34FnYrQ_fZSYkpxj_NKbPtVGPq00"
BOT_NAME = "Insta Saqla Bot"
BOT_USERNAME = "Insta_saqlagichbot"

loader = instaloader.Instaloader()

def insta_dl(url):
    try:
        post = loader.get_post_by_url(url)
        files = []
        if post.is_video:
            r = requests.get(post.video_url)
            files.append({'type': 'video', 'file': BytesIO(r.content), 'cap': f"Instagram Video 🎥\n{url}"})
        else:
            for img in post.get_sidecar_nodes():
                r = requests.get(img.display_url)
                files.append({'type': 'photo', 'file': BytesIO(r.content), 'cap': f"Instagram Photo 📸\n{url}"})
            if not files:
                r = requests.get(post.url)
                files.append({'type': 'photo', 'file': BytesIO(r.content), 'cap': f"Instagram Photo 📸\n{url}"})
        return files
    except Exception as e:
        print(f"❌ Insta: {e}")
        return None

def yt_search(query, n=5):
    try:
        res = YoutubeSearch(query, max_results=n)
        vids = [{'title': v['title'], 'url': f"https://www.youtube.com/watch?v={v['id']}", 'id': v['id'], 'thumb': v['thumbnails'][0], 'dur': v['duration'], 'ch': v['channel'], 'views': v['views']} for v in res.videos]
        return vids
    except Exception as e:
        print(f"❌ YT search: {e}")
        return None

def yt_dl(url):
    try:
        ydl = yt_dlp.YoutubeDL({'format': 'best[ext=mp4]', 'quiet': True, 'no_warnings': True})
        info = ydl.extract_info(url, download=False)
        r = requests.get(info['url'])
        return {'file': BytesIO(r.content), 'title': info['title'], 'thumb': info['thumbnail'], 'dur': info['duration']}
    except Exception as e:
        print(f"❌ YT dl: {e}")
        return None

def music_search(song):
    vids = yt_search(f"{song} song official", 10)
    if not vids:
        return None
    mus = [v for v in vids if 'official' in v['title'].lower() or 'music' in v['title'].lower()]
    return mus[:5] if mus else vids[:5]

async def start(update, context):
    txt = f"""📥 **{BOT_NAME}** 📥

Instagram + YouTube + Music yuklab olish!

📌 **Instagram:** Link send qil → Video/rasm
📌 **YouTube:** /youtube [nom] → Video topish
📌 **Music:** /music [nom] → Qo'shiq topish

Commands:
/youtube [nom] - YouTube
/music [nom] - Music
/instagram [link] - Instagram
/search [nom] - Hamma
"""
    await update.message.reply_text(txt)

async def youtube_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Nom yuborilmadi!\nMisol: /youtube Baby Shark")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"⏳ Topish... {query}")
    vids = yt_search(query)
    if not vids:
        await update.message.reply_text("❌ Topilmadi!")
        return
    msg = "🎥 **YouTube Topildi:**\n\n"
    kb = []
    for i, v in enumerate(vids[:5], 1):
        msg += f"{i}. **{v['title']}**\n📺 {v['ch']}\n⏱ {v['dur']}\n\n"
        kb.append([InlineKeyboardButton(f"{i}. {v['title'][:25]}...", callback_data=f"yt_{v['id']}")])
    await update.message.reply_text(msg + "📌 Raqam tanlang:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def music_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Nom yuborilmadi!\nMisol: /music Baby Shark")
        return
    song = " ".join(context.args)
    await update.message.reply_text(f"⏳ Topish... {song}")
    vids = music_search(song)
    if not vids:
        await update.message.reply_text("❌ Topilmadi!")
        return
    msg = f"🎵 **Qo'shiq Topildi ({song}):**\n\n"
    kb = []
    for i, v in enumerate(vids[:5], 1):
        msg += f"{i}. **{v['title']}**\n📺 {v['ch']}\n⏱ {v['dur']}\n\n"
        kb.append([InlineKeyboardButton(f"🎵 {i}. {v['title'][:25]}...", callback_data=f"music_{v['id']}")])
    await update.message.reply_text(msg + "📌 Raqam tanlang:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def vid_cb(update, context):
    q = update.callback_query
    await q.answer()
    vid_id = q.data.split('_')[1]
    url = f"https://www.youtube.com/watch?v={vid_id}"
    await q.edit_message_text("⏳ Yuklab olish...")
    dl = yt_dl(url)
    if not dl:
        await q.edit_message_text("❌ Xato!")
        return
    try:
        if dl['thumb']:
            th = requests.get(dl['thumb'])
            await context.bot.send_photo(chat_id=q.message.chat_id, photo=BytesIO(th.content))
        await context.bot.send_video(chat_id=q.message.chat_id, video=dl['file'], caption=f"🎥 **{dl['title']}**\n⏱ {dl['dur']}", parse_mode='Markdown')
        await q.edit_message_text("✅ Yuklab olish muvaffaqiyatli!")
    except Exception as e:
        await q.edit_message_text(f"❌ Xato: {e}")

async def insta_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Link yuborilmadi!\nMisol: /instagram https://www.instagram.com/p/ABC/")
        return
    url = context.args[0]
    if not url.startswith("https://www.instagram.com/"):
        await update.message.reply_text("❌ Noto'g'ri link!")
        return
    await update.message.reply_text(f"⏳ Yuklab olish... {url}")
    files = insta_dl(url)
    if not files:
        await update.message.reply_text("❌ Xato!")
        return
    for f in files:
        if f['type'] == 'video':
            await update.message.reply_video(video=f['file'], caption=f['cap'], parse_mode='Markdown')
        else:
            await update.message.reply_photo(photo=f['file'], caption=f['cap'], parse_mode='Markdown')
    await update.message.reply_text("✅ Yuklab olish muvaffaqiyatli!")

async def search_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Nom yuborilmadi!\nMisol: /search Baby Shark")
        return
    query = " ".join(context.args)
    await update.message.reply_text(f"⏳ Topish... {query}")
    if "instagram.com/" in query:
        links = re.findall(r'https://www\.instagram\.com/p/[\w/-]+', query)
        if links:
            files = insta_dl(links[0])
            if files:
                for f in files:
                    if f['type'] == 'video':
                        await update.message.reply_video(video=f['file'], caption=f['cap'])
                    else:
                        await update.message.reply_photo(photo=f['file'], caption=f['cap'])
                return
    vids = yt_search(query)
    if vids:
        msg = f"🎥 **YouTube ({query}):**\n\n"
        kb = []
        for i, v in enumerate(vids[:5], 1):
            msg += f"{i}. **{v['title']}**\n📺 {v['ch']}\n⏱ {v['dur']}\n\n"
            kb.append([InlineKeyboardButton(f"{i}. {v['title'][:25]}...", callback_data=f"yt_{v['id']}")])
        await update.message.reply_text(msg + "📌 Raqam tanlang:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Topilmadi!")

async def auto_link(update, context):
    txt = update.message.text
    if "instagram.com/" in txt:
        links = re.findall(r'https://www\.instagram\.com/p/[\w/-]+', txt)
        if links:
            files = insta_dl(links[0])
            if files:
                await update.message.reply_text(f"⏳ Yuklab olish... {links[0]}")
                for f in files:
                    if f['type'] == 'video':
                        await update.message.reply_video(video=f['file'], caption=f['cap'])
                    else:
                        await update.message.reply_photo(photo=f['file'], caption=f['cap'])

def main():
    print(f"🚀 {BOT_NAME} ishga tushmoqda...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("youtube", youtube_cmd))
    app.add_handler(CommandHandler("music", music_cmd))
    app.add_handler(CommandHandler("instagram", insta_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(vid_cb))
    from telegram.ext import MessageHandler, filters
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_link))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
