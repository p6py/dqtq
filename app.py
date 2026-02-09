from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
import os
import random

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///admission.db'
db = SQLAlchemy(app)

class Entrant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phys = db.Column(db.Integer)
    rus = db.Column(db.Integer)
    math = db.Column(db.Integer)
    ind = db.Column(db.Integer)
    total = db.Column(db.Integer)
    applications = db.relationship('Application', backref='entrant', lazy=True, cascade="all, delete-orphan")

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entrant_id = db.Column(db.Integer, db.ForeignKey('entrant.id'), nullable=False)
    op = db.Column(db.String(10))
    priority = db.Column(db.Integer)
    consent = db.Column(db.Boolean)

class PassingScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    op = db.Column(db.String(10))
    day = db.Column(db.String(10))
    score = db.Column(db.String(20))

with app.app_context():
    db.create_all()

def load_day(day):
    ops = ['PM', 'IVT', 'ITSS', 'IB']
    if day != '01.08':
        # Apply churn: delete 5-10%, update rest
        all_entrants = Entrant.query.all()
        if all_entrants:
            num_to_delete = random.randint(int(0.05 * len(all_entrants)), int(0.10 * len(all_entrants)))
            to_delete = random.sample(all_entrants, num_to_delete)
            for entrant in to_delete:
                db.session.delete(entrant)
            db.session.commit()
            # Update remaining: change some scores or consents
            remaining = Entrant.query.all()
            for entrant in remaining:
                if random.random() < 0.2:  # 20% chance to update
                    entrant.phys = max(0, entrant.phys + random.randint(-5, 5))
                    entrant.rus = max(0, entrant.rus + random.randint(-5, 5))
                    entrant.math = max(0, entrant.math + random.randint(-5, 5))
                    entrant.ind = max(0, entrant.ind + random.randint(-2, 2))
                    entrant.total = entrant.phys + entrant.rus + entrant.math + entrant.ind
                    # Possibly change consents in applications
                    for app in entrant.applications:
                        if random.random() < 0.1:  # 10% chance
                            app.consent = not app.consent
            db.session.commit()
    # Load from CSV
    for op in ops:
        filepath = f'../{day}_{op}.csv'
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            for _, row in df.iterrows():
                entrant_id = int(row['ID'])
                entrant = Entrant.query.get(entrant_id)
                if entrant:
                    entrant.phys = int(row['Physics'])
                    entrant.rus = int(row['Russian'])
                    entrant.math = int(row['Math'])
                    entrant.ind = int(row['Individual'])
                    entrant.total = int(row['Total'])
                else:
                    entrant = Entrant(id=entrant_id, phys=int(row['Physics']), rus=int(row['Russian']), math=int(row['Math']), ind=int(row['Individual']), total=int(row['Total']))
                    db.session.add(entrant)
                # Update application
                app_exist = Application.query.filter_by(entrant_id=entrant_id, op=op).first()
                if app_exist:
                    app_exist.priority = int(row['Priority'])
                    app_exist.consent = str(row['Consent']).lower() == 'true'
                else:
                    app_new = Application(entrant_id=entrant_id, op=op, priority=int(row['Priority']), consent=str(row['Consent']).lower() == 'true')
                    db.session.add(app_new)
    db.session.commit()
    # Calculate passing scores
    spots = {'PM': 40, 'IVT': 50, 'ITSS': 30, 'IB': 20}
    for op in ops:
        apps = Application.query.filter_by(op=op, consent=True).join(Entrant).order_by(Application.priority, Entrant.total.desc()).all()
        if len(apps) <= spots[op]:
            score = "NEDOBOR"
        else:
            score = str(apps[spots[op] - 1].entrant.total)
        ps = PassingScore(op=op, day=day, score=score)
        db.session.add(ps)
    db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/load/<day>')
def load(day):
    load_day(day)
    return redirect(url_for('index'))

@app.route('/view/<view_type>')
def view(view_type):
    if view_type == 'programs':
        ops = ['PM', 'IVT', 'ITSS', 'IB']
        data = {}
        for op in ops:
            apps = Application.query.filter_by(op=op).join(Entrant).order_by(Entrant.total.desc()).all()
            data[op] = [{'id': app.entrant.id, 'total': app.entrant.total, 'consent': app.consent, 'priority': app.priority, 'phys': app.entrant.phys, 'rus': app.entrant.rus, 'math': app.entrant.math, 'ind': app.entrant.ind} for app in apps]
        return render_template('view_programs.html', data=data)
    elif view_type == 'overall':
        # Get all entrants with their applications
        entrants = Entrant.query.all()
        data = []
        for entrant in entrants:
            apps = {app.op: {'priority': app.priority, 'consent': app.consent} for app in entrant.applications}
            data.append({
                'id': entrant.id,
                'phys': entrant.phys,
                'rus': entrant.rus,
                'math': entrant.math,
                'ind': entrant.ind,
                'total': entrant.total,
                'applications': apps
            })
        return render_template('view_overall.html', data=data)
    else:
        return "Invalid view type", 404

def generate_pdf():
    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Admission Report", ln=True, align='C')
    pdf.cell(200, 10, txt="Date and Time: " + str(pd.Timestamp.now()), ln=True)
    # Passing scores (latest for each OP)
    pdf.cell(200, 10, txt="Passing Scores", ln=True)
    ops = ['PM', 'IVT', 'ITSS', 'IB']
    for op in ops:
        latest_score = PassingScore.query.filter_by(op=op).order_by(PassingScore.day.desc()).first()
        score_text = latest_score.score if latest_score else "N/A"
        pdf.cell(200, 10, txt=f"{op}: {score_text}", ln=True)
    # Dynamics graphs
    import tempfile
    import os
    for op in ops:
        scores = [(s.day, int(s.score) if s.score != "NEDOBOR" else 0) for s in PassingScore.query.filter_by(op=op).order_by(PassingScore.day).all()]
        if scores:
            days, vals = zip(*scores)
            plt.figure()
            plt.plot(days, vals)
            plt.title(f"Passing Score Dynamics for {op}")
            plt.xlabel("Day")
            plt.ylabel("Score")
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                plt.savefig(tmp.name, format='png')
                pdf.image(tmp.name, w=100)
                os.unlink(tmp.name)
            plt.close()
    # Enrolled lists
    pdf.add_page()
    pdf.cell(200, 10, txt="Enrolled Applicants", ln=True)
    spots = {'PM': 40, 'IVT': 50, 'ITSS': 30, 'IB': 20}
    for op in ops:
        pdf.cell(200, 10, txt=f"{op}", ln=True)
        apps = Application.query.filter_by(op=op, consent=True).join(Entrant).order_by(Application.priority, Entrant.total.desc()).limit(spots[op]).all()
        for app in apps:
            pdf.cell(200, 10, txt=f"ID: {app.entrant.id}, Total: {app.entrant.total}", ln=True)
    pdf.output("report.pdf")

@app.route('/report')
def report():
    generate_pdf()
    return send_file("report.pdf", as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)