from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")


def classify_transaction(description):

    if not description:
        return "unknown"

    text = str(description).lower()

    # -----------------------------
    # SAVINGS (OPAY OWEALTH ETC)
    # -----------------------------
    if "owealth" in text:
        return "savings"

    if "savings" in text:
        return "savings"

    # -----------------------------
    # INCOME (CREDITS)
    # -----------------------------
    if any(x in text for x in ["salary", "credit", "deposit", "incoming", "received", "payment from"]):
        return "income"

    # -----------------------------
    # TRANSFER (INTERNAL MOVEMENT)
    # -----------------------------
    if "transfer" in text and "owealth" not in text:
        return "transfer"

    if "wallet transfer" in text:
        return "transfer"

    # -----------------------------
    # EXPENSE CATEGORIES
    # -----------------------------
    if any(x in text for x in ["uber", "bolt", "taxi"]):
        return "expense_transport"

    if any(x in text for x in ["shoprite", "spar", "food", "restaurant", "kfc"]):
        return "expense_food"

    if any(x in text for x in ["netflix", "cinema", "movie", "spotify"]):
        return "expense_entertainment"

    if any(x in text for x in ["phcn", "electric", "dstv", "gotv", "bill"]):
        return "expense_bills"

    # -----------------------------
    # DEFAULT EXPENSE
    # -----------------------------
    return "expense_other"