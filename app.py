"""Flask application entry point for Smart Food Waste Management Platform."""
import os
from flask import Flask, request, send_from_directory
from server.database import init
from server.auth import auth_middleware, register, login, me
import routes.food as food
import routes.waste as waste
import routes.recipes as recipes
import routes.analytics as analytics
import routes.ai_recipes as ai_recipes

PUBLIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public')
app = Flask(__name__, static_folder=PUBLIC_DIR, static_url_path='/static')

# Initialize database on startup
init()


def _dispatch(handlers):
    """Dispatch a request to the handler matching its HTTP method."""
    def view(*args, **kwargs):
        handler = handlers.get(request.method)
        if handler is None:
            return {'error': 'Method not allowed'}, 405
        return handler(*args, **kwargs)
    return view

# ---- Auth routes (public) ----
app.add_url_rule('/api/auth/register', 'register', register, methods=['POST'])
app.add_url_rule('/api/auth/login', 'login', login, methods=['POST'])
app.add_url_rule('/api/auth/me', 'me', auth_middleware(me), methods=['GET'])

# ---- Food pantry routes (protected) ----
app.add_url_rule('/api/food', 'food_collection', auth_middleware(_dispatch({
    'GET': food.get_food, 'POST': food.create})), methods=['GET', 'POST'])
app.add_url_rule('/api/food/<int:item_id>', 'food_get', auth_middleware(food.get_one), methods=['GET'])
app.add_url_rule('/api/food/<int:item_id>', 'food_update', auth_middleware(food.update), methods=['PUT'])
app.add_url_rule('/api/food/<int:item_id>', 'food_delete', auth_middleware(food.remove), methods=['DELETE'])
app.add_url_rule('/api/food/all', 'food_clear', auth_middleware(food.clear_all), methods=['DELETE'])

# ---- Waste log routes (protected) ----
app.add_url_rule('/api/waste', 'waste_collection', auth_middleware(_dispatch({
    'GET': waste.get_waste, 'POST': waste.create})), methods=['GET', 'POST'])
app.add_url_rule('/api/waste/all', 'waste_clear', auth_middleware(waste.clear_all), methods=['DELETE'])
app.add_url_rule('/api/waste/<int:waste_id>', 'waste_delete', auth_middleware(waste.remove), methods=['DELETE'])

# ---- Recipe routes (protected) ----
app.add_url_rule('/api/recipes', 'recipe_collection', auth_middleware(_dispatch({
    'GET': recipes.get_recipes, 'POST': recipes.create})), methods=['GET', 'POST'])
app.add_url_rule('/api/recipes/ai-generate', 'ai_generate', auth_middleware(ai_recipes.ai_generate), methods=['POST'])
app.add_url_rule('/api/recipes/ai-generate-save', 'ai_generate_save', auth_middleware(ai_recipes.ai_generate_save), methods=['POST'])
app.add_url_rule('/api/recipes/<int:recipe_id>', 'recipe_delete', auth_middleware(recipes.remove), methods=['DELETE'])

# ---- Analytics (protected) ----
app.add_url_rule('/api/analytics', 'analytics', auth_middleware(analytics.get_stats), methods=['GET'])


# ---- Serve frontend ----
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')


# ---- Serve React AI recipe conveyor build ----
# REMOVED: The /conveyor route is no longer needed. Recipes tab now shows AI-generated recipes from inventory.


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=False)