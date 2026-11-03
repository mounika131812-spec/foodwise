"""End-to-end API test for Smart Food Waste Management Platform."""
import json
import urllib.request
import urllib.error

BASE = 'http://localhost:3000/api'
TOKEN = None
passed = 0
failed = 0


def req(method, path, data=None):
    url = f'{BASE}{path}'
    body = json.dumps(data).encode() if data is not None else None
    headers = {'Content-Type': 'application/json'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}


def check(label, ok, detail=''):
    global passed, failed
    if ok:
        passed += 1
        print(f'  PASS  {label}')
    else:
        failed += 1
        print(f'  FAIL  {label}  {detail}')


def main():
    global TOKEN

    # Public health of frontend
    status, _ = req('GET', '/../../../')  # not used; static tested below
    print('API tests:')

    # 1. Register a fresh user
    email = 'tester@example.com'
    req('DELETE', '/food/999999')  # no-op warmup
    status, data = req('POST', '/auth/register', {
        'name': 'Test User', 'email': email,
        'password': 'secret123', 'role': 'household'})
    check('register', status in (201, 409), f'status={status}')

    # 2. Login
    status, data = req('POST', '/auth/login', {'email': email, 'password': 'secret123'})
    check('login', status == 200 and 'token' in data, f'status={status}')
    TOKEN = data.get('token')
    req('DELETE', '/food/all')    # clean slate for this run
    req('DELETE', '/waste/all')   # wastedItems counts every row ever logged

    # 3. Wrong password rejected
    s2, _ = req('POST', '/auth/login', {'email': email, 'password': 'wrong'})
    check('rejects bad password', s2 == 401, f'status={s2}')

    # 4. /auth/me
    status, data = req('GET', '/auth/me')
    check('me', status == 200 and data.get('name') == 'Test User', f'status={status}')

    # 5. No token -> 401
    saved = TOKEN
    TOKEN = None
    s2, _ = req('GET', '/food')
    check('requires auth', s2 == 401, f'status={s2}')
    TOKEN = saved

    # 6. Add food items
    ids = []
    for item in [
        {'name': 'Bananas', 'category': 'fruits', 'quantity': 3, 'unit': 'pieces',
         'purchase_date': '2026-11-01', 'expiry_date': '2026-11-05', 'location': 'pantry'},
        {'name': 'Milk', 'category': 'dairy', 'quantity': 2, 'unit': 'L',
         'purchase_date': '2026-10-25', 'expiry_date': '2026-11-02', 'location': 'fridge'},
        {'name': 'Spinach', 'category': 'vegetables', 'quantity': 500, 'unit': 'g',
         'purchase_date': '2026-10-30', 'expiry_date': '2026-11-03', 'location': 'fridge'},
    ]:
        status, data = req('POST', '/food', item)
        if status == 201:
            ids.append(data['id'])
    check('create food items', len(ids) == 3, f'created={len(ids)}')

    # 7. Validation rejects bad payload
    status, _ = req('POST', '/food', {'name': 'No dates'})
    check('validates required fields', status == 400, f'status={status}')

    # 8. List food
    status, data = req('GET', '/food')
    check('list food', status == 200 and len(data) == 3, f'count={len(data)}')

    # 9. Filter by category
    status, data = req('GET', '/food?category=dairy')
    check('filter by category', status == 200 and len(data) == 1, f'count={len(data)}')

    # 10. Update food
    status, data = req('PUT', f'/food/{ids[0]}', {'notes': 'ripe ones'})
    check('update food', status == 200 and data.get('notes') == 'ripe ones', f'status={status}')

    # 11. Log waste linked to item
    status, data = req('POST', '/waste', {
        'food_item_id': ids[1], 'name': 'Milk', 'category': 'dairy',
        'quantity': 2, 'unit': 'L', 'reason': 'expired'})
    check('log waste', status == 201, f'status={status}')
    waste_id = data.get('id')

    # 12. Linked item marked wasted
    status, data = req('GET', f'/food/{ids[1]}')
    check('item marked wasted', status == 200 and data.get('status') == 'wasted',
          f"status={data.get('status')}")

    # 13. Waste list
    status, data = req('GET', '/waste')
    check('list waste', status == 200 and len(data) >= 1, f'count={len(data)}')

    # 14. Analytics
    status, data = req('GET', '/analytics')
    ov = data.get('overview', {})
    check('analytics', status == 200 and ov.get('totalItems') == 3
          and ov.get('wastedItems') == 1,
          f'data={ov}')
    check('analytics by category', len(data.get('wasteByCategory', '')) >= 1)

    # 15. Recipe CRUD
    status, data = req('POST', '/recipes', {
        'title': 'Banana Bread', 'ingredients': ['3 bananas', '2 cups flour', '1 egg'],
        'instructions': 'Mash bananas, mix, bake at 180C for 50 min.', 'prep_time': 20})
    check('create recipe', status == 201, f'status={status}')
    rid = data.get('id')

    status, data = req('GET', '/recipes')
    ok = (status == 200 and len(data) == 1
          and isinstance(data[0].get('ingredients'), list))
    check('recipe ingredients parsed', ok, f'ing={data[0].get("ingredients") if data else None}')

    # 16. AI generate + save recipes from pantry (AI-only: needs GEMINI_API_KEY,
    # otherwise the endpoint returns an explanatory message and zero recipes)
    status, data = req('POST', '/recipes/ai-generate-save')
    has_key = data.get('count', 0) > 0
    check('ai-generate-save', status == 200 and (has_key or data.get('message')),
          f'status={status}, count={data.get("count")}, msg={bool(data.get("message"))}')
    if has_key:
        ai_ids = [r['id'] for r in data['recipes']]
        # Verify saved recipes appear in GET /recipes
        status, all_recipes = req('GET', '/recipes')
        check('ai recipes saved to collection',
              status == 200 and len(all_recipes) >= data['count'],
              f'count={len(all_recipes)}')
        # Second click must not create duplicate titles
        status, again = req('POST', '/recipes/ai-generate-save')
        status, after = req('GET', '/recipes')
        titles = [r['title'].strip().lower() for r in after]
        check('no duplicate recipe titles after regeneration',
              status == 200 and len(titles) == len(set(titles)),
              f'titles={titles}')

    # 17. Delete food + recipe
    status, _ = req('DELETE', f'/food/{ids[2]}')
    check('delete food', status == 200)
    status, _ = req('DELETE', f'/recipes/{rid}')
    check('delete recipe', status == 200)
    s2, _ = req('DELETE', '/food/999999')
    check('404 on missing item', s2 == 404, f'status={s2}')

    # 18. Waste delete
    status, _ = req('DELETE', f'/waste/{waste_id}')
    check('delete waste entry', status == 200)

    print(f'\n{passed} passed, {failed} failed')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
