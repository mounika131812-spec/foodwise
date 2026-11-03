"""Recipe management routes."""
import json
from datetime import date
from flask import request, jsonify
from server.database import get_connection


def get_recipes():
    conn = get_connection()
    rows = conn.execute(
        'SELECT * FROM recipes WHERE user_id = ? ORDER BY created_at DESC',
        (request.user['id'],)
    ).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try:
            d['ingredients'] = json.loads(d['ingredients'])
        except Exception:
            d['ingredients'] = []
        result.append(d)
    return jsonify(result)


def create():
    data = request.get_json(force=True, silent=True) or {}
    title = data.get('title')
    ingredients = data.get('ingredients')
    instructions = data.get('instructions')
    prep_time = data.get('prep_time')

    if not title or not ingredients or not instructions:
        return jsonify({'error': 'title, ingredients, and instructions are required'}), 400

    conn = get_connection()
    cur = conn.execute(
        'INSERT INTO recipes (user_id, title, ingredients, instructions, prep_time) VALUES (?, ?, ?, ?, ?)',
        (request.user['id'], title, json.dumps(ingredients), instructions, prep_time)
    )
    conn.commit()
    row = conn.execute('SELECT * FROM recipes WHERE id = ?', (cur.lastrowid,)).fetchone()
    conn.close()
    d = dict(row)
    try:
        d['ingredients'] = json.loads(d['ingredients'])
    except Exception:
        d['ingredients'] = []
    return jsonify(d), 201


def remove(recipe_id):
    conn = get_connection()
    cur = conn.execute(
        'DELETE FROM recipes WHERE id = ? AND user_id = ?',
        (recipe_id, request.user['id'])
    )
    conn.commit()
    changes = cur.rowcount
    conn.close()
    if changes == 0:
        return jsonify({'error': 'Recipe not found'}), 404
    return jsonify({'ok': True})
