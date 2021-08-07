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

def items(results):
    table = Table(expand=True)
    table.add_column("Item Number", justify="left", no_wrap=True)
    table.add_column("Description", justify="left", no_wrap=True)
    table.add_column("Category", justify="left", no_wrap=True)
    table.add_column("Stock Item", justify="left", no_wrap=True, style="magenta")
    table.add_column("Stocking UOM", justify="left", no_wrap=True)
    table.add_column("Default Price List", justify="left", no_wrap=True)
    table.add_column("Weight", justify="left", no_wrap=True)

    for r in results:
        table.add_row(
            r.FMTITEMNO.rstrip(),
            r.DESC.rstrip(),
            r.CATEGORY.rstrip(),
            str(r.STOCKITEM),
            r.STOCKUNIT.rstrip(),
            r.DEFPRICLST.strip(),
            f"{r.UNITWGT} " + f"({r.WEIGHTUNIT.strip()})"
        )
    return table

def sales_by_years(item):
    # Creating dataframe
    df = pd.read_sql(queries.sales_analysis('FMTITEMNO', item), con)
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
    table.add_column("Net Sales", justify="right", no_wrap=True, style="blue")
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
@click.option("-i", "--item", required=False, help="Item number")
@click.option("-f", "--find", required=False, help="Find item by code or description")
def cli(item, find):
    """ Table: Items (ICITEM) """

    if item:
        results = cursor.execute("SELECT * FROM ICITEM WHERE FMTITEMNO = ?", item).fetchall()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="upper", size=8),
            Layout(name="lower", size=15)
        )

        # Divide the lower layout in two parts
        layout["lower"].split_row(
            Layout(name="optf"),
            Layout(name="sales", ratio=2),
        )

        # Rendered data into the layouts
        layout["header"].split(
            Layout(Panel(f"Itemcode: [blue]{item}[/blue]"))
        )
        layout["upper"].update(
            items(results)
        )
        #layout["optf"].split(
        #   Layout(Panel(credit_available(results), title="Credit Status")),
        #   Layout(Panel(receivables(account), title="Receivables"))
        #)
        layout["sales"].update(
            Panel(sales_by_years(item), title="Sales by Years")
        )
        console.print(layout)

    elif find:
        results = cursor.execute(f"SELECT * FROM ICITEM WHERE FMTITEMNO LIKE '%{find}%' OR [DESC] LIKE '%{find}%'").fetchall()
        console.print(f"Total records found: [blue]{len(results)}[/blue]")
        console.print(items(results))

    else:
        results = cursor.execute("SELECT COUNT(*) FROM ICITEM")
        console.print(f"Total items: [blue]{results.fetchone()[0]}[/blue]")
