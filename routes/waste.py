"""Waste logging routes."""
from flask import request, jsonify
from server.database import get_connection


def get_waste():
    user_id = request.user['id']
    from_date = request.args.get('from')
    to_date = request.args.get('to')

    query = 'SELECT * FROM waste_log WHERE user_id = ?'
    params = [user_id]
    if from_date:
        query += ' AND waste_date >= ?'
        params.append(from_date)
    if to_date:
        query += ' AND waste_date <= ?'
        params.append(to_date)
    query += ' ORDER BY waste_date DESC'

    conn = get_connection()
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


def create():
    data = request.get_json(force=True, silent=True) or {}
    user_id = request.user['id']
    food_item_id = data.get('food_item_id')
    name = data.get('name')
    category = data.get('category')
    quantity = data.get('quantity')
    unit = data.get('unit')
    reason = data.get('reason')

    if not name or not category or quantity is None or not unit:
        return jsonify({'error': 'name, category, quantity, and unit are required'}), 400

    conn = get_connection()
    cur = conn.execute(
        '''INSERT INTO waste_log (user_id, food_item_id, name, category, quantity, unit, reason)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, food_item_id, name, category, float(quantity), unit, reason)
    )
    conn.commit()
    if food_item_id:
        conn.execute(
            'UPDATE food_items SET status = ? WHERE id = ? AND user_id = ?',
            ('wasted', food_item_id, user_id)
        )
        conn.commit()
    row = conn.execute('SELECT * FROM waste_log WHERE id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    return jsonify(dict(row)), 201


def clear_all():
    """Delete every waste entry for the authenticated user (test/dev helper)."""
    conn = get_connection()
    cur = conn.execute('DELETE FROM waste_log WHERE user_id = ?', (request.user['id'],))
    conn.commit()
    n = cur.rowcount
    conn.close()
    return jsonify({'ok': True, 'deleted': n})


def remove(waste_id):
    conn = get_connection()
    cur = conn.execute(
        'DELETE FROM waste_log WHERE id = ? AND user_id = ?',
        (waste_id, request.user['id'])
    )
    conn.commit()
    changes = cur.rowcount
    conn.close()
    if changes == 0:
        return jsonify({'error': 'Waste log entry not found'}), 404
    return jsonify({'ok': True})