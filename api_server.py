"""JSON API over the payment schedule calculator. All the maths lives in main.py."""

import os

from flask import Flask, jsonify, request
from flask_cors import CORS

from main import MAX_DAYS, build_schedule, make_txn

app = Flask(__name__)
CORS(app)

SAMPLE = [
    {
        "operation": "in",
        "frequency": "B",
        "amount": 3000,
        "startDate": "2024-10-01",
        "endDate": "",
        "description": "PAY",
    },
    {
        "operation": "out",
        "frequency": "M",
        "amount": 1500,
        "startDate": "2024-10-01",
        "endDate": "",
        "description": "Rent",
    },
    {
        "operation": "out",
        "frequency": "M",
        "amount": 500,
        "startDate": "2024-10-15",
        "endDate": "",
        "description": "Car Insurance",
    },
    {
        "operation": "out",
        "frequency": "B",
        "amount": 500,
        "startDate": "2024-10-15",
        "endDate": "2025-10-15",
        "description": "Car Payment",
    },
    {
        "operation": "out",
        "frequency": "M",
        "amount": 300,
        "startDate": "2024-10-01",
        "endDate": "",
        "description": "Insurance",
    },
    {
        "operation": "out",
        "frequency": "B",
        "amount": 100,
        "startDate": "2024-10-05",
        "endDate": "",
        "description": "Gym",
    },
    {
        "operation": "out",
        "frequency": "BY",
        "amount": 50,
        "startDate": "2024-10-01",
        "endDate": "",
        "description": "Microsoft",
    },
    {
        "operation": "out",
        "frequency": "W",
        "amount": 50,
        "startDate": "2024-10-01",
        "endDate": "",
        "description": "Gas",
    },
]


@app.get("/api/sample")
def get_sample():
    return jsonify(SAMPLE)


@app.post("/api/calculate")
def calculate_schedule():
    data = request.get_json(silent=True) or {}
    transactions = data.get("transactions")
    if not isinstance(transactions, list) or not transactions:
        return jsonify({"error": "Provide a non-empty 'transactions' list"}), 400

    try:
        days = int(data.get("days", 100))
    except (TypeError, ValueError):
        return jsonify({"error": "'days' must be a whole number"}), 400

    try:
        txns = [
            make_txn(
                t.get("operation"),
                t.get("frequency"),
                t.get("amount"),
                t.get("startDate"),
                t.get("endDate") or "",
                t.get("description") or "",
            )
            for t in transactions
        ]
        schedule = build_schedule(
            txns, days, opening=data.get("openingBalance", 0) or 0
        )
    except (ValueError, AttributeError) as e:
        return jsonify({"error": str(e)}), 400

    return jsonify(
        [
            {
                "date": day.date.isoformat(),
                "payments": day.total,
                "balance": day.balance,
                "items": [{"description": d, "amount": a} for d, a in day.items],
            }
            for day in schedule
        ]
    )


@app.get("/")
def index():
    return f"Payment Schedule API. POST /api/calculate, GET /api/sample. Max {MAX_DAYS} days."


if __name__ == "__main__":
    # debug stays off by default: the Werkzeug debugger is a remote shell for
    # anyone who can reach the port.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "3000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
