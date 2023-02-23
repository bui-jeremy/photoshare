######################################
# author ben lawson <balawson@bu.edu>
# Edited by: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flask import Flask, Response, request, render_template, redirect, url_for, session, flash
from flaskext.mysql import MySQL
import flask_login

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'cs460'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

#begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = request.form['password'] == pwd
	return user

'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
	return new_page_html
'''

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if flask.request.form['password'] == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

#you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress=False)

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email=request.form.get('email')
		password=request.form.get('password')
		fname=request.form.get('fname')
		lname=request.form.get('lname')
		hometown=request.form.get('hometown')
		dob=request.form.get('dob')
		gender=request.form.get('gender')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (first_name, last_name, email, password, hometown, dob, gender) VALUES ('{0}', '{1}','{2}','{3}','{4}','{5}','{6}')".format(fname, lname, email, password, hometown, dob, gender)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=email, message='Account Created!') 
	else:
		print("couldn't find all tokens")
		flash("Email already in use! Use another one or login with the existing e-mail.")
		return flask.redirect(flask.url_for('register'))

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
#end login code

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	albums = view_albums() # this was also added for the else statement
	if request.method == 'POST':
		uid = getUserIdFromEmail(flask_login.current_user.id)
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		album = request.form.get('album')   # code modified here and in execute statement to add album id, selection added in upload
		album_id = getAlbumId(album)
		
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption, album_id) VALUES (%s, %s, %s, %s )''', (photo_data, uid, caption, album_id))
		conn.commit()

		# incoporate tags 
		tags = request.form.get('tags')
		if (tags != None):
			tags = tags.split(',')
			for i in tags: 
				cursor.execute("INSERT INTO Tags (tag_description) VALUES ('{0}')".format(i))
				conn.commit()
				cursor.execute("INSERT INTO Photo_contain (tag_id, picture_id) VALUES ('{0}', '{1}')".format(getMaxTagID(), getMaxPictureId()))
				conn.commit()

		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html', data=albums)
	
# used to return most recently created picture id
def getMaxPictureId():
	cursor = conn.cursor()
	cursor.execute("SELECT MAX(picture_id) FROM Pictures")
	return cursor.fetchone()[0]

# used to return most recently created tag id
def getMaxTagID():
	cursor = conn.cursor()
	cursor.execute("SELECT MAX(tag_id) FROM Tags")
	return cursor.fetchone()[0]

