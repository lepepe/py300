import click
import pyodbc
import pandas as pd
from prettytable import PrettyTable
import config

con = pyodbc.connect('DRIVER={FreeTDS};SERVER='+config.SQL_SERVER+';DATABASE='+config.DB_NAME+';PORT='+config.SQL_PORT+';UID='+config.SQL_USER+';PWD='+ config.SQL_PASSWD)
cursor = con.cursor()

def customers(results):
    t = PrettyTable(['Customer Number', 'Customer Name', 'On Hold', 'Country', 'City'])
    t.align = "l"
    for r in results:
        t.add_row(
            [
                r.IDCUST.rstrip(),
                r.NAMECUST.rstrip(),
                r.SWHOLD,
                r.CODECTRY.rstrip(),
                r.NAMECITY.rstrip()
            ]
        )
    return t

def credit_available(limit, balance):
    a = limit-balance
    if a > 0:
        click.secho(f"Outstanding Balance: {balance}", fg="green", bold=True),
        click.secho(f"Available: {a}", fg="green", bold=True),
    else:
        click.secho(f"Available: {a}", fg="red", bold=True),

@click.command()
@click.option("-a", "--account", required=False, help="Customer account number")
def cli(account):
    """ Table: Customers (ARCUS) """

    if account:
        results = cursor.execute("SELECT * FROM ARCUS WHERE IDCUST = ?", account).fetchall()
        print(customers(results))

        for r in results:
            click.secho(f"Credit limit: {r.AMTCRLIMT}", fg="blue", bold=True),
            credit_available(r.AMTCRLIMT, r.AMTBALDUET)
            click.secho(f"Terms: {r.CODETERM}", fg="blue", bold=True)
    else:
        print("All Customers")
        results = cursor.execute(""" SELECT * FROM ARCUS """).fetchall()
        print(customers(results))
