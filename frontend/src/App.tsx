import { useState, useEffect, useRef } from "react";
import { Transaction, PaymentSchedule } from "./types";
import { Calendar, Plus, Download, Upload, Trash2 } from "lucide-react";

// Relative: vite proxies /api to Flask in dev, so there's no hardcoded host.
const API = "/api";
const STORAGE_KEY = "payments-schedule";
const MAX_DAYS = 3650;

// Local date, not toISOString() — that's UTC and can read as tomorrow.
const todayISO = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const frequencyOptions = [
  { value: "Y", label: "Yearly" },
  { value: "BY", label: "Bi-Yearly" },
  { value: "Q", label: "Quarterly" },
  { value: "M", label: "Monthly" },
  { value: "B", label: "Bi-Weekly" },
  { value: "SW", label: "Semi-Weekly (Mon & Thu)" },
  { value: "W", label: "Weekly" },
  { value: "D", label: "Daily" },
  { value: "O", label: "One-time" },
];

const operationOptions = [
  { value: "in", label: "Income" },
  { value: "out", label: "Expense" },
];

const money = (n: number) =>
  n.toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const blankRecurring = (): Partial<Transaction> => ({
  operation: "in",
  frequency: "M",
  amount: 0,
  startDate: todayISO(),
  endDate: "",
  description: "",
});

const blankQuick = () => ({
  operation: "out" as "in" | "out",
  amount: "",
  date: todayISO(),
  description: "",
});

function loadSaved() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null");
  } catch {
    return null;
  }
}

const saved = loadSaved();

