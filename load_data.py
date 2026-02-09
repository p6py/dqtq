from app import app, load_day

with app.app_context():
    load_day('01.08')