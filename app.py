from flask import Flask,redirect,url_for,render_template,request,flash,abort,session
from flask_session import Session
from key import secret_key,salt1,salt2
from stoken import token
from cmail import sendmail
from itsdangerous import URLSafeTimedSerializer
import mysql.connector
app=Flask(__name__)
app.secret_key=secret_key
app.config['SESSION_TYPE']='filesystem'
Session(app)
mydb=mysql.connector.connect(host='localhost',user='root',password='admin',db='tms')
@app.route('/')
def index():
    return render_template('title.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('admin'):
        return redirect(url_for('home'))
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from admin where email=%s and password=%s',[email,password])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['admin']=email
                cursor.execute('select email_status from admin where email=%s',[email])
                status=cursor.fetchone()[0]
                cursor.close()
                if status!='confirmed':
                    return redirect(url_for('inactive'))
                else:
                    return redirect(url_for('home'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('login.html')
        else:
            cursor.close()
            flash('invalid username')
            return render_template('login.html')
    return render_template('login.html')
@app.route('/inactive')
def inactive():
    if session.get('admin'):
        email=session.get('admin')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return redirect(url_for('home'))
        else:
            return render_template('inactive.html')
    else:
        return redirect(url_for('login'))
@app.route('/homepage')
def home():
    if session.get('admin'):
        email=session.get('admin')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            return render_template('homepage.html')
        else:
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/resendconfirmation')
def resend():
    if session.get('admin'):
        email=session.get('admin')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.execute('select email from admin where email=%s',[email])
        email=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('home'))
        else:
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Please confirm your mail-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return redirect(url_for('inactive'))
    else:
        return redirect(url_for('login'))
@app.route('/signup_admin',methods=['GET','POST'])
def signup_admin():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        try:
            cursor.execute('insert into admin (username,password,email) values(%s,%s,%s)',(username,password,email))
        except mysql.connector.IntegrityError:
            flash('Username or email is already in use')
            return render_template('signup_admin.html')
        else:
            mydb.commit()
            cursor.close()
            subject='Email Confirmation'
            confirm_link=url_for('confirm',token=token(email,salt1),_external=True)
            body=f"Thanks for signing up.Follow this link-\n\n{confirm_link}"
            sendmail(to=email,body=body,subject=subject)
            flash('Confirmation link sent check your email')
            return render_template('signup_admin.html')
    return render_template('signup_admin.html')
@app.route('/empregister', methods=['GET','POST'])
def empregister():
    if session.get('admin'):
        if request.method=='POST':
            ename=request.form['ename']
            empdept=request.form['empdept']
            empmail=request.form['empmail']
            emppassword=request.form['emppassword']
            added_by=session.get('admin')
            cursor = mydb.cursor(buffered=True)
            cursor.execute('SELECT count(*) FROM emp WHERE empmail=%s',[empmail])
            count= cursor.fetchone()[0]
            if count!=0:
                flash('Username or email is already in use')
                return render_template('empregister.html')
            else:
                cursor.execute('insert into emp (ename,empdept,empmail,emppassword,added_by) values(%s,%s,%s,%s,%s)',(ename,empdept,empmail,emppassword,added_by))
                mydb.commit()
                cursor.close()
                flash('Registration Successful')
                subject='Work Space Employee Credintials'
                body=f' Thanks for registering to Work Space please use this credintials to login mail:{empmail} and password:{emppassword}'
                sendmail(empmail,subject,body)
                return redirect(url_for('dashboard'))
        return render_template('empregister.html')
    else:
        return render_template('empregister.html')        
@app.route('/confirm/<token>')
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt1,max_age=120)
    except Exception as e:
        #print(e)
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select email_status from admin where email=%s',[email])
        status=cursor.fetchone()[0]
        cursor.close()
        if status=='confirmed':
            flash('Email already confirmed')
            return redirect(url_for('login'))
        else:
            cursor=mydb.cursor(buffered=True)
            cursor.execute("update admin set email_status='confirmed' where email=%s",[email])
            mydb.commit()
            flash('Email confirmation success')
            return redirect(url_for('login'))
@app.route('/forget',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from admin where email=%s',[email])
        count=cursor.fetchone()[0]
        cursor.close()
        if count==1:
            cursor=mydb.cursor(buffered=True)
            cursor.execute('SELECT email_status from admin where email=%s',[email])
            status=cursor.fetchone()[0]
            cursor.close()
            if status!='confirmed':
                flash('Please Confirm your email first')
                return render_template('forgot.html')
            else:
                subject='Forget Password'
                confirm_link=url_for('reset',token=token(email,salt=salt2),_external=True)
                body=f"Use this link to reset your password-\n\n{confirm_link}"
                sendmail(to=email,body=body,subject=subject)
                flash('Reset link sent check your email')
                return redirect(url_for('login'))
        else:
            flash('Invalid email id')
            return render_template('forgot.html')
    return render_template('forgot.html')
@app.route('/reset/<token>',methods=['GET','POST'])
def reset(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        email=serializer.loads(token,salt=salt2,max_age=180)
    except:
        abort(404,'Link Expired')
    else:
        if request.method=='POST':
            newpassword=request.form['npassword']
            confirmpassword=request.form['cpassword']
            if newpassword==confirmpassword:
                cursor=mydb.cursor(buffered=True)
                cursor.execute('update admin set password=%s where email=%s',[newpassword,email])
                mydb.commit()
                flash('Reset Successful')
                return redirect(url_for('login'))
            else:
                flash('Passwords mismatched')
                return render_template('newpassword.html')
        return render_template('newpassword.html')
@app.route('/logout')
def logout():
    if session.get('admin'):
        session.pop('admin')
        return redirect(url_for('home'))
    else:
        return redirect(url_for('home'))
@app.route('/addtask', methods=['GET', 'POST'])
def addtask():
    if session.get('admin'):
        email=session.get('admin')
        cursor = mydb.cursor(buffered=True)
        cursor.execute('select * from emp where added_by=%s',[email])
        adddata = cursor.fetchall()
        print(adddata)
        if request.method == 'POST':
            taskid = request.form['taskid']
            tasktitle = request.form['tasktitle']
            duedate = request.form['duedate']
            taskcontent = request.form['taskcontent']
            empmail = request.form['assigned_to']
            
            try:
                cursor = mydb.cursor(buffered=True)
                cursor.execute('INSERT INTO task (taskid, tasktitle, duedate, taskcontent,empemail,assignedby) VALUES (%s, %s, %s,%s,%s,%s)',
                            (taskid, tasktitle, duedate, taskcontent,empmail,email))
                mydb.commit()
            except mysql.connector.IntegrityError:
                flash('Task ID already exists')
                return render_template('addtask.html',adddata=adddata)
            else:
                mydb.commit()
                cursor.close()
                flash('Task assigned successfully')
                return render_template('addtask.html',adddata=adddata)
    return render_template('addtask.html')
@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT * FROM task')
        tasks = cursor.fetchall()
        cursor.close()
        
        return render_template('dashboard.html', tasks=tasks)
    else:
        return redirect(url_for('login'))
@app.route('/emplogin',methods=['GET','POST'])
def emplogin():
    if session.get('user'):
        return redirect(url_for('emphome'))
    if request.method=='POST':
        empmail=request.form['empmail']
        emppassword=request.form['emppassword']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from emp where empmail=%s',[empmail])
        count=cursor.fetchone()[0]
        if count==1:
            cursor.execute('select count(*) from emp where empmail=%s and emppassword=%s',[empmail,emppassword])
            p_count=cursor.fetchone()[0]
            if p_count==1:
                session['user'] = empmail
                return redirect(url_for('emphome'))
            else:
                cursor.close()
                flash('invalid password')
                return render_template('emplogin.html')
        else:
            cursor.close()
            flash('invalid email')
            return render_template('emplogin.html')
    return render_template('emplogin.html')
@app.route('/emphome')
def emphome():
    if session.get('user'):
        empmail=session.get('user')
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select empmail from emp where empmail=%s',[empmail])
        status=cursor.fetchone()
        cursor.close()
        return render_template('emphome.html')
    else:
        return redirect(url_for('emplogin'))
@app.route('/empdashboard')
def empdashboard():
    if session.get('user'):
        cursor = mydb.cursor(buffered=True)
        cursor.execute('SELECT * FROM task')
        tasks = cursor.fetchall()
        cursor.close()
        
        return render_template('empdashboard.html', tasks=tasks)
    else:
        return redirect(url_for('emplogin'))
@app.route('/emplogout')
def emplogout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('emplogin'))
    else:
        return redirect(url_for('emplogin'))
@app.route('/empupdate', methods=['POST'])
def empupdate():
    status = request.form['status']
    if not status:
        flash("Please select a status!")
        return render_template('emphome.html')
    cursor = mydb.cursor(buffered=True)
    cursor.execute("UPDATE task SET status = %s", (status,))
    mydb.commit()
    cursor.close()

    flash("Table updated successfully!")
    return render_template('emphome.html')
@app.route('/adminupdate', methods=['GET','POST'])
def adminupdate():
    if request.method=='POST':
        taskid = request.form['taskid']
        tasktitle=request.form['tasktitle']
        duedate=request.form['duedate']
        taskcontent=request.form['taskcontent']
        cursor = mydb.cursor(buffered=True)
        cursor.execute("UPDATE task SET tasktitle = %s,duedate=%s,taskcontent=%s where taskid=%s", (tasktitle,duedate,taskcontent,taskid))
        mydb.commit()
        cursor.close()
        empemail=session.get('user')
        flash("Task updated successfully!")
        subject='Task Updated'
        body=f'Please check the task requirements and complete it before the due date of Task ID={taskid}.\n\nThank you:)'
        sendmail(empemail,subject,body)
        return render_template('dashboard.html',taskid=taskid,tasktitle=tasktitle,duedate=duedate,taskcontent=taskcontent)
    return render_template('taskupdate.html')
@app.route('/taskdelete/<int:id>',methods=['GET','POST'])
def taskdelete(id):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from task where taskid=%s',[id])
        mydb.commit()
        cursor.close()
        flash('Task deleted successfully')
        return redirect(url_for('dashboard'))
app.run(debug=True,use_reloader=True)