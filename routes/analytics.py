"""Analytics and dashboard routes.

Serves both the simple dashboard overview and the rich aggregates that feed
the bento analytics cards (trend line, inventory waves, category treemap,
seasonality radar). Status semantics here match compute_status() in
server/database.py and getStatus() in public/js/app.js.
"""
from datetime import date, datetime, timedelta
from flask import request, jsonify
from server.database import get_connection

CATEGORY_COLORS = {
    'fruits':     {'color': '#FF6B3D', 'ink': 'light'},
    'vegetables': {'color': '#7CFF5B', 'ink': 'dark'},
    'dairy':      {'color': '#FFD23F', 'ink': 'dark'},
    'meat':       {'color': '#FF3DA5', 'ink': 'light'},
    'grains':     {'color': '#FFB800', 'ink': 'dark'},
    'beverages':  {'color': '#22D3EE', 'ink': 'dark'},
    'snacks':     {'color': '#8B3DFF', 'ink': 'light'},
    'other':      {'color': '#9FB3A8', 'ink': 'dark'},
}
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _pct(cur, prev):
    """Format a delta percentage; None when there is no baseline."""
    if not prev:
        return None
    return f"{abs(cur - prev) / prev * 100:.1f}%"


def _day_series(rows, days, offset=0):
    """Daily sums of waste rows over `days` days ending `offset` days ago."""
    today = date.today()
    start = today - timedelta(days=days - 1 + offset)
    buckets = {start + timedelta(days=i): 0.0 for i in range(days)}
    for r in rows:
        d = datetime.strptime(r['waste_date'][:10], '%Y-%m-%d').date()
        if start <= d < start + timedelta(days=days):
            buckets[d] += r['quantity']
    return buckets


def _window_sum(rows, days, offset=0):
    today = date.today()
    lo = today - timedelta(days=days - 1 + offset)
    hi = today - timedelta(days=offset)
    return sum(r['quantity'] for r in rows
               if lo <= datetime.strptime(r['waste_date'][:10], '%Y-%m-%d').date() <= hi)


def _entries(rows, days, offset=0):
    today = date.today()
    lo = today - timedelta(days=days - 1 + offset)
    hi = today - timedelta(days=offset)
    return sum(1 for r in rows
               if lo <= datetime.strptime(r['waste_date'][:10], '%Y-%m-%d').date() <= hi)


