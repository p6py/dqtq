from app import app, db, Entrant, Application

with app.app_context():
    entrants = Entrant.query.count()
    apps = Application.query.count()
    print(f"Entrants: {entrants}, Applications: {apps}")