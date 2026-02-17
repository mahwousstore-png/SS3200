import streamlit as st
import pandas as pd
import json
import io
import time
from openai import OpenAI
from description_generator import generate_description, generate_batch_descriptions
from utils import parse_excel, export_to_excel

# ──────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────
st.set_page_config(
    page_title="مولّد وصوف المنتجات | لي غابريال",
    page_icon="🌹",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────
# Custom CSS (RTL + Gold Theme)
# ──────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@300;400;500;700&display=swap');

  * { font-family: 'Tajawal', sans-serif !important; direction: rtl; }
  .main { background: #fafafa; }
  h1, h2, h3 { color: #1a1a1a !important; }

  .gold-badge {
    display: inline-block;
    background: linear-gradient(135deg, #d4af37, #a8880d);
    color: white;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .product-card {
    background: white;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }

  .stButton > button {
    background: linear-gradient(135deg, #d4af37, #a8880d) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    padding: 10px 24px !important;
    font-size: 1rem !important;
  }

  .stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(212,175,55,0.4) !important;
  }

  .metric-box {
    background: white;
    border-radius: 10px;
    padding: 16px;
    text-align: center;
    border: 1px solid #f0e8c8;
    box-shadow: 0 2px 6px rgba(212,175,55,0.1);
  }

  .stTextArea textarea, .stTextInput input {
    border: 1.5px solid #e0d0a0 !important;
    border-radius: 8px !important;
    direction: rtl !important;
  }

  .stSelectbox > div > div {
    border: 1.5px solid #e0d0a0 !important;
    border-radius: 8px !important;
  }

  .sidebar .sidebar-content { background: #fffbf0; }

  div[data-testid="stExpander"] {
    border: 1px solid #f0e8c8 !important;
    border-radius: 10px !important;
  }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────
# Sidebar — Settings
# ──────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="gold-badge">⚙️ الإعدادات</div>', unsafe_allow_html=True)
    st.markdown("## 🌹 لي غابريال")
    st.markdown("مولّد وصوف المنتجات بالذكاء الاصطناعي")
    st.divider()

    api_key = st.text_input(
        "🔑 OpenRouter API Key",
        type="password",
        help="أدخل مفتاح OpenRouter API الخاص بك",
        value=st.session_state.get("api_key", ""),
    )
    if api_key:
        st.session_state["api_key"] = api_key

    model_choice = st.selectbox(
        "🤖 النموذج",
        [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "google/gemini-pro-1.5",
        ],
        index=0,
        help="اختر النموذج المناسب لتوليد الوصوف",
    )
    st.session_state["model"] = model_choice

    st.divider()
    st.markdown("### 📋 نمط الوصف")
    tone = st.selectbox("نبرة الكتابة", ["فاخر وراقي", "عصري وجذاب", "بسيط ومباشر"])
    include_faq = st.checkbox("تضمين الأسئلة الشائعة", value=True)
    include_notes = st.checkbox("تضمين نوتات العطر", value=True)
    st.session_state["tone"] = tone
    st.session_state["include_faq"] = include_faq
    st.session_state["include_notes"] = include_notes

    st.divider()
    st.caption("💡 يستخدم نفس تنسيق وصوف لي غابريال الأصلية")

# ──────────────────────────────────────────
# Header
# ──────────────────────────────────────────
col_logo, col_title = st.columns([1, 5])
with col_logo:
    st.markdown("## 🌹")
with col_title:
    st.markdown("# مولّد وصوف منتجات لي غابريال")
    st.caption("توليد وصوف احترافية بالذكاء الاصطناعي بنفس أسلوب لي غابريال")

st.divider()

# ──────────────────────────────────────────
# Tabs
# ──────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["✍️ منتج واحد", "📦 معالجة جماعية (Excel)", "📖 تعليمات الاستخدام"])

# ══════════════════════════════════════════
# TAB 1: Single Product
# ══════════════════════════════════════════
with tab1:
    st.markdown("### إنشاء وصف لمنتج واحد")

    col1, col2 = st.columns(2)

    with col1:
        product_name = st.text_input("🏷️ اسم المنتج *", placeholder="مثال: عطر مين نيويورك استار دست 75مل")
        brand = st.text_input("🏢 الماركة", placeholder="مثال: لي غابريال")
        category = st.text_input("📂 التصنيف", placeholder="مثال: العطور > عطور رجالية")
        sku = st.text_input("🔢 رمز المنتج (SKU)", placeholder="مثال: 1453582986")

    with col2:
        volume = st.text_input("📏 الحجم/الكمية", placeholder="مثال: 75 مل")
        product_type = st.selectbox("🏷️ نوع العطر", ["رجالي", "نسائي", "للجنسين", "عود", "نيش", "أخرى"])
        extra_info = st.text_area(
            "📝 معلومات إضافية (اختياري)",
            placeholder="مثال: نوتات العطر، مزايا خاصة، مناسبة الاستخدام...",
            height=100,
        )

    # Sample template button
    if st.button("📋 استخدام مثال جاهز"):
        st.session_state["sample_loaded"] = True

    if st.session_state.get("sample_loaded"):
        product_name = "تستر عطر مين نيويورك استار دست 75مل"
        brand = "لي غابريال"
        category = "العطور > عطور رجالية"
        sku = "1453582986"
        volume = "75 مل"
        extra_info = "بدون كرتون، نوتات عليا: حمضيات، نوتات وسطى: زهور بيضاء، نوتات قاعدية: خشب الصندل والعنبر"

    st.divider()

    generate_btn = st.button("🚀 توليد الوصف الآن", use_container_width=True)

    if generate_btn:
        if not st.session_state.get("api_key"):
            st.error("❌ يرجى إدخال مفتاح API في الإعدادات الجانبية أولاً")
        elif not product_name:
            st.error("❌ يرجى إدخال اسم المنتج على الأقل")
        else:
            with st.spinner("🔮 جاري توليد الوصف..."):
                product_data = {
                    "name": product_name,
                    "brand": brand,
                    "category": category,
                    "sku": sku,
                    "volume": volume,
                    "product_type": product_type,
                    "extra_info": extra_info,
                }
                try:
                    result = generate_description(
                        product_data=product_data,
                        api_key=st.session_state["api_key"],
                        model=st.session_state["model"],
                        tone=st.session_state["tone"],
                        include_faq=st.session_state["include_faq"],
                        include_notes=st.session_state["include_notes"],
                    )

                    st.success("✅ تم توليد الوصف بنجاح!")

                    # Preview tabs
                    preview_tab, html_tab, raw_tab = st.tabs(["👁️ معاينة", "💻 كود HTML", "📋 نسخ النص"])

                    with preview_tab:
                        st.markdown(
                            f'<div style="background:white;padding:24px;border-radius:12px;border:1px solid #eee;">{result}</div>',
                            unsafe_allow_html=True,
                        )

                    with html_tab:
                        st.code(result, language="html")
                        st.download_button(
                            "⬇️ تحميل HTML",
                            data=result,
                            file_name=f"{product_name[:30]}_description.html",
                            mime="text/html",
                        )

                    with raw_tab:
                        st.text_area("الكود الكامل", value=result, height=400)

                except Exception as e:
                    st.error(f"❌ خطأ في التوليد: {str(e)}")

# ══════════════════════════════════════════
# TAB 2: Batch Processing
# ══════════════════════════════════════════
with tab2:
    st.markdown("### معالجة جماعية من ملف Excel")

    col_up, col_info = st.columns([2, 1])
    with col_up:
        uploaded_file = st.file_uploader(
            "📂 ارفع ملف Excel (بنفس تنسيق سلة)",
            type=["xlsx", "xls"],
            help="يجب أن يحتوي الملف على أعمدة: أسم المنتج، الماركة، التصنيف، SKU",
        )

    with col_info:
        st.markdown("""
        <div style="background:#fffbf0;border:1px solid #f0e8c8;border-radius:10px;padding:14px;font-size:0.85rem;">
        <b>📋 الأعمدة المطلوبة:</b><br>
        • أسم المنتج ✅<br>
        • الماركة<br>
        • تصنيف المنتج<br>
        • رمز المنتج sku<br>
        • الوصف (موجود سيُحدَّث)
        </div>
        """, unsafe_allow_html=True)

    if uploaded_file:
        try:
            df = parse_excel(uploaded_file)
            st.success(f"✅ تم تحميل {len(df)} منتج")

            # Preview
            with st.expander("👁️ معاينة البيانات", expanded=False):
                display_cols = ["أسم المنتج", "الماركة", "تصنيف المنتج", "رمز المنتج sku"]
                available_cols = [c for c in display_cols if c in df.columns]
                st.dataframe(df[available_cols].head(10), use_container_width=True)

            st.divider()

            col_range1, col_range2, col_delay = st.columns(3)
            with col_range1:
                start_row = st.number_input("من منتج رقم", min_value=1, max_value=len(df), value=1)
            with col_range2:
                end_row = st.number_input("إلى منتج رقم", min_value=1, max_value=len(df), value=min(5, len(df)))
            with col_delay:
                delay_sec = st.number_input("تأخير بين الطلبات (ثانية)", min_value=0.5, max_value=10.0, value=1.5, step=0.5)

            total_to_process = end_row - start_row + 1
            st.info(f"📊 سيتم معالجة **{total_to_process}** منتج")

            batch_btn = st.button("🚀 بدء المعالجة الجماعية", use_container_width=True)

            if batch_btn:
                if not st.session_state.get("api_key"):
                    st.error("❌ يرجى إدخال مفتاح API في الإعدادات الجانبية أولاً")
                else:
                    subset = df.iloc[start_row - 1 : end_row].copy()
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    results_container = st.container()

                    processed_df = generate_batch_descriptions(
                        df=subset,
                        api_key=st.session_state["api_key"],
                        model=st.session_state["model"],
                        tone=st.session_state["tone"],
                        include_faq=st.session_state["include_faq"],
                        include_notes=st.session_state["include_notes"],
                        progress_bar=progress_bar,
                        status_text=status_text,
                        delay=delay_sec,
                    )

                    # Merge back into original df
                    df.iloc[start_row - 1 : end_row] = processed_df

                    st.success(f"✅ اكتملت المعالجة! تم توليد {total_to_process} وصف")

                    # Download
                    output_buffer = export_to_excel(df)
                    st.download_button(
                        label="⬇️ تحميل ملف Excel المحدّث",
                        data=output_buffer,
                        file_name="gabriel_products_updated.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )

        except Exception as e:
            st.error(f"❌ خطأ في قراءة الملف: {str(e)}")

# ══════════════════════════════════════════
# TAB 3: Instructions
# ══════════════════════════════════════════
with tab3:
    st.markdown("""
    ## 📖 كيفية استخدام التطبيق

    ### 1️⃣ منتج واحد
    - أدخل بيانات المنتج في الحقول المطلوبة
    - اضغط **توليد الوصف الآن**
    - انسخ HTML أو حمّله مباشرة

    ### 2️⃣ معالجة جماعية (Excel)
    - ارفع ملف Excel بنفس تنسيق سلة
    - حدد نطاق المنتجات التي تريد معالجتها
    - اضغط **بدء المعالجة الجماعية**
    - حمّل الملف المحدّث مع الوصوف الجديدة

    ### 📝 أعمدة Excel المدعومة
    | العمود | الاستخدام |
    |--------|-----------|
    | أسم المنتج | **إلزامي** — اسم المنتج الكامل |
    | الماركة | اسم الماركة/الدار |
    | تصنيف المنتج | التصنيف الهرمي |
    | رمز المنتج sku | الرمز التعريفي |
    | الوصف | سيتم استبداله بالوصف الجديد |

    ### 💡 نصائح للحصول على أفضل النتائج
    - أضف معلومات النوتات في حقل "معلومات إضافية"
    - استخدم نموذج `gpt-4o` للوصوف الأكثر جودة
    - فعّل خيار "الأسئلة الشائعة" للوصوف الأكثر اكتمالاً

    ### ⚠️ ملاحظات
    - المعالجة الجماعية تستغرق وقتاً حسب عدد المنتجات
    - يُنصح بمعالجة 50 منتج كحد أقصى في كل مرة
    - يتم حفظ التقدم في ملف Excel القابل للتحميل
    """)