def get_stats():
    user_id = request.user['id']
    conn = get_connection()

    # ---- Overview (dashboard) — status derived from dates, not the stored flag,
    # so it stays correct even for rows created before status was computed.
    food = conn.execute(
        'SELECT name, category, quantity, unit, purchase_date, expiry_date, status '
        'FROM food_items WHERE user_id = ?', (user_id,)
    ).fetchall()
    rows = conn.execute(
        'SELECT category, quantity, unit, waste_date, reason FROM waste_log '
        'WHERE user_id = ?', (user_id,)
    ).fetchall()
    recent_waste = conn.execute(
        'SELECT * FROM waste_log WHERE user_id = ? ORDER BY waste_date DESC LIMIT 5',
        (user_id,)
    ).fetchall()
    conn.close()

    today = date.today()
    live = [f for f in food if f['status'] != 'wasted']
    fresh_items = sum(1 for f in live if f['expiry_date'] > str(today + timedelta(days=3)))
    expiring_soon = sum(1 for f in live
                        if str(today) <= f['expiry_date'] <= str(today + timedelta(days=3)))

    # ---- Card A: waste trend, last 30 days (previous 30 as baseline)
    buckets = _day_series(rows, 30)
    trend_total = sum(buckets.values())
    trend_prev = _window_sum(rows, 30, offset=30)
    trend = {
        'points': [{'label': f"{MONTHS[d.month - 1]} {d.day}", 'value': round(v, 1)}
                   for d, v in buckets.items()],
        'total': round(trend_total, 1),
        'delta': _pct(trend_total, trend_prev),
        'up': trend_total > trend_prev,
        'worse': trend_total > trend_prev,
        'entries': _entries(rows, 30),
        'prevTotal': round(trend_prev, 1),
    }

    # ---- Card B: pantry inventory waves, last 14 days + prior 14
    inv_days, in_date, past, in_prev, past_prev, inv_labels = 14, [], [], [], [], []
    for window_off in (0, 14):
        for i in range(inv_days - 1, -1, -1):
            d = str(today - timedelta(days=i + window_off))
            bought = [f for f in food if f['status'] != 'wasted' and f['purchase_date'] <= d]
            good = sum(1 for f in bought if f['expiry_date'] >= d)
            if window_off == 0:
                in_date.append(good)
                past.append(len(bought) - good)
                inv_labels.append(
                    f"{MONTHS[int(d[5:7]) - 1]} {int(d[8:10])}")
            else:
                in_prev.append(good)
                past_prev.append(len(bought) - good)
    inventory = {
        'labels': inv_labels,
        'inDate': in_date, 'past': past,
        'inDatePrev': in_prev, 'pastPrev': past_prev,
        'today': in_date[-1] if in_date else 0,
        'delta': _pct(in_date[-1] if in_date else 0, in_prev[-1] if in_prev else 0),
        'up': (in_date[-1] > in_prev[-1]) if in_prev and in_date else False,
        'worse': (in_prev[-1] - in_date[-1]) > 0 if in_prev and in_date else False,
    }

    # ---- Card C: waste by category, treemap over 3 periods
    weekly = _day_series(rows, 7)
    week_total = sum(weekly.values())
    month_total = _window_sum(rows, 30)
    all_total = sum(r['quantity'] for r in rows)
    cats = {}
    for r in rows:
        d = datetime.strptime(r['waste_date'][:10], '%Y-%m-%d').date()
        slot = cats.setdefault(r['category'], [0.0, 0.0, 0.0])
        slot[2] += r['quantity']
        if d >= today - timedelta(days=6):
            slot[0] += r['quantity']
        if d >= today - timedelta(days=29):
            slot[1] += r['quantity']
    week_prev = _window_sum(rows, 7, offset=7)
    month_prev = _window_sum(rows, 30, offset=30)
    year_ago = str(today - timedelta(days=365))
    prev_year_total = sum(r['quantity'] for r in rows if r['waste_date'][:10] < year_ago)
    def period(label, cur, prev, compare):
        return {'label': label, 'total': round(cur, 1), 'delta': _pct(cur, prev),
                'up': bool(prev and cur > prev), 'worse': bool(prev and cur > prev),
                'compare': compare}

    def baseline(prev, span):
        """Comparison line for a period. Says "nothing last week" rather than
        "vs 0.0 last week", which reads as a collapse to zero rather than
        an absence of history."""
        return f"vs {round(prev, 1)} {span}" if prev else f"nothing {span}"

    categories = {
        'periods': [
            period('Weekly', week_total, week_prev, baseline(week_prev, 'last week')),
            period('Monthly', month_total, month_prev, baseline(month_prev, 'last month')),
            period('All time', all_total, None, 'every entry ever logged'),
        ],
        'items': [{'name': name, 'group': name, 'values': [round(v, 1) for v in vals]}
                  for name, vals in sorted(cats.items(), key=lambda kv: -kv[1][2])],
        'groups': [{'id': k, 'name': k.capitalize(), **v}
                   for k, v in CATEGORY_COLORS.items()],
    }

    # ---- Card D: seasonality radar, this year vs last
    this_year, last_year = today.year, today.year - 1
    month_totals = {y: [0.0] * 12 for y in (this_year, last_year)}
    month_entries = {y: [0] * 12 for y in (this_year, last_year)}
    year_cats = {y: {} for y in (this_year, last_year)}
    for r in rows:
        d = datetime.strptime(r['waste_date'][:10], '%Y-%m-%d')
        if d.year in month_totals:
            month_totals[d.year][d.month - 1] += r['quantity']
            month_entries[d.year][d.month - 1] += 1
            year_cats[d.year][r['category']] = year_cats[d.year].get(r['category'], 0) + r['quantity']
    years = []
    for y, label in ((this_year, str(this_year)), (last_year, str(last_year))):
        vals = month_totals[y]
        total = sum(vals)
        elapsed = today.month if y == this_year else 12
        avg = total / elapsed if elapsed else 0
        # Compare whole months only, so a month in progress never reads as a collapse.
        last_full = today.month - 2 if y == this_year else None
        cur_m = vals[last_full] if last_full is not None and last_full >= 0 else None
        prev_m = vals[last_full - 1] if last_full is not None and last_full >= 1 else None
        prev_year_same = sum(month_totals.get(y - 1, [0] * 12)[:elapsed]) if y - 1 in month_totals else None
        top = sorted(year_cats[y].items(), key=lambda kv: -kv[1])[:3]
        years.append({
            'label': label,
            'values': [round(v, 1) for v in vals],
            'stats': [
                {'label': 'Monthly avg', 'value': round(avg, 1),
                 'delta': _pct(cur_m, prev_m) if cur_m is not None else None,
                 'up': bool(cur_m is not None and prev_m is not None and cur_m > prev_m),
                 'worse': bool(cur_m is not None and prev_m is not None and cur_m > prev_m),
                 'note': f"{sum(month_entries[y])} entries"},
                {'label': 'Year total', 'value': round(total, 1),
                 'delta': _pct(total, prev_year_same) if prev_year_same else None,
                 'up': bool(prev_year_same and total > prev_year_same),
                 'worse': bool(prev_year_same and total > prev_year_same),
                 'note': f"across {sum(1 for v in vals if v)} active months"},
            ],
            'rows': [{'label': name.capitalize(), 'value': f"{val:.1f}"}
                     for name, val in top],
        })
    seasonality = {'years': years}

    # Waste-by-category rows for the dashboard's bar list (kept for compatibility)
    grouped = {}
    for r in rows:
        key = (r['category'], r['unit'])
        grouped[key] = grouped.get(key, 0) + r['quantity']
    waste_by_category = [
        {'category': c, 'unit': u, 'total_quantity': round(q, 1)}
        for (c, u), q in sorted(grouped.items(), key=lambda kv: -kv[1])
    ]

    unit_counts = {}
    for r in rows:
        unit_counts[r['unit']] = unit_counts.get(r['unit'], 0) + 1
    unit_mode = max(unit_counts, key=unit_counts.get) if unit_counts else 'kg'

    return jsonify({
        'overview': {
            'totalItems': len(food),
            'freshItems': fresh_items,
            'expiringSoon': expiring_soon,
            'wastedItems': sum(1 for r in rows),
        },
        'wasteByCategory': waste_by_category,
        'recentWaste': [dict(r) for r in recent_waste],
        'bento': {
            'unit': unit_mode,
            'trend': trend,
            'inventory': inventory,
            'categories': categories,
            'seasonality': seasonality,
        },
    })
