from dotenv import load_dotenv
load_dotenv()
import os

SQL_SERVER = os.environ.get("sql_server")
DB_NAME = os.environ.get("db_name")
SQL_USER = os.environ.get("sql_user")
SQL_PASSWD = os.environ.get("sql_passwd")
SQL_PORT = os.environ.get("sql_port")

# Helper functions
def currency(value):
    formatted_float = "${:,.2f}".format(value)
    return formatted_float

def number_precision(value):
    formatted_float = "{:,.2f}".format(value)
    return formatted_float

def gross_margin(netsales, cogs):
    if netsales > 0:
        gm = ((netsales - cogs)/netsales)*100
    else:
        gm = 0
    return "{:,.2f} %".format(gm)

def year():
    return (datetime.now().year - 5)
