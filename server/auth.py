"""Authentication: JWT, register, login, and auth middleware."""
import sqlite3
import jwt
import bcrypt
from datetime import datetime, timedelta
from flask import request, jsonify
from server.database import get_connection

JWT_SECRET = 'foodwaste-dev-secret-change-in-production'
JWT_EXPIRY_DAYS = 7


def sign_token(user):
    payload = {
        'id': user['id'],
        'role': user['role'],
        'exp': datetime.utcnow() + timedelta(days=JWT_EXPIRY_DAYS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def auth_middleware(view):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else None
        if not token:
            return jsonify({'error': 'Authentication required'}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        conn = get_connection()
        user = conn.execute(
            'SELECT id, name, email, role FROM users WHERE id = ?', (payload['id'],)
        ).fetchone()
        conn.close()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        request.user = dict(user)
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper


def register():
    data = request.get_json(force=True, silent=True) or {}
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')

    if not name or not email or not password:
        return jsonify({'error': 'Name, email, and password are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    allowed_roles = ['household', 'restaurant', 'admin']
    user_role = role if role in allowed_roles else 'household'

    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    conn = get_connection()
    try:
        cur = conn.execute(
            'INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)',
            (name, email.lower(), hashed, user_role)
        )
        conn.commit()
        user = conn.execute(
            'SELECT id, name, email, role FROM users WHERE id = ?', (cur.lastrowid,)
        ).fetchone()
        conn.close()
        user = dict(user)
        return jsonify({'token': sign_token(user), 'user': user}), 201
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'Email already registered'}), 409


def login():
    data = request.get_json(force=True, silent=True) or {}
    email = data.get('email')
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    conn = get_connection()
    row = conn.execute('SELECT * FROM users WHERE email = ?', (email.lower(),)).fetchone()
    conn.close()
    if not row or not bcrypt.checkpw(password.encode('utf-8'), row['password'].encode('utf-8')):
        return jsonify({'error': 'Invalid email or password'}), 401

    safe = {'id': row['id'], 'name': row['name'], 'email': row['email'], 'role': row['role']}
    return jsonify({'token': sign_token(safe), 'user': safe})


def me():
    return jsonify(request.user)