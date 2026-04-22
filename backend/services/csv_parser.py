import pandas as pd

def parse_csv(file):
    df = pd.read_csv(file)

    # Standardize column names
    df.columns = [col.lower() for col in df.columns]

    # Try to map common bank formats
    if "description" not in df.columns:
        if "name" in df.columns:
            df["description"] = df["name"]
        elif "narration" in df.columns:
            df["description"] = df["narration"]

    if "type" not in df.columns:
        # Infer debit/credit from amount
        df["type"] = df["amount"].apply(lambda x: "debit" if x < 0 else "credit")

    df["amount"] = df["amount"].abs()

    return df[["date", "description", "amount", "type"]]