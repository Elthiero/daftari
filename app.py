"""Daftari: turn a photo of a handwritten sales notebook into digital records.

Powered by Gemma 4 (gemma-4-26b-a4b-it) through the Gemini API.
Setup: copy .env.example to .env, add your key, then run: streamlit run app.py
"""
import json
import os
import re

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))  # .env next to app.py

MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")  # or gemma-4-31b-it
COLUMNS = ["date", "item", "quantity", "unit_price", "total", "customer", "status"]
REPO_URL = "https://github.com/Elthiero/daftari"

EXTRACT_PROMPT = """You are reading a photo of a handwritten sales notebook from a small shop in Rwanda.
Entries may mix English, French and Kinyarwanda, and use abbreviations.
Extract every sale or credit entry you can read.

Return ONLY a JSON array, no explanation, no markdown. Each element:
{"date": "YYYY-MM-DD or null", "item": "string", "quantity": number or null,
 "unit_price": number or null, "total": number or null,
 "customer": "name or null", "status": "paid" or "credit"}

Rules:
- Amounts are in Rwandan Francs (RWF). Write numbers without separators. "1.5k" means 1500.
- If total is missing but quantity and unit_price exist, compute it.
- Mark "credit" when the entry shows debt (e.g. "ideni", "credit", "dette", "anadaiwa", a name with "owes"),
  including every line listed under an "IDENI" heading. Put the person's name in "customer".
- Skip lines that are crossed out.
- If a value is unreadable, use null. Do not invent entries.
"""

# Sample page used only when the user clicks "Load sample data" (clearly labelled in the UI).
SAMPLE_ROWS = [
    ["2026-10-31", "Isukari 2kg", 2, 1500, 3000, None, "paid"],
    ["2026-10-31", "Umuceri 3kg", 3, 1300, 3900, None, "paid"],
    ["2026-10-31", "Amavuta 1L", 1, 3200, 3200, None, "paid"],
    ["2026-10-31", "Savon", 2, 600, 1200, None, "paid"],
    ["2026-10-31", "Amagi", 10, 150, 1500, None, "paid"],
    ["2026-10-31", "Umugati", 2, 1000, 2000, None, "paid"],
    ["2026-10-31", "Amata", 4, 500, 2000, None, "paid"],
    ["2026-10-31", "Airtime MTN", 1, 1000, 1000, None, "paid"],
    ["2026-10-31", "Umuceri 2kg", 2, 1300, 2600, "Jean", "credit"],
    ["2026-10-31", "Amavuta 1L", 1, 3200, 3200, "Mukamana", "credit"],
]

st.set_page_config(page_title="Daftari", page_icon="📒", layout="wide")

st.markdown(
    """
<style>
.block-container {padding-top: 3.2rem; max-width: 1200px;}
.hero {
  background: linear-gradient(135deg, #0E7C66 0%, #0B4F43 100%);
  color: #fff; padding: 1.8rem 2rem; border-radius: 20px; margin-bottom: 1.4rem;
  box-shadow: 0 8px 24px rgba(14,124,102,.18);
}
.hero .title {font-size: 2.6rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1;}
.hero .tagline {font-size: 1.1rem; opacity: .92; margin-top: .4rem; max-width: 640px;}
.badge {
  display: inline-block; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28);
  padding: .25rem .75rem; border-radius: 999px; font-size: .8rem; margin: .9rem .4rem 0 0;
}
.card {
  background: #FFFFFF; border: 1px solid #E6DFD3; border-radius: 16px;
  padding: 1.1rem 1.3rem; margin-bottom: 1rem;
}
.card h4 {margin: 0 0 .3rem 0;}
.muted {color: #6F685C; font-size: .92rem;}
div[data-testid="stMetric"] {
  background: #FFFFFF; border: 1px solid #E6DFD3; border-radius: 16px;
  padding: 1rem 1.2rem; box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
div[data-testid="stMetricValue"] {font-weight: 800;}
.stButton > button, .stDownloadButton > button {border-radius: 12px; font-weight: 600; padding: .5rem 1.1rem;}
.stTabs [data-baseweb="tab"] {font-weight: 600; font-size: 1rem;}
.footer {text-align: center; color: #8A8273; font-size: .85rem; margin-top: 2.5rem;}
.footer a {color: #0E7C66;}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        st.error("GEMINI_API_KEY is missing. Copy .env.example to .env and add your key.")
        st.stop()
    return genai.Client(api_key=key)


def parse_json_array(text: str):
    """Gemma may wrap JSON in code fences or add text; pull out the array."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON array found in model output")
    return json.loads(match.group(0))


