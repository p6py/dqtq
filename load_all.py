from app import app, load_day

days = ['01.08', '02.08', '03.08', '04.08']

with app.app_context():
    for day in days:
        load_day(day)