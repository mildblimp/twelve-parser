import time

import pandas as pd

# defaults
pd.options.mode.chained_assignment = None  # default='warn'
INPUTFILE = "export_ruwe_transactiegegevens.csv"
# Paymenttypes in Twelve
PIN = "Omzet PIN"
TAPPERS = "Gebruik tappers"
BESTUUR_VVTP = "Bestuur VvTP"
EVENEMENT_VVTP = "Activiteit VvTP"
EXTERN = "Externe borrel"
# Cost Units (as defined in Exact online). Used to distinguish between Wed/Fri
# revenue.
CU_WOENSDAG = "1"
CU_VRIJDAG = "2"
CU_EXTERN = "3"
# Customers (as defined in Exact online). Internal payments (such as "Gebruik
# tappers") go through KASSAINTERN, direct payments (currently only paying by
# card) go through KASSADEBITEUR, while external payments are assigned a
# placeholder EXTERN_PLACEHOLDER.
VVTP = "1"
EXTERN_PLACEHOLDER = "9997"
KASSAINTERN = "9998"
KASSADEBITEUR = "9999"
# Payment Conditions (as defined in Exact online).
DIRECT = "02"
ON_CREDITS = "30"  # 30 days
# Invoice journal number (as defined in Exact online).
JOURNAL = 50
# Specify which payment methods should be grouped per month (used to bundle
# e.g. "Gebruik tappers" per month)
BUNDLE_PAYMENTS = [TAPPERS, BESTUUR_VVTP]
# Specify which payments are internal, for the VvTP, and external
VVTP_PAYMENTS = [BESTUUR_VVTP, EVENEMENT_VVTP]
EXTERNAL_PAYMENTS = [EXTERN]
INTERNAL_PAYMENTS = [TAPPERS]
# Warnings
WARN_EXTERN = 0
WARN_BORREL_VVTP = 0

EXTERN_MSG = """
Let op: er zijn een of meerdere borrels voor een externe instantie gegeven. Het
script heeft automatisch de relatie 9997 als plaatshouder gebruikt (nodig voor
de Exact import), maar die moet je handmatig veranderen! Zorg dat je ook een
duidelijke waarde bij Uw. Ref. invult, dan is het voor de betreffende
penningmeester duidelijk om welke borrel het gaat (bijv. "Borrel Leeghwater
15-01-2021").
"""
VVTP_MSG = """
Let op: er zijn een of meerdere borrels voor de VvTP gegeven. Zorg dat je bij
Uw. Ref. een duidelijke omschrijving invult, bijvoorbeeld "Borrel SpoSpeCo
Mario Kart 2020"
"""

msg = r"""

___________              .__                __________
\__    ___/_  _  __ ____ |  |___  __ ____   \______   \_____ _______  ______ ___________
  |    |  \ \/ \/ // __ \|  |\  \/ // __ \   |     ___/\__  \\_  __ \/  ___// __ \_  __ \
  |    |   \     /\  ___/|  |_\   /\  ___/   |    |     / __ \|  | \/\___ \\  ___/|  | \/
  |____|    \/\_/  \___  >____/\_/  \___  >  |____|    (____  /__|  /____  >\___  >__|
                       \/               \/                  \/           \/     \/


Dit script haalt ruwe transactiegegevens uit Twelve en maakt daarvan een
importbestand voor facturen voor in Exact.

Zorg dat je nooit handmatig de transactiegegevens uit Twelve haalt en nooit
handmatig facturen aanmaakt!

N.B. Lees de README! (Staat op Github)
"""


def get_transactions(inputfile=INPUTFILE):
    """Read the exported file from Twelve and return a pandas DataFrame"""
    with open(inputfile, "r", encoding="utf-8") as f:
        df_transactions = pd.read_csv(f, delimiter=";")
        print(f"Reading {inputfile}...\n")
    df = df_transactions[
        [
            "Product Id",
            "Datum",
            "Betaaltype",
            "Product",
            "Aantal",
            "Prijs (per product)",
            "BTW Type",
            "Aantal * prijs",
        ]
    ]
    # group transactions by day
    df["Datum"] = pd.to_datetime(df["Datum"], format="%d-%m-%Y %H:%M").dt.floor("d")
    return df


def add_invoicenumber(data):
    global InvoiceNumber
    data["InvoiceNumber"] = InvoiceNumber
    InvoiceNumber += 1
    return data


def add_customer(data):
    PaymentType = data.name
    if PaymentType == PIN:
        data["PaymentCondition"] = DIRECT
        data["OrderAccountCode"] = KASSADEBITEUR
    elif PaymentType in INTERNAL_PAYMENTS:
        data["PaymentCondition"] = DIRECT
        data["OrderAccountCode"] = KASSAINTERN
    elif PaymentType in VVTP_PAYMENTS:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = VVTP
    elif PaymentType in EXTERNAL_PAYMENTS:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = EXTERN_PLACEHOLDER
    else:
        raise NotImplementedError(
            "Er is weggeboekt op een no-sale categorie dit niet bekend is bij het "
            f"script: {PaymentType}. Is er een categorie hernoemd? Of is er een nieuwe "
            "toegevoegd? In het laatste geval moet het script worden aangepast, "
            "vraag om hulp."
        )
    return data


