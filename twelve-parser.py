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
# Cost Unit links in Exact Online
CU_WOENSDAG = "1"
CU_VRIJDAG = "2"
CU_EXTERN = "3"
# Customers
VVTP = "1"
KASSADEBITEUR = "9999"
# Payment Conditions
DIRECT = "02"
ON_CREDITS = "30"  # 30 days
# Invoice journal number
JOURNAL = 50
# Payment types on credit (used to bundle e.g. "Rekening VvTP bestuur" per month)
BUNDLE_PAYMENTS = [TAPPERS, BESTUUR_VVTP, REPRESENTATIE]


def get_transactions(inputfile=INPUTFILE):
    with open(inputfile, "r", encoding="utf-8") as f:
        df_transactions = pd.read_csv(f, delimiter=";")
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
    if PaymentType in [PIN, TAPPERS, REPRESENTATIE]:
        data["PaymentCondition"] = DIRECT
        data["OrderAccountCode"] = KASSADEBITEUR
    elif PaymentType in [BESTUUR_VVTP, EVENEMENT_VVTP]:
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
        if PaymentType == PIN:
            data["Description"] = "kassamutaties {}".format(Date.strftime("%d-%m-%Y"))
            data["YourRef"] = None
        elif PaymentType == TAPPERS:
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
            data["Description"] = "Borrel VvTP"
            data["YourRef"] = "Borrel VvTP"
        else:
            raise NotImplementedError(
                "Not implemented: {} and {}".format(Customer, PaymentType)
            )
    else:
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
        "Aantal",
        "Aantal * prijs",
        "Description",
        "Journal",
        "PaymentCondition",
        "YourRef",
        "OrderAccountCode",
        "CostUnit",
        "Datum",
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
    totals.rename(columns={"Datum": "OrderDate"}, inplace=True)
    totals.rename(columns={"Product Id": "ItemCode"}, inplace=True)
    return totals


if __name__ == "__main__":
    InvoiceNumber = int(input("Eerstvolgend verkoopfactuurnummer: ")) - 1
    InputFile = input("Input file name (default: {}): ".format(INPUTFILE))
    InputFile = INPUTFILE if InputFile == "" else InputFile
    transactions = get_transactions(InputFile)
    invoice = add_all_fields(transactions)
    with open("facturen.csv", "w") as f:
        invoice.to_csv(f, sep=";", float_format="%.2f")