@app.route('/pictures', methods=['GET'])
def retrieve_tags(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT tag_description FROM tags WHERE tag_id IN (SELECT tag_id FROM Photo_contain WHERE picture_id = '{0}')".format(picture_id))
	return cursor.fetchall()
#end photo uploading code


#default page
@app.route("/", methods=['GET'])
@flask_login.login_required
def hello():
	return render_template('hello.html', message='Welcome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)


### new stuff:

######## FRIEND METHODS #########


# 	still need to make changes so friend search only appears when user is logged in
#	friend is added immediately upon finding them and hitting submit button

@app.route('/', methods=['GET','POST'])
def hello_friend_handler():
	try: 
		cmd = request.form.get('cmd')
		email = request.form.get('email')
		temp_email = request.form.get('hidden')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	if cmd == 'Search':
		return search_friends(email)
	elif cmd == 'Add Friend':
		return add_friends(temp_email)
	else:
		return friend_profile(temp_email)

@app.route('/')
def search_friends(email):
	
	test = isEmailUnique(email)
	if test:
		return render_template('hello.html', message='user does not exist')
	else: 
		super = getUserIdFromEmail(flask_login.current_user.id)
		sub = getUserIdFromEmail(email)
		if super == sub: # checks if searching for themselves
			return render_template('hello.html', message='cannot search for yourself')
		else: 
			return render_template('hello.html', message='user exists', show_add_view_btns = email)
		
# search for one particular user, adds to friends if user exists
@app.route('/')
@flask_login.login_required
def add_friends(email):
	cursor = conn.cursor()
	test =  isEmailUnique(email)

	if not test:
		#email exists
		super = getUserIdFromEmail(flask_login.current_user.id)
		sub = getUserIdFromEmail(email)
		if super == sub: # checks if searching for themselves
			return render_template('hello.html', message='cannot befriend yourself')
		elif alreadyFriends(super, sub): 
			return render_template('hello.html', message='already friends with this user')
		print(cursor.execute("INSERT INTO Friends (super_user_id, sub_user_id) VALUES ('{0}', '{1}')".format(int(super), int(sub))))
		conn.commit()
		return render_template('hello.html', message='user {0} added as a friend'.format(email))
	else:
		#email does not exist in database
		return render_template('hello.html', message='user does not exist')


#checks if user relationship is already in the table
def alreadyFriends(super, sub):
	cursor = conn.cursor()
	if cursor.execute("SELECT super_user_id  FROM Friends WHERE (super_user_id = '{0}' AND sub_user_id = '{1}')".format(super, sub)):
		#this means there are greater than zero entries with this relationship
		return True
	else:
		return False


# adds friends to array to be printed in html table
@app.route("/friends", methods=['GET'])
@flask_login.login_required
def friends():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT sub_user_id FROM Friends WHERE super_user_id = '{0}'".format(uid))
	friends = []
	for i in cursor:
		fid = i[0]
		friends.append(getEmailFromUserId(fid))
	return render_template('friends.html', data=friends)

#takes int of user id and returns email
def getEmailFromUserId(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT email FROM Users WHERE user_id = '{0}'".format(uid))
	return cursor.fetchone()[0]

@app.route("/friends", methods=['POST', 'GET'])
def friend_handler():
	email = request.form.get('hidden') 
	return friend_profile(email)

# view friends' profile with buttons to view their photos
@app.route("/friendProfile")
def friend_profile(email):
	uid = getUserIdFromEmail(email)
	name = getNameFromUserId(uid)
	if (name == None):
		name = email
	return render_template('friendProfile.html', name=name, photos=getUsersPhotos(uid), base64=base64)

def getUserIDFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Users WHERE email ='{0}'".format(email))
	return cursor.fetchone()[0]

def getNameFromUserId(uid): 
	cursor = conn.cursor() 
	cursor.execute("SELECT first_name, last_name FROM Users WHERE user_id= '{0}'".format(uid))
	fname = cursor.fetchone()[0]
	cursor.execute("SELECT last_name, last_name FROM Users WHERE user_id= '{0}'".format(uid))
	lname = cursor.fetchone()[0]
	return fname + " " + lname


######## END FRIEND METHODS #########



######## ALBUM METHODS ###########

@app.route("/album", methods=['GET'])
@flask_login.login_required
def album():
	albums = view_albums()
	return render_template('album.html', data=albums)

@app.route("/album", methods=['POST', 'GET'])
@flask_login.login_required
def album_handler():
	cmd = request.form.get("cmd")
	album = request.form.get('album') 
	if cmd == "View":
		return viewAlbumPage(album)
	elif cmd == "Delete":
		return delete_album(album)
	else:
		return create_album()


@app.route("/viewAlbum")
def viewAlbumPage(album):
	album_id = getAlbumId(album)
	uid = getUserIdFromEmail(flask_login.current_user.id)
	photos=getUsersPhotosFromAlbum(uid, album_id)
	return render_template('viewAlbum.html', album_name=album, photos=photos, base64=base64)

@app.route("/album")
def delete_album(album):
	album_id = getAlbumId(album)
	cursor = conn.cursor()
	print(cursor.execute("DELETE FROM Albums WHERE album_id = '{0}'".format(int(album_id))))
	conn.commit()
	return render_template('album.html', message="deleted", data=view_albums())

from datetime import date # need to move this to the top, but i wanted to keep new stuff in one place for now

@app.route("/album")
def create_album():
	try:
		album_name=request.form.get('album_name')

	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('album'))
	cursor = conn.cursor()
	test = albumExists(album_name)
	
	if not test:
		uid = getUserIdFromEmail(flask_login.current_user.id)
		doc = date.today()
		print(cursor.execute("INSERT INTO Albums (owner_id, album_name, date_of_creation) VALUES ('{0}', '{1}', '{2}')".format(int(uid), album_name, doc)))
		conn.commit()
		return render_template('album.html', message = 'album created', data=view_albums())
	else:
		return render_template('album.html', message='album under same name already exists', data=view_albums())

def view_albums():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT album_name FROM Albums WHERE owner_id = '{0}'".format(uid))
	albums = []
	for i in cursor:
		album = i[0]
		albums.append(album)
	return (albums)

def albumExists(album_name):
	#use this to check if an album has already been created
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	if cursor.execute("SELECT album_name  FROM Albums WHERE (album_name = '{0}' AND owner_id = '{1}')".format(album_name, uid)):
		#this means there are greater than zero entries with that album name for this user
		return True
	else:
		return False

def getAlbumId(album_name):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id  FROM Albums WHERE album_name = '{0}'".format(album_name))
	return cursor.fetchone()[0]


def getUsersPhotosFromAlbum(uid, album_id):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE (user_id = '{0}' AND album_id = '{1}')".format(uid, album_id))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]
### END OF ALBUM METHODS ###

### ACTIVITY METHODS ### 
@app.route("/activity", methods=['GET'])
def activity():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, SUM(posts_or_comments) as Total FROM (SELECT user_id, COUNT(*) as posts_or_comments FROM pictures GROUP BY user_id UNION ALL SELECT user_id, COUNT(*) as posts_or_comments FROM comments GROUP BY user_id) as combinted_table GROUP BY user_id ORDER BY Total DESC LIMIT 3")
	activity_dict = {}
	for i in cursor:
		activity_dict[getEmailFromUserId(i[0])] = i[1] 
	return render_template('activity.html', data=activity_dict, number='3')


# adds buttons to view friends' profiles
@app.route("/activity", methods=['POST', 'GET'])
def activity_handler():
	email = request.form.get('hidden') 
	return friend_profile(email)

@app.route("/friendProfile", methods=['Post','GET'])
def friendProfilePicture_handler():
	picture_id = request.form.get('hidden')
	return picture(picture_id)

### ACTIVITY ENDS ###

### PICTURE METHODS ###
@app.route("/viewAlbum", methods=['Post','GET'])
def albumPicture_handler():
	picture_id = request.form.get('hidden')
	return picture(picture_id)

@app.route("/picture")
def picture(picture_id): 
	photo = getPhotoFromPictureID(picture_id)
	# styling to display email that posted picture
	name = getNameFromPictureID(picture_id)
	# load in comments of picture
	comment = retrieve_comments(picture_id)
	# load in tags
	tags = retrieve_tags(picture_id)
	return render_template('picture.html', photo=photo, name = name, comment=comment, tags=tags, base64=base64)

def getPhotoFromPictureID(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchone()

def getNameFromPictureID(picture_id):
	userid = getUserIDFromPictureID(picture_id)
	name = getNameFromUserId(userid)
	if (name == None):
		name = getEmailFromUserId(userid)
	return name

def getUserIDFromPictureID(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	return cursor.fetchone()[0]

### PICTURE METHODS END ###

### COMMENT METHODS ###
	
@app.route("/picture", methods=['Post','GET'])
def insert_comment():
	# fields to update with comments
	picture_id = request.form.get('hidden')
	text = request.form.get('comment')
	uid = getUserIDFromEmail(flask_login.current_user.id)
	doc = date.today()

	photo = getPhotoFromPictureID(picture_id)
	name = getNameFromPictureID(picture_id)

	# update new comments page
	comment = retrieve_comments(picture_id)

	# check if user is trying to comment on their own picture
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	owner_id = cursor.fetchone()[0]
	if (owner_id == uid): 
		return render_template('picture.html', err_message='You cannot comment on your own picture.', photo=photo, name=name, comment=comment, base64=base64)
	# retrieve original fields 

	# insert into database if the passes conditional
	print(cursor.execute("INSERT INTO Comments (picture_id, user_id, text_comment, date_of_comment) VALUES ('{0}','{1}','{2}','{3}')".format(picture_id, uid, text, doc)))
	conn.commit()
	return render_template('picture.html', photo=photo, name=name, comment=comment, base64=base64)

@app.route("/picture", methods=['GET'])
def retrieve_comments(picture_id):
	picture_id = picture_id
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, text_comment FROM Comments WHERE picture_id = '{0}'".format(picture_id))
	comment_dict = {}
	for i in cursor: 
		comment_dict[i[1]] = getEmailFromUserId(i[0])
	return comment_dict

### COMMENT METHODS END ###


### end of new stuff