def clean_frame(df: pd.DataFrame) -> pd.DataFrame:
    df = df.reindex(columns=COLUMNS)
    for col in ["quantity", "unit_price", "total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    missing = df["total"].isna() & df["quantity"].notna() & df["unit_price"].notna()
    df.loc[missing, "total"] = df.loc[missing, "quantity"] * df.loc[missing, "unit_price"]
    df["status"] = df["status"].fillna("paid").astype(str).str.lower()
    return df


def extract_entries(image_bytes: bytes, mime_type: str) -> pd.DataFrame:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACT_PROMPT,
        ],
    )
    return clean_frame(pd.DataFrame(parse_json_array(response.text)))


def ask_question(df: pd.DataFrame, question: str) -> str:
    client = get_client()
    prompt = (
        "You are a friendly bookkeeping assistant for a small shop owner in Rwanda. "
        "Answer using ONLY the records below. Amounts are in RWF. "
        "Be short and clear. Answer in the same language as the question "
        "(English, French or Kinyarwanda).\n\n"
        f"Records (CSV):\n{df.to_csv(index=False)}\n\nQuestion: {question}"
    )
    response = client.models.generate_content(model=MODEL, contents=prompt)
    return response.text


def rwf(x) -> str:
    return f"{x:,.0f} RWF"


# ---------- State ----------
if "records" not in st.session_state:
    st.session_state.records = pd.DataFrame(columns=COLUMNS)
if "chat" not in st.session_state:
    st.session_state.chat = []

# ---------- Header ----------
st.markdown(
    f"""
<div class="hero">
  <div class="title">📒 Daftari</div>
  <div class="tagline">Keep your paper notebook. Take one photo a day.
  Daftari turns your handwriting into clean records, totals and answers.</div>
  <span class="badge">🧠 Gemma 4 · {MODEL}</span>
  <span class="badge">🔓 Open weights · MIT licensed</span>
  <span class="badge">🇷🇼 Kinyarwanda · Français · English</span>
</div>
""",
    unsafe_allow_html=True,
)

tab_scan, tab_dash, tab_ask = st.tabs(["📷  Scan a page", "📊  My business", "💬  Ask Daftari"])

# ---------- Tab 1: Scan ----------
with tab_scan:
    left, right = st.columns([1, 1.35], gap="large")

    with left:
        st.markdown(
            '<div class="card"><h4>1 · Your notebook page</h4>'
            '<div class="muted">Upload a photo, or use your phone camera.</div></div>',
            unsafe_allow_html=True,
        )
        use_camera = st.toggle("Use camera", value=False)
        source = (
            st.camera_input("Take a photo", label_visibility="collapsed")
            if use_camera
            else st.file_uploader(
                "Photo of a notebook page",
                type=["jpg", "jpeg", "png", "webp"],
                label_visibility="collapsed",
            )
        )
        if source:
            st.image(source, width="stretch")
            if st.button("✨ Read this page", type="primary", width="stretch"):
                with st.spinner("Gemma is reading the handwriting..."):
                    try:
                        st.session_state.draft = extract_entries(source.getvalue(), source.type)
                    except Exception as e:
                        st.error(f"Could not read the page: {e}")

    with right:
        st.markdown(
            '<div class="card"><h4>2 · Check and save</h4>'
            '<div class="muted">The AI does the heavy lifting. You stay in control: '
            "fix any cell before saving.</div></div>",
            unsafe_allow_html=True,
        )
        if "draft" in st.session_state:
            draft = st.session_state.draft
            m1, m2, m3 = st.columns(3)
            m1.metric("Lines read", len(draft))
            m2.metric("Cash", rwf(draft.loc[draft["status"] == "paid", "total"].sum()))
            m3.metric("Credit", rwf(draft.loc[draft["status"] == "credit", "total"].sum()))
            edited = st.data_editor(
                draft,
                num_rows="dynamic",
                width="stretch",
                hide_index=True,
                column_config={
                    "date": st.column_config.TextColumn("Date"),
                    "item": st.column_config.TextColumn("Item"),
                    "quantity": st.column_config.NumberColumn("Qty"),
                    "unit_price": st.column_config.NumberColumn("Unit price", format="%d"),
                    "total": st.column_config.NumberColumn("Total (RWF)", format="%d"),
                    "customer": st.column_config.TextColumn("Customer"),
                    "status": st.column_config.SelectboxColumn("Status", options=["paid", "credit"]),
                },
            )
            if st.button("💾 Save to my records", type="primary", width="stretch"):
                st.session_state.records = pd.concat(
                    [st.session_state.records, clean_frame(edited)], ignore_index=True
                )
                del st.session_state.draft
                st.toast(f"Saved {len(edited)} entries", icon="✅")
                st.rerun()
        else:
            st.info("Your digital page will appear here after Gemma reads the photo.")

