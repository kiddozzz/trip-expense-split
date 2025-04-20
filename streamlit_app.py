import streamlit as st
import pandas as pd
import json
from io import BytesIO
from collections import defaultdict
from datetime import date
import openpyxl
import os

# Function to load expenses from JSON file
def load_expenses(report_name="default"):
    filename = f"expenses_{report_name}.json"
    try:
        with open(filename, "r") as f:
            data = json.load(f)
            expenses = data.get("expenses", [])
            for expense in expenses:
                if isinstance(expense['date'], str):
                    expense['date'] = date.fromisoformat(expense['date'])
            participants = data.get("participants", [])
            return expenses, participants
    except FileNotFoundError:
        return [], []
    except Exception as e:
        st.error(f"Error loading expenses: {e}")
        return [], []

# Function to save expenses to JSON file
def save_expenses(expenses, report_name="default", participants=None):
    filename = f"expenses_{report_name}.json"
    expenses_serializable = []
    for expense in expenses:
        expense_copy = expense.copy()
        if isinstance(expense_copy['date'], date):
            expense_copy['date'] = expense_copy['date'].isoformat()
        expenses_serializable.append(expense_copy)
    try:
        with open(filename, "w") as f:
            json.dump({
                "participants": participants or [],
                "expenses": expenses_serializable
            }, f, indent=4)
    except Exception as e:
        st.error(f"Error saving expenses: {e}")

st.set_page_config(page_title="Trip Expense Splitter", layout="wide")
if "editing_index" not in st.session_state:
    st.session_state.editing_index = None
st.title("✈️ Trip Expense Sharing Agent")

st.markdown("#### 🗂️ Manage Reports")

if "available_reports" not in st.session_state:
    report_files = [f for f in os.listdir() if f.startswith("expenses_") and f.endswith(".json")]
    reports = [f[len("expenses_"):-len(".json")] for f in report_files]
    st.session_state.available_reports = sorted(reports)  # No default manually added

# Select or create a report


# If no report is selected yet, don't show any selection
selected_report = st.selectbox(
    "Choose an expense report",
    options=st.session_state.available_reports,
    index=None,
    placeholder="Select an expense report"
)

# If user selected a new report, update and rerun immediately
if selected_report:
    st.session_state.current_report = selected_report
    st.session_state.expenses, st.session_state.participants = load_expenses(selected_report)
    # rest of your logic here

new_report = st.text_input("Create a new report", "")

if new_report.strip() and new_report.strip() not in st.session_state.available_reports:
    #if st.button("➕ Create and Switch to New Report"):
        new_report = new_report.strip()
        st.session_state.expenses = []
        st.session_state.participants = []
        st.session_state.available_reports.append(new_report)
        st.session_state.current_report = new_report
        st.rerun()
    
# Save report manually with the name provided or selected
if st.button("💾 Save Expense Report"):
    target_report = new_report.strip() if new_report.strip() else selected_report
    if target_report not in st.session_state.available_reports:
        st.session_state.available_reports.append(target_report)
    save_expenses(st.session_state.expenses, target_report, st.session_state.participants)
    st.success(f"Report saved as '{target_report}'")


st.markdown("Enter the details of each expense below:")

# Step 1: Get participant list
# Load selected report data if necessary
if (
    "expenses" not in st.session_state or
    st.session_state.get("current_report") != selected_report
):
    st.session_state.expenses, st.session_state.participants = load_expenses(selected_report)
    st.session_state.current_report = selected_report

# Ensure participants exist
current_names = ", ".join(st.session_state.participants) if st.session_state.participants else ""

participants_input = st.text_input("Enter participant names (comma-separated)", current_names)
participant_list = [p.strip() for p in participants_input.split(",") if p.strip()]
st.session_state.participants = participant_list
st.markdown("---")

# Load expenses from file or session state
if "expenses" not in st.session_state or st.session_state.get("current_report") != selected_report:
    st.session_state.expenses, st.session_state.participants = load_expenses(selected_report)
    st.session_state.current_report = selected_report
else:
    #If expenses are in session state, it means the user has added/removed
    #something, so we don't want to override.
    pass

