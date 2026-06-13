import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
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
        # /reel/, /p/, /tv/ hammasi ishlaydi
        post = instaloader.Post.from_shortcode(loader.context, re.search(r'/(p|reel|tv)/([^/?]+)', url).group(2))
        files = []
        if post.is_video:
            r = requests.get(post.video_url, timeout=30)
            files.append({'type': 'video', 'file': BytesIO(r.content), 'cap': f"Instagram Video 🎥\n{url}"})
        else:
            try:
                for node in post.get_sidecar_nodes():
                    r = requests.get(node.display_url, timeout=30)
                    files.append({'type': 'photo', 'file': BytesIO(r.content), 'cap': f"Instagram Photo 📸\n{url}"})
            except:
                pass
            if not files:
                r = requests.get(post.url, timeout=30)
                files.append({'type': 'photo', 'file': BytesIO(r.content), 'cap': f"Instagram Photo 📸\n{url}"})
        return files
    except Exception as e:
        print(f"Insta xato: {e}")
        return None

def yt_search(query, n=5):
    try:
        res = YoutubeSearch(query, max_results=n)
        vids = []
        for v in res.videos:
            vids.append({
                'title': v['title'],
                'id': v['id'],
                'thumb': v['thumbnails'][0] if v['thumbnails'] else '',
                'dur': v['duration'],
                'ch': v['channel'],
            })
        return vids
    except Exception as e:
        print(f"YT search xato: {e}")
        return None

