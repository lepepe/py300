import click
import pyodbc
import pandas as pd
from rich import box
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout

import queries
import config
from config import currency, gross_margin

console = Console()
layout = Layout()

con = pyodbc.connect('DRIVER={FreeTDS};SERVER='+config.SQL_SERVER+';DATABASE='+config.DB_NAME+';PORT='+config.SQL_PORT+';UID='+config.SQL_USER+';PWD='+ config.SQL_PASSWD)
cursor = con.cursor()

def customers(results):
    table = Table(title="Customer(s)", expand=True)
    table.add_column("Customer Number", justify="left", no_wrap=True)
    table.add_column("Customer Name", justify="left", no_wrap=True)
    table.add_column("On Hold", justify="left", no_wrap=True, style="magenta")
    table.add_column("Country", justify="left", no_wrap=True)
    table.add_column("City", justify="left", no_wrap=True)

    for r in results:
        table.add_row(r.IDCUST.rstrip(), r.NAMECUST.rstrip(), str(r.SWHOLD), r.CODECTRY.rstrip(), r.NAMECITY.rstrip())
    return table

def credit_available(results):
    for r in results:
        limit = r.AMTCRLIMT
        balance = r.AMTBALDUET
        terms = r.CODETERM
        a = limit-balance

        if a > 0:
            panel = (
                f"Credit limit: [green]{currency(limit)}[/green]\n"
                f"Outstarnding Balance: [green]{currency(balance)}[/green]\n"
                f"Available: [green]{currency(a)}[/green]\n"
                f"Terms: [blue]{terms}[/blue]"
            )
        else:
            panel = (
                f"Credit limit: [red]{currency(limit)}[/red]\n"
                f"Outstarnding Balance: [red]{currency(balance)}[/red]\n"
                f"Available: [red]{currency(a)}[/red]\n"
                f"Terms: [blue]{terms}[/blue]"
            )

    return panel

def check_empty_df(value, account):
    if value.empty == True:
        value = value.append({'INAMTOVER': 0, 'IDCUST': account}, ignore_index=True)
    else:
       value
    return value

def receivables(account):
    df = pd.read_sql(queries.UNPAID_RECEIVABLES, con, params=account.split())
    u30 = df[(df['TERMDAYSOVER'] > 0) & (df['TERMDAYSOVER'] <= 30)].groupby(df['IDCUST'])['INAMTOVER'].sum().reset_index()
    u60 = df[(df['TERMDAYSOVER'] > 31) & (df['TERMDAYSOVER'] <= 60)].groupby(df['IDCUST'])['INAMTOVER'].sum().reset_index()
    u90 = df[(df['TERMDAYSOVER'] > 61) & (df['TERMDAYSOVER'] <= 90)].groupby(df['IDCUST'])['INAMTOVER'].sum().reset_index()
    m90 = df[(df['TERMDAYSOVER'] > 90)].groupby(df['IDCUST'])['INAMTOVER'].sum().reset_index()
    data = pd.concat([
        check_empty_df(u30, account),
        check_empty_df(u60, account),
        check_empty_df(u90, account),
        check_empty_df(m90, account)
    ])

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("", no_wrap=True)
    table.add_column("0-30", justify="right", no_wrap=True)
    table.add_column("31-60", justify="right", no_wrap=True)
    table.add_column("61-90", justify="right", no_wrap=True)
    table.add_column("90+", justify="right", no_wrap=True)

    table.add_row(
        "Amount Overdue",
        currency(data.iloc[0]['INAMTOVER']),
        currency(data.iloc[1]['INAMTOVER']),
        currency(data.iloc[2]['INAMTOVER']),
        currency(data.iloc[3]['INAMTOVER'])
    )
    return table

def sales_by_years(account):
    # Creating dataframe
    df = pd.read_sql(queries.SALES_ANALYSIS, con, params=account.split())
    data = df.groupby(['YR']).agg({
        'NETSALES':sum,
        'FAMTSALES':sum,
        'FRETSALES':sum,
        'FCSTSALES':sum,
    }).reset_index()

    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("Year", justify="left", no_wrap=True)
    table.add_column("Sales", justify="right", no_wrap=True)
    table.add_column("Returns", justify="right", no_wrap=True)
    table.add_column("Netsales", justify="right", no_wrap=True, style="blue")
    table.add_column("COGS", justify="right", no_wrap=True)
    table.add_column("Margin (%)", justify="right", no_wrap=True)

    for index, row in data.iterrows():
        table.add_row(
            str(row['YR']),
            currency(row['FAMTSALES']),
            currency(row['FRETSALES']),
            currency(row['NETSALES']),
            currency(row['FCSTSALES']),
            gross_margin(row['NETSALES'], row['FCSTSALES'])
        )
    return table

@click.command()
@click.option("-a", "--account", required=False, help="Customer account number")
@click.option("-f", "--find", required=False, help="Find customer by account number or name")
def cli(account, find):
    """ Table: Customers (ARCUS) """

    if account:
        results = cursor.execute("SELECT * FROM ARCUS WHERE IDCUST = ?", account).fetchall()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="upper", size=8),
            Layout(name="lower", size=15)
        )

        # Divide the lower layout in two parts
        layout["lower"].split_row(
            Layout(name="credit"),
            Layout(name="sales", ratio=2),
        )

        # Rendered data into the layouts
        layout["header"].split(
            Layout(Panel(f"Customer: [blue]{account}[/blue]"))
        )
        layout["upper"].update(
            customers(results)
        )
        layout["credit"].split(
            Layout(Panel(credit_available(results), title="Credit Status")),
            Layout(Panel(receivables(account), title="Receivables"))
        )
        layout["sales"].update(
            Panel(sales_by_years(account), title="Sales by Years")
        )
        console.print(layout)


    elif find:
        results = cursor.execute(f"SELECT * FROM ARCUS WHERE IDCUST LIKE '%{find}%' OR NAMECUST LIKE '%{find}%'").fetchall()
        console.print(f"Total records found: [blue]{len(results)}[/blue]")
        console.print(customers(results))

    else:
        results = cursor.execute("SELECT COUNT(*) FROM ARCUS")
        console.print(f"Total customers: [blue]{results.fetchone()[0]}[/blue]")
