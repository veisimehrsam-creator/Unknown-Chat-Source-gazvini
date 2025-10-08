# anon_chat_bot_with_owner.py
# نیاز به telepot: pip install telepot
# اجرا: python3 anon_chat_bot_with_owner.py

import telepot
from telepot.loop import MessageLoop
import time
import threading

# ====== تنظیمات ======
BOT_TOKEN = "7202403883:AAEirCffdnkphr3EQRRop_RXw9P5IoJrgE8"   # توکن ربات رو اینجا بذار
OWNER_ID = 6586112677               # آیدی صاحب که فرستادی
# ======================

bot = telepot.Bot(BOT_TOKEN)

# وضعیت‌ها و داده‌ها (in-memory)
waiting_queue = []        # صف عادی (برای جفت‌سازی بین کاربران)
owner_queue = []          # صف ویژه برای وصل شدن به صاحب
active = {}               # user_id -> partner_user_id
status = {}               # user_id -> "idle"/"waiting"/"chatting"
lock = threading.Lock()   # برای هم‌زمانی

WELCOME = (
    "ربات چت ناشناس فعال شد!\n\n"
    "دستورها:\n"
    "/start - شروع یا یافتن هم‌صحبت\n"
    "/next  - قطع اتصال فعلی و یافتن هم‌صحبت جدید\n"
    "/stop  - قطع اتصال و خروج از صف\n"
    "/owner - وصل شدن به صاحب (در صورت آزاد بودن)\n"
    "/help  - نمایش این پیام"
)

def send_safe(chat_id, text, **kwargs):
    try:
        bot.sendMessage(chat_id, text, **kwargs)
    except Exception as e:
        print("send_safe error:", e)

def match_pair():
    """
    جفت‌سازی بین کاربران در صف عادی.
    فرض: lock گرفته شده.
    """
    while len(waiting_queue) >= 2:
        a = waiting_queue.pop(0)
        b = waiting_queue.pop(0)
        active[a] = b
        active[b] = a
        status[a] = "chatting"
        status[b] = "chatting"
        send_safe(a, "✅ به هم‌صحبت وصل شدی — پیام‌هایتان اکنون به هم فرستاده می‌شود. برای رفتن به نفر بعدی /next را بزن.")
        send_safe(b, "✅ به هم‌صحبت وصل شدی — پیام‌هایتان اکنون به هم فرستاده می‌شود. برای رفتن به نفر بعدی /next را بزن.")
        print(f"Matched {a} <-> {b}")

def match_owner_if_possible():
    """
    اگر صاحب آزاد باشه و صف owner_queue پر باشه، نفر بعدی رو وصل کن.
    فرض: lock گرفته شده.
    """
    # اگر صاحب در حالت chatting هست یا هیچکس در صف نیست کاری نکن
    if status.get(OWNER_ID) == "chatting":
        return
    if not owner_queue:
        return
    user_id = owner_queue.pop(0)
    # اگر کاربر هنوز بخواد (و وضعیت مناسب) باشه وصلش کن
    if status.get(user_id) in ("waiting_owner", "idle", None):
        active[user_id] = OWNER_ID
        active[OWNER_ID] = user_id
        status[user_id] = "chatting"
        status[OWNER_ID] = "chatting"
        send_safe(user_id, "✅ الان به صاحب وصل شدی — پیام‌هات به صاحب فرستاده می‌شه. برای قطع /next یا /stop رو بزن.")
        send_safe(OWNER_ID, f"✅ یک کاربر به شما وصل شد (id: {user_id}). برای قطع /next یا /stop را بزن.")
        print(f"Owner matched with {user_id}")

def enqueue_user(user_id):
    with lock:
        if status.get(user_id) == "chatting":
            send_safe(user_id, "شما در حال حاضر با کسی در چت هستید. برای جدا شدن /next یا /stop را بزنید.")
            return
        if status.get(user_id) == "waiting":
            send_safe(user_id, "شما قبلاً در صف انتظار هستید، لطفا کمی صبر کنید تا جفت شوید.")
            return
        # تازه وارد صف می‌کنیم
        waiting_queue.append(user_id)
        status[user_id] = "waiting"
        send_safe(user_id, "⏳ شما در صف انتظار قرار گرفتید، به محض یافتن هم‌صحبت اطلاع‌رسانی می‌شوید.")
        match_pair()

def enqueue_owner_request(user_id):
    with lock:
        if status.get(user_id) == "chatting":
            send_safe(user_id, "شما در حال حاضر با کسی در چت هستید. برای وصل شدن به صاحب ابتدا /next یا /stop را بزنید.")
            return
        if status.get(user_id) == "waiting_owner":
            send_safe(user_id, "شما قبلاً درخواست وصل شدن به صاحب را داده‌اید، لطفاً صبر کنید.")
            return
        # اگر صاحب الان آزاد باشه، بلافاصله وصل کن
        if status.get(OWNER_ID) != "chatting" and OWNER_ID not in active:
            active[user_id] = OWNER_ID
            active[OWNER_ID] = user_id
            status[user_id] = "chatting"
            status[OWNER_ID] = "chatting"
            send_safe(user_id, "✅ الان به صاحب وصل شدی — پیام‌هات به صاحب فرستاده می‌شه. برای قطع /next یا /stop رو بزن.")
            send_safe(OWNER_ID, f"✅ یک کاربر به شما وصل شد (id: {user_id}). برای قطع /next یا /stop را بزن.")
            print(f"Direct matched owner <-> {user_id}")
            return
        # در غیر اینصورت وارد صف صاحب کن
        owner_queue.append(user_id)
        status[user_id] = "waiting_owner"
        send_safe(user_id, "⏳ صاحب مشغول است. شما در صف صاحب قرار گرفتید، به محض آزاد شدن صاحب وصل می‌شوید.")
        # اطلاع به صاحب که یک نفر درخواست کرد (اختیاری)
        try:
            send_safe(OWNER_ID, f"ℹ️ یک کاربر درخواست اتصال به شما داده است. صف فعلی: {len(owner_queue)}")
        except Exception:
            pass

