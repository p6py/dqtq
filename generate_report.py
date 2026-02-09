from app import app, generate_pdf

with app.app_context():
    generate_pdf()