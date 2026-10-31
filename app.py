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

load_dotenv()  # reads variables from .env in the project folder

MODEL = os.getenv("GEMMA_MODEL", "gemma-4-26b-a4b-it")  # or gemma-4-31b-it
COLUMNS = ["date", "item", "quantity", "unit_price", "total", "customer", "status"]

EXTRACT_PROMPT = """You are reading a photo of a handwritten sales notebook from a small shop in Rwanda.
Entries may mix English, French and Kinyarwanda, and use abbreviations.
Extract every sale or credit entry you can read.

Return ONLY a JSON array, no explanation, no markdown. Each element:
{"date": "YYYY-MM-DD or null", "item": "string", "quantity": number or null,
 "unit_price": number or null, "total": number or null,
 "customer": "name or null", "status": "paid" or "credit"}

Rules:
- Amounts are in Rwandan Francs (RWF). Write numbers without separators.
- If total is missing but quantity and unit_price exist, compute it.
- Mark "credit" when the entry shows debt (e.g. "ideni", "credit", "dette", "anadaiwa", a name with "owes").
- If a value is unreadable, use null. Do not invent entries.
"""

st.set_page_config(page_title="Daftari", page_icon="📒", layout="wide")


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


def extract_entries(image_bytes: bytes, mime_type: str) -> pd.DataFrame:
    client = get_client()
    response = client.models.generate_content(
        model=MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            EXTRACT_PROMPT,
        ],
    )
    rows = parse_json_array(response.text)
    df = pd.DataFrame(rows).reindex(columns=COLUMNS)
    for col in ["quantity", "unit_price", "total"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    missing = df["total"].isna() & df["quantity"].notna() & df["unit_price"].notna()
    df.loc[missing, "total"] = df.loc[missing, "quantity"] * df.loc[missing, "unit_price"]
    df["status"] = df["status"].fillna("paid").str.lower()
    return df


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


# ---------- UI ----------
if "records" not in st.session_state:
    st.session_state.records = pd.DataFrame(columns=COLUMNS)

st.title("📒 Daftari")
st.caption(f"Your paper notebook, now digital. Powered by Gemma 4 (`{MODEL}`) via the Gemini API.")

tab_scan, tab_dash, tab_ask = st.tabs(["1. Scan a page", "2. My business", "3. Ask Daftari"])

with tab_scan:
    left, right = st.columns([1, 1.4])
    with left:
        upload = st.file_uploader("Photo of a notebook page", type=["jpg", "jpeg", "png", "webp"])
        camera = st.camera_input("Or take a photo")
        source = camera or upload
        if source:
            st.image(source, use_container_width=True)
    with right:
        if source and st.button("Read this page", type="primary"):
            with st.spinner("Gemma is reading the handwriting..."):
                try:
                    st.session_state.draft = extract_entries(source.getvalue(), source.type)
                except Exception as e:
                    st.error(f"Could not read the page: {e}")
        if "draft" in st.session_state:
            st.subheader("Check and correct before saving")
            edited = st.data_editor(
                st.session_state.draft,
                num_rows="dynamic",
                use_container_width=True,
                column_config={
                    "status": st.column_config.SelectboxColumn(options=["paid", "credit"]),
                },
            )
            if st.button("Save to my records"):
                st.session_state.records = pd.concat(
                    [st.session_state.records, edited], ignore_index=True
                )
                del st.session_state.draft
                st.success(f"Saved {len(edited)} entries.")
                st.rerun()

with tab_dash:
    df = st.session_state.records
    if df.empty:
        st.info("No records yet. Scan a notebook page first.")
    else:
        paid = df[df["status"] == "paid"]["total"].sum()
        credit = df[df["status"] == "credit"]["total"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("Cash sales", f"{paid:,.0f} RWF")
        c2.metric("Unpaid credit", f"{credit:,.0f} RWF")
        c3.metric("Entries", len(df))

        st.subheader("Top items by sales")
        top = df.groupby("item")["total"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top)

        debtors = df[df["status"] == "credit"].groupby("customer", dropna=False)["total"].sum()
        if not debtors.empty:
            st.subheader("Who owes me money")
            st.dataframe(debtors.rename("amount owed (RWF)"), use_container_width=True)

        st.subheader("All records")
        st.dataframe(df, use_container_width=True)
        st.download_button(
            "Download CSV", df.to_csv(index=False), "daftari_records.csv", "text/csv"
        )

with tab_ask:
    df = st.session_state.records
    if df.empty:
        st.info("Save some records first, then ask questions about your business.")
    else:
        q = st.text_input("Ask anything", placeholder="What sold most? Who owes me money?")
        if q:
            with st.spinner("Thinking..."):
                st.write(ask_question(df, q))
