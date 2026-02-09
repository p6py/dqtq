from nicegui import ui, app
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, text
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
import pandas as pd
import matplotlib.pyplot as plt
import io
from fpdf import FPDF
import os
import random

data = '00.00'

# Database setup
if os.path.exists('admission.db'):
    os.remove('admission.db')
engine = create_engine('sqlite:///admission.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Entrant(Base):
    __tablename__ = 'entrant'
    id = Column(Integer, primary_key=True)
    phys = Column(Integer)
    rus = Column(Integer)
    math = Column(Integer)
    ind = Column(Integer)
    total = Column(Integer)
    applications = relationship('Application', backref='entrant', lazy=True, cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = 'application'
    id = Column(Integer, primary_key=True)
    entrant_id = Column(Integer, ForeignKey('entrant.id'), nullable=False)
    op = Column(String(10))
    priority = Column(Integer)
    consent = Column(Boolean)

class PassingScore(Base):
    __tablename__ = 'passing_score'
    id = Column(Integer, primary_key=True)
    op = Column(String(10))
    day = Column(String(10))
    score = Column(String(20))

Base.metadata.create_all(bind=engine)
db = SessionLocal()

db.execute(text('PRAGMA foreign_keys=ON'))
db.commit()

# Clear existing data
db.execute(text('DELETE FROM entrant'))
db.execute(text('DELETE FROM application'))
db.execute(text('DELETE FROM passing_score'))
db.commit()

def load_day(day):
    ops = ['PM', 'IVT', 'ITSS', 'IB']
    if day != '01.08':
        # Apply churn: delete 5-10%, update rest
        all_entrants = db.query(Entrant).all()
        if all_entrants:
            num_to_delete = random.randint(int(0.05 * len(all_entrants)), int(0.10 * len(all_entrants)))
            to_delete = random.sample(all_entrants, num_to_delete)
            for entrant in to_delete:
                db.delete(entrant)
            db.commit()
            # Update remaining: change some scores or consents
            remaining = db.query(Entrant).all()
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
            db.commit()
    # Load from CSV
    for op in ops:
        filepath = f'../{day}_{op}.csv'
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            for _, row in df.iterrows():
                entrant_id = int(row['ID'])
                entrant = db.query(Entrant).filter(Entrant.id == entrant_id).first()
                if entrant:
                    entrant.phys = int(row['Physics'])
                    entrant.rus = int(row['Russian'])
                    entrant.math = int(row['Math'])
                    entrant.ind = int(row['Individual'])
                    entrant.total = int(row['Total'])
                else:
                    entrant = Entrant(id=entrant_id, phys=int(row['Physics']), rus=int(row['Russian']), math=int(row['Math']), ind=int(row['Individual']), total=int(row['Total']))
                    db.add(entrant)
                # Update application
                app_exist = db.query(Application).filter(Application.entrant_id == entrant_id, Application.op == op).first()
                if app_exist:
                    app_exist.priority = int(row['Priority'])
                    app_exist.consent = str(row['Consent']).lower() == 'true'
                else:
                    app_new = Application(entrant_id=entrant_id, op=op, priority=int(row['Priority']), consent=str(row['Consent']).lower() == 'true')
                    db.add(app_new)
    db.commit()
    # Calculate passing scores
    spots = {'PM': 40, 'IVT': 50, 'ITSS': 30, 'IB': 20}
    for op in ops:
        apps = db.query(Application).filter(Application.op == op, Application.consent == True).join(Entrant).order_by(Application.priority, Entrant.total.desc()).all()
        if len(apps) <= spots[op]:
            score = "NEDOBOR"
        else:
            score = str(apps[spots[op] - 1].entrant.total)
        ps = PassingScore(op=op, day=day, score=score)
        db.add(ps)
    db.commit()



@ui.page('/')
def index():
    ui.label('Admission Analysis System').classes('text-h4')

    ui.label('Load Days').classes('text-h5')
    with ui.row():
        for day in ['01.08', '02.08', '03.08', '04.08']:
            ui.button(f'Load {day}', on_click=lambda d=day: load_and_refresh(d))

    ui.label('View Data').classes('text-h5')
    with ui.row():
        ui.link('View by Programs', '/view/programs')
        ui.link('View Overall List', '/view/overall')

    ui.label('Report').classes('text-h5')
    ui.button('Generate Report', on_click=generate_report)

def load_and_refresh(day):
    try:
        load_day(day)
        ui.notify(f'Successfully loaded data for {day}')
        global data 
        data = day
    except Exception as e:
        ui.notify(f'Error loading data for {day}: {str(e)}', type='error')

@ui.page('/view/programs')
def view_programs():
    CSV_FILENAME_IB = f'{data}_IB.csv'  # Измените на ваше имя файла
    CSV_FILENAME_ITSS = f'{data}_ITSS.csv'  # Измените на ваше имя файла
    CSV_FILENAME_IVT = f'{data}_IVT.csv'  # Измените на ваше имя файла
    CSV_FILENAME_PM = f'{data}_PM.csv'  # Измените на ваше имя файла

    # Загружаем CSV файл
    try:
        df1 = pd.read_csv(CSV_FILENAME_IB)
        print(f"Загружен файл: {CSV_FILENAME_IB}")
        print(f"Строк: {len(df1)}, Столбцов: {len(df1.columns)}")

        df2 = pd.read_csv(CSV_FILENAME_ITSS)
        print(f"Загружен файл: {CSV_FILENAME_ITSS}")
        print(f"Строк: {len(df2)}, Столбцов: {len(df2.columns)}")

        df3 = pd.read_csv(CSV_FILENAME_IVT)
        print(f"Загружен файл: {CSV_FILENAME_IVT}")
        print(f"Строк: {len(df3)}, Столбцов: {len(df3.columns)}")
    except Exception as e:
        print(f"Ошибка загрузки файла: {e}")
        df1 = pd.DataFrame()  # Пустой DataFrame если ошибка
        df2 = pd.DataFrame()  # Пустой DataFrame если ошибка
        df3 = pd.DataFrame()  # Пустой DataFrame если ошибка


    # Создаем интерфейс
    ui.label(f'📊 Просмотр списока: {CSV_FILENAME_IB}').classes('text-2xl font-bold')

    
    # Отображаем таблицу
    if not df1.empty:
        # Создаем таблицу с помощью ag-Grid (более мощная)
        columns = [{'field': col, 'headerName': col, 'sortable': True, 'filter': True} for col in df1.columns]
        rows = df1.to_dict('records')
        
        grid = ui.aggrid({
            'columnDefs': columns,
            'rowData': rows,
            'pagination': True,
            'paginationPageSize': 20,
            'defaultColDef': {
                'resizable': True,
                'sortable': True,
                'filter': True,
                'floatingFilter': True,
            }
        }).classes('w-full h-96')
        
        # Кнопка для обновления
        def refresh_data():
            try:
                new_df = pd.read_csv(CSV_FILENAME_IB)
                grid.options['rowData'] = new_df.to_dict('records')
                grid.update()
                ui.notify('Данные обновлены!', type='positive')
            except Exception as e:
                ui.notify(f'Ошибка обновления: {e}', type='negative')
        
        #ui.button('🔄 Обновить данные', on_click=refresh_data).props('color=primary')
        
        # Предпросмотр данных в текстовом формате
        #with ui.expansion('📝 Сырые данные (первые 10 строк)').classes('w-full mt-4'):
            #ui.code(df1.head(10).to_string())
    else:
        ui.label('❌ Не удалось загрузить данные из CSV файла').classes('text-red text-lg')

    ui.label(f'📊 Просмотр списока: {CSV_FILENAME_ITSS}').classes('text-2xl font-bold')

    #Таблица 2
    if not df2.empty:
        # Создаем таблицу с помощью ag-Grid (более мощная)
        columns = [{'field': col, 'headerName': col, 'sortable': True, 'filter': True} for col in df2.columns]
        rows = df2.to_dict('records')
        
        grid = ui.aggrid({
            'columnDefs': columns,
            'rowData': rows,
            'pagination': True,
            'paginationPageSize': 20,
            'defaultColDef': {
                'resizable': True,
                'sortable': True,
                'filter': True,
                'floatingFilter': True,
            }
        }).classes('w-full h-96')
        
        # Кнопка для обновления
        def refresh_data():
            try:
                new_df = pd.read_csv(CSV_FILENAME_ITSS)
                grid.options['rowData'] = new_df.to_dict('records')
                grid.update()
                ui.notify('Данные обновлены!', type='positive')
            except Exception as e:
                ui.notify(f'Ошибка обновления: {e}', type='negative')
        
        #ui.button('🔄 Обновить данные', on_click=refresh_data).props('color=primary')
        
        # Предпросмотр данных в текстовом формате
        #with ui.expansion('📝 Сырые данные (первые 10 строк)').classes('w-full mt-4'):
            #ui.code(df1.head(10).to_string())
    else:
        ui.label('❌ Не удалось загрузить данные из CSV файла').classes('text-red text-lg')

    ui.label(f'📊 Просмотр списока: {CSV_FILENAME_IVT}').classes('text-2xl font-bold')

    if not df3.empty:
        # Создаем таблицу с помощью ag-Grid (более мощная)
        columns = [{'field': col, 'headerName': col, 'sortable': True, 'filter': True} for col in df3.columns]
        rows = df3.to_dict('records')
        
        grid = ui.aggrid({
            'columnDefs': columns,
            'rowData': rows,
            'pagination': True,
            'paginationPageSize': 20,
            'defaultColDef': {
                'resizable': True,
                'sortable': True,
                'filter': True,
                'floatingFilter': True,
            }
        }).classes('w-full h-96')
        
        # Кнопка для обновления
        def refresh_data():
            try:
                new_df = pd.read_csv(CSV_FILENAME_IVT)
                grid.options['rowData'] = new_df.to_dict('records')
                grid.update()
                ui.notify('Данные обновлены!', type='positive')
            except Exception as e:
                ui.notify(f'Ошибка обновления: {e}', type='negative')
        
        #ui.button('🔄 Обновить данные', on_click=refresh_data).props('color=primary')
        
        # Предпросмотр данных в текстовом формате
        #with ui.expansion('📝 Сырые данные (первые 10 строк)').classes('w-full mt-4'):
            #ui.code(df1.head(10).to_string())
    else:
        ui.label('❌ Не удалось загрузить данные из CSV файла').classes('text-red text-lg')

@ui.page('/view/overall')
def view_overall():
    if not db.query(Entrant).first():
        load_day('01.08')

    ui.label('Overall Competition List with Cascade Priorities').classes('text-h4')
    ui.button('Back to Home', on_click=lambda: ui.open('/'))

    entrants = db.query(Entrant).all()
    data = []
    for entrant in entrants:
        apps = {app.op: {'priority': app.priority, 'consent': app.consent} for app in entrant.applications}
        row = {
            'ID': entrant.id,
            'Physics': entrant.phys,
            'Russian': entrant.rus,
            'Math': entrant.math,
            'Individual': entrant.ind,
            'Total': entrant.total,
            'PM Priority': apps.get('PM', {}).get('priority', '-'),
            'PM Consent': apps.get('PM', {}).get('consent', '-'),
            'IVT Priority': apps.get('IVT', {}).get('priority', '-'),
            'IVT Consent': apps.get('IVT', {}).get('consent', '-'),
            'ITSS Priority': apps.get('ITSS', {}).get('priority', '-'),
            'ITSS Consent': apps.get('ITSS', {}).get('consent', '-'),
            'IB Priority': apps.get('IB', {}).get('priority', '-'),
            'IB Consent': apps.get('IB', {}).get('consent', '-'),
        }
        data.append(row)
    ui.table.from_pandas(pd.DataFrame(data))

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
def generate_report():
    generate_pdf()
    ui.download('report.pdf')

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()
