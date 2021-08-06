from dotenv import load_dotenv
load_dotenv()
import os

SQL_SERVER = os.environ.get("sql_server")
DB_NAME = os.environ.get("db_name")
SQL_USER = os.environ.get("sql_user")
SQL_PASSWD = os.environ.get("sql_passwd")
SQL_PORT = os.environ.get("sql_port")

def currency(value):
    formatted_float = "${:,.2f}".format(value)
    return formatted_float
