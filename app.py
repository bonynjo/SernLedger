import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from fpdf import FPDF
import base64

# --- DATABASE SETUP ---
conn = sqlite3.connect('sern_group.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, member_no TEXT, name TEXT, phone TEXT, id_no TEXT, join_date DATE, status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS savings (id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, date DATE, amount REAL, receipt_no TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS loans (loan_id INTEGER PRIMARY KEY AUTOINCREMENT, member_id TEXT, amount REAL, interest_rate REAL, duration INTEGER, status TEXT, date_issued DATE)')
    c.execute('CREATE TABLE IF NOT EXISTS repayments (id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER, date DATE, total_paid REAL, interest_portion REAL, principal_portion REAL)')
    conn.commit()

init_db()

# --- PDF GENERATOR FUNCTION ---
def create_pdf(member_no, name, savings_df, total_savings):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "SERN SAVINGS GROUP", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, f"Official Member Statement: {datetime.now().strftime('%Y-%m-%d')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Member No: {member_no}", ln=True)
    pdf.cell(0, 10, f"Member Name: {name}", ln=True)
    pdf.cell(0, 10, f"Total Savings: UGX {total_savings:,.0f}", ln=True)
    pdf.ln(5)
    
    # Table Header
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(40, 10, "Date", 1, 0, 'C', 1)
    pdf.cell(100, 10, "Description", 1, 0, 'C', 1)
    pdf.cell(50, 10, "Amount (UGX)", 1, 1, 'C', 1)
    
    # Table Rows
    pdf.set_font("Arial", '', 10)
    for index, row in savings_df.iterrows():
        pdf.cell(40, 10, str(row['date']), 1)
        pdf.cell(100, 10, f"Savings Deposit (Ref: {row['receipt_no']})", 1)
        pdf.cell(50, 10, f"{row['amount']:,.0f}", 1, 1, 'R')
        
    return pdf.output(dest="S").encode("latin-1")

# --- UTILITY: AUTO-GENERATE MEMBER NO (YYMMNNN) ---
def generate_member_no():
    now = datetime.now()
    prefix = now.strftime("%y%m")
    c.execute("SELECT member_no FROM members WHERE member_no LIKE ? ORDER BY member_no DESC LIMIT 1", (prefix + '%',))
    last_no = c.fetchone()
    if last_no:
        seq = int(last_no[0][-3:]) + 1
    else:
        seq = 1
    return f"{prefix}{seq:03d}"

# --- INTERFACE ---
st.set_page_config(page_title="Sern Savings Group", layout="wide")
st.title("🏦 Sern Savings Group")

menu = ["Member Register", "Member Detail View", "Savings Ledger", "Loan System", "Loan Calculator"]
choice = st.sidebar.selectbox("Navigation", menu)

if choice == "Member Register":
    st.header("👥 Member Register")
    with st.form("reg_form"):
        n, p, i = st.text_input("Full Name"), st.text_input("Phone"), st.text_input("National ID")
        if st.form_submit_button("Register"):
            new_no = generate_member_no()
            c.execute("INSERT INTO members (member_no, name, phone, id_no, join_date, status) VALUES (?,?,?,?,?,?)", 
                      (new_no, n, p, i, datetime.now().date(), "Active"))
            conn.commit()
            st.success(f"Registered! Member Number: {new_no}")
    st.table(pd.read_sql("SELECT member_no, name, phone, join_date, status FROM members", conn))

elif choice == "Member Detail View":
    st.header("👤 Individual Portfolio")
    m_list = pd.read_sql("SELECT member_no, name FROM members", conn)
    if not m_list.empty:
        selected_m = st.selectbox("Select Member", m_list['member_no'] + " - " + m_list['name'])
        m_no = selected_m.split(" - ")[0]
        m_name = selected_m.split(" - ")[1]

        m_sav = pd.read_sql("SELECT SUM(amount) FROM savings WHERE member_id = ?", conn, params=(m_no,)).iloc[0,0] or 0
        hist = pd.read_sql("SELECT date, amount, receipt_no FROM savings WHERE member_id = ?", conn, params=(m_no,))
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.metric("Total Accumulated Savings", f"UGX {m_sav:,.0f}")
            st.dataframe(hist, use_container_width=True)
        
        with col2:
            st.subheader("Statement Actions")
            # PDF Download Button
            pdf_data = create_pdf(m_no, m_name, hist, m_sav)
            st.download_button(label="📥 Download PDF Statement", data=pdf_data, file_name=f"{m_no}_Statement.pdf", mime="application/pdf")
    else:
        st.warning("No members registered yet.")

