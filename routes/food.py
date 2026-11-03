"""Food pantry routes."""
from flask import request, jsonify
from server.database import get_connection, compute_status


def get_food():
    user_id = request.user['id']
    status = request.args.get('status')
    category = request.args.get('category')
    sort = request.args.get('sort', 'expiry')

    query = 'SELECT * FROM food_items WHERE user_id = ?'
    params = [user_id]
    if status:
        query += ' AND status = ?'
        params.append(status)
    if category:
        query += ' AND category = ?'
        params.append(category)

    order_map = {
        'expiry': 'expiry_date ASC',
        'name': 'name ASC',
        'purchased': 'purchase_date DESC',
        'created': 'created_at DESC',
    }
    query += ' ORDER BY ' + order_map.get(sort, 'expiry_date ASC')

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


def get_one(item_id):
    conn = get_connection()
    row = conn.execute(
        'SELECT * FROM food_items WHERE id = ? AND user_id = ?',
        (item_id, request.user['id'])
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Food item not found'}), 404
    return jsonify(dict(row))


def create():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name')
    category = data.get('category')
    quantity = data.get('quantity')
    unit = data.get('unit')
    purchase_date = data.get('purchase_date')
    expiry_date = data.get('expiry_date')
    location = data.get('location', 'fridge')
    notes = data.get('notes')

    if not name or not category or quantity is None or not unit or not purchase_date or not expiry_date:
        return jsonify({
            'error': 'name, category, quantity, unit, purchase_date, and expiry_date are required'
        }), 400

    status = compute_status(expiry_date, data.get('status'))
    conn = get_connection()
    cur = conn.execute(
        '''INSERT INTO food_items
           (user_id, name, category, quantity, unit, purchase_date, expiry_date, location, notes, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (request.user['id'], name, category, float(quantity), unit, purchase_date,
         expiry_date, location, notes, status)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM food_items WHERE id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


def update(item_id):
    conn = get_connection()
    existing = conn.execute(
        'SELECT * FROM food_items WHERE id = ? AND user_id = ?',
        (item_id, request.user['id'])
    ).fetchone()
    if not existing:
        conn.close()
        return jsonify({'error': 'Food item not found'}), 404

    data = request.get_json(force=True, silent=True) or {}
    existing = dict(existing)
    name = data.get('name') or existing['name']
    category = data.get('category') or existing['category']
    quantity = float(data['quantity']) if data.get('quantity') is not None else existing['quantity']
    unit = data.get('unit') or existing['unit']
    purchase_date = data.get('purchase_date') or existing['purchase_date']
    expiry_date = data.get('expiry_date') or existing['expiry_date']
    location = data.get('location') or existing['location']
    notes = data.get('notes') if data.get('notes') is not None else existing['notes']
    # 'wasted' outlives the item it came from, so it survives an edit that says
    # nothing about status. Otherwise fixing a typo on something you already
    # logged would put it back on the shelf.
    requested = data.get('status') or ('wasted' if existing['status'] == 'wasted' else None)
    status = compute_status(expiry_date, requested)

    conn.execute(
        '''UPDATE food_items SET name=?, category=?, quantity=?, unit=?,
           purchase_date=?, expiry_date=?, location=?, notes=?, status=?
           WHERE id=? AND user_id=?''',
        (name, category, quantity, unit, purchase_date, expiry_date,
         location, notes, status, item_id, request.user['id'])
    )
    conn.commit()
    row = conn.execute('SELECT * FROM food_items WHERE id = ?', (item_id,)).fetchone()
    conn.close()
    return jsonify(dict(row))


def clear_all():
    """Delete every food item for the authenticated user (test/dev helper)."""
    conn = get_connection()
    cur = conn.execute('DELETE FROM food_items WHERE user_id = ?', (request.user['id'],))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return jsonify({'ok': True, 'deleted': n})


def remove(item_id):
    conn = get_connection()
    cur = conn.execute(
        'DELETE FROM food_items WHERE id = ? AND user_id = ?',
        (item_id, request.user['id'])
    )
    conn.commit()
    changes = cur.rowcount
    conn.close()
    if changes == 0:
        return jsonify({'error': 'Food item not found'}), 404
    return jsonify({'ok': True})