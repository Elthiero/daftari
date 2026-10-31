# 📒 DukaAI

**Keep your paper notebook. Take one photo. Get your business records, totals and answers.**

DukaAI turns the handwritten sales notebook every small shop already uses into clean digital records and business insights, from a single phone photo. Powered by **Gemma 4**, an open-weight model, through the Gemini API.

🔗 **Live demo:** [daftari-zu84.onrender.com](https://daftari-zu84.onrender.com/)
*(Hosted on Render's free tier: the first load can take up to a minute while the server wakes up.)*

Built at **Hacktoberfest Hack Day Kigali 2026** (Build54 Africa, ALX Rwanda, GDG Rwanda, MLH).
Submitted to: **Best Use of Gemma 4** and **Best Open-Source AI Project**.

![DukaAI dashboard](docs/dashboard.png)

## The problem

Most small businesses in Rwanda (boutiques, market stalls, butcheries, salons) record sales and debts in a handwritten notebook. Those records are hard to total, easy to lose and impossible to analyse, so owners rarely know their real revenue or who owes them money, and they cannot prove their income to a SACCO or microfinance lender. Accounting apps exist, but typing every sale is too slow and the notebook habit is hard to change.

## The solution

DukaAI does not ask owners to change their habit. They keep writing in their notebook and take one photo a day. DukaAI:

1. **Reads the handwriting**, mixing Kinyarwanda, French and English, including local terms like *ideni* (debt) and shorthand like *1.5k*
2. **Builds a structured table**: date, item, quantity, unit price, total, customer, paid or credit
3. **Computes missing totals** and skips crossed-out lines
4. **Keeps the owner in control**: every cell can be corrected before saving
5. **Shows the business at a glance**: cash sales, unpaid credit, top items, who owes money
6. **Answers questions** in the owner's language, e.g. *"Who owes me money?"* or *"Combien j'ai vendu aujourd'hui ?"*
7. **Exports** records as CSV

![Scan screen](docs/scan.png)

## How Gemma 4 is used

Model: **`gemma-4-26b-a4b-it`** (Gemma 4, open weights) via the Gemini API, using the `google-genai` SDK.

| Function in `app.py` | What Gemma does |
|---|---|
| `extract_entries()` | Multimodal: notebook photo in, structured JSON rows out |
| `ask_question()` | Answers questions grounded only in the saved records, in the user's language |
| `generate()` | Shared call with thinking off, temperature 0 and capped output for fast, consistent answers |

Because Gemma is open weight, DukaAI can later run fully offline on a local device, which matters for shops with unreliable internet, and avoids lock-in to a single provider.

## Performance

- Photos are auto-rotated and resized to 1280 px (JPEG) before sending, so uploads stay small
- Gemma's thinking mode is turned off and output is capped, which cuts response time
- Results are cached by image content, so reading the same page again is instant
- The scan screen shows read time and token counts for transparency

## Tech stack

Python · Streamlit · pandas · Pillow · Gemma 4 via Gemini API (`google-genai`) · Render

## Run it locally

```bash
git clone https://github.com/Elthiero/daftari.git
cd daftari
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then put your Gemini API key in .env
streamlit run app.py
```

Get a free API key at [Google AI Studio](https://aistudio.google.com/apikey).

### Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GEMINI_API_KEY` | Yes | | Gemini API key |
| `GEMMA_MODEL` | No | `gemma-4-26b-a4b-it` | Or `gemma-4-31b-it` |
| `MAX_IMAGE_SIDE` | No | `1280` | Max photo size in px sent to Gemma |

## Deploy on Render

1. New **Web Service** from this repo, runtime **Python 3**
2. Build command: `pip install -r requirements.txt`
3. Start command:
   ```bash
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```
4. Add `GEMINI_API_KEY` (and optionally `GEMMA_MODEL`, `PYTHON_VERSION=3.12.7`) under **Environment**

## Project structure

```
daftari/
├── app.py               # Streamlit app and Gemma calls
├── requirements.txt
├── .env.example         # copy to .env and add your key
├── .streamlit/
│   └── config.toml      # theme
├── docs/                # screenshots
└── LICENSE              # MIT
```

## Roadmap

- **WhatsApp channel**: send a photo, get the summary back
- **Voice answers in Kinyarwanda**
- **Monthly income reports** owners can share with SACCOs and microfinance lenders as proof of business activity
- **Offline mode** running Gemma locally on a phone or laptop
- **Fine-tuning** on a localized dataset of Rwandan shop vocabulary
- **Production stack**: FastAPI backend, React mobile web app, persistent database, Docker

## Team

- Potiphar Gaye Vaye
- Aime Serge Ukobizaba
- Ahourdet Donambi Thierry ([GitHub](https://github.com/Elthiero), [LinkedIn](https://linkedin.com/in/thierry-donambi))
- Ndatimana Jean de Dieu
- Apongseh Iyan

## License

[MIT](LICENSE)
