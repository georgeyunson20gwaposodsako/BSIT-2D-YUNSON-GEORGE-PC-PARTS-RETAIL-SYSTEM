import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = "supersecretkey"

# === Database Configuration ===
DB_NAME = "pcstoreDB.db"


def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    # Allows access to columns by name
    conn.row_factory = sqlite3.Row
    return conn


# Original dummy data, used for initial database population
INITIAL_PC_PARTS = [
    {"name": "Intel Core i5 12400F", "category": "Processor", "price": 9500.0},
    {"name": "ASUS B660M Motherboard", "category": "Motherboard", "price": 7200.0},
    {"name": "NVIDIA RTX 3060 12GB", "category": "Graphics Card", "price": 18500.0},
    {"name": "Corsair 16GB DDR4 RAM", "category": "Memory", "price": 3200.0},
    {"name": "Samsung 1TB NVMe SSD", "category": "Storage", "price": 4400.0}
]


# === DB INITIALIZATION ===
def initial_setup():
    """Creates the necessary tables if they don't exist and populates pc_parts."""
    conn = get_db_connection()
    try:
        # 1. Create the PC_PARTS table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pc_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price REAL NOT NULL
            );
        """)

        # 2. Create the ORDERS table (NEW)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT NOT NULL,
                item TEXT NOT NULL,
                status TEXT NOT NULL
            );
        """)

        # Check if the pc_parts table is empty and populate it
        count = conn.execute('SELECT COUNT(*) FROM pc_parts').fetchone()[0]
        if count == 0:
            for part in INITIAL_PC_PARTS:
                conn.execute(
                    "INSERT INTO pc_parts (name, category, price) VALUES (?, ?, ?)",
                    (part['name'], part['category'], part['price'])
                )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database setup error: {e}")
    finally:
        conn.close()


# Run the setup when the app starts
initial_setup()


# === Helper Function (Uses DB) ===
def get_part_by_id(part_id):
    """Fetches a single part from the database by ID."""
    try:
        conn = get_db_connection()
        # Ensure part_id is treated as an integer for lookup
        part = conn.execute('SELECT * FROM pc_parts WHERE id = ?', (int(part_id),)).fetchone()
        conn.close()
        return part
    except Exception as e:
        print(f"Error fetching part by ID: {e}")
        return None


def update_order_status(order_id, status):
    """Helper function to update order status in the DB."""
    try:
        conn = get_db_connection()
        conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?",
            (status, order_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error updating order status: {e}")
    finally:
        conn.close()


# === AUTH ROUTES (Unchanged) ===

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ? AND password = ? AND role = ?",
                       (username, password, role))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('index'))
        else:
            error = "Invalid username, password, or role"

    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error = "Username already exists"
        else:
            cursor.execute("INSERT INTO user (username, password, role) VALUES (?, ?, ?)",
                           (username, password, 'customer'))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))

        conn.close()

    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# === MAIN ROUTES (Uses DB) ===

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    # FETCH ALL PARTS FROM DB
    try:
        conn = get_db_connection()
        db_parts = conn.execute('SELECT * FROM pc_parts').fetchall()
    except sqlite3.Error:
        db_parts = []
    finally:
        conn.close()

    return render_template('index.html', parts=db_parts, username=session['username'], role=session['role'])


@app.route('/home')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))

    # FETCH ALL PARTS FROM DB
    try:
        conn = get_db_connection()
        db_parts = conn.execute('SELECT * FROM pc_parts').fetchall()
    except sqlite3.Error:
        db_parts = []
    finally:
        conn.close()

    return render_template('home.html', parts=db_parts)


@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        try:
            price = float(request.form.get('price'))
        except (ValueError, TypeError):
            return redirect(url_for('add'))

        # DB INSERTION LOGIC
        try:
            conn = get_db_connection()
            conn.execute(
                "INSERT INTO pc_parts (name, category, price) VALUES (?, ?, ?)",
                (name, category, price)
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during part insertion: {e}")
        finally:
            conn.close()

        return redirect(url_for('index'))

    return render_template('add.html')


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_part(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    part = get_part_by_id(id)
    if part is None:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        try:
            price = float(request.form.get('price'))
        except (ValueError, TypeError):
            return redirect(url_for('edit_part', id=id))

        # DB UPDATE LOGIC
        try:
            conn = get_db_connection()
            conn.execute(
                "UPDATE pc_parts SET name = ?, category = ?, price = ? WHERE id = ?",
                (name, category, price, id)
            )
            conn.commit()
        except sqlite3.Error as e:
            print(f"Database error during update: {e}")
        finally:
            conn.close()

        return redirect(url_for('index'))

    # Retrieve current part data for template rendering
    current_part = get_part_by_id(id)
    return render_template('edit.html', part=current_part)


@app.route('/delete/<int:id>')
def delete(id):
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    # DB DELETE LOGIC
    try:
        conn = get_db_connection()
        conn.execute("DELETE FROM pc_parts WHERE id = ?", (id,))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error during deletion: {e}")
    finally:
        conn.close()

    return redirect(url_for('index'))


# === ORDER ROUTES (UPDATED to use DB) ===

@app.route('/admin/orders')
def admin_orders():
    if 'role' not in session or session['role'] != 'admin':
        return redirect(url_for('index'))

    # FETCH ALL ORDERS FROM DB
    try:
        conn = get_db_connection()
        # Admin views all orders
        db_orders = conn.execute('SELECT * FROM orders').fetchall()
    except sqlite3.Error:
        db_orders = []
    finally:
        conn.close()

    return render_template('admin_orders.html', orders=db_orders)


@app.route('/admin/orders/approve/<int:order_id>')
def approve_order(order_id):
    # Uses helper function to update DB
    update_order_status(order_id, 'Completed')
    return redirect(url_for('admin_orders'))


@app.route('/admin/orders/reject/<int:order_id>')
def reject_order(order_id):
    # Uses helper function to update DB
    update_order_status(order_id, 'Rejected')
    return redirect(url_for('admin_orders'))


@app.route('/orders')
def customer_orders():
    if 'role' not in session or session['role'] != 'customer':
        return redirect(url_for('index'))

    # FETCH ONLY CURRENT USER'S ORDERS FROM DB
    customer_name = session['username']
    try:
        conn = get_db_connection()
        # Customer sees only their own orders
        db_orders = conn.execute('SELECT * FROM orders WHERE customer = ?', (customer_name,)).fetchall()
    except sqlite3.Error:
        db_orders = []
    finally:
        conn.close()

    return render_template('customer_orders.html', orders=db_orders)


@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    if 'role' not in session or session['role'] != 'customer':
        return redirect(url_for('index'))

    if request.method == 'POST':
        customer = session.get('username', 'Unknown')
        part_id = request.form.get('part_id')

        # Use DB helper function to get part details
        part = get_part_by_id(part_id)

        if part:
            # DB INSERTION LOGIC (NEW)
            try:
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO orders (customer, item, status) VALUES (?, ?, ?)",
                    (customer, part['name'], 'Pending')
                )
                conn.commit()
            except sqlite3.Error as e:
                print(f"Database error during order creation: {e}")
            finally:
                conn.close()

            return redirect(url_for('customer_orders'))

    # Fetch parts list from DB for the selection dropdown
    try:
        conn = get_db_connection()
        db_parts = conn.execute('SELECT * FROM pc_parts').fetchall()
    except sqlite3.Error:
        db_parts = []
    finally:
        conn.close()

    return render_template('add_order.html', parts=db_parts)


# === RUN APP ===
if __name__ == '__main__':
    app.run(debug=True)