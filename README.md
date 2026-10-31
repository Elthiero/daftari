# 📒 Daftari

Turn the paper notebook every small shop already uses into digital records and business insights, from a single phone photo.

Built at Hacktoberfest Hack Day Kigali 2026 (Build54 Africa, ALX Rwanda, GDG Rwanda, MLH).

## The problem

Most small businesses in Rwanda record sales and debts in a handwritten notebook. Those records are hard to total, easy to lose, and impossible to analyse, so owners rarely know their real revenue or who owes them money, and they cannot prove their income to a SACCO or microfinance lender. Accounting apps exist, but typing every sale is too slow and the notebook habit is hard to change.

## The solution

Owners keep writing in their notebook. At the end of the day they take one photo. Daftari:

1. Reads the handwriting (English, French and Kinyarwanda, with local abbreviations)
2. Turns it into a structured table: date, item, quantity, unit price, total, customer, paid or credit
3. Lets the owner correct any cell before saving
4. Shows cash sales, unpaid credit, top items and who owes money
5. Answers plain-language questions in the owner's language
6. Exports records as CSV

## AI model

**Gemma 4, `gemma-4-26b-a4b-it`**, an open-weight model from Google, accessed through the Gemini API.

Gemma is used in two places in `app.py`:
- `extract_entries()`: multimodal call, notebook image in, structured JSON out
- `ask_question()`: answers questions grounded in the saved records

Because Gemma is open weight, Daftari can later run fully offline on a local device, which matters for shops with unreliable internet.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env    # then put your Gemini API key in .env
streamlit run app.py
```

## Roadmap

- WhatsApp version: send a photo, get the summary back
- Voice answers in Kinyarwanda
- Monthly income reports shareable with SACCOs and microfinance lenders
- Offline mode running Gemma locally
- Fine-tuning on a localized dataset of Rwandan shop notebook vocabulary

## License

MIT