# ---------- Tab 2: Dashboard ----------
with tab_dash:
    df = st.session_state.records
    if df.empty:
        st.info("No records yet. Scan a notebook page first.")
        if st.button("Load sample data (for exploring the dashboard)"):
            st.session_state.records = clean_frame(pd.DataFrame(SAMPLE_ROWS, columns=COLUMNS))
            st.rerun()
    else:
        paid = df.loc[df["status"] == "paid", "total"].sum()
        credit = df.loc[df["status"] == "credit", "total"].sum()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💵 Cash sales", rwf(paid))
        c2.metric("📝 Unpaid credit", rwf(credit))
        c3.metric("🧾 Entries", len(df))
        c4.metric("📈 Total business", rwf(paid + credit))

        g1, g2 = st.columns([1.5, 1], gap="large")
        with g1:
            st.markdown("#### Top items by sales")
            top = df.groupby("item")["total"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top, color="#0E7C66", horizontal=True)
        with g2:
            st.markdown("#### Who owes me money")
            debtors = (
                df[df["status"] == "credit"]
                .assign(customer=lambda d: d["customer"].fillna("Unknown"))
                .groupby("customer")["total"].sum()
                .sort_values(ascending=False)
                .reset_index()
                .rename(columns={"customer": "Customer", "total": "Owes (RWF)"})
            )
            if debtors.empty:
                st.success("Nobody owes you money. 🎉")
            else:
                st.dataframe(debtors, hide_index=True, width="stretch")

        with st.expander("All records"):
            st.dataframe(df, hide_index=True, width="stretch")
        b1, b2 = st.columns([1, 4])
        b1.download_button(
            "⬇️ Download CSV", df.to_csv(index=False), "daftari_records.csv", "text/csv"
        )
        if b2.button("Clear all records"):
            st.session_state.records = pd.DataFrame(columns=COLUMNS)
            st.session_state.chat = []
            st.rerun()

# ---------- Tab 3: Ask ----------
with tab_ask:
    df = st.session_state.records
    if df.empty:
        st.info("Save some records first, then ask questions about your business.")
    else:
        st.markdown(
            '<div class="muted">Try: “Who owes me money?” · “What sold most today?” · '
            "“Combien j'ai vendu aujourd'hui ?”</div>",
            unsafe_allow_html=True,
        )
        for role, msg in st.session_state.chat:
            with st.chat_message(role, avatar="🧑🏾" if role == "user" else "📒"):
                st.write(msg)
        q = st.chat_input("Ask about your business in English, Français or Kinyarwanda")
        if q:
            st.session_state.chat.append(("user", q))
            with st.spinner("Thinking..."):
                try:
                    answer = ask_question(df, q)
                except Exception as e:
                    answer = f"Sorry, I could not answer right now: {e}"
            st.session_state.chat.append(("assistant", answer))
            st.rerun()

st.markdown(
    f'<div class="footer">Built at Hacktoberfest Hack Day Kigali 2026 · Powered by Gemma 4 via the Gemini API · '
    f'<a href="{REPO_URL}" target="_blank">Open source on GitHub</a></div>',
    unsafe_allow_html=True,
)
