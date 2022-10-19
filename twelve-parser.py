import time
from enum import Enum

import pandas as pd

# defaults
pd.options.mode.chained_assignment = None  # default='warn'
INPUTFILE = "export_ruwe_transactiegegevens.csv"


class PaymentType(Enum):
    """PaymentTypes in Twelve"""

    PIN = "Omzet PIN"
    TAPPERS = "Gebruik tappers"
    BESTUUR_VVTP = "Bestuur VvTP"
    EVENEMENT_VVTP = "Activiteit VvTP"
    EXTERN = "Externe borrel"


class CostUnit(Enum):
    """Cost Units (as defined in Exact online).

    Used to distinguish between Wed/Fri revenue."""

    WOENSDAG = "1"
    VRIJDAG = "2"
    EXTERN = "3"


class Customer(Enum):
    """Customers (as defined in Exact online).

    Internal payments (such as "Gebruik tappers") go through KASSAINTERN,
    direct payments (currently only paying by card) go through KASSADEBITEUR,
    while external payments are assigned a placeholder EXTERN_PLACEHOLDER."""

    VVTP = "1"
    EXTERN_PLACEHOLDER = "9997"
    KASSAINTERN = "9998"
    KASSADEBITEUR = "9999"


class PaymentCondition(Enum):
    """Payment Conditions (as defined in Exact online)."""

    DIRECT = "02"
    ON_CREDITS = "30"  # 30 days


# Specify which payment methods should be grouped per month (used to bundle
# e.g. "Gebruik tappers" per month)
BUNDLE_PAYMENTS = [PaymentType.TAPPERS, PaymentType.BESTUUR_VVTP]
# Specify which payments are direct, internal, for the VvTP, and external
DIRECT_PAYMENTS = [PaymentType.PIN]
VVTP_PAYMENTS = [PaymentType.BESTUUR_VVTP, PaymentType.EVENEMENT_VVTP]
EXTERNAL_PAYMENTS = [PaymentType.EXTERN]
INTERNAL_PAYMENTS = [PaymentType.TAPPERS]
# Invoice journal number (as defined in Exact online).
JOURNAL = 50
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
    payment_type = PaymentType(data.name)
    # The following match/case statement is not really orthodox. Unfortunately
    # it's not possible to check for values in a list, so we use case guards
    # instead. See https://stackoverflow.com/questions/74123249/how-to-use-
    # multiple-cases-in-structural-pattern-matching-switch-case-in-python
    match payment_type:
        case _ if payment_type in DIRECT_PAYMENTS:
            data["PaymentCondition"] = PaymentCondition.DIRECT.value
            data["OrderAccountCode"] = Customer.KASSADEBITEUR.value
        case _ if payment_type in INTERNAL_PAYMENTS:
            data["PaymentCondition"] = PaymentCondition.DIRECT.value
            data["OrderAccountCode"] = Customer.KASSAINTERN.value
        case _ if payment_type in VVTP_PAYMENTS:
            data["PaymentCondition"] = PaymentCondition.ON_CREDITS.value
            data["OrderAccountCode"] = Customer.VVTP.value
        case _ if payment_type in EXTERNAL_PAYMENTS:
            data["PaymentCondition"] = PaymentCondition.ON_CREDITS.value
            data["OrderAccountCode"] = Customer.EXTERN_PLACEHOLDER.value
        case _:
            raise NotImplementedError(
                "Er is weggeboekt op een no-sale categorie dit niet bekend is bij het "
                f"script: {payment_type}. Is er een categorie hernoemd? Of is er een "
                "nieuwe toegevoegd? In het laatste geval moet het script worden "
                " aangepast, vraag om hulp."
            )
    return data


def add_description(data):
    date = data["Datum"].iloc[0]
    customer = Customer(data["OrderAccountCode"].iloc[0])
    payment_type = PaymentType(data["Betaaltype"].iloc[0])
    match customer, payment_type:
        case Customer.KASSADEBITEUR, PaymentType.PIN:
            data["Description"] = "kassamutaties {}".format(date.strftime("%d-%m-%Y"))
            data["YourRef"] = None
        case Customer.KASSAINTERN, PaymentType.TAPPERS:
            data["Description"] = "gebruik tappers {}".format(date.strftime("%B %Y"))
            data["YourRef"] = None
        case Customer.VVTP, PaymentType.BESTUUR_VVTP:
            description = "Bestuur VvTP {}".format(date.strftime("%B %Y"))
            data["Description"] = description
            data["YourRef"] = description
        case Customer.VVTP, PaymentType.EVENEMENT_VVTP:
            global WARN_BORREL_VVTP
            WARN_BORREL_VVTP += 1
            data["Description"] = "Borrel VvTP PLAATSHOUDER"
            data["YourRef"] = "Borrel VvTP PLAATSHOUDER"
        case Customer.EXTERN_PLACEHOLDER, PaymentType.EXTERN:
            global WARN_EXTERN
            WARN_EXTERN += 1
            data["Description"] = "Borrel PLAATSHOUDER"
            data["YourRef"] = "PLAATSHOUDER"
        case _:
            raise NotImplementedError(
                "De combinatie relatie en betaaltype is niet bekend "
                f"({customer} en {payment_type}). Is er nieuwe betaallogica "
                "bijgekomen? Dan moet het script worden aangepast, vraag om "
                "hulp."
            )
    return data


def add_costunit(data):
    date = data["Datum"].iloc[0]
    payment_type = PaymentType(data["Betaaltype"].iloc[0])
    weekday = date.strftime("%w")
    match payment_type, weekday:
        case _, "3" if payment_type in DIRECT_PAYMENTS:
            data["CostUnit"] = CostUnit.WOENSDAG.value
        case _, "5" if payment_type in DIRECT_PAYMENTS:
            data["CostUnit"] = CostUnit.VRIJDAG.value
        case _ if payment_type == PaymentType.EXTERN:
            data["CostUnit"] = CostUnit.EXTERN.value
        case _:
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
    bundle = [payment_type.value for payment_type in BUNDLE_PAYMENTS]
    totals1 = (
        totals.query("Betaaltype in {}".format(bundle))
        .groupby(["Betaaltype", pd.Grouper(key="Datum", freq="1M")])
        .apply(add_invoicenumber)
    )
    totals2 = (
        totals.query("Betaaltype not in {}".format(bundle))
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
