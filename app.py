import streamlit as st
import pandas as pd
import json
import time
import io
import re
import openpyxl
import asyncio
import aiohttp
import threading
import base64
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from datetime import datetime

# ══════════════════════════════════════════════════════════════
#  معالج أوصاف العطور - خلفية حقيقية | تنزيل في أي وقت
#  بدون SKU | بدون ذكر مدة الثبات
# ══════════════════════════════════════════════════════════════

st.set_page_config(page_title="معالج العطور | خلفية", page_icon="⚡", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap');
*{font-family:'Tajawal',sans-serif}
[data-testid="stAppViewContainer"]{direction:rtl;text-align:right}
[data-testid="stSidebar"]{direction:rtl;text-align:right}
.dash-card{background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:18px;text-align:center}
.dash-title{font-size:14px;color:#64748b;margin-bottom:4px}
.dash-value{font-size:28px;font-weight:bold;color:#d4af37}
.log-box{background:#1e293b;color:#10b981;padding:15px;border-radius:8px;font-family:monospace;font-size:13px;direction:ltr;text-align:left;height:180px;overflow-y:auto;white-space:pre-wrap}
.dl-btn{display:block;text-align:center;padding:16px;border-radius:12px;text-decoration:none;font-size:20px;font-weight:bold;margin:8px 0}
.status-running{background:#dcfce7;border:1px solid #86efac;padding:10px 16px;border-radius:8px;color:#166534;font-weight:bold;margin:10px 0}
.status-done{background:#eff6ff;border:1px solid #93c5fd;padding:10px 16px;border-radius:8px;color:#1e3a8a;font-weight:bold;margin:10px 0}
.status-stopped{background:#fef2f2;border:1px solid #fca5a5;padding:10px 16px;border-radius:8px;color:#991b1b;font-weight:bold;margin:10px 0}
</style>
""", unsafe_allow_html=True)

API_URL_OPENROUTER = "https://openrouter.ai/api/v1/chat/completions"

# ══════════════ حالة مشتركة بين التحديثات ══════════════
if "job" not in st.session_state:
    st.session_state.job = {
        "running": False, "completed": 0, "success": 0, "failed": 0,
        "total": 0, "log": [], "wb_bytes": None, "save_time": None,
        "done": False, "stopped": False, "stop_flag": False,
        "start_time": None,
    }
job = st.session_state.job

# ══════════════ دوال ══════════════

def is_empty(val):
    if pd.isna(val):
        return True
    return str(val).strip() in ("", "nan", "<p></p>", "<p><br></p>", "None", "<p> </p>")

def build_html(name, d, store_name, store_link):
    a_tag = (f'<a href="{store_link}" style="color:#d4af37;font-weight:bold;text-decoration:none;">{store_name}</a>'
             if store_link else f'<strong style="color:#d4af37;">{store_name}</strong>')
    m = re.search(r"(\d+)\s*مل", name)
    size = m.group(0) if m else "حسب الاختيار"
    h2 = "background:#f9f9f9;border-right:4px solid #d4af37;padding:8px 12px;font-size:18px;color:#333;margin:20px 0 10px;border-radius:3px;"
    h3 = "font-size:16px;color:#d4af37;border-bottom:1px solid #eee;padding-bottom:5px;margin:15px 0 10px;display:inline-block;"
    ul = "padding-right:20px;margin-bottom:15px;font-size:15px;"
    html = (
        f'<div style="font-family:\'Tajawal\',sans-serif;color:#333;line-height:1.8;text-align:right;direction:rtl;">'
        f'<p style="margin-bottom:15px;">{d.get("intro_paragraph","")} يقدم لك {a_tag} هذا العطر الفاخر.</p>'
        f'<h2 style="{h2}">تفاصيل المنتج</h2>'
        f'<ul style="{ul}">'
        f'<li><strong>الاسم:</strong> {d.get("perfume_ar", name)} ({d.get("perfume_en","")})</li>'
        f'<li><strong>السعة:</strong> {size}</li>'
        f'<li><strong>التركيز:</strong> {d.get("concentration","")}</li>'
        f'<li><strong>العائلة العطرية:</strong> {d.get("family","")}</li>'
        f'<li><strong>متوفر عبر:</strong> {a_tag}</li>'
        f'</ul>'
        f'<h3 style="{h3}">رحلة العطر</h3>'
        f'<ul style="{ul}">'
        f'<li><strong>الافتتاحية:</strong> {d.get("top_notes","")}</li>'
        f'<li><strong>القلب:</strong> {d.get("heart_notes","")}</li>'
        f'<li><strong>القاعدة:</strong> {d.get("base_notes","")}</li>'
        f'<li><strong>الطابع العام:</strong> {d.get("general_vibe","")}</li>'
        f'</ul>'
        f'<h3 style="{h3}">لماذا هذا العطر؟</h3>'
        f'<ul style="{ul}">'
        f'<li><strong>التميز:</strong> {d.get("why_choose_1","")}</li>'
        f'<li><strong>الجودة:</strong> {d.get("why_choose_2","")}</li>'
        f'</ul>'
        f'<h3 style="{h3}">الأسئلة الشائعة</h3>'
        f'<ul style="{ul}">'
        f'<li><strong>{d.get("faq_1_q","هل يناسب الاستخدام اليومي؟")}</strong><br>{d.get("faq_1_a","")}</li>'
        f'<li><strong>{d.get("faq_2_q","هل يناسب الرجال والنساء؟")}</strong><br>{d.get("faq_2_a","")}</li>'
        f'</ul>'
        f'<p>{d.get("closing_paragraph","")} اختر {a_tag}.</p>'
        f'</div>'
    )
    return re.sub(r'\s{2,}', ' ', html)


@retry(wait=wait_exponential(multiplier=1, min=5, max=20), stop=stop_after_attempt(4),
       retry=retry_if_exception_type(Exception))
async def fetch_ai(session, name, api_key, model, store_name, semaphore):
    system_msg = (
        'أنت خبير تسويق عطور. أعد وصفاً تسويقياً (أكثر من 2000 حرف) كـ JSON فقط:\n'
        '{"perfume_en":"","perfume_ar":"","concentration":"","family":"",'
        '"intro_paragraph":"","top_notes":"","heart_notes":"","base_notes":"",'
        '"general_vibe":"","why_choose_1":"","why_choose_2":"",'
        '"faq_1_q":"","faq_1_a":"","faq_2_q":"","faq_2_a":"","closing_paragraph":""}'
    )
    user_msg = (
        f'وصف لـ: "{name}" في متجر "{store_name}".\n'
        f'مهم: لا تذكر رقم SKU أو الرمز التعريفي، ولا تذكر مدة الثبات أو الساعات.'
    )
    async with semaphore:
        if api_key.startswith("AIza"):
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            body = {"contents":[{"role":"user","parts":[{"text":system_msg+"\n\n"+user_msg}]}],"generationConfig":{"temperature":0.4}}
            async with session.post(url, headers={"Content-Type":"application/json"}, json=body) as res:
                if res.status == 429: await asyncio.sleep(15); raise Exception("Rate limit")
                if res.status != 200: raise Exception(f"Gemini {res.status}")
                data = await res.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            headers = {"Authorization":f"Bearer {api_key}","Content-Type":"application/json"}
            body = {"model":model,"messages":[{"role":"system","content":system_msg},{"role":"user","content":user_msg}]}
            async with session.post(API_URL_OPENROUTER, headers=headers, json=body) as res:
                if res.status == 429: await asyncio.sleep(15); raise Exception("Rate limit")
                if res.status != 200: raise Exception(f"OpenRouter {res.status}")
                data = await res.json()
                text = data["choices"][0]["message"]["content"]
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            parsed = json.loads(m.group(0))
            if isinstance(parsed, dict): return parsed
        raise ValueError("No JSON")


async def async_worker(tasks, keys, model, store_name, store_link, limit, job, wb, ws, desc_col, save_interval):
    semaphore = asyncio.Semaphore(limit)
    last_save = 0

    async def do_one(idx, row_i, pname):
        key = keys[idx % len(keys)]
        try:
            data = await fetch_ai(session, pname, key, model, store_name, semaphore)
            if data:
                ws.cell(row=row_i + 3, column=desc_col).value = build_html(pname, data, store_name, store_link)
                return True
        except Exception:
            pass
        return False

    async with aiohttp.ClientSession() as session:
        coros = [do_one(i, r, p) for i,(r,p) in enumerate(tasks)]
        for future in asyncio.as_completed(coros):
            if job["stop_flag"]:
                job["stopped"] = True
                break
            ok = await future
            job["completed"] += 1
            if ok: job["success"] += 1
            else: job["failed"] += 1

            elapsed = time.time() - job["start_time"]
            avg = elapsed / job["completed"]
            eta = int(avg * (job["total"] - job["completed"]))
            h,m_,s = eta//3600, (eta%3600)//60, eta%60
            eta_str = f"{h:02d}:{m_:02d}:{s:02d}" if h else f"{m_:02d}:{s:02d}"
            icon = "✅" if ok else "❌"
            current_name = tasks[job["completed"]-1][1][:42] if job["completed"] <= len(tasks) else ""
            job["log"].insert(0, f"[{job['completed']:>4}/{job['total']}] {icon} {current_name} | ⏱{eta_str}")
            if len(job["log"]) > 60: job["log"].pop()

            if job["completed"] - last_save >= save_interval:
                buf = io.BytesIO(); wb.save(buf)
                job["wb_bytes"] = buf.getvalue()
                job["save_time"] = datetime.now().strftime("%H:%M:%S")
                last_save = job["completed"]

    # حفظ نهائي
    buf = io.BytesIO(); wb.save(buf)
    job["wb_bytes"] = buf.getvalue()
    job["save_time"] = datetime.now().strftime("%H:%M:%S")
    job["running"] = False
    job["done"] = not job.get("stopped", False)


def run_thread(tasks, keys, model, store_name, store_link, limit, job, wb, ws, desc_col, save_interval):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_worker(tasks, keys, model, store_name, store_link, limit, job, wb, ws, desc_col, save_interval))
    finally:
        loop.close()


def dl_link(b64, fname, label, color):
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{fname}" class="dl-btn" style="background:{color};color:white;">{label}</a>'


# ══════════════ الشريط الجانبي ══════════════
with st.sidebar:
    st.markdown("### 🔑 مفاتيح API")
    keys_input = st.text_area("كل مفتاح في سطر:", height=120, placeholder="AIza...")
    active_keys = [k.strip() for k in keys_input.split('\n') if k.strip()]
    st.markdown("---")
    model_name = st.selectbox("النموذج", ["google/gemini-2.0-flash-001","google/gemini-flash-1.5","openai/gpt-4o-mini"])
    concurrency = st.slider("طلبات متزامنة:", 3, 25, 10)
    save_every = st.slider("حفظ تلقائي كل (منتج):", 30, 300, 100)
    store_name = st.text_input("اسم المتجر", "متجر ماركات عالمية اصلية")
    store_link = st.text_input("رابط المتجر", "https://legabreil.com/ar")
    mode = st.radio("المنتجات:", ["📋 الكل (3200+)", "⚡ الفارغة فقط"])

# ══════════════ العنوان ══════════════
st.title("⚡ معالج الأوصاف | خلفية حقيقية")

# ══════════════ زر تنزيل دائم في الأعلى ══════════════
if job["wb_bytes"]:
    b64 = base64.b64encode(job["wb_bytes"]).decode()
    saved = job["completed"]
    total = job["total"]
    color = "#10b981" if job["done"] else "#3b82f6"
    label = "📥 تنزيل الملف الكامل ✅" if job["done"] else f"💾 تنزيل الحالي ({saved:,} / {total:,} منتج)"
    st.markdown(dl_link(b64, f"Salla_{saved}.xlsx", label, color), unsafe_allow_html=True)
    st.caption(f"📌 آخر حفظ: {job['save_time']}")
    st.markdown("---")

# ══════════════ رفع الملف ══════════════
if not job["running"]:
    uploaded = st.file_uploader("ارفع ملف المنتجات (Excel)", type=["xlsx"])
    if uploaded:
        raw = uploaded.getvalue()
        df_p = pd.read_excel(io.BytesIO(raw), header=1)
        try:
            desc_col_idx = list(df_p.columns).index("الوصف") + 1
            all_t = [(i, str(r["أسم المنتج"]).strip()) for i,r in df_p.iterrows() if str(r["أسم المنتج"]).strip() not in ("nan","","None")]
            empty_t = [t for t in all_t if is_empty(df_p.iloc[t[0]]["الوصف"])]
            tasks_run = all_t if "الكل" in mode else empty_t

            c1,c2,c3 = st.columns(3)
            c1.markdown(f"<div class='dash-card'><div class='dash-title'>إجمالي</div><div class='dash-value'>{len(all_t):,}</div></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='dash-card'><div class='dash-title'>لها وصف</div><div class='dash-value' style='color:#10b981'>{len(all_t)-len(empty_t):,}</div></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='dash-card'><div class='dash-title'>ستُعالج</div><div class='dash-value'>{len(tasks_run):,}</div></div>", unsafe_allow_html=True)

            est = round((len(tasks_run)/max(concurrency,1))*1.5/60, 1)
            st.info(f"⏱️ الوقت المقدر ~{est} دقيقة | حفظ تلقائي كل {save_every} منتج")

            if st.button("🚀 بدء في الخلفية", type="primary", use_container_width=True):
                if not active_keys:
                    st.error("❌ أدخل مفتاح API")
                elif not tasks_run:
                    st.warning("✅ لا يوجد منتجات تحتاج معالجة")
                else:
                    wb_w = openpyxl.load_workbook(io.BytesIO(raw))
                    ws_w = wb_w.active
                    job.update({"running":True,"done":False,"stopped":False,"stop_flag":False,
                                "completed":0,"success":0,"failed":0,"total":len(tasks_run),
                                "log":[],"wb_bytes":None,"save_time":None,"start_time":time.time()})
                    threading.Thread(
                        target=run_thread,
                        args=(tasks_run, active_keys, model_name, store_name, store_link,
                              concurrency, job, wb_w, ws_w, desc_col_idx, save_every),
                        daemon=True
                    ).start()
                    st.rerun()
        except ValueError:
            st.error("❌ تأكد وجود عمود 'الوصف' و 'أسم المنتج'")

# ══════════════ لوحة المراقبة ══════════════
if job["running"] or job["done"] or job["stopped"]:
    if job["running"]:
        st.markdown("<div class='status-running'>⚙️ يعمل في الخلفية — يمكنك مغادرة الصفحة والعودة لاحقاً</div>", unsafe_allow_html=True)
    elif job["done"]:
        st.markdown("<div class='status-done'>🎉 اكتملت المعالجة! الملف جاهز للتنزيل</div>", unsafe_allow_html=True)
    elif job["stopped"]:
        st.markdown("<div class='status-stopped'>⛔ تم الإيقاف — الملف المحفوظ جاهز</div>", unsafe_allow_html=True)

    pct = int(job["completed"] / job["total"] * 100) if job["total"] > 0 else 0
    st.progress(min(pct/100, 1.0))

    c1,c2,c3,c4 = st.columns(4)
    c1.markdown(f"<div class='dash-card'><div class='dash-title'>المنجز</div><div class='dash-value'>{job['completed']:,}/{job['total']:,}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='dash-card'><div class='dash-title'>نجاح ✅</div><div class='dash-value' style='color:#10b981'>{job['success']:,}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='dash-card'><div class='dash-title'>فشل ❌</div><div class='dash-value' style='color:#ef4444'>{job['failed']:,}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='dash-card'><div class='dash-title'>الإنجاز</div><div class='dash-value'>{pct}%</div></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    log_html = "\n".join(job["log"][:25]) if job["log"] else "⏳ في انتظار أول نتيجة..."
    st.markdown(f"<div class='log-box'>{log_html}</div>", unsafe_allow_html=True)

    # ── أزرار التحكم والتنزيل ──
    st.markdown("<br>", unsafe_allow_html=True)
    col_dl, col_stop, col_ref = st.columns([3, 2, 1])

    with col_dl:
        if job["wb_bytes"]:
            b64 = base64.b64encode(job["wb_bytes"]).decode()
            color = "#10b981" if job["done"] else "#3b82f6"
            label = "📥 تنزيل الملف الكامل" if job["done"] else f"💾 تنزيل الآن ({job['completed']:,} منتج)"
            st.markdown(dl_link(b64, f"Salla_{job['completed']}.xlsx", label, color), unsafe_allow_html=True)
        else:
            st.info("💾 زر التنزيل سيظهر بعد أول حفظ تلقائي")

    with col_stop:
        if job["running"]:
            if st.button("⛔ إيقاف وتنزيل", use_container_width=True, type="secondary"):
                job["stop_flag"] = True
                st.warning("⏳ جارٍ الإيقاف...")
                time.sleep(3)
                st.rerun()

    with col_ref:
        if st.button("🔄", use_container_width=True, help="تحديث"):
            st.rerun()

    # تحديث تلقائي كل 5 ثواني
    if job["running"]:
        time.sleep(5)
        st.rerun()
