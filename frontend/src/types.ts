export interface Transaction {
  operation: "in" | "out";
  frequency: string;
  amount: number;
  startDate: string;
  endDate?: string; // empty means it never stops
  description?: string;
}

export interface ScheduleItem {
  description: string;
  amount: number; // signed: negative is money out
}

export interface PaymentSchedule {
  date: string;
  payments: number; // net for the day
  balance: number;
  items: ScheduleItem[];
}
