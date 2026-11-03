"""AI recipe generation from pantry items.

Recipes come exclusively from Gemini AI (routes/gemini_recipes.py) — there is
no curated-template fallback. If Gemini is unavailable the endpoints return an
empty list with an explanatory message instead of silently substituting
canned recipes.
"""
import json
from flask import request, jsonify
from server.database import get_connection
from routes.gemini_recipes import generate_recipes as gemini_generate

_TIER_FOR_PRICE = lambda p: max(1, min(5, int(round(p / 1.5))))

NO_KEY_MESSAGE = (
    'AI recipe generation needs the GEMINI_API_KEY environment variable. '
    'Add it in Render → Environment and redeploy.'
)


def _pantry_items(include_expiring_only=False):
    """Fetch the current user's pantry items."""
    conn = get_connection()
    if include_expiring_only:
        rows = conn.execute(
            """SELECT id, name, category, quantity, unit, expiry_date, status
               FROM food_items
               WHERE user_id = ? AND status IN ('expiring', 'expired')
               ORDER BY expiry_date ASC""",
            (request.user['id'],)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, name, category, quantity, unit, expiry_date, status
               FROM food_items
               WHERE user_id = ?
               ORDER BY expiry_date ASC""",
            (request.user['id'],)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _validate(raw, items):
    """Keep only Gemini recipes that actually use items the user has."""
    pantry_names = {i['name'].lower() for i in items}
    recipes = []
    seen_titles = set()
    for r in raw:
        if not isinstance(r, dict):
            continue
        name = (r.get('name') or '').strip()
        if not name or name.lower() in seen_titles:
            continue
        uses = [u.lower() for u in r.get('uses', []) if isinstance(u, str)]
        # Every recipe must use at least one exact pantry item name
        matched_uses = [
            u for u in uses
            if any(u == n or u in n or n in u for n in pantry_names)
        ]
        if not matched_uses:
            continue

        try:
            price = float(r.get('price', 3.0))
        except (TypeError, ValueError):
            price = 3.0
        price = max(1.0, min(6.0, price))
        try:
            prep = int(r.get('prep', 30))
        except (TypeError, ValueError):
            prep = 30

        matched_items = []
        for u in uses:
            for item in items:
                if item['name'].lower() == u or u in item['name'].lower():
                    if item not in matched_items:
                        matched_items.append(item)
                    break

        seen_titles.add(name.lower())
        recipes.append({
            "name": name,
            "description": r.get('desc', ''),
            "ingredients": r.get('ingredients') or [i['name'] for i in matched_items[:4]],
            "price": f"${price:.2f}",
            "tier": _TIER_FOR_PRICE(price),
            "details": [d for d in r.get('details', []) if isinstance(d, str)][:4],
            "instructions": [s for s in r.get('instructions', []) if isinstance(s, str)][:8],
            "pantry_items": [i['name'] for i in matched_items[:4]],
            "prep_time": prep,
        })

    return recipes


def _uncovered_items(existing_titles):
    """Pantry item names that appear in none of the user's saved recipes."""
    conn = get_connection()
    rows = conn.execute(
        'SELECT name FROM food_items WHERE user_id = ?', (request.user['id'],)
    ).fetchall()
    conn.close()
    names = [r['name'] for r in rows]
    if not names or not existing_titles:
        return []
    haystack = ' || '.join(existing_titles).lower()
    seen = set()
    unique = []
    for n in names:
        key = n.lower()
        if key not in seen:
            seen.add(key)
            unique.append(n)
    return [n for n in unique if n.lower() not in haystack][:6]


def ai_generate():
    """Generate (without saving) AI recipe suggestions for the pantry.

    Prefers items nearing expiry; falls back to the whole pantry if nothing
    is expiring. AI-only: no template fallback.
    """
    items = _pantry_items(include_expiring_only=True) or _pantry_items()
    if not items:
        return jsonify({'recipes': [], 'message': 'Add some pantry items first'})

    recipes = _validate(gemini_generate(items, count=8), items)
    if not recipes:
        return jsonify({'recipes': [], 'message': NO_KEY_MESSAGE})
    return jsonify({'recipes': recipes})


def ai_generate_save():
    """Generate AI recipes from ALL inventory items and save them.

    Main endpoint for the Recipes tab. Deduplicates on save: titles the user
    already has are skipped, so repeated clicks add new dishes instead of
    stacking copies. Items missing from every saved recipe are passed to the
    model as a priority hint so newly added ingredients (e.g. potato) are
    actually used. AI-only: no template fallback.
    """
    items = _pantry_items()
    if not items:
        return jsonify({'recipes': [], 'message': 'No pantry items found'})

    # Existing titles: used both for dedupe and to steer the model toward
    # uncovered ingredients.
    conn = get_connection()
    existing_rows = conn.execute(
        'SELECT title FROM recipes WHERE user_id = ?', (request.user['id'],)
    ).fetchall()
    conn.close()
    existing_titles = {r['title'].strip().lower() for r in existing_rows}
    uncovered = _uncovered_items(list(existing_titles))

    generated = _validate(
        gemini_generate(items, count=8, uncovered=uncovered), items
    )
    if not generated:
        return jsonify({'recipes': [], 'message': NO_KEY_MESSAGE})

    saved_recipes = []
    skipped = 0
    for r in generated:
        if r['name'].strip().lower() in existing_titles:
            skipped += 1
            continue
        existing_titles.add(r['name'].strip().lower())

        ingredients = r.get('ingredients') or r.get('pantry_items', [])
        instructions = r.get('instructions', [])
        if isinstance(instructions, list):
            instructions = '\n'.join(instructions)

        conn = get_connection()
        cur = conn.execute(
            'INSERT INTO recipes (user_id, title, ingredients, instructions, prep_time) VALUES (?, ?, ?, ?, ?)',
            (request.user['id'], r['name'], json.dumps(ingredients), instructions, r['prep_time'])
        )
        conn.commit()
        row = conn.execute('SELECT * FROM recipes WHERE id = ?', (cur.lastrowid,)).fetchone()
        conn.close()

        saved_recipes.append({
            'id': row['id'],
            'title': row['title'],
            'ingredients': ingredients,
            'instructions': instructions,
            'prep_time': r['prep_time'],
            'price': r.get('price', 3.0),
        })

    message = None
    if not saved_recipes and skipped:
        message = ('You already have every recipe AI suggested — add new pantry '
                   'items or delete a few recipes, then generate again.')

    return jsonify({
        'recipes': saved_recipes,
        'count': len(saved_recipes),
        'skipped_duplicates': skipped,
        'message': message,
    })
