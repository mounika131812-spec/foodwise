# Smart Food Waste Management Platform

A full-stack web application for tracking household/restaurant food inventory,
logging waste, managing recipes, and analyzing food waste patterns — built as a
college internship project.

![Stack](https://img.shields.io/badge/backend-Flask-green)
![Frontend](https://img.shields.io/badge/frontend-HTML%20%7C%20CSS%20%7C%20JS-blue)
![Database](https://img.shields.io/badge/database-SQLite-orange)

## Features

- **User authentication** — Register / Login with JWT tokens and bcrypt-hashed passwords.
  Supports Household / Restaurant / Admin roles.
- **Smart pantry** — Track food items with category, quantity, unit, purchase and expiry dates,
  storage location, and notes. Auto-computed status badges:
  Fresh / Expiring Soon / Expired / Wasted.
- **Waste logging** — Log waste either from existing pantry items (auto-marks them
  as wasted) or via manual entry. Track reasons: expired, spoiled, overcooked, leftovers, other.
- **Recipes** — Store favorite recipes with ingredients list, instructions and prep time
  to plan meals around soon-to-expire items.
- **Analytics** — Dashboard with key stats and a bar chart of waste by category, plus a
  four-card bento view: 30-day waste trend, pantry inventory waves, a category treemap
  (weekly / monthly / all-time) and a this-year-vs-last seasonality radar. Hand-drawn SVG,
  no charting library.
- **Responsive UI** — Modern CSS Grid / Flexbox layout that works on mobile and desktop.

## Tech stack

| Layer      | Technology                         |
|------------|------------------------------------|
| Backend    | Python + Flask                     |
| Database   | SQLite (via Python's built-in `sqlite3`) |
| Auth       | JWT (PyJWT) + bcrypt               |
| Frontend   | Vanilla HTML, CSS, JavaScript      |
| No build tools, no frameworks       |

## Project structure

```
web/
├── app.py                 # Flask application entry point
├── requirements.txt       # Python dependencies
├── run.bat                # One-click launcher (Windows)
├── test.py                # End-to-end API tests
├── server/
│   ├── database.py        # SQLite schema and connection helpers
│   └── auth.py            # JWT auth, register, login, middleware
├── routes/
│   ├── food.py            # Pantry CRUD
│   ├── waste.py           # Waste log CRUD
│   ├── recipes.py         # Recipe CRUD
│   └── analytics.py       # Dashboard statistics
├── public/                # Frontend
│   ├── index.html
│   ├── css/styles.css
│   └── js/
│       ├── app.js         # Router, views, API calls
│       └── bento.js       # Bento analytics engine (SVG charts, no library)
└── data/                  # SQLite database file (created at runtime)
```

## Getting started

### Prerequisites
- Python 3.8+ installed and available on PATH

### Quick start (Windows)
Double-click `run.bat`, or run from terminal:

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:3000** in your browser.

### Manual run

```bash
# 1. Install dependencies
pip install flask pyjwt bcrypt

# 2. Start the server
python app.py

# 3. Open the app
# http://localhost:3000
```

### Running the test suite

With the server running in another terminal:

```bash
python test.py
```

Expected output: `21 passed, 0 failed`.

## API reference

All endpoints under `/api/...`. Protected routes require header
`Authorization: Bearer <token>`.

### Auth
| Method | Endpoint           | Auth | Description        |
|--------|--------------------|------|--------------------|
| POST   | `/auth/register`   | No   | Create account     |
| POST   | `/auth/login`      | No   | Get JWT token      |
| GET    | `/auth/me`         | Yes  | Current user info  |

### Food
| Method | Endpoint        | Auth | Description           |
|--------|-----------------|------|-----------------------|
| GET    | `/food`         | Yes  | List (filter by status, category, sort) |
| POST   | `/food`         | Yes  | Create item           |
| GET    | `/food/:id`     | Yes  | Get one item          |
| PUT    | `/food/:id`     | Yes  | Update item           |
| DELETE | `/food/:id`     | Yes  | Delete item           |

### Waste
| Method | Endpoint        | Auth | Description           |
|--------|-----------------|------|-----------------------|
| GET    | `/waste`        | Yes  | List (filter by date range) |
| POST   | `/waste`        | Yes  | Log waste entry       |
| DELETE | `/waste/:id`    | Yes  | Delete entry          |
| DELETE | `/waste/all`    | Yes  | Clear the log (test/dev helper) |

### Recipes
| Method | Endpoint          | Auth | Description           |
|--------|-------------------|------|-----------------------|
| GET    | `/recipes`        | Yes  | List recipes          |
| POST   | `/recipes`        | Yes  | Create recipe         |
| DELETE | `/recipes/:id`    | Yes  | Delete recipe         |

### Analytics
| Method | Endpoint      | Auth | Description                       |
|--------|---------------|------|-----------------------------------|
| GET    | `/analytics`  | Yes  | Dashboard stats and waste breakdown |

#### Response shape

```jsonc
{
  "overview": { "totalItems": 8, "freshItems": 5, "expiringSoon": 2, "wastedItems": 1074 },
  "wasteByCategory": [ { "category": "snacks", "unit": "kg", "total_quantity": 290.8 } ],
  "recentWaste":     [ /* last five waste_log rows, verbatim */ ],

  // Feeds the bento cards in public/js/bento.js. Every chart is drawn from
  // these arrays alone — nothing is recomputed on the client.
  "bento": {
    "unit": "kg",                       // modal unit; label suffix throughout

    "trend": {                          // card A — daily waste, last 30 days
      "points": [ { "label": "Oct 4", "value": 6.3 } ],   // always exactly 30
      "total": 118.3, "prevTotal": 131.2,
      "delta": "9.8%", "up": false, "worse": false,
      "entries": 44
    },

    "inventory": {                      // card B — pantry waves, last 14 days
      "labels": ["Oct 19", "…"],        // 14 labels, oldest first
      "inDate": [6], "past": [2],       // items usable / past expiry each day
      "inDatePrev": [8], "pastPrev": [1],   // same, the fortnight before
      "today": 6, "delta": "25.0%", "up": false, "worse": true
    },

    "categories": {                     // card C — treemap, three periods
      "periods": [ { "label": "Weekly", "total": 12.4, "delta": "32.4%",
                     "up": false, "worse": false, "compare": "vs 18.3 last week" } ],
      "items":  [ { "name": "snacks", "group": "snacks",
                    "values": [4.1, 41.5, 290.8] } ],   // aligned to periods[]
      "groups": [ { "id": "snacks", "name": "Snacks", "color": "#8B3DFF", "ink": "light" } ]
    },

    "seasonality": {                    // card D — radar, this year vs last
      "years": [ {
        "label": "2026",
        "values": [8.1, 0, "…"],        // 12 monthly totals
        "stats": [ { "label": "Monthly avg", "value": 90.2, "delta": "23.6%",
                     "up": true, "worse": true, "note": "319 entries" } ],
        "rows":  [ { "label": "Snacks", "value": "135.2" } ]   // top 3 categories
      } ]
    }
  }
}
```

Two conventions the client relies on:

- **`delta` is a magnitude, never signed.** `"9.8%"` with `"up": false` means a 9.8%
  *fall*. `null` means "no baseline exists yet" (a first period, or a second too small
  to compare), and the card omits the badge rather than showing 0%.
- **`worse` is independent of `up`.** Falling pantry stock is bad (`up: false, worse: true`);
  falling waste is good (`up: false, worse: false`). The renderer colours on `worse`
  and points the arrow on `up`.

## Database schema

Four tables: `users`, `food_items`, `waste_log`, `recipes`,
with foreign-key relations and indexes for common queries.
See `server/database.py` for full DDL.

## Screenshots

1. Login / Register screen with toggle.
2. Dashboard with 4 stat cards and recent waste list.
3. Pantry with filter dropdowns and food-item badges.
4. Waste Log timeline.
5. Recipe card grid.
6. Analytics bento — waste trend line, inventory waves, category treemap, seasonality radar.

## Security considerations

- Passwords hashed with bcrypt (10 salt rounds) before storage.
- JWT tokens signed with HS256, 7-day expiry.
- Every user can only see and modify their own data (`WHERE user_id = ?`).
- HTML escaping on user input to prevent XSS.

## Future ideas

- Email reminders for items about to expire
- Community donations (surplus food to nearby people)
- Barcode scanning for quick grocery entry
- Machine-learning waste prediction

## Deploy on Render (one click)

This repo ships a [`render.yaml`](render.yaml) blueprint, so the fastest way to
deploy is:

1. Go to [render.com](https://render.com) → **New Web Service** → **Import**.
2. Select the `mounika131812-spec/foodwise` repository.
3. Click **Create**. Render builds the image, installs `requirements.txt`,
   and starts the app with `gunicorn -w 1 --threads 8 --timeout 120 app:app`.

That start command matters: the default `python app.py` runs Flask's dev server
and prints a "do not use in production" warning. Gunicorn is the production
server, and `--timeout 120` covers the AI recipe endpoint, which waits on the
Gemini API.

### Environment variables

In the Render dashboard → **Settings → Environment**, add:

| Key | Value | Notes |
|-----|-------|-------|
| `GEMINI_API_KEY` | your Gemini key | Without it, **AI Generate** in the Recipes tab silently falls back to template recipes. Never commit this — Render's push protection will block it. |

### Cold starts

Free-tier instances sleep after 15 minutes of inactivity. The first request
after that can return a plain-text 404 for 15–30 seconds while the instance
boots. Keep the app warm during demo hours with a free
[UptimeRobot](https://uptimerobot.com) monitor pinging the service URL every
5 minutes.

### Data persistence

The app uses SQLite (`data/foodwaste.db`). Render's free tier has an
ephemeral filesystem, so the database resets on every deploy/restart. That is
fine for a demo. If you need persistence later, use Render's paid persistent
disk or swap the DDL in `server/database.py` for Postgres.

## License

Free to use for academic/internship purposes.

---

Built for college internship. Ask any follow-ups about the code!