# Add expense form
with st.form("expense_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        item = st.text_input("Item (e.g. Lunch, Taxi)", "")
    with col2:
        payer = st.selectbox("Who paid?", participant_list)
    with col3:
        amount = st.number_input("Amount", min_value=0.01, format="%.2f")

    date_col, shared_col = st.columns([1, 3])
    with date_col:
        expense_date = st.date_input("Date", value=date.today())
    with shared_col:
        shared_options = ["All"] + participant_list
        shared_by_raw = st.multiselect("Shared among", shared_options, default=["All"])
        if "All" in shared_by_raw:
            shared_by = participant_list  # Select everyone if "All" is picked
        else:
            shared_by = shared_by_raw

    submitted = st.form_submit_button("Add Expense")
    if submitted and item:
        st.session_state.expenses.append({
            "item": item,
            "payer": payer,
            "amount": amount,
            "shared_by": shared_by,
            "date": expense_date  # Store as date object
        })
        save_expenses(st.session_state.expenses, selected_report) # Save after adding

# Show current expenses
if st.session_state.expenses:
    st.markdown("### 📋 Current Expenses")

    exp_table_data = []
    for i, e in enumerate(st.session_state.expenses):
        exp_table_data.append({
            "Date": e["date"],
            "Item": e["item"],
            "Paid By": e["payer"],
            "Amount": e["amount"],
            "Shared By": ", ".join(e["shared_by"]),
            "Remove": f"Remove_{i}"
        })

    exp_df = pd.DataFrame(exp_table_data)
    for idx, row in exp_df.iterrows():
        is_editing = st.session_state.editing_index == idx

        col1, col2, col3, col4, col5, col6, col7 = st.columns([1.2, 2, 1.2, 1.2, 2.5, 1, 1])

        if is_editing:
            # Editable form
            with col1:
                edited_date = st.date_input(f"Edit Date {idx}", value=row["Date"], key=f"edit_date_{idx}")
            with col2:
                edited_item = st.text_input(f"Edit Item {idx}", value=row["Item"], key=f"edit_item_{idx}")
            with col3:
                edited_payer = st.selectbox(f"Edit Payer {idx}", participant_list, index=participant_list.index(row["Paid By"]), key=f"edit_payer_{idx}")
            with col4:
                edited_amount = st.number_input(f"Edit Amount {idx}", min_value=0.01, value=row["Amount"], format="%.2f", key=f"edit_amount_{idx}")
            with col5:
                shared_options = ["All"] + participant_list
                default_shared = participant_list if set(row["Shared By"].split(", ")) == set(participant_list) else row["Shared By"].split(", ")
                edited_shared_by_raw = st.multiselect(f"Edit Shared {idx}", shared_options, default=default_shared, key=f"edit_shared_{idx}")
                edited_shared_by = participant_list if "All" in edited_shared_by_raw else edited_shared_by_raw
            with col6:
                if st.button("💾 Save", key=f"save_{idx}"):
                    st.session_state.expenses[idx] = {
                        "item": edited_item,
                        "payer": edited_payer,
                        "amount": edited_amount,
                        "shared_by": edited_shared_by,
                        "date": edited_date
                    }
                    st.session_state.editing_index = None
                    save_expenses(st.session_state.expenses, selected_report)
                    st.rerun()
            with col7:
                if st.button("❌ Cancel", key=f"cancel_{idx}"):
                    st.session_state.editing_index = None
                    st.rerun()
        else:
            # Regular display mode
            with col1: st.write(row["Date"])
            with col2: st.write(row["Item"])
            with col3: st.write(row["Paid By"])
            with col4: st.write(f"${row['Amount']:.2f}")
            with col5: st.write(row["Shared By"])
            with col6:
                if st.button("✏️", key=f"edit_{idx}", help="Edit this expense"):
                    st.session_state.editing_index = idx
                    st.rerun()
            with col7:
                if st.button("🗑️", key=f"remove_{idx}", help="Remove this expense"):
                    st.session_state.expenses.pop(idx)
                    save_expenses(st.session_state.expenses, selected_report)
                    st.rerun()


    # Step 2: Calculate balances
    balances = defaultdict(float)
    for exp in st.session_state.expenses:
        per_person = exp["amount"] / len(exp["shared_by"])
        for person in exp["shared_by"]:
            balances[person] -= per_person
        balances[exp["payer"]] += exp["amount"]

    def simplify_debts(balances):
        balance_items = sorted(balances.items(), key=lambda x: x[1])
        settlements = []
        i, j = 0, len(balance_items) - 1
        while i < j:
            debtor, debt_amt = balance_items[i]
            creditor, cred_amt = balance_items[j]
            settled_amt = min(-debt_amt, cred_amt)
            if settled_amt > 0.01:
                settlements.append((debtor, creditor, round(settled_amt, 2)))
                balance_items[i] = (debtor, debt_amt + settled_amt)
                balance_items[j] = (creditor, cred_amt - settled_amt)
                if balance_items[i][1] >= -0.01: i += 1
                if balance_items[j][1] <= 0.01: j -= 1
            else:
                break
        return settlements

    settlements = simplify_debts(balances)

    st.markdown("### 💸 Settlement Summary")
    if settlements:
        for s in settlements:
            st.markdown(f"- **{s[0]}** pays **${s[2]:.2f}** to **{s[1]}**")
    else:
        st.success("Everyone is settled up! 🎉")

    # Step 3: Generate Excel
    def to_excel(expenses, settlements, balances):
        output = BytesIO()

        # Step 1: Calculate total paid and total share per person
        total_paid = defaultdict(float)
        total_share = defaultdict(float)

        for exp in expenses:
            per_person_share = exp["amount"] / len(exp["shared_by"])
            for person in exp["shared_by"]:
                total_share[person] += per_person_share
            total_paid[exp["payer"]] += exp["amount"]

        # Step 2: Construct participant-level summary table
        all_participants = set(total_paid.keys()) | set(total_share.keys()) | set(balances.keys())
        settlement_summary = pd.DataFrame([
            {
                "Participant": p,
                "Total Paid": round(total_paid[p], 2),
                "Share of Expenses": round(total_share[p], 2),
                "Net Balance": round(balances[p], 2)
            }
            for p in sorted(all_participants)
        ])

        # Step 3: Write to Excel
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Detailed Expenses Sheet
            expenses_for_excel = []
            for e in expenses:
                e_copy = e.copy()
                if isinstance(e_copy['date'], date):
                    e_copy['date'] = e_copy['date'].isoformat()
                expenses_for_excel.append(e_copy)
            pd.DataFrame(expenses_for_excel).to_excel(writer, sheet_name="Detailed Expenses", index=False)

            # Pairwise Settlements Sheet (optional)
            pd.DataFrame(settlements, columns=["From", "To", "Amount"]).to_excel(writer, sheet_name="Settlement Details", index=False)

            # Summary Sheet
            settlement_summary.to_excel(writer, sheet_name="Settlement", index=False)

        output.seek(0)
        return output

    excel_data = to_excel(st.session_state.expenses, settlements, balances)

    st.download_button(
        label="📥 Download Excel Report",
        data=excel_data,
        file_name="trip_expense_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Add at least one expense to get started.")
