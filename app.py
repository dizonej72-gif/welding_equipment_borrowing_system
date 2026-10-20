from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'welding_borrowing_secret_key'

# Inventory List (17 Items)
inventory = [
    {"id": 1, "name": "SMAW Welding Machine", "available_qty": 50},
    {"id": 2, "name": "TIG Welding Torch", "available_qty": 30},
    {"id": 3, "name": "Auto-Darkening Helmet", "available_qty": 50},
    {"id": 4, "name": "Welding Gloves (Pair)", "available_qty": 120},
    {"id": 5, "name": "Welding Apron", "available_qty": 80},
    {"id": 6, "name": "Wire Extension Cord", "available_qty": 80},
    {"id": 7, "name": "Oxy-Acetylene Cutting Set", "available_qty": 80},
    {"id": 8, "name": "Plasma Cutter", "available_qty": 80},
    {"id": 9, "name": "MIG Welding Torch", "available_qty": 80},
    {"id": 10, "name": "Electrode Holder", "available_qty": 80},
    {"id": 11, "name": "Ground Clamp & Cable", "available_qty": 80},
    {"id": 12, "name": "Oxygen Regulator", "available_qty": 80},
    {"id": 13, "name": "Acetylene Regulator", "available_qty": 80},
    {"id": 14, "name": "Welding Goggles", "available_qty": 80},
    {"id": 15, "name": "Chipping Hammer", "available_qty": 80},
    {"id": 16, "name": "Wire Brush", "available_qty": 80},
    {"id": 17, "name": "Welding Electrodes", "available_qty": 80}
]

borrowed_records = []
record_id_counter = 1

ADMIN_USER = "supervisor"
ADMIN_PASS = "welding123"

@app.route('/')
def home():
    session.pop('logged_in', None)
    session.pop('admin_name', None)
    
    today_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template('inventory.html', inventory=inventory, records=borrowed_records, today_str=today_str)

@app.route('/api/inventory_data')
def api_inventory_data():
    today_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return jsonify({
        "inventory": inventory,
        "records": borrowed_records,
        "today_str": today_str
    })

@app.route('/request_borrow/<int:item_id>', methods=['POST'])
def request_borrow(item_id):
    global record_id_counter
    borrower_name = request.form.get('borrower_name')
    position = request.form.get('position')
    requested_qty = int(request.form.get('requested_qty', 1))
    return_datetime = request.form.get('return_datetime')

    item = next((i for i in inventory if i["id"] == item_id), None)

    if item and item["available_qty"] >= requested_qty:
        formatted_return = return_datetime.replace('T', ' ') if return_datetime else ''
        
        record = {
            "id": record_id_counter,
            "borrower_name": borrower_name,
            "position": position,
            "item_name": item["name"],
            "item_id": item["id"],
            "requested_qty": requested_qty,
            "borrow_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "approved_at_iso": None,
            "expected_return_date": formatted_return,
            "status": "Pending Approval"
        }
        borrowed_records.append(record)
        record_id_counter += 1
        flash(f'Borrow request for {requested_qty}x {item["name"]} submitted successfully!', 'info')
    else:
        flash('Requested quantity exceeds available stock!', 'danger')

    return redirect(url_for('home'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('view_records'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            session['admin_name'] = username
            flash('Successfully logged in as Supervisor!', 'success')
            return redirect(url_for('view_records'))
        else:
            flash('Invalid username or password!', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('admin_name', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/records')
def view_records():
    if not session.get('logged_in'):
        flash('Please log in as supervisor to access the dashboard.', 'warning')
        return redirect(url_for('login'))
        
    today_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return render_template('status.html', records=borrowed_records, today_str=today_str)

@app.route('/api/records')
def api_records():
    if not session.get('logged_in'):
        return jsonify({"error": "Unauthorized"}), 401
    today_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
    return jsonify({"records": borrowed_records, "today_str": today_str})

@app.route('/supervisor/approve/<int:record_id>', methods=['POST'])
def approve_request(record_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    record = next((r for r in borrowed_records if r["id"] == record_id), None)
    if record and record["status"] == "Pending Approval":
        item = next((i for i in inventory if i["id"] == record["item_id"]), None)
        
        if item and item["available_qty"] >= record["requested_qty"]:
            item["available_qty"] -= record["requested_qty"]
            record["status"] = "Approved / Borrowed"
            record["approved_at_iso"] = datetime.now().isoformat()
            flash(f'Request #{record["id"]} approved!', 'success')
        else:
            flash(f'Cannot approve. Insufficient stock for {record["item_name"]}!', 'danger')

    return redirect(url_for('view_records'))

@app.route('/supervisor/reject/<int:record_id>', methods=['POST'])
def reject_request(record_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    record = next((r for r in borrowed_records if r["id"] == record_id), None)
    if record and record["status"] == "Pending Approval":
        record["status"] = "Rejected"
        flash(f'Request #{record["id"]} has been rejected.', 'warning')

    return redirect(url_for('view_records'))

@app.route('/return/<int:record_id>', methods=['POST'])
def return_item(record_id):
    record = next((r for r in borrowed_records if r["id"] == record_id), None)
    if record and record["status"] == "Approved / Borrowed":
        item = next((i for i in inventory if i["id"] == record["item_id"]), None)
        if item:
            item["available_qty"] += record["requested_qty"]

        record["status"] = "Returned"
        flash(f'Returned {record["requested_qty"]}x {record["item_name"]} successfully!', 'info')

    if session.get('logged_in') and request.referrer and 'records' in request.referrer:
        return redirect(url_for('view_records'))
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
