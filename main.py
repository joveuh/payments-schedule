from datetime import datetime, date, time, timedelta
import csv, json, os
import sys
import boto3
from io import StringIO

s3 = boto3.client("s3")
DATE_FORMATTER = "%Y-%m-%d"
date_dict = {}


def fill_in_dict(startdate, enddate):
    while startdate != enddate:
        date_dict[startdate] = []
        startdate = startdate + timedelta(days=1)


def adjust_date(date: datetime, frequency: str) -> datetime:
    return {
        "Y": date + timedelta(365),  # Yearly
        "BY": date + timedelta(365 / 2),  # Bi-Yearly
        "Q": date + timedelta(days=90),  # Quarterly
        "M": date + timedelta(30),  # Monthly
        "B": date + timedelta(weeks=2),  # Bi-Weekly
        "W": date + timedelta(weeks=1),  # Weekly
        "D": date + timedelta(days=1),  # Daily
    }.get(
        frequency, date
    )  # Default case returns the unchanged date


def performops(ops, calculateuntil):
    for op in ops[1:]:
        type, freq, amount, date = op
        amount = int(amount)
        date = datetime.strptime(date.split("#")[0].strip(), DATE_FORMATTER).date()
        until = date + timedelta(calculateuntil)

        while date < until:
            if date in date_dict:
                date_dict[date].append(amount if type == "in" else -amount)
            date = adjust_date(date, freq)
        

def printsummary():
    balance = 0
    for index, (date,payment_denominations_list) in enumerate(date_dict.items()):
        sum_of_ops = sum(payment_denominations_list) if payment_denominations_list != None and len(payment_denominations_list) > 0 else 0
        balance = balance + sum_of_ops
        balance_str = f"Balance: {str(balance)}"
        date = f"Date: {date}"
        if payment_denominations_list != None and len(payment_denominations_list) > 0:
            payment_denominations = f"Payments: {payment_denominations_list}"
            total = f"In/Out Total: {sum_of_ops}"
            line = f"{date:<20} {payment_denominations:<40} {total:<60} {balance_str:<80}"
        else:
            line = f"{date:<20} {'':<40} {'':<60} {balance_str:<80}"
        print(line)
            


def startcalculations(ops_content, calculateuntil):
    today = date.today()
    enddate = today + timedelta(days=calculateuntil)
    fill_in_dict(today, enddate)
    performops(ops_content,  calculateuntil)
    return printsummary()


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
    return respond(None, startcalculations(ops_content, int(calculateuntil)))


ops_content_text = """
operation,frequency,amount,startDate
in,B, 3000, 2024-10-01 # PAY
out,M, 1500, 2024-10-01 # Rent
out,M, 500, 2024-10-15 # Car Insurance
out,B, 500, 2024-10-15 # Car Payment
out,M, 300, 2024-10-01 # Insurance
out,B, 100, 2024-10-05 # Gym
out,BY, 50, 2024-10-01 # Microsoft
out,W, 50, 2024-10-01 # Gas"""


if __name__ == "__main__":
    args = [arg.lower() for arg in sys.argv[1:]]
    default_days = 100
    if len(args) == 0:
        run(default_days)
        exit
    else:
        opscsvfile = args[0] if len(args) > 0 and args[0] else None
        days = args[1] if len(args) > 1 and args[1] else default_days
        run(days, opscsvfile)