elif choice == "Savings Ledger":
    st.header("💰 Savings Ledger")
    m_data = pd.read_sql("SELECT member_no, name FROM members", conn)
    with st.form("save_form"):
        m_id = st.selectbox("Member Number", m_data['member_no'])
        amt = st.number_input("Amount (UGX)", min_value=0.0)
        rec = st.text_input("Receipt Number")
        if st.form_submit_button("Record Saving"):
            c.execute("INSERT INTO savings (member_id, date, amount, receipt_no) VALUES (?,?,?,?)", (m_id, datetime.now().date(), amt, rec))
            conn.commit()
            st.success("Saving recorded successfully.")

elif choice == "Loan System":
    st.header("🏦 Loan Management")
    tab1, tab2, tab3 = st.tabs(["Issue Loan", "Record Repayment", "Loan Register"])
    
    with tab1:
        m_list = pd.read_sql("SELECT member_no, name FROM members", conn)
        with st.form("loan_issue"):
            m_id = st.selectbox("Select Member", m_list['member_no'] + " - " + m_list['name'])
            amt = st.number_input("Principal Amount", min_value=1000)
            if st.form_submit_button("Approve & Issue"):
                m_no = m_id.split(" - ")[0]
                c.execute("INSERT INTO loans (member_id, amount, interest_rate, duration, status, date_issued) VALUES (?,?,?,?,?,?)",
                          (m_no, amt, 3.5, 4, "Active", datetime.now().date()))
                conn.commit()
                st.success(f"Loan Issued to {m_no}")

    with tab2:
        # Fetch only active loans to repay
        active_loans = pd.read_sql("SELECT l.loan_id, l.member_id, m.name FROM loans l JOIN members m ON l.member_id = m.member_no WHERE l.status='Active'", conn)
        if not active_loans.empty:
            with st.form("repay_form"):
                selection = st.selectbox("Select Loan Account", active_loans['loan_id'].astype(str) + " - " + active_loans['name'])
                l_id = selection.split(" - ")[0]
                p_amt = st.number_input("Total Amount Paid (UGX)")
                # Rule: 3.5% Interest Calculation for the user to confirm
                int_suggested = p_amt * 0.035 
                int_port = st.number_input("Interest Portion", value=int_suggested)
                
                if st.form_submit_button("Save Repayment"):
                    pri_port = p_amt - int_port
                    c.execute("INSERT INTO repayments (loan_id, date, total_paid, interest_portion, principal_portion) VALUES (?,?,?,?,?)",
                              (l_id, datetime.now().date(), p_amt, int_port, pri_port))
                    conn.commit()
                    st.success("Payment recorded against Principal and Interest.")
        else:
            st.write("No active loans found.")

    with tab3:
        st.subheader("All Issued Loans")
        all_loans = pd.read_sql("SELECT * FROM loans", conn)
        st.dataframe(all_loans, use_container_width=True)

elif choice == "Loan Calculator":
    st.header("🧮 Loan Simulation (3.5% Reducing Balance)")
    calc_amt = st.number_input("Loan Amount", value=1000000)
    # Simulation Logic
    remaining = calc_amt
    sched = []
    for i in range(1, 5):
        interest = remaining * 0.035
        principal_pay = calc_amt / 4
        sched.append({"Month": i, "Principal": round(principal_pay), "Interest": round(interest), "Total": round(principal_pay + interest)})
        remaining -= principal_pay
    st.table(pd.DataFrame(sched))
