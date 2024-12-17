from datetime import datetime, date, timedelta
import csv, json, sys
from io import StringIO
from schedule_summary_db_ops import DB_Ops

ops_content_text = """
operation,frequency,amount,date
in,B, 3000, 2024-10-01 # PAY
out,M, 1500, 2024-10-01 # Rent
out,M, 500, 2024-10-15 # Car Insurance
out,B, 500, 2024-10-15 # Car Payment
out,M, 300, 2024-10-01 # Insurance
out,B, 100, 2024-10-05 # Gym
out,BY, 50, 2024-10-01 # Microsoft
out,W, 50, 2024-10-01 # Gas"""


DATE_FORMATTER = "%Y-%m-%d"
date_dict = {}


def fill_in_dict(startdate, enddate):
    while startdate != enddate:
        date_dict[startdate] = []
        startdate = startdate + timedelta(days=1)


def adjust_date(date: datetime, frequency: str) -> datetime:
    _DAYS_IN_MONTH = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    days_in_curr_month = _DAYS_IN_MONTH[date.month]
    return {
        "Y": date + timedelta(365),  # Yearly
        "BY": date + timedelta(365 / 2),  # Bi-Yearly
        "Q": date + timedelta(days=90),  # Quarterly
        "M": date + timedelta(days_in_curr_month),  # Monthly
        "B": date + timedelta(weeks=2),  # Bi-Weekly
        "W": date + timedelta(weeks=1),  # Weekly
        "D": date + timedelta(days=1),  # Daily
    }.get(
        frequency, date
    )  # Default case returns the unchanged date


def sort_csv_by_date(ops):
    # 1) the CSV could potentially be a file with dates that are not from present times
    # The user supplied or default 'calculateuntil' variable assumes entries contain recent dates, particularly today's date and following dates.
    # Depending on the user-supplied value of #days to calculate payment schedule for, this logic may cause issues.

    # Suppose the default value of 100 days is used in case user does not supply calculateuntil integer number. So we begin to
    # calculate the next 100 days of payment schedule. However, if the latest date in the CSV is from 365 year ago, this will surely fail
    # because the datetime keys in date_dict being generated will not make it as far as today's date considering the logic  until = date + timedelta(calculateuntil)
    # The last key in the dict will be -365 + 100 = -265 days, so 265 days in the past. And so the calculations for those dates won't happen.

    # TO-DO
    #
    # There may be user-interest to actually move the backdated entries to the present dates

    # think of the entries along an x-axis,
    # if the earliest date is more than 6 months away from the latest date, user may want to calculate it as it is
    # if the earliest date is within 2 months of the latest date, move all dates forward by delta from below

    ops = sorted(
        ops[1:],
        key=lambda row: datetime.strptime(row[3].split("#")[0].strip(), DATE_FORMATTER),
    )
    return ops


def get_detla_from_earliest_csv_date(ops):
    ops = sort_csv_by_date(ops)

    earliest_date_in_csv = ops[0][3].split("#")[0].strip()
    latest_date_in_csv = next(reversed(ops))[3].split("#")[0].strip()

    delta = (
        datetime.today() - datetime.strptime(earliest_date_in_csv, DATE_FORMATTER)
    ).days
    return delta


def performops(ops, calculateuntil):
    calculateuntil += get_detla_from_earliest_csv_date(ops)
    for op in ops[1:]:
        type, freq, amount, date = op
        amount = int(amount)
        date = datetime.strptime(date.split("#")[0].strip(), DATE_FORMATTER).date()
        until = date + timedelta(calculateuntil)

        while date < until:
            if date in date_dict:
                date_dict[date].append(amount if type.lower() == "in" else -amount)
            date = adjust_date(date, freq.upper())


def save_summary():
    rows = []
    balance = 0
    for index, (date, payment_denominations_list) in enumerate(date_dict.items()):
        sum_of_ops = (
            sum(payment_denominations_list)
            if payment_denominations_list != None
            and len(payment_denominations_list) > 0
            else 0
        )
        balance = balance + sum_of_ops
        balance_str = f"Balance: {str(balance)}"
        date_str = f"Date: {date}"
        if payment_denominations_list != None and len(payment_denominations_list) > 0:
            payment_denominations = f"Payments: {payment_denominations_list}"
            total = f"In/Out Total: {sum_of_ops}"
            line = f"{date_str:<20} {payment_denominations:<40} {total:<30} {balance_str:<30}"
        else:
            line = f"{date_str:<20} {'':<40} {'':<30} {balance_str:<30}"
        rows.append((datetime.strftime(date, DATE_FORMATTER), sum_of_ops, balance))
        print(line)
    return rows


def store_db_table(rows: list = None, db_handler: DB_Ops = None):
    if rows is None:
        raise Exception("sorry, empty list to store in db")
    if db_handler is None:
        raise Exception("sorry, no db instance specififed")
    for tuple_txn in rows:
        db_handler.cursor_execute(None, tuple_txn)


def startcalculationsandstore(ops_content, calculateuntil):
    today = date.today()
    enddate = today + timedelta(days=calculateuntil)
    fill_in_dict(today, enddate)
    performops(ops_content, calculateuntil)
    db_handler = DB_Ops()
    db_handler.create_table()
    store_db_table(save_summary(), db_handler)
    # db_handler.show_db_table()
    print(db_handler.cursor_execute("SELECT * FROM summary_table").fetchall())


def respond(err, res=None):
    return {
        "statusCode": "400" if err else "200",
        "body": err.message if err else json.dumps(res),
        "headers": {
            "Content-Type": "application/json",
        },
    }


def getCSVfromfile(csvfile):
    try:
        with open(csvfile, mode="r") as file:
            csv_reader = csv.reader(file)
            rows = []
            for row in csv_reader:
                rows.append(row)
            if len(rows) < 2:
                raise ValueError(
                    "The CSV file seems to have an issue. It only contains single line. It must contain a header line and at least 1 data line."
                )
            print("\nCSV file contents:")
            return rows
    except Exception as e:
        raise Exception(f"Error reading csv file: {str(e)}")


def getCSVfromtext(ops_text=None):
    reader = csv.reader(StringIO(ops_text))
    rows = []
    for row in reader:
        rows.append(row)
    print("\nSample CSV file contents:")
    return rows[1:]


def run(calculateuntil: int, opscsvfile: str = None):
    ops_content = (
        getCSVfromtext(ops_content_text)
        if opscsvfile == None
        else getCSVfromfile(opscsvfile)
    )
    print("\n".join(map(str, ops_content)))
    print("\nSummary of payments schedule")
    return respond(None, startcalculationsandstore(ops_content, int(calculateuntil)))


if __name__ == "__main__":
    args = [arg.lower() for arg in sys.argv[1:]]
    default_days = 100
    if len(args) == 0:
        run(default_days, None)
        exit
    else:
        opscsvfile = args[0] if len(args) > 0 and args[0] else None
        days = args[1] if len(args) > 1 and args[1] else default_days
        run(days, opscsvfile)