function App() {
  const [transactions, setTransactions] = useState<Transaction[]>(
    saved?.transactions ?? [],
  );
  const [schedule, setSchedule] = useState<PaymentSchedule[]>([]);
  // Kept as strings: a number input is transiently empty or "-" mid-type.
  const [days, setDays] = useState<string>(saved?.days ?? "100");
  const [opening, setOpening] = useState<string>(saved?.opening ?? "0");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showRecurring, setShowRecurring] = useState(false);
  const [onlyActiveDays, setOnlyActiveDays] = useState(true);
  const [recurring, setRecurring] =
    useState<Partial<Transaction>>(blankRecurring());
  const [quick, setQuick] = useState(blankQuick());
  const quickAmountRef = useRef<HTMLInputElement>(null);

  const daysNum = Number(days);
  const daysValid =
    Number.isInteger(daysNum) && daysNum >= 1 && daysNum <= MAX_DAYS;
  const openingNum = opening.trim() === "" ? 0 : Number(opening);
  const openingValid = Number.isFinite(openingNum);
  const today = todayISO();

  const loadSample = async () => {
    try {
      const res = await fetch(`${API}/sample`);
      setTransactions(await res.json());
      setError("");
    } catch {
      setError(
        "Failed to load sample data — is the Flask API running on port 3000?",
      );
    }
  };

  useEffect(() => {
    if (!saved?.transactions?.length) loadSample();
  }, []);

  useEffect(() => {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ transactions, days, opening }),
    );
  }, [transactions, days, opening]);

  // Recalculates as you type. Skips transiently invalid input so a half-typed
  // number doesn't flash a validation error from the server.
  useEffect(() => {
    if (!transactions.length) {
      setSchedule([]);
      return;
    }
    if (!daysValid || !openingValid) return;

    let cancelled = false;
    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`${API}/calculate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            transactions,
            days: daysNum,
            openingBalance: openingNum,
          }),
        });
        const data = await res.json();
        if (cancelled) return;
        if (!res.ok)
          throw new Error(data.error || "Failed to calculate schedule");
        setSchedule(data);
        setError("");
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof Error ? err.message : "Failed to calculate schedule",
        );
        setSchedule([]);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }, 250);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [transactions, days, opening]);

  const addQuick = (e: React.FormEvent) => {
    e.preventDefault();
    const amount = Number(quick.amount);
    if (!amount || amount <= 0) {
      setError("Enter an amount first");
      quickAmountRef.current?.focus();
      return;
    }
    if (quick.date < today) {
      setError(
        "The schedule starts today, so a date in the past would never show up",
      );
      return;
    }
    setTransactions([
      ...transactions,
      {
        operation: quick.operation,
        frequency: "O",
        amount,
        startDate: quick.date,
        endDate: "",
        description:
          quick.description.trim() ||
          (quick.operation === "in" ? "Windfall" : "One-off"),
      },
    ]);
    setQuick({ ...quick, amount: "", description: "" }); // keep date and in/out
    setError("");
    quickAmountRef.current?.focus();
  };

  const addRecurring = () => {
    if (!recurring.amount || !recurring.startDate) {
      setError("Amount and start date are required");
      return;
    }
    if (recurring.endDate && recurring.endDate < recurring.startDate) {
      setError("End date cannot be before the start date");
      return;
    }
    setError("");
    setTransactions([
      ...transactions,
      { ...recurring, amount: Number(recurring.amount) } as Transaction,
    ]);
    setRecurring(blankRecurring());
    setShowRecurring(false);
  };

  const deleteTransaction = (index: number) =>
    setTransactions(transactions.filter((_, i) => i !== index));

  // Matches the CSV main.py reads: the endDate cell carries "# description".
  const exportToCSV = () => {
    const csv = [
      "operation,frequency,amount,startDate,endDate",
      ...transactions.map((t) => {
        const tail = t.description
          ? `${t.endDate || ""} # ${t.description}`
          : t.endDate || "";
        return `${t.operation},${t.frequency},${t.amount},${t.startDate},${tail}`;
      }),
    ].join("\n");

    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "transactions.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importFromCSV = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const parsed: Transaction[] = [];
        for (const raw of (e.target?.result as string).split("\n")) {
          const line = raw.trim();
          if (!line || line.toLowerCase().startsWith("operation,")) continue;
          const cells = line.split(",");
          if (cells.length < 5)
            throw new Error(
              `Expected 5 columns, got ${cells.length}: "${line}"`,
            );
          const [operation, frequency, amount, startDate] = cells.map((c) =>
            c.trim(),
          );
          const [endDate, description] = cells.slice(4).join(",").split("#");
          parsed.push({
            operation: operation.toLowerCase() as "in" | "out",
            frequency: frequency.toUpperCase(),
            amount: Number(amount),
            startDate,
            endDate: endDate.trim(),
            description: (description || "").trim(),
          });
        }
        if (!parsed.length)
          throw new Error("No transactions found in that file");
        setTransactions(parsed);
        setError("");
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Could not read that CSV",
        );
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  // Income and expenses come from the individual items: a day's net would hide
  // an expense landing on the same day as a bigger paycheck.
  const totals = schedule.reduce(
    (acc, day) => {
      for (const item of day.items ?? []) {
        if (item.amount >= 0) acc.income += item.amount;
        else acc.expenses += Math.abs(item.amount);
      }
      return acc;
    },
    { income: 0, expenses: 0 },
  );
  const finalBalance = schedule.length
    ? schedule[schedule.length - 1].balance
    : 0;
  const lowest = schedule.reduce(
    (min, d) => (d.balance < min.balance ? d : min),
    schedule[0],
  );
  const visibleDays = onlyActiveDays
    ? schedule.filter((d) => d.items?.length)
    : schedule;

  return (
    <div className="min-h-screen bg-gray-100 p-4 sm:p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold text-gray-800 mb-8">
          Payment Schedule Calculator
        </h1>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Setup</h2>

              <div className="mb-4">
                <label
                  className="block text-sm font-medium mb-1"
                  htmlFor="opening"
                >
                  Opening Balance
                </label>
                <input
                  id="opening"
                  type="number"
                  value={opening}
                  onChange={(e) => setOpening(e.target.value)}
                  className={`w-full p-2 border rounded ${openingValid ? "" : "border-red-400"}`}
                  step="0.01"
                  placeholder="0.00"
                />
                <p className="text-xs text-gray-500 mt-1">
                  What the account holds today. Negative is fine.
                </p>
              </div>

              <div className="mb-6">
                <label
                  className="block text-sm font-medium mb-1"
                  htmlFor="days"
                >
                  Days to Calculate
                </label>
                <input
                  id="days"
                  type="number"
                  value={days}
                  onChange={(e) => setDays(e.target.value)}
                  className={`w-full p-2 border rounded ${daysValid ? "" : "border-red-400"}`}
                  min="1"
                  max={MAX_DAYS}
                />
                {!daysValid && (
                  <p className="text-xs text-red-600 mt-1">
                    Enter a whole number between 1 and {MAX_DAYS}.
                  </p>
                )}
              </div>

              <h2 className="text-xl font-semibold mb-4">Transactions</h2>

              {showRecurring && (
                <div className="mb-6 p-4 border rounded-lg bg-gray-50">
                  <h3 className="font-medium mb-3">
                    Add Recurring Transaction
                  </h3>
                  <div className="space-y-3">
                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="operation"
                      >
                        Operation
                      </label>
                      <select
                        id="operation"
                        value={recurring.operation}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            operation: e.target.value as "in" | "out",
                          })
                        }
                        className="w-full p-2 border rounded"
                      >
                        {operationOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="frequency"
                      >
                        Frequency
                      </label>
                      <select
                        id="frequency"
                        value={recurring.frequency}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            frequency: e.target.value,
                          })
                        }
                        className="w-full p-2 border rounded"
                      >
                        {frequencyOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="amount"
                      >
                        Amount
                      </label>
                      <input
                        id="amount"
                        type="number"
                        value={recurring.amount}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            amount: Number(e.target.value),
                          })
                        }
                        className="w-full p-2 border rounded"
                        step="0.01"
                        min="0"
                      />
                    </div>

                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="startDate"
                      >
                        Start Date
                      </label>
                      <input
                        id="startDate"
                        type="date"
                        value={recurring.startDate}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            startDate: e.target.value,
                          })
                        }
                        className="w-full p-2 border rounded"
                      />
                    </div>

                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="endDate"
                      >
                        End Date{" "}
                        <span className="font-normal text-gray-500">
                          — blank means it never stops
                        </span>
                      </label>
                      <input
                        id="endDate"
                        type="date"
                        value={recurring.endDate}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            endDate: e.target.value,
                          })
                        }
                        className="w-full p-2 border rounded"
                      />
                    </div>

                    <div>
                      <label
                        className="block text-sm font-medium mb-1"
                        htmlFor="description"
                      >
                        Description
                      </label>
                      <input
                        id="description"
                        type="text"
                        value={recurring.description}
                        onChange={(e) =>
                          setRecurring({
                            ...recurring,
                            description: e.target.value,
                          })
                        }
                        className="w-full p-2 border rounded"
                      />
                    </div>

                    <div className="flex gap-2">
                      <button
                        onClick={addRecurring}
                        className="flex-1 bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600"
                      >
                        Add
                      </button>
                      <button
                        onClick={() => setShowRecurring(false)}
                        className="bg-gray-300 text-gray-700 py-2 px-4 rounded hover:bg-gray-400"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}

              <button
                onClick={() => setShowRecurring(true)}
                className="w-full bg-green-500 text-white py-2 px-4 rounded hover:bg-green-600 mb-4 flex items-center justify-center gap-2"
              >
                <Plus size={20} /> Add Recurring
              </button>

              <div className="flex gap-2 mb-6">
                <button
                  onClick={exportToCSV}
                  className="flex-1 bg-gray-500 text-white py-2 px-4 rounded hover:bg-gray-600 flex items-center justify-center gap-2"
                >
                  <Download size={20} /> Export CSV
                </button>
                <label className="flex-1 bg-gray-500 text-white py-2 px-4 rounded hover:bg-gray-600 cursor-pointer flex items-center justify-center gap-2">
                  <Upload size={20} /> Import CSV
                  <input
                    type="file"
                    accept=".csv"
                    onChange={importFromCSV}
                    className="hidden"
                  />
                </label>
              </div>

              <div className="space-y-2 max-h-96 overflow-y-auto">
                {transactions.map((transaction, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between p-3 border rounded bg-gray-50"
                  >
                    <div className="flex-1">
                      <div
                        className={`font-medium ${transaction.operation === "in" ? "text-green-700" : "text-red-700"}`}
                      >
                        {transaction.operation === "in" ? "+" : "−"}
                        {money(transaction.amount)}
                        <span className="text-gray-500 font-normal text-sm">
                          {" "}
                          {frequencyOptions.find(
                            (f) => f.value === transaction.frequency,
                          )?.label ?? transaction.frequency}
                        </span>
                      </div>
                      <div className="text-sm text-gray-600">
                        {transaction.description && (
                          <span className="font-medium">
                            {transaction.description} ·{" "}
                          </span>
                        )}
                        {transaction.frequency === "O" ? "on" : "from"}{" "}
                        {transaction.startDate}
                        {transaction.endDate && ` until ${transaction.endDate}`}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteTransaction(index)}
                      className="text-red-500 hover:text-red-700"
                      aria-label={`Delete ${transaction.description || "transaction"}`}
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                ))}
                {transactions.length === 0 && (
                  <div className="text-gray-500 text-center py-4">
                    No transactions yet.{" "}
                    <button
                      onClick={loadSample}
                      className="text-blue-600 hover:underline"
                    >
                      Load the sample
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="lg:col-span-2">
            <div className="bg-white rounded-lg shadow-md p-6">
              <form
                onSubmit={addQuick}
                className="mb-6 p-4 border rounded-lg bg-gray-50"
              >
                <label
                  className="block font-medium mb-2"
                  htmlFor="quick-amount"
                >
                  Quick add a one-off
                </label>
                <div className="flex flex-wrap gap-2">
                  <select
                    value={quick.operation}
                    onChange={(e) =>
                      setQuick({
                        ...quick,
                        operation: e.target.value as "in" | "out",
                      })
                    }
                    className="p-2 border rounded"
                    aria-label="Expense or windfall"
                  >
                    <option value="out">Expense</option>
                    <option value="in">Windfall</option>
                  </select>
                  <input
                    id="quick-amount"
                    ref={quickAmountRef}
                    type="number"
                    value={quick.amount}
                    onChange={(e) =>
                      setQuick({ ...quick, amount: e.target.value })
                    }
                    placeholder="Amount"
                    step="0.01"
                    min="0"
                    className="p-2 border rounded w-28"
                  />
                  <input
                    type="date"
                    value={quick.date}
                    min={today}
                    onChange={(e) =>
                      setQuick({ ...quick, date: e.target.value })
                    }
                    className="p-2 border rounded"
                    aria-label="Date"
                  />
                  <input
                    type="text"
                    value={quick.description}
                    onChange={(e) =>
                      setQuick({ ...quick, description: e.target.value })
                    }
                    placeholder="What for?"
                    className="p-2 border rounded flex-1 min-w-32"
                  />
                  <button
                    type="submit"
                    className="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600 flex items-center gap-1"
                  >
                    <Plus size={18} /> Add
                  </button>
                </div>
              </form>

              <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <Calendar size={24} /> Payment Schedule Summary
                  {isLoading && (
                    <span className="text-sm font-normal text-gray-400">
                      updating…
                    </span>
                  )}
                </h2>
                {schedule.length > 0 && (
                  <label className="text-sm text-gray-600 flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={onlyActiveDays}
                      onChange={(e) => setOnlyActiveDays(e.target.checked)}
                    />
                    Only days with payments
                  </label>
                )}
              </div>

              {schedule.length > 0 ? (
                <div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-center mb-6">
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">Total Income</div>
                      <div className="text-lg font-semibold text-green-600">
                        +{money(totals.income)}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">
                        Total Expenses
                      </div>
                      <div className="text-lg font-semibold text-red-600">
                        −{money(totals.expenses)}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">Final Balance</div>
                      <div
                        className={`text-lg font-semibold ${finalBalance >= 0 ? "text-green-600" : "text-red-600"}`}
                      >
                        {money(finalBalance)}
                      </div>
                    </div>
                    <div className="p-3 bg-gray-50 rounded-lg">
                      <div className="text-sm text-gray-600">
                        Lowest Balance
                      </div>
                      <div
                        className={`text-lg font-semibold ${lowest && lowest.balance >= 0 ? "text-green-600" : "text-red-600"}`}
                      >
                        {lowest ? money(lowest.balance) : "0.00"}
                      </div>
                      {lowest && (
                        <div className="text-xs text-gray-500">
                          on {lowest.date}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="min-w-full table-auto">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-4 py-3 text-left">Date</th>
                          <th className="px-4 py-3 text-left">Activity</th>
                          <th className="px-4 py-3 text-right">Net</th>
                          <th className="px-4 py-3 text-right">Balance</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visibleDays.map((item) => (
                          <tr
                            key={item.date}
                            className="border-t hover:bg-gray-50 group"
                          >
                            <td className="px-4 py-3 font-mono whitespace-nowrap">
                              {item.date}
                              <button
                                onClick={() => {
                                  setQuick({ ...quick, date: item.date });
                                  quickAmountRef.current?.focus();
                                }}
                                className="ml-2 text-gray-300 group-hover:text-blue-500 hover:text-blue-700"
                                aria-label={`Add a one-off on ${item.date}`}
                                title={`Add a one-off on ${item.date}`}
                              >
                                <Plus size={14} />
                              </button>
                            </td>
                            <td className="px-4 py-3 text-sm text-gray-600">
                              {(item.items ?? []).map((p, i) => (
                                <span
                                  key={i}
                                  className="inline-block mr-2 whitespace-nowrap"
                                >
                                  {p.description || "unnamed"}
                                  <span
                                    className={
                                      p.amount >= 0
                                        ? "text-green-600"
                                        : "text-red-600"
                                    }
                                  >
                                    {" "}
                                    ({p.amount >= 0 ? "+" : "−"}
                                    {money(Math.abs(p.amount))})
                                  </span>
                                </span>
                              ))}
                            </td>
                            <td
                              className={`px-4 py-3 text-right font-mono ${
                                item.payments > 0
                                  ? "text-green-600"
                                  : item.payments < 0
                                    ? "text-red-600"
                                    : "text-gray-400"
                              }`}
                            >
                              {item.payments > 0 ? "+" : ""}
                              {money(item.payments)}
                            </td>
                            <td
                              className={`px-4 py-3 text-right font-mono font-semibold ${
                                item.balance >= 0
                                  ? "text-green-600"
                                  : "text-red-600"
                              }`}
                            >
                              {money(item.balance)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {visibleDays.length === 0 && (
                      <div className="text-gray-500 text-center py-8">
                        No payments land in the next {days} days.
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-12">
                  <Calendar size={48} className="mx-auto mb-4 opacity-50" />
                  <p>Add a transaction to see your schedule.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
