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
from config import currency, gross_margin, number_precision

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

def inv_coverage_global(df):
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("Available", justify="left", no_wrap=True, style="green")
    table.add_column("QtySO", justify="right", no_wrap=True)
    table.add_column("QtyPO", justify="right", no_wrap=True)
    table.add_column("QtyAve", justify="right", no_wrap=True, style="blue")
    table.add_column("Coverage", justify="right", no_wrap=True, style="blue")

    table.add_row(
        number_precision(df.iloc[0]['QtyAV']),
        number_precision(df.iloc[0]['QtySO']),
        number_precision(df.iloc[0]['QtyPO']),
        number_precision(df.iloc[0]['QtyAve']),
        number_precision(df.iloc[0]['QtyAV']/df.iloc[0]['QtyAve']),
    )
    return table

def inv_coverage_by_loc(df):
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("Loc", justify="left", no_wrap=True)
    table.add_column("Available", justify="right", no_wrap=True, style="green")
    table.add_column("QtySO", justify="right", no_wrap=True)
    table.add_column("QtyPO", justify="right", no_wrap=True)
    table.add_column("QtyAve", justify="right", no_wrap=True, style="blue")
    table.add_column("Coverage", justify="right", no_wrap=True, style="blue")

    for index, row in df.iterrows():
        table.add_row(
            row['Location'],
            number_precision(row['QtyAV']),
            number_precision(row['QtySO']),
            number_precision(row['QtyPO']),
            number_precision(row['QtyAve']),
            number_precision(row['Coverage']),
        )
    return table

def inv_coverage(item):
    df = pd.read_sql(queries.inv_analysis(item), con)

    data = df.set_index("Trandate").sort_values(by="Trandate",ascending=True).last('12M')
    data['QtyAve'] = data.groupby(['Item', 'Location'])['Quantity'].transform('sum')/12
    data['Coverage'] = data['QtyAV']/data['QtyAve']
    data['Period'] = data[['Year', 'Period']].apply(lambda x: '-'.join(x), axis=1)

    sum_df = data.groupby(['Item', 'Period']).agg({'Quantity':sum})
    sum_df['QtyAve'] = sum_df.groupby(['Item'])['Quantity'].transform('sum')/12

    serie = data.pivot_table('Quantity', index=['Item', 'Location', 'QtyAV', 'QtySO', 'QtyPO', 'Coverage', 'QtyAve'], columns=['Period'], aggfunc={'Quantity':sum}).reset_index()
    global_serie = sum_df.pivot_table('Quantity', index=['Item', 'QtyAve'], fill_value=0, columns=['Period'], aggfunc={'Quantity':sum}).reset_index()

    global_df = df[['Item','QtyAV','QtySO','QtyPO']].drop_duplicates()
    global_df = global_df.groupby(
        ['Item'], as_index=False
    ).agg(
        {
            'QtyAV':sum,
            'QtySO':sum,
            'QtyPO':sum
        }
    ).sort_values(by='Item', ascending=False)
    global_data = pd.merge(global_df, global_serie, how='outer')
    return inv_coverage_global(global_data), inv_coverage_by_loc(serie)

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
            Layout(name="lower", size=25)
        )

        # Divide the lower layout in two parts
        layout["lower"].split_row(
            Layout(name="optf"),
            Layout(name="sales"),
        )

        # Rendered data into the layouts
        layout["header"].split(
            Layout(Panel(f"Item Number: [blue]{item}[/blue]"))
        )
        layout["upper"].update(
            items(results)
        )
        layout["optf"].split(
           Layout(Panel(inv_coverage(item)[0], title="Inventory Coverage")),
           Layout(Panel(inv_coverage(item)[1], title="By Locations"))
        )
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
