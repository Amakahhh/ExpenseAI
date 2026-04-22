import pandas as pd

def clean_transactions(df):

    if df is None or df.empty:
        raise ValueError("No transactions extracted from file")

    df.columns = [c.lower() for c in df.columns]

    if "description" not in df:
        df["description"] = "UNKNOWN"

    if "amount" not in df:
        df["amount"] = 0

    df["description"] = df["description"].astype(str).str.upper()

    return df