def add_description(data):
    Date = data["Datum"].iloc[0]
    Customer = data["OrderAccountCode"].iloc[0]
    PaymentType = data["Betaaltype"].iloc[0]
    match Customer, PaymentType:
        case KASSADEBITEUR, PIN:
            data["Description"] = "kassamutaties {}".format(Date.strftime("%d-%m-%Y"))
            data["YourRef"] = None
        case KASSAINTERN, TAPPERS:
            data["Description"] = "gebruik tappers {}".format(Date.strftime("%B %Y"))
            data["YourRef"] = None
        case VVTP, BESTUUR_VVTP:
            description = "Bestuur VvTP {}".format(Date.strftime("%B %Y"))
            data["Description"] = description
            data["YourRef"] = description
        case VVTP, EVENEMENT_VVTP:
            global WARN_BORREL_VVTP
            WARN_BORREL_VVTP += 1
            data["Description"] = "Borrel VvTP PLAATSHOUDER"
            data["YourRef"] = "Borrel VvTP PLAATSHOUDER"
        case EXTERN_PLACEHOLDER, EXTERN:
            global WARN_EXTERN
            WARN_EXTERN += 1
            data["Description"] = "Borrel PLAATSHOUDER"
            data["YourRef"] = "PLAATSHOUDER"
        case _:
            raise NotImplementedError(
                "De combinatie relatie en betaaltype is niet bekend "
                f"({Customer} en {PaymentType}). Is er nieuwe betaallogica "
                "bijgekomen? Dan moet het script worden aangepast, vraag om "
                "hulp."
            )
    return data


def add_costunit(data):
    PaymentType, Date = data.name
    Weekday = Date.strftime("%w")
    if PaymentType == PIN:
        if Weekday == "3":
            data["CostUnit"] = CU_WOENSDAG
        elif Weekday == "5":
            data["CostUnit"] = CU_VRIJDAG
        else:
            data["CostUnit"] = None
    elif PaymentType == EXTERN:
        data["CostUnit"] = CU_EXTERN
    else:
        data["CostUnit"] = None
    return data


def add_date(data):
    data["Datum"] = data["Datum"].max()
    return data


def add_all_fields(totals):
    """Takes twelve transaction export and create Exact Online import files.

    First, transactions are separated based on whether the payments are bundled
    by month (like "Gebruik tappers"), or settled directly (like card
    payments).

    Next, different fields get added according to some respective logic by
    functions starting with "add_". Once these have all been applied, the final
    invoice file is made that can be imported into Exact online.
    """
    totals1 = (
        totals.query("Betaaltype in {}".format(BUNDLE_PAYMENTS))
        .groupby(["Betaaltype", pd.Grouper(key="Datum", freq="1M")])
        .apply(add_invoicenumber)
    )
    totals2 = (
        totals.query("Betaaltype not in {}".format(BUNDLE_PAYMENTS))
        .groupby(["Betaaltype", "Datum"])
        .apply(add_invoicenumber)
    )
    totals = pd.concat([totals1, totals2])
    totals = totals.groupby(["Betaaltype"]).apply(add_customer)
    totals = totals.groupby(["InvoiceNumber"]).apply(add_description)
    totals = totals.groupby(["InvoiceNumber"]).apply(add_date)
    totals = totals.groupby(["Betaaltype", "Datum"]).apply(add_costunit)
    totals["Journal"] = JOURNAL
    factuur = totals.groupby(["InvoiceNumber", "Product Id", "Prijs (per product)"])[
        [
            "Aantal",
            "Aantal * prijs",
            "Description",
            "Journal",
            "PaymentCondition",
            "YourRef",
            "OrderAccountCode",
            "CostUnit",
            "Datum",
        ]
    ].agg(
        {
            "Aantal": "sum",
            "Aantal * prijs": "sum",
            "Description": "first",
            "Journal": "first",
            "PaymentCondition": "first",
            "YourRef": "first",
            "OrderAccountCode": "first",
            "CostUnit": "first",
            "Datum": "first",
        }
    )
    factuur.rename(columns={"Datum": "OrderDate"}, inplace=True)
    factuur.rename(columns={"Product Id": "ItemCode"}, inplace=True)
    return factuur


if __name__ == "__main__":
    print(msg)
    InvoiceNumber = 1  # We don't have to track this, Exact does it for us.
    if input("Doorgaan (en README gelezen) y/n? ").lower() not in ["j", "y"]:
        exit()
    transactions = get_transactions()
    invoice = add_all_fields(transactions)
    out_factuur = "facturen.csv"
    invoice.to_csv(out_factuur, sep=";", float_format="%.2f")

    time.sleep(1)
    print(f"Writing {out_factuur}...")

    time.sleep(1)
    if WARN_EXTERN:
        print(EXTERN_MSG)
    if WARN_BORREL_VVTP:
        print(VVTP_MSG)
