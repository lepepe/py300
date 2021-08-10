import click
import pyodbc
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import inventorize3 as inv
import numpy as np
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
year = (datetime.now().year - 5)

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

def ranking(item):
    sql = """
        SELECT
            RTRIM(i.FMTITEMNO) AS 'Item', s.YR,
            CONVERT(datetime,CONVERT(char(8),s.TRANDATE)) AS 'Trandate',
            SUM(s.QTYSOLD) AS 'Quantity',
            SUM(FAMTSALES-FRETSALES) AS 'Netsales'
        FROM OESHDT s
        JOIN ICITEM i ON i.ITEMNO = s.ITEM
        WHERE (YR > ?)
        GROUP BY i.FMTITEMNO, s.YR, s.TRANDATE
    """

    df = pd.read_sql(sql, con, params=str(year).split())
    data = df.set_index("Trandate").sort_values(by="Trandate",ascending=True).last('12M')
    data = data.groupby(['Item']).agg(Volume=('Quantity',np.sum),Revenue=('Netsales',np.sum)).reset_index()
    ranking = inv.ABC(data[['Item','Revenue']]).reset_index()
    item_rank = ranking[ranking['Item'] == item]

    if item_rank.empty:
        panel = (
            f"Ranking: [magenta]No sales found for the last 12 months.[/magenta]"
        )
    else:
        for index, i in item_rank.iterrows():
            if i.Category == 'A':
                panel = (
                    f"Ranking: [yellow]{i.Category}[/yellow]\n"
                    f"Revenue: [yellow]{currency(i.Revenue)}[/yellow]\n"
                    f"Percentage: [yellow]{number_precision(i.Percentage*100)}%[/yellow]\n"
                )
            elif i.Category == 'B':
                panel = (
                    f"Ranking: [white]{i.Category}[/white]\n"
                    f"Revenue: [white]{currency(i.Revenue)}[/white]\n"
                    f"Percentage: [white]{number_precision(i.Percentage*100)}%[/white]\n"
                )
            elif i.Category == 'C':
                panel = (
                    f"ranking: [red]{i.category}[/red]\n"
                    f"Revenue: [red]{currency(i.Revenue)}[/red]\n"
                    f"Percentage: [red]{number_precision(i.Percentage*100)}%[/red]\n"
                )
    return panel

def sales_by_years(item):
    # Creating dataframe
    df = pd.read_sql(queries.sales_analysis('FMTITEMNO', item, year), con)
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

# Aggregated inventory coverage and availability
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

# Display inventory coverage and availability by locations
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

def last_12_months(df):
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, expand=True)
    months = [col for col in df.columns if col.startswith('20') | col.startswith('Loc')]

    for m in months:
        table.add_column(m, justify="right", no_wrap=True)

    for index, row in df.iterrows():
        table.add_row(
            row['Location'],
            number_precision(row[7]),
            number_precision(row[8]),
            number_precision(row[9]),
            number_precision(row[10]),
            number_precision(row[11]),
            number_precision(row[12]),
            number_precision(row[13]),
            number_precision(row[14]),
            number_precision(row[15]),
            number_precision(row[16]),
            number_precision(row[17]),
            number_precision(row[18]),
        )
    return table

# Calculate inventory coverage, availability and sales aggregated and
# by locations using pandas
def inv_coverage(item):
    df = pd.read_sql(queries.inv_analysis(item, year), con)

    # Generate a dataframe for the last 12 periods (YYYY-mm)
    months_ago = datetime.now() - relativedelta(months=11)
    periods = pd.period_range(months_ago.strftime('%Y-%m-%d'), datetime.today().strftime('%Y-%m-%d'), freq='M')
    df2 = pd.DataFrame(periods, columns = ['Period']).reset_index()
    df2['Period'] = df2['Period'].astype(str)
    first = df2.iloc[[0]]['Period'][0]
    last = df2.iloc[[-1]]['Period'][11]

    # Trnasforming data and combine with the last 12 periods
    data = df.set_index("Trandate").sort_values(by="Trandate",ascending=True).last('12M')
    data['QtyAve'] = data.groupby(['Item', 'Location'])['Quantity'].transform('sum')/12
    data['Coverage'] = data['QtyAV']/data['QtyAve']
    data['Period'] = data['Period'].str.zfill(2)
    data['Period'] = data[['Year', 'Period']].apply(lambda x: '-'.join(x), axis=1)
    data = data[(data['Period'] >= first) & (data['Period'] <= last)]
    data = pd.merge(df2, data, how='outer')
    data['Item'] = item
    fill_data = data.fillna(0)

    # Group data including locations
    data = fill_data.groupby(
        ['Item', 'Location','Period','QtyAV','QtySO','QtyPO','Coverage','QtyAve'], as_index=False
    ).agg(
        {'Quantity':sum}
    ).sort_values(by='Item', ascending=False)

    # Pivot
    serie = data.pivot_table('Quantity', index=['Item', 'Location', 'QtyAV', 'QtySO', 'QtyPO', 'Coverage', 'QtyAve'], columns=['Period'], aggfunc={'Quantity':sum}).reset_index()
    serie = serie[(serie['Location'] != 0)].fillna(0)

    # Global analysis grouped
    sum_df = data.groupby(['Item', 'Period']).agg({'Quantity':sum})
    sum_df['QtyAve'] = sum_df.groupby(['Item'])['Quantity'].transform('sum')/12
    global_serie = sum_df.pivot_table('Quantity', index=['Item', 'QtyAve'], fill_value=0, columns=['Period'], aggfunc={'Quantity':sum}).reset_index()
    global_df = df[['Item','QtyAV','QtySO','QtyPO']].drop_duplicates()
    global_df = global_df.groupby(
        ['Item'], as_index=False
    ).agg(
        {'QtyAV':sum, 'QtySO':sum, 'QtyPO':sum}
    ).sort_values(by='Item', ascending=False)
    global_data = pd.merge(global_df, global_serie, how='outer')

    return inv_coverage_global(global_data), inv_coverage_by_loc(serie), last_12_months(serie)

@click.command()
@click.option("-i", "--item", required=False, help="Item number")
@click.option("-f", "--find", required=False, help="Find item by code or description")
@click.option("-r", "--rank", required=False, help="Summary item ranking")
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
            Layout(name="sales", ratio=2),
        )

        # Rendered data into the layouts
        layout["header"].split(
            Layout(Panel(f"Item Number: [blue]{item}[/blue]"))
        )
        layout["upper"].split(
            Layout(Panel(ranking(item), title="Ranking"))
        )
        layout["optf"].split(
            Layout(Panel(inv_coverage(item)[0], title="Inventory Coverage")),
            Layout(Panel(inv_coverage(item)[1], title="By Locations"))
        )
        layout["sales"].split(
            Layout(Panel(sales_by_years(item), title="Sales by Years")),
            Layout(Panel(inv_coverage(item)[2], title="Last 12 months"))
        )
        console.print(layout)

    elif find:
        results = cursor.execute(f"SELECT * FROM ICITEM WHERE FMTITEMNO LIKE '%{find}%' OR [DESC] LIKE '%{find}%'").fetchall()
        console.print(f"Total records found: [blue]{len(results)}[/blue]")
        console.print(items(results))

    else:
        results = cursor.execute("SELECT COUNT(*) FROM ICITEM")
        console.print(f"Total items: [blue]{results.fetchone()[0]}[/blue]")
