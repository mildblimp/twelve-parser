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
# Cost Unit links in Exact Online
CU_WOENSDAG = "1"
CU_VRIJDAG = "2"
CU_EXTERN = "3"
# Customers
VVTP = "1"
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

Belangrijk om te lezen voor gebruik:
  - Exporteer transactiegegevens (Rapportage > Overige > Basisgegevens > Deze
    lijst naar csv) NB: pak de goede begin- en einddatum!
  - Zorg dat alle artikelen in Exact aanwezig zijn
  - Zorg dat alle inkoopprijzen van de artikelen up-to-date zijn!
  - Zorg dat er geen "facturen.csv" file aanwezig is
  - Voeg na afloop een duidelijke Uw. Ref. in bij externe borrels en borrels
    van de VvTP (zo weten de respectieve penningmeesters waar de factuur om
    gaat)

Na afloop krijg je een file "facturen.csv" die je kan importeren in Exact. Alle
PIN transacties gaan via de relatie kassadebiteur, en die letteren precies goed
af op het bedrag dat via de PIN is binnengekomen. Interne transacties gaan via
de relatie KassaIntern, deze moeten nog handmatig worden afgeletterd op de
juiste grootboekkaarten zoals "gebruik tappers" en "breuk & bederf".

"""


def get_transactions(inputfile=INPUTFILE):
    with open(inputfile, "r", encoding="utf-8") as f:
        df_transactions = pd.read_csv(f, delimiter=";")
        print(f"Reading {inputfile}...")
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
    elif PaymentType in EXTERNAL_PAYMENTS:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = VVTP
    else:
        data["PaymentCondition"] = ON_CREDITS
        data["OrderAccountCode"] = None
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
    """Takes twelve transation export and create Exact Online import file."""
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
    totals = totals.groupby(["InvoiceNumber", "Product Id"])[
        [
            "Aantal",
            "Aantal * prijs",
            "Prijs (per product)",
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
            "Prijs (per product)": "first",
            "Description": "first",
            "Journal": "first",
            "PaymentCondition": "first",
            "YourRef": "first",
            "OrderAccountCode": "first",
            "CostUnit": "first",
            "Datum": "first",
        }
    )
    totals.rename(columns={"Datum": "OrderDate"}, inplace=True)
    totals.rename(columns={"Product Id": "ItemCode"}, inplace=True)
    return totals


if __name__ == "__main__":
    print(msg)
    InvoiceNumber = int(input("Eerstvolgend verkoopfactuurnummer: ")) - 1
    transactions = get_transactions()
    invoice = add_all_fields(transactions)
    outfile = "facturen.csv"
    with open(outfile, "x") as f:
        invoice.to_csv(f, sep=";", float_format="%.2f")
        print(f"Writing {outfile}...\n")

    if WARN_EXTERN:
        print("LET OP: Externe borrel gevonden, check facturen voor afdrukken!")
        print(
            "Zorg dat je de juiste relatie toevoegd en Uw. Ref. zoals Borrel PS 15-01-2018"
        )
    if WARN_BORREL_VVTP:
        print("LET OP: VvTP borrel gevonden, check facturen voor afdrukken!")
        print(
            "Zorg dat je een duidelijke Uw. Ref. toevoegd bijv. Borrel Lustrumreis 21-09-2018"
        )
