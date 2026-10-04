import tkinter as tk
from tkinter import ttk, messagebox
from api import fetch_rates
from db import init_db, save_rate, get_saved_rate


class CurrencyConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Конвертер валют")
        self.geometry("400x600")
        self.loan_var = tk.StringVar()
        self.loan_time_var = tk.StringVar()
        self.annual_interest_var = tk.StringVar()
        self.base_var = tk.StringVar(value="RUB")
        self.target_var = tk.StringVar(value="USD")
        init_db()
        self.create_widgets()

    def create_widgets(self):
        tk.Label(self, text="Сумма кредита:").pack()
        self.loan_entry = ttk.Entry(self, textvariable=self.loan_var)
        self.loan_entry.pack()

        tk.Label(self, text="Срок кредита (мес):").pack()
        self.loan_time_entry = ttk.Entry(self, textvariable=self.loan_time_var)
        self.loan_time_entry.pack()

        tk.Label(self, text="Процентная ставка (%):").pack()
        self.interest_entry = ttk.Entry(self, textvariable=self.annual_interest_var)
        self.interest_entry.pack()

        ttk.Button(self, text="Рассчитать", command=self.calculate_loan).pack()

        self.monthly_label = tk.Label(self, text="Ежемесячный платёж: 0 RUB")
        self.monthly_label.pack()
        self.loan_sum_label = tk.Label(self, text="Сумма всех платежей: 0 RUB")
        self.loan_sum_label.pack()
        self.interest_label = tk.Label(self, text="Начисленные проценты: 0 RUB")
        self.interest_label.pack()

        tk.Label(self, text="Базовая валюта:").pack()
        tk.Label(self, textvariable=self.base_var).pack()

        tk.Label(self, text="Целевая валюта:").pack()
        self.target_entry = ttk.Combobox(self, textvariable=self.target_var)
        self.target_entry["values"] = ("USD", "EUR", "CNY", "GBP", "JPY")
        self.target_entry.pack()

        ttk.Button(self, text="Конвертировать", command=self.convert).pack()

        self.result_label = tk.Label(self, text="")
        self.result_label.pack()

        ttk.Button(self, text="Обновить курсы", command=self.update_db).pack()

        self.log_text = tk.Text(self, height=5)
        self.log_text.pack()

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def is_loan_invalid(self, value, message):
        if value <= 0:
            messagebox.showerror("Ошибка", message)
            self.log(message)
            return True
        return False

    def calculate_loan(self):
        try:
            loan = float(self.loan_var.get())
            months = int(self.loan_time_var.get())
            annual_rate = float(self.annual_interest_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите числа!")
            return

        if self.is_loan_invalid(loan, "Сумма должна быть больше 0"):
            return
        if self.is_loan_invalid(months, "Срок должен быть больше 0"):
            return
        if self.is_loan_invalid(annual_rate, "Ставка должна быть больше 0"):
            return

        monthly_rate = annual_rate / 100 / 12
        monthly_payment = loan * (monthly_rate + monthly_rate / ((1 + monthly_rate) ** months - 1))
        total_payment = monthly_payment * months
        interest = total_payment - loan

        self.monthly_label.config(text=f"Ежемесячный платёж: {monthly_payment:.2f} RUB")
        self.loan_sum_label.config(text=f"Сумма всех платежей: {total_payment:.2f} RUB")
        self.interest_label.config(text=f"Начисленные проценты: {interest:.2f} RUB")

        self.log(f"Рассчитан кредит на {loan} RUB")

    def convert(self):
        target = self.target_var.get()
        rate = get_saved_rate(target)

        if rate is None:
            messagebox.showwarning("Курс не найден", f"Курс {target} не в БД. Нажмите «Обновить курсы».")
            return

        try:
            loan = float(self.loan_var.get())
        except ValueError:
            messagebox.showerror("Ошибка", "Введите сумму кредита!")
            return

        converted = loan / rate
        self.result_label.config(text=f"{loan} RUB = {converted:.2f} {target}")
        self.log(f"Конвертация: {loan} RUB → {converted:.2f} {target}")

    def update_db(self):
        rates = fetch_rates()
        valute = rates.get("Valute", {})

        for i, (code, info) in enumerate(valute.items(), start=1):
            save_rate(i, code, info["Value"])

        self.log(f"Обновлено курсов: {len(valute)}")
        messagebox.showinfo("Готово", f"Обновлено курсов: {len(valute)}")


if __name__ == "__main__":
    app = CurrencyConverterApp()
    app.mainloop()