def yt_dl(url):
    try:
        opts = {
            'format': 'best[ext=mp4][filesize<50M]/best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info['url']
            r = requests.get(video_url, timeout=60)
            return {
                'file': BytesIO(r.content),
                'title': info['title'],
                'thumb': info.get('thumbnail', ''),
                'dur': info.get('duration', 0)
            }
    except Exception as e:
        print(f"YT dl xato: {e}")
        return None

def music_search(song):
    vids = yt_search(f"{song} music official", 10)
    if not vids:
        return None
    mus = [v for v in vids if any(w in v['title'].lower() for w in ['official', 'music', 'audio', 'lyrics'])]
    return mus[:5] if mus else vids[:5]

def is_insta_url(text):
    return 'instagram.com/' in text

def extract_insta_url(text):
    match = re.search(r'https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[^\s/?]+', text)
    return match.group(0) if match else None

async def start(update, context):
    txt = f"""📥 {BOT_NAME} 📥

Instagram + YouTube + Music yuklab olish!

📌 Instagram reel/post linkni yuboring → Video/rasm
📌 /youtube [nom] → YouTube video
📌 /music [nom] → Qo'shiq
📌 /instagram [link] → Instagram
📌 /search [nom] → Qidirish
"""
    await update.message.reply_text(txt)

async def youtube_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Misol: /youtube Dildora Niyozova")
        return
    query = " ".join(context.args)
    msg = await update.message.reply_text(f"⏳ Qidirilmoqda: {query}")
    vids = yt_search(query)
    if not vids:
        await msg.edit_text("❌ Topilmadi!")
        return
    text = "🎥 YouTube natijalari:\n\n"
    kb = []
    for i, v in enumerate(vids[:5], 1):
        text += f"{i}. {v['title']}\n📺 {v['ch']} | ⏱ {v['dur']}\n\n"
        title_short = v['title'][:30] + ('...' if len(v['title']) > 30 else '')
        kb.append([InlineKeyboardButton(f"⬇️ {i}. {title_short}", callback_data=f"yt_{v['id']}")])
    await msg.edit_text(text + "Birini tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def music_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Misol: /music Shahzoda")
        return
    song = " ".join(context.args)
    msg = await update.message.reply_text(f"⏳ Qidirilmoqda: {song}")
    vids = music_search(song)
    if not vids:
        await msg.edit_text("❌ Topilmadi!")
        return
    text = f"🎵 Musiqa natijalari ({song}):\n\n"
    kb = []
    for i, v in enumerate(vids[:5], 1):
        text += f"{i}. {v['title']}\n📺 {v['ch']} | ⏱ {v['dur']}\n\n"
        title_short = v['title'][:30] + ('...' if len(v['title']) > 30 else '')
        kb.append([InlineKeyboardButton(f"🎵 {i}. {title_short}", callback_data=f"yt_{v['id']}")])
    await msg.edit_text(text + "Birini tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def insta_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Misol: /instagram https://www.instagram.com/reel/ABC/")
        return
    url = context.args[0]
    if not is_insta_url(url):
        await update.message.reply_text("❌ Instagram linki emas!")
        return
    await download_insta(update, url)

async def download_insta(update, url):
    msg = await update.message.reply_text(f"⏳ Yuklab olinmoqda...")
    files = insta_dl(url)
    if not files:
        await msg.edit_text("❌ Yuklab bo'lmadi! Login kerak bo'lishi mumkin.")
        return
    await msg.delete()
    for f in files:
        try:
            if f['type'] == 'video':
                await update.message.reply_video(video=f['file'], caption=f['cap'])
            else:
                await update.message.reply_photo(photo=f['file'], caption=f['cap'])
        except Exception as e:
            await update.message.reply_text(f"❌ Yuborishda xato: {e}")
    await update.message.reply_text("✅ Tayyor!")

async def search_cmd(update, context):
    if not context.args:
        await update.message.reply_text("❌ Misol: /search Ulug'bek Rahmatullayev")
        return
    query = " ".join(context.args)
    if is_insta_url(query):
        url = extract_insta_url(query)
        if url:
            await download_insta(update, url)
            return
    await update.message.reply_text(f"⏳ Qidirilmoqda: {query}")
    vids = yt_search(query)
    if not vids:
        await update.message.reply_text("❌ Topilmadi!")
        return
    text = f"🎥 Natijalar ({query}):\n\n"
    kb = []
    for i, v in enumerate(vids[:5], 1):
        text += f"{i}. {v['title']}\n📺 {v['ch']} | ⏱ {v['dur']}\n\n"
        title_short = v['title'][:30] + ('...' if len(v['title']) > 30 else '')
        kb.append([InlineKeyboardButton(f"⬇️ {i}. {title_short}", callback_data=f"yt_{v['id']}")])
    await update.message.reply_text(text + "Birini tanlang:", reply_markup=InlineKeyboardMarkup(kb))

async def yt_callback(update, context):
    q = update.callback_query
    await q.answer()
    vid_id = q.data.replace("yt_", "")
    url = f"https://www.youtube.com/watch?v={vid_id}"
    await q.edit_message_text("⏳ Yuklab olinmoqda... (1-2 daqiqa)")
    dl = yt_dl(url)
    if not dl:
        await q.edit_message_text("❌ Yuklab bo'lmadi!")
        return
    try:
        await context.bot.send_video(
            chat_id=q.message.chat_id,
            video=dl['file'],
            caption=f"🎥 {dl['title']}"
        )
        await q.edit_message_text("✅ Yuklab olindi!")
    except Exception as e:
        await q.edit_message_text(f"❌ Xato: {e}")

async def auto_handler(update, context):
    txt = update.message.text
    if not txt:
        return
    # Instagram link avtomatik
    if is_insta_url(txt):
        url = extract_insta_url(txt)
        if url:
            await download_insta(update, url)
            return
    # YouTube link avtomatik
    if 'youtube.com/watch' in txt or 'youtu.be/' in txt:
        msg = await update.message.reply_text("⏳ YouTube yuklab olinmoqda...")
        dl = yt_dl(txt.strip())
        if dl:
            try:
                await update.message.reply_video(video=dl['file'], caption=f"🎥 {dl['title']}")
                await msg.delete()
            except Exception as e:
                await msg.edit_text(f"❌ Xato: {e}")
        else:
            await msg.edit_text("❌ Yuklab bo'lmadi!")
        return

def main():
    print(f"🚀 {BOT_NAME} ishga tushmoqda...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("youtube", youtube_cmd))
    app.add_handler(CommandHandler("music", music_cmd))
    app.add_handler(CommandHandler("instagram", insta_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CallbackQueryHandler(yt_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_handler))
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
