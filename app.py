from flask import Flask,render_template,request,redirect,url_for,flash,session,abort
from flask_session import Session
import mysql.connector
from itsdangerous import URLSafeTimedSerializer
from stoken import token
from key import secret_key,salt,salt2
from otp import uotp
from cmail import sendmail
import os
import re
app=Flask(__name__)
app.config['SESSION_TYPE']='filesystem'
Session(app)
app.secret_key=secret_key
#mydb=mysql.connector.connect(host='localhost',user='root',password='Admin',db='dev')
user=os.environ.get('RDS_USERNAME')
db=os.environ.get('RDS_DB_NAME')
password=os.environ.get('RDS_PASSWORD')
host=os.environ.get('RDS_HOSTNAME')
port=os.environ.get('RDS_PORT')
with mysql.connector.connect(host=host,port=port,user=user,password=password,db=db) as conn:
    cursor=conn.cursor()
    cursor.execute('create table if not exists users(user_id varchar(6) not null,user_name varchar(30) primary key,email varchar(50) not null unique,password varchar(8))')
    cursor.execute('create table if not exists post(pid binary(16),title varchar(250) not null,descr longtext,img_id varchar(15),date timestamp not null default current_timestamp,addedby varchar(30),foreign key(addedby) references users(user_name))')
mydb=mysql.connector.connect(host=host,user=user,password=password,db=db,port=port)
@app.route('/')
def index():
    return render_template('welcome.html')
@app.route('/home')
def home():
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select title,img_id,descr,bin_to_uuid(pid) from post')
    data=cursor.fetchall()
    #print(data[0][0])
    cursor.close()
    return render_template('home.html',data=data)
@app.route('/signup',methods=['GET','POST'])
def signup():
    if request.method=='POST':
        uid=uotp()
        user=request.form['user']
        email=request.form['email']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where user_name=%s',[user])
        count=cursor.fetchone()[0]
        print(count)
        if count==1:
            flash('User already registered')
            return redirect(url_for('home'))
        else:
            data={'uid':uid,'user':user,'email':email,'password':password}
            subject="One time link for your registration"
            body=f"Click this link for confirm the registration{url_for('confirm',token=token(data,salt=salt),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('The link has sent to given email')
            print('hi')
            return redirect(url_for('login'))
    return render_template('signup.html')
@app.route('/login',methods=['GET','POST'])
def login():
    if session.get('user'):
        return redirect(url_for('home'))
    if request.method=='POST':
        user=request.form['user']
        password=request.form['password']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select user_name,password from users where user_name=%s and password=%s',[user,password])
        count=cursor.fetchone()
        print(count)
        if count==(user,password):
            session['user']=user
            return redirect(url_for('home'))
    return render_template('login.html')
@app.route('/confirm/<token>',methods=['GET','POST'])
def confirm(token):
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt,max_age=300)
    except Exception as e:
        abort(404,'Link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('insert into users(user_id,user_name,email,password) values(%s,%s,%s,%s)',[data['uid'],data['user'],data['email'],data['password']])
        mydb.commit()
        cursor.close()
        flash('Details registered successfully')
        return redirect(url_for('login'))
@app.route('/logout')
def logout():
    if session.get('user'):
        session.pop('user')
        return redirect(url_for('login'))
    return redirect(url_for('home'))
@app.route('/forgot',methods=['GET','POST'])
def forgot():
    if request.method=='POST':
        email=request.form['email']
        npassword=request.form['newpassword']
        cpassword=request.form['confirmpassword']
        cursor=mydb.cursor(buffered=True)
        cursor.execute('select count(*) from users where user_name=%s',[email])
        count=cursor.fetchone()[0]
        print(count)
        if count != 1:
            return redirect(url_for('login'))
        elif npassword==cpassword:
            data={'user':email,'password':npassword}
            subject='The reset link for your page login'
            body=f"The reset link for login verify {url_for('verify',token=token(data,salt=salt2),_external=True)}"
            sendmail(to=email,subject=subject,body=body)
            flash('The reset password link as sent to given mail')
            return redirect(url_for('forgot'))
    return render_template('forgot.html')
@app.route('/verify',methods=['GET','POST'])
def verify():
    try:
        serializer=URLSafeTimedSerializer(secret_key)
        data=serializer.loads(token,salt=salt2,max_age=300)
    except Exception as e:
        abort(404,'link expired')
    else:
        cursor=mydb.cursor(buffered=True)
        cursor.execute('update users set password=%s where user_name=%s',[data['password'],data['user']])
        mydb.commit()
        cursor.close()
        return redirect(url_for('login'))
@app.route('/create',methods=['GET','POST'])
def create():
    if session.get('user'):
        if request.method=='POST':
            title=request.form['title']
            desc=request.form['descr']
            img=request.files['img']
            addedby=session.get('user')
            filename=uotp()+'.jpg'
            print(filename)
            img_path=os.path.dirname(os.path.abspath(__file__))
            static_path=os.path.join(img_path,'static')
            img.save(os.path.join(static_path,filename))
            cursor=mydb.cursor(buffered=True)
            cursor.execute('insert into post(pid,title,descr,img_id,addedby) values(uuid_to_bin(uuid()),%s,%s,%s,%s)',[title,desc,filename,addedby])
            mydb.commit()
            cursor.close()
            return redirect(url_for('home'))
        return render_template('post.html')
    else:
        return redirect(url_for('login'))
@app.route('/search',methods=['GET','POST'])
def search():
    if request.method=='POST':
        name=request.form['search']
        strg=['A-Za-z0-9']
        pattern=re.compile(f'^{strg}', re.IGNORECASE)
        if pattern.match(name):
            cursor=mydb.cursor(buffered=True)
            cursor.execute('select title,img_id,descr from post where title LIKE %s',[name + '%'])
            data=cursor.fetchall()
            cursor.close()
            return render_template('home.html',data=data)
        else:
            return 'Result not found'
    return render_template('home.html')
@app.route('/accont',methods=['GET','POST'])
def account():
    addedby=session.get('user')
    cursor=mydb.cursor(buffered=True)
    cursor.execute('select title,img_id,descr from post where addedby=%s',[addedby])  
    count1=cursor.fetchall()
    print(count1)
    cursor.close()
    return render_template('user.html',count1=count1) 
@app.route('/view/<pid>')
def view(pid):
    cursor=mydb.cursor()
    cursor.execute('select title,img_id,descr from post where pid=uuid_to_bin(%s)',[pid])
    data1=cursor.fetchone()
    cursor.close()
    return render_template('view.html',data1=data1)
@app.route('/delete/<pid>')
def delete(pid):
    if session.get('user'):
        cursor=mydb.cursor(buffered=True)
        cursor.execute('delete from post where pid=uuid_to_bin(%s)',[pid])
        mydb.commit()
        cursor.close()
        return redirect(url_for('home'))
@app.route('/share/<pid>')
def share(pid):
    cursor=mydb.cursor(buffere=True)
    cursor.execute('select title,img_id,descr from post where pid=uuid_to_bin(%s)',[pid])
    cursor.close()
if __name__=='__main__':
    app.run()