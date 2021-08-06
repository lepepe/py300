import click
import pyodbc
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import config
from config import currency

console = Console()
layout = Layout()

con = pyodbc.connect('DRIVER={FreeTDS};SERVER='+config.SQL_SERVER+';DATABASE='+config.DB_NAME+';PORT='+config.SQL_PORT+';UID='+config.SQL_USER+';PWD='+ config.SQL_PASSWD)
cursor = con.cursor()

def customers(results):
    table = Table(title="Customer(s)")
    table.add_column("Customer Number", justify="left", no_wrap=True)
    table.add_column("Custoemer Name", justify="left", no_wrap=True)
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

@click.command()
@click.option("-a", "--account", required=False, help="Customer account number")
@click.option("-f", "--find", required=False, help="Find customer by account number or name")
def cli(account, find):
    """ Table: Customers (ARCUS) """

    if account:
        results = cursor.execute("SELECT * FROM ARCUS WHERE IDCUST = ?", account).fetchall()
        customers(results)
        credit_available(results)

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="upper", size=8),
            Layout(name="lower", size=15)
        )

        # Divide the lower layout in two parts
        layout["lower"].split_row(
            Layout(name="credit"),
            Layout(name="right"),
        )

        # Rendered data into the layouts
        layout["header"].split(
            Layout(Panel(f"Customer: [blue]{account}[/blue]"))
        )
        layout["credit"].update(
            Panel(credit_available(results), title="Credit Status")
        )
        layout["upper"].update(
            customers(results)
        )
        console.print(layout)

    elif find:
        results = cursor.execute(f"SELECT * FROM ARCUS WHERE IDCUST LIKE '%{find}%' OR NAMECUST LIKE '%{find}%'").fetchall()
        console.print(f"Total records found: [blue]{len(results)}[/blue]")
        console.print(customers(results))

    else:
        results = cursor.execute("SELECT COUNT(*) FROM ARCUS")
        console.print(f"Total customers: [blue]{results.fetchone()[0]}[/blue]")
