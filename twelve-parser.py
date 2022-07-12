import time

import pandas as pd

# defaults
pd.options.mode.chained_assignment = None  # default='warn'
INPUTFILE = "export_ruwe_transactiegegevens.csv"
# Paymenttypes in Twelve
PIN = "Omzet PIN"
TAPPERS = "gebruik tappers"
REPRESENTATIE = "representatie"
BESTUUR_VVTP = "rekening VvTP"
EVENEMENT_VVTP = "commissie"
EXTERN = "externe borrel"
CAMPUS_CRAWL = "Campus crawl muntje"
# GL types for internal bookings
GL_TAPPERS = 4491
GL_REPRESENTATIE = 4470
# Cost Unit links in Exact Online
CU_WOENSDAG = "1"
CU_VRIJDAG = "2"
CU_EXTERN = "3"
# Customers
VVTP = "1"
UNUSED = "9997"
KASSAINTERN = "9998"
KASSADEBITEUR = "9999"
# Payment Conditions
DIRECT = "02"
ON_CREDITS = "30"  # 30 days
# Invoice journal number
JOURNAL = 50
# Payment types on credit (used to bundle e.g. "Rekening VvTP bestuur" per month)
BUNDLE_PAYMENTS = [TAPPERS, BESTUUR_VVTP, REPRESENTATIE]
EXTERNAL_PAYMENTS = [BESTUUR_VVTP, EVENEMENT_VVTP, EXTERN, CAMPUS_CRAWL]
INTERNAL_PAYMENTS = [REPRESENTATIE, TAPPERS]
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


Met dit script kan je transactiegegevens uit Twelve halen om vervolgens te
importeren in Exact online. Het script werkt, maar het weet niet wat er is
aangepast in Twelve. Dus als er nieuwe producten zijn,  of als er nieuwe "no
sale" mogelijkheden zijn bijgekomen, dan moet het script worden aangepast!

Zorg dat je nooit handmatig de transactiegegevens uit Twelve haalt!

- Exporteer transactiegegevens (Rapportage > Overige > Basisgegevens > Deze
  lijst naar csv) NB: pak de goede begin- en einddatum!
- Zorg dat alle artikelen in Exact aanwezig zijn met de juiste btw-code en
  inkoopprijs
- Voeg na afloop een duidelijke Uw. Ref. in bij externe borrels en borrels van
  de VvTP (zo weten de respectieve penningmeesters waar de factuur om gaat)

Na afloop krijg je een bestand `facturen.csv` en `kassa_intern.csv` die je kan
importeren in Exact. Alle PIN transacties gaan via de relatie "Kassadebiteur",
en die letteren precies goed af op het bedrag dat via de PIN is binnengekomen.
Interne transacties gaan via de relatie "Kassa intern", deze worden automatisch
afgeletterd op de juiste grootboekkaarten zoals "gebruik tappers" en "breuk &
bederf" als je dit bestand importeerd.

"""


def get_transactions(inputfile=INPUTFILE):
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
        # Add the GL (grootboekrekening) for internal transactions
        if PaymentType == TAPPERS:
            data["GLAccount"] = GL_TAPPERS
        elif PaymentType == REPRESENTATIE:
            data["GLAccount"] = GL_REPRESENTATIE
    elif PaymentType in EXTERNAL_PAYMENTS:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = VVTP
    else:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = UNUSED
    return data


def add_description(data):
    Customer = data["OrderAccountCode"].iloc[0]
    Date = data["Datum"].iloc[0]
    PaymentType = data["Betaaltype"].iloc[0]
    if Customer == KASSADEBITEUR:
        data["Description"] = "kassamutaties {}".format(Date.strftime("%d-%m-%Y"))
        data["YourRef"] = None
    elif Customer == KASSAINTERN:
        if PaymentType == TAPPERS:
            data["Description"] = "gebruik tappers {}".format(Date.strftime("%B %Y"))
            data["YourRef"] = None
        elif PaymentType == REPRESENTATIE:
            data["Description"] = "representatie {}".format(Date.strftime("%B %Y"))
            data["YourRef"] = None
        else:
            raise NotImplementedError(
                "Not implemented: {} and {}".format(Customer, PaymentType)
            )
    elif Customer == VVTP:
        if PaymentType == BESTUUR_VVTP:
            description = "Bestuur VvTP {}".format(Date.strftime("%B %Y"))
            data["Description"] = description
            data["YourRef"] = description
        elif PaymentType == EVENEMENT_VVTP:
            global WARN_BORREL_VVTP
            WARN_BORREL_VVTP += 1
            data["Description"] = "Borrel VvTP"
            data["YourRef"] = "Borrel VvTP"
        elif PaymentType == CAMPUS_CRAWL:
            data["Description"] = "Campus Crawl Muntje"
            data["YourRef"] = "Campus Crawl Muntje"
        else:
            raise NotImplementedError(
                "Not implemented: {} and {}".format(Customer, PaymentType)
            )
    else:
        global WARN_EXTERN
        WARN_EXTERN += 1
        data["Description"] = "Borrel"
        data["YourRef"] = None
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
    """Takes twelve transation export and create Exact Online import files."""
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
    memo = (
        totals.loc[totals["Betaaltype"].isin(INTERNAL_PAYMENTS)]
        .groupby(["Description"])[
            [
                "Prijs (per product)",
                "Journal",
                "PaymentCondition",
                "OrderAccountCode",
                "Datum",
                "GLAccount",
            ]
        ]
        .agg(
            {
                "Prijs (per product)": "sum",
                "Journal": "first",
                "PaymentCondition": "first",
                "OrderAccountCode": "first",
                "Datum": "first",
                "GLAccount": "first",
            }
        )
    )
    memo["GLAccount"] = memo["GLAccount"].astype(int)
    memo["Prijs (per product)"] *= -1
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
    return factuur, memo


if __name__ == "__main__":
    print(msg)
    InvoiceNumber = 1  # We don't have to track this, Exact does it for us.
    if input("Doorgaan y/n? ").lower() not in ["j", "y"]:
        exit()
    transactions = get_transactions()
    invoice, memo = add_all_fields(transactions)
    out_factuur = "facturen.csv"
    out_memo = "kassa_intern.csv"
    invoice.to_csv(out_factuur, sep=";", float_format="%.2f")
    memo.to_csv(out_memo, sep=";", float_format="%.2f")

    time.sleep(1)
    print(f"Writing {out_factuur}...")
    print(f"Writing {out_memo}...\n")

    time.sleep(1)
    if WARN_EXTERN:
        print(EXTERN_MSG)
    if WARN_BORREL_VVTP:
        print(VVTP_MSG)
