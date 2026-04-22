import pdfplumber
import pandas as pd


def parse_pdf(file):

    transactions = []

    with pdfplumber.open(file) as pdf:

        for page in pdf.pages:
            text = page.extract_text()

            # ❗ SAFETY CHECK
            if not text:
                continue

            lines = text.split("\n")

            for line in lines:
                line = line.strip()

                # ❗ SUPER SIMPLE EXTRACTION (NO COMPLEX REGEX)
                parts = line.split()

                if len(parts) < 3:
                    continue

                # Try last item as amount
                try:
                    amount = float(parts[-1].replace(",", ""))

                    description = " ".join(parts[:-2])
                    date = parts[0]

                    transactions.append({
                        "date": date,
                        "description": description,
                        "amount": amount
                    })

                except:
                    continue

    # ❗ NEVER FAIL — ALWAYS RETURN DATAFRAME
    return pd.DataFrame(transactions)