from flask import Flask, request, session, redirect, url_for, render_template, flash
from flask.scaffold import F
from fpdf import FPDF
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import boto3
import random
from dotenv import load_dotenv
load_dotenv()
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

conn = psycopg2.connect(dbname = DB_NAME, user = DB_USER, password = DB_PASS, host = DB_HOST)

@app.route('/',methods=['GET','POST'])
def home():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if 'loggedin' in session:
        try:
            if request.method == 'POST' and 'item_name' in request.form and 'quantity' in request.form and 'total_amount' in request.form and 'invoice_date' in request.form:
                item_name = request.form['item_name']
                quantity = request.form['quantity']
                total_amount = request.form['total_amount']
                invoice_date = request.form['invoice_date']
                user_id = session['id']
                
                
                pdf = FPDF()
                pdf.add_page()
                page_width = pdf.w - 2*pdf.l_margin

                pdf.set_font('Times','B',14.0)
                pdf.cell(page_width,0.0,'Invoice Data',align='C')
                pdf.ln(10)

                pdf.set_font('Courier','',12)

                th = pdf.font_size
                pdf.cell(page_width,th, "Item name : "+item_name,align='L')
                pdf.ln(th*2)
                pdf.cell(page_width,th,"Item Quantity : "+quantity,align='L')
                pdf.ln(th*2)
                pdf.cell(page_width,th,"Amount to pay : "+total_amount,align='L')
                pdf.ln(th*2)
                pdf.cell(page_width,th,"Invoice date : "+invoice_date,align='L')
                pdf.ln(th*2)
                n = str(random.randint(10000,99999))
                pdf_name = "INV" + invoice_date[8:10] + invoice_date[5:7] + invoice_date[:4] + invoice_date[11:13] + invoice_date[14:] + n + ".pdf"
                pdf.output(pdf_name)
                s3 = boto3.client("s3")
                s3.upload_file(
                    Filename = pdf_name,
                    Bucket = "ims2022",
                    Key = pdf_name,
                )
                cursor.execute("INSERT INTO invoice (item_name, quantity, total_amount, invoice_date, pdf_name, user_id) VALUES (%s,%s,%s,%s,%s,%s)", (item_name, quantity, total_amount, invoice_date, pdf_name, user_id,))
                conn.commit()
                flash('Invoice submitted successfully')
            elif request.method == 'POST':
                flash('Please fill out the form!')
        except Exception as e:
            print(e)
        finally:
            cursor.close()
        return render_template('home.html',username=session['username'])
    return redirect(url_for('login'))
    


@app.route('/login/', methods=['GET','POST'])
def login():
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute("CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(50) NOT NULL UNIQUE, password VARCHAR(150) NOT NULL)")
    cursor.execute("TRUNCATE TABLE users")
    password = os.getenv("password")
    hashed_password = generate_password_hash(password)
    cursor.execute("INSERT INTO users(username, password) VALUES(%s,%s)",("Suraj",hashed_password))

    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']

        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        account = cursor.fetchone()
        conn.commit()
        if account: 
            password_rs = account['password']
            if check_password_hash(password_rs, password):
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                return redirect(url_for('home'))
            else:
                flash('Incorrect username or password')
        else:
            flash('Incorrect username or password')

    return render_template('login.html')

if __name__ == "__main__":
    app.run(debug=True)