def disconnect_user(user_id, notify_partner=True):
    """
    اگر کاربر در حال چت هست، اتصال رو قطع کن.
    """
    with lock:
        partner = active.pop(user_id, None)
        if partner:
            # پاک کردن مرجع متقابل
            active.pop(partner, None)
            status[user_id] = "idle"
            status[partner] = "idle"
            if notify_partner:
                send_safe(partner, "🔴 هم‌صحبت شما اتصال را قطع کرد.")
            print(f"Disconnected {user_id} and {partner}")
            # اگر شریک صاحب بود و صاحب صف داشت، صاحب رو به نفر بعدی وصل کن
            if partner == OWNER_ID or user_id == OWNER_ID:
                # owner احتمالا الان idle هست؛ سعی کن نفر بعدی رو وصل کنی
                match_owner_if_possible()
            return partner
        # اگر در صف عادی بود حذفش کن
        if user_id in waiting_queue:
            waiting_queue.remove(user_id)
            status[user_id] = "idle"
            send_safe(user_id, "✅ از صف خارج شدید.")
            return None
        # اگر در صف صاحب بود حذفش کن
        if user_id in owner_queue:
            owner_queue.remove(user_id)
            status[user_id] = "idle"
            send_safe(user_id, "✅ از صف صاحب خارج شدید.")
            return None
        return None

def handle_command(msg, user_id, cmd):
    cmd = cmd.split()[0].lower()
    if cmd == "/start":
        # خوش‌آمد و افزودن به صف
        send_safe(user_id, WELCOME)
        enqueue_user(user_id)
    elif cmd == "/next":
        # قطع و دوباره صف عادی (برای صاحب هم همین دستور کار می‌کنه)
        with lock:
            if status.get(user_id) == "chatting":
                disconnect_user(user_id, notify_partner=True)
            elif status.get(user_id) == "waiting":
                if user_id in waiting_queue:
                    waiting_queue.remove(user_id)
                status[user_id] = "idle"
        send_safe(user_id, "⏭️ در حال یافتن هم‌صحبت جدید...")
        enqueue_user(user_id)
    elif cmd == "/stop":
        with lock:
            partner = active.get(user_id)
        if partner:
            disconnect_user(user_id, notify_partner=True)
            send_safe(user_id, "🔴 چت قطع شد. اگر می‌خواهی مجدد /start بزن.")
        else:
            # اگر در صف بود حذف می‌کنیم
            with lock:
                if user_id in waiting_queue:
                    waiting_queue.remove(user_id)
                if user_id in owner_queue:
                    owner_queue.remove(user_id)
                status[user_id] = "idle"
            send_safe(user_id, "✅ شما از صف خارج شدید.")
    elif cmd == "/owner":
        # کاربر درخواست وصل به صاحب می‌ده
        if user_id == OWNER_ID:
            send_safe(user_id, "شما صاحب هستید — برای مدیریت از /next یا /stop استفاده کنید.")
            return
        enqueue_owner_request(user_id)
    elif cmd == "/help":
        send_safe(user_id, WELCOME)
    else:
        send_safe(user_id, "دستور نامشخص. از /help برای دیدن دستورها استفاده کن.")

def forward_to_partner(msg, user_id):
    with lock:
        partner = active.get(user_id)
    if not partner:
        send_safe(user_id, "❗ فعلاً با کسی در چت نیستید. برای پیوستن /start یا برای وصل به صاحب /owner را بزنید.")
        return
    try:
        # سعی می‌کنیم پیام را فوروارد کنیم (این روش متن و اکثر مدیا را حفظ می‌کند)
        bot.forwardMessage(partner, user_id, msg['message_id'])
    except Exception as e:
        print("forward error:", e)
        send_safe(user_id, "ارسال پیام با خطا مواجه شد. اگر مشکل ادامه داشت /next را بزن.")

def on_chat_message(msg):
    content_type = telepot.flavor(msg)
    user_id = msg['chat']['id']
    text = msg.get('text', '')

    # ابتدا اگر پیام یک دستور (شروع با /) است هندل کن
    if text and text.startswith('/'):
        handle_command(msg, user_id, text)
        return

    # اگر پیام از گروه یا کانال است نادیده بگیر
    if msg['chat']['type'] != 'private':
        return

    # اگر پیام معمولیه، به پارنتر منتقل کن
    forward_to_partner(msg, user_id)

def main():
    print("Starting anon chat bot with owner support...")
    MessageLoop(bot, on_chat_message).run_as_thread()
    print("Bot listening...")
    # حلقه نگهدارنده
    try:
        while True:
            time.sleep(10)
            # می‌تونیم اینجا عملیات دوره‌ای مثل پاکسازی کاربران غیرفعال اضافه کنیم
    except KeyboardInterrupt:
        print("Bot stopped by user")

if __name__ == "__main__":
    main()
