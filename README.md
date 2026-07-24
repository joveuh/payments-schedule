# Payment Schedule

Ever wonder what is coming in and out of your account on a daily basis? Project your
recurring income and expenses forward and see the running daily balance — and the day
it dips lowest.

## Run it

Once:

```bash
npm run setup
```

That builds the Python venv, installs the API's dependencies, and installs the frontend.
Then, any time:

```bash
npm run dev
```

One command starts both the Flask API (:3000) and the UI on http://localhost:5173 —
vite runs the API as a child process, so Ctrl+C stops both.

## Using it

- **Opening balance** — what the account holds today. Negative is fine. Everything
  else is projected on top of it.
- **Quick add a one-off** — an expense or a windfall on any future date. Hit the `+`
  next to any day in the schedule to aim at that date. The schedule recalculates as
  you type; there is no calculate button.
- **Add Recurring** — for anything that repeats. See the frequency table below.

Your transactions are saved in the browser, so a refresh keeps them.

## Command line

```bash
python main.py                            # built-in sample
python main.py mycsvfile.csv 365          # your file, 365 days out
python main.py mycsvfile.csv 365 --opening 1200 --save
```

`--opening` sets the starting balance, `--save` also writes the summary to sqlite.

## CSV format

The UI reads and writes this same format, so you can export from one and read in the other.

```
operation,frequency,amount,startDate,endDate
in,B, 3000, 2024-10-01, # PAY
out,M, 1500, 2024-10-01, # Rent
out,B, 500, 2024-10-15, 2025-10-15 # Car Payment
```

- **operation** — `in` or `out`, money deposited or withdrawn.
- **frequency** — see the table below.
- **amount** — a positive number; `operation` decides the sign.
- **startDate** — `YYYY-MM-DD`, when the payment first lands.
- **endDate** — `YYYY-MM-DD`, the last day it can land (inclusive). **Leave it blank
  if the payment never stops.** An endDate before the startDate is also read as "never
  stops", which is what makes a `1970-01-01` placeholder behave.

Anything after a `#` in the last column is a description, and shows up in the UI.

| Code | Meaning                                |
| ---- | -------------------------------------- |
| `Y`  | Yearly                                 |
| `BY` | Bi-Yearly (every 6 months)             |
| `Q`  | Quarterly (every 3 months)             |
| `M`  | Monthly                                |
| `B`  | Bi-Weekly (every 2 weeks)              |
| `SW` | Semi-Weekly (then Mondays & Thursdays) |
| `W`  | Weekly                                 |
| `D`  | Daily                                  |
| `O`  | One-time, on the start date            |

Month-based frequencies step whole calendar months measured from the start date, so a
payment on the 31st lands Jan 31 → Feb 28 → Mar 31 rather than drifting. Every
frequency lands on its start date first, then follows its own rhythm — so an `SW`
payment starting on a Saturday shows Saturday, then settles onto Mondays & Thursdays.

## What the balance means

The schedule starts today and builds on the opening balance, so it shows what the
account holds on each day ahead. Payments dated before today are skipped: a
transaction that started last year picks up at its next occurrence, which is what you
want for anything recurring.

That includes one-offs — a `O` entry dated in the past has already happened and is
skipped. To carry a starting balance in, use the opening balance rather than a
backdated one-time row.

## Tests

```bash
npm test          # or: python test_main.py
```

## Sample output

![Screenshot 2024-12-14 at 11 19 23 PM](https://github.com/user-attachments/assets/a524b2e1-c302-4d8d-80c5-86848c5fdf60)

![Screenshot 2024-12-14 at 11 27 48 PM](https://github.com/user-attachments/assets/8a75a258-d744-44e5-9339-db3a112b83ea)
