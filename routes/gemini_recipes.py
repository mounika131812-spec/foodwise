"""Gemini AI recipe generation from pantry items.

Uses the google-genai SDK to ask Gemini for Indian-style recipes that use the
user's actual inventory. This is the only recipe source — there is no
template fallback, so a missing GEMINI_API_KEY means no recipes.
"""
import base64
import io
import json
import os
import threading

from google import genai

# The API key is provided by the user via GEMINI_API_KEY env var
_API_KEY = os.environ.get('GEMINI_API_KEY')
_client = None
# Gemini needs longer than a few seconds for a batch of full recipes.
_RECIPE_TIMEOUT = 14
_IMAGE_TIMEOUT = 8


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=_API_KEY)
    return _client


RECIPE_PROMPT = """You are an Indian home cook creating {count} complete recipes using the following pantry items.

Pantry items:
{items}
{priority}
Return ONLY a valid JSON array of exactly {count} objects, no markdown fences, no explanation. Each object must have:
- "name": recipe name (string)
- "desc": one-sentence description (string)
- "ingredients": array of ingredient names that will be used in the recipe (strings)
- "uses": array of specific pantry item names from above that this recipe uses (lowercase)
- "price": estimated cost in USD (number, 2.0-6.0)
- "prep": prep time in minutes (number)
- "details": array of 2-3 tags like ["Indian", "Vegetarian", "Quick"]
- "instructions": array of step strings (full cooking instructions)

Rules:
- Every recipe MUST name at least 2 pantry items from the list above in "uses", spelled exactly as written there
- Spread across the whole pantry: do NOT build every recipe around one popular ingredient. Each recipe must be driven by a different set of pantry items
- If any item is listed as uncovered below, at least one recipe must star that item
- All {count} recipes must be different dishes — never repeat a dish, a name, or a near-variant of the same curry/sabzi
- Prefer Indian-style cooking (curries, dal, sabzi, rice dishes, dosa, paratha, chai, etc.)
- Keep instructions clear, simple, and achievable for a home cook
- If only 1-2 pantry items exist, still generate {count} recipes that use them in genuinely different ways"""


def _strip_code_fences(text):
    """Remove ```json fences if Gemini wrapped the response."""
    text = text.strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[1] if '\n' in text else text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()
    return text


def _call_with_timeout(fn, timeout_secs):
    """Run fn() on a worker thread with a hard timeout.

    Returns (value, error). value is None on timeout or error.
    """
    result = {'value': None, 'error': None}

    def run():
        try:
            result['value'] = fn()
        except Exception as e:
            result['error'] = str(e)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    thread.join(timeout_secs)

    if thread.is_alive():
        return None, f'timed out after {timeout_secs}s'
    return result['value'], result['error']


def _parse_recipes(text, count):
    recipes = json.loads(_strip_code_fences(text))
    if not isinstance(recipes, list):
        raise ValueError('expected a JSON array from the model')
    return recipes[:count]


def generate_recipes(items, count=8, uncovered=None):
    """Use Gemini to generate recipes from pantry items.

    Args:
        items: list of dicts with keys name, category, quantity, unit.
        count: number of recipes to request.
        uncovered: optional list of item names that have no recipe yet;
            passed to the model as a priority hint.

    Returns:
        list of recipe dicts (empty on failure).
    """
    if not items:
        return []
    if not _API_KEY:
        print('[gemini] GEMINI_API_KEY is not set — cannot generate recipes')
        return []

    item_lines = [
        f"- {i['name']} ({i['category']}, {i['quantity']} {i['unit']})"
        for i in items
    ]
    priority = ''
    if uncovered:
        priority = (
            '\nThese items are in the pantry but appear in none of the saved recipes, '
            'so they must be the star of at least one recipe each:\n'
            + '\n'.join(f"- {n}" for n in uncovered)
            + '\n'
        )
    prompt = RECIPE_PROMPT.format(
        items='\n'.join(item_lines), priority=priority, count=count
    )
    client = _get_client()

    def request_once(config=None):
        kwargs = {'model': 'gemini-flash-latest', 'contents': prompt}
        if config:
            kwargs['config'] = config
        resp = client.models.generate_content(**kwargs)
        return _parse_recipes(resp.text or '', count)

    # Strict-JSON first; retry without config if the model/SDK rejects it.
    for config in ({'response_mime_type': 'application/json', 'temperature': 1.0}, None):
        recipes, error = _call_with_timeout(
            lambda c=config: request_once(c), _RECIPE_TIMEOUT
        )
        if recipes:
            return recipes
        if error:
            print(f'[gemini] recipe generation failed: {error}')

    return []


def generate_image(prompt, model='gemini-2.5-flash-image'):
    """Try to generate an image with Gemini. Returns a data URI or None."""
    if not _API_KEY:
        return None

    def call():
        client = _get_client()
        resp = client.models.generate_images(
            model=model,
            prompt=prompt,
            config={'number_of_images': 1, 'aspect_ratio': '1:1'},
        )
        if not (resp and getattr(resp, 'images', None)):
            return None
        img = resp.images[0]
        if hasattr(img, 'save'):
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()
        if isinstance(img, (bytes, bytearray)):
            return 'data:image/png;base64,' + base64.b64encode(bytes(img)).decode()
        return None

    image, error = _call_with_timeout(call, _IMAGE_TIMEOUT)
    if error:
        print(f'[gemini] image generation failed: {error}')
    return image
