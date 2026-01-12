import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- DATABASE SETUP ---
conn = sqlite3.connect('sern_finance.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT, id_no TEXT, join_date DATE, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS savings (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, date DATE, amount REAL, mode TEXT, receipt_no TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS loans (loan_no INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, date_issued DATE, amount REAL, rate REAL, duration INTEGER, approved_by TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS repayments (id INTEGER PRIMARY KEY AUTOINCREMENT, loan_no INTEGER, date DATE, amount REAL, interest REAL, principal REAL, receipt_no TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT, category TEXT, amount REAL, ref_no TEXT, date DATE, remarks TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS withdrawals (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, date DATE, amount REAL, reason TEXT, approved_by TEXT)')
    conn.commit()

init_db()

# --- GLOBAL CALCULATIONS (Fixes the NameError) ---
total_savings = pd.read_sql("SELECT SUM(amount) FROM savings", conn).iloc[0,0] or 0
total_income = pd.read_sql("SELECT SUM(amount) FROM transactions WHERE type='Income'", conn).iloc[0,0] or 0
total_repayments = pd.read_sql("SELECT SUM(amount) FROM repayments", conn).iloc[0,0] or 0
total_loans = pd.read_sql("SELECT SUM(amount) FROM loans", conn).iloc[0,0] or 0
total_expenses = pd.read_sql("SELECT SUM(amount) FROM transactions WHERE type='Expense'", conn).iloc[0,0] or 0
total_withdrawals = pd.read_sql("SELECT SUM(amount) FROM withdrawals", conn).iloc[0,0] or 0

receipts = total_savings + total_income + total_repayments
payments = total_loans + total_expenses + total_withdrawals
closing_balance = receipts - payments

# --- INTERFACE ---
st.title("⚡ SERN ELECTRIC LEDGER SYSTEM")
menu = ["Cash Book", "Member Register", "Savings Ledger", "Loan System", "Income & Expenses", "Monthly Summary"]
choice = st.sidebar.selectbox("Menu", menu)

# --- 1. MEMBER REGISTER ---
if choice == "Member Register":
    st.header("👥 Member Master List")
    with st.form("mem_form"):
        n, p, i = st.text_input("Full Name"), st.text_input("Phone"), st.text_input("National ID No.")
        if st.form_submit_button("Register Member"):
            c.execute("INSERT INTO members (name, phone, id_no, join_date, status) VALUES (?,?,?,?,?)", (n, p, i, datetime.now().date(), "Active"))
            conn.commit()
            st.success("Member Registered!")
    
    df_m = pd.read_sql("SELECT id as 'Member No', name, phone, id_no as 'ID', join_date, status FROM members", conn)
    st.dataframe(df_m, use_container_width=True)

# --- 2. SAVINGS LEDGER ---
elif choice == "Savings Ledger":
    st.header("💰 Savings Contribution Ledger")
    m_data = pd.read_sql("SELECT id, name FROM members", conn)
    m_dict = dict(zip(m_data['name'], m_data['id']))
    
    with st.form("save_form"):
        name = st.selectbox("Select Member", m_data['name'])
        amt = st.number_input("Amount", min_value=0.0)
        mode = st.selectbox("Mode", ["Cash", "Mobile Money"])
        rec = st.text_input("Receipt No")
        if st.form_submit_button("Record Saving"):
            c.execute("INSERT INTO savings (member_id, date, amount, mode, receipt_no) VALUES (?,?,?,?,?)", (m_dict[name], datetime.now().date(), amt, mode, rec))
            conn.commit()
    
    df_s = pd.read_sql("SELECT s.date, m.name, s.amount, s.receipt_no FROM savings s JOIN members m ON s.member_id = m.id", conn)
    st.dataframe(df_s, use_container_width=True)

# --- 3. LOAN SYSTEM ---
elif choice == "Loan System":
    st.header("🏦 Loan Management")
    # simplified for brevity - can be expanded
    st.write("Current Total Loans Issued: UGX ", total_loans)
    df_l = pd.read_sql("SELECT * FROM loans", conn)
    st.dataframe(df_l)

# --- 4. INCOME & EXPENSES ---
elif choice == "Income & Expenses":
    st.header("💸 Group Transactions")
    t_type = st.radio("Type", ["Income", "Expense"])
    with st.form("trans_form"):
        cat = st.text_input("Category (e.g., Fines, Stationery)")
        t_amt = st.number_input("Amount", min_value=0.0)
        ref = st.text_input("Reference/Voucher No")
        if st.form_submit_button("Save Transaction"):
            c.execute("INSERT INTO transactions (type, category, amount, ref_no, date) VALUES (?,?,?,?,?)", (t_type, cat, t_amt, ref, datetime.now().date()))
            conn.commit()
    
    df_t = pd.read_sql("SELECT * FROM transactions", conn)
    st.dataframe(df_t)

# --- 5. CASH BOOK ---
elif choice == "Cash Book":
    st.header("📖 Daily Cash Position")
    st.metric("Current Cash at Hand", f"UGX {closing_balance:,.2f}")
    
    # Visual Breakdown
    st.bar_chart(pd.DataFrame({"Receipts": [receipts], "Payments": [payments]}))

# --- 6. MONTHLY SUMMARY ---
elif choice == "Monthly Summary":
    st.header("📊 Performance Report")
    summary = {
        "Description": ["Total Savings", "Loans Issued", "Repayments", "Other Income", "Expenses", "Withdrawals"],
        "Amount (UGX)": [total_savings, total_loans, total_repayments, total_income, total_expenses, total_withdrawals]
    }
    st.table(pd.DataFrame(summary))
