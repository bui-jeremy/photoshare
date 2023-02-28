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
from flask_login import AnonymousUserMixin

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

class Anonymous(AnonymousUserMixin):
  def __init__(self):
    self.username = 'Anonymous'
    
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
	uid = getUserIDFromEmail(flask_login.current_user.id)
	photos = getUsersPhotos(uid)
	print(photos)
	return render_template('hello.html', name=flask_login.current_user.id, photos=photos, message="Here's your profile", base64=base64)

#begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	albums = view_albums(uid) # this was also added for the else statement
	if request.method == 'POST':
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
		if (tags != ""):
			tags = tags.split(',')
			for i in tags: 
				if not tagExists(i):
					cursor.execute("INSERT INTO Tags (tag_description) VALUES ('{0}')".format(i))
					conn.commit()
				cursor.execute("INSERT INTO Photo_contain (tag_id, picture_id) VALUES ('{0}', '{1}')".format(getIDFromTagDescription(i), getMaxPictureId()))
				conn.commit()

		return render_template('hello.html', name=flask_login.current_user.id, message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html', data=albums)
	
@app.route('/recommendation', methods=['GET'])
def pictureRecommendations():
	pictures = getPictureRecsInOrder()
	return render_template('pictureRecommend.html', pictures=pictures, base64=base64)

# gets current user's top 3 tags in order
def getCurrentUserTopTags():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Pictures NATURAL JOIN Photo_contain NATURAL JOIN Tags WHERE (user_id = '{0}') \
					GROUP BY tag_id ORDER BY COUNT(tag_id) DESC LIMIT 3".format(uid))
	conn.commit()
	tags = []
	for i in cursor:
		tags.append(i[0])
		print(i)
	return tags


# gets picture recommendations, in sql orders first by how many tags and then conciseness (calculates difference)
def getPictureRecsInOrder():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	tags = getCurrentUserTopTags()
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, pid, caption FROM \
					(SELECT picture_id as pid, imgdata, caption, COUNT(picture_id) AS specified_tags FROM Pictures NATURAL JOIN Photo_contain WHERE (tag_id = '{0}' OR tag_id = '{1}' OR tag_id = '{2}') AND user_id != '{3}' \
					GROUP BY picture_id) t1 \
					NATURAL JOIN \
					(SELECT picture_id as pid, COUNT(picture_id) AS all_tags FROM Pictures NATURAL JOIN Photo_contain \
					GROUP BY picture_id) t2 \
					ORDER BY specified_tags DESC, t2.all_tags-t1.specified_tags ".format(tags[0], tags[1], tags[2], uid))
	conn.commit()
	return cursor.fetchall()

def tagExists(description):
	cursor = conn.cursor()
	if cursor.execute("SELECT tag_id  FROM Tags WHERE (tag_description = '{0}')".format(description)):
		#this means there are greater than zero entries with this relationship
		return True
	else:
		return False

def getIDFromTagDescription(description):
	cursor = conn.cursor()
	cursor.execute("SELECT tag_id FROM Tags WHERE tag_description = '{0}'".format(description))
	return cursor.fetchone()[0]

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
	cursor.execute("SELECT tag_description FROM Tags WHERE tag_id IN (SELECT tag_id FROM Photo_contain WHERE picture_id = '{0}')".format(picture_id))
	tags = []
	for i in cursor:
		tags.append(i[0])
	return tags
#end photo uploading code


#default page
@app.route("/", methods=['GET'])
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
		photo_id = request.form.get('photo_id')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	if cmd == 'Search':
		return search_friends(email)
	elif cmd == 'Add Friend':
		return add_friends(temp_email)
	elif photo_id != None: 
		return picture(photo_id)
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
	friends = get_friends(uid)
	recommended = friends_of_friends()
	requested = added_by()
	return render_template('friends.html', data=friends, recommended=recommended, requested=requested)

def get_friends(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT sub_user_id FROM Friends WHERE super_user_id = '{0}'".format(uid))
	friends = []
	for i in cursor:
		fid = i[0]
		friends.append(getEmailFromUserId(fid))
	return friends

#takes int of user id and returns email
def getEmailFromUserId(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT email FROM Users WHERE user_id = '{0}'".format(uid))
	return cursor.fetchone()[0]

@app.route("/friends", methods=['POST', 'GET'])
def friend_handler():
	email = request.form.get('hidden') 
	uid = getUserIdFromEmail(email)
	data = view_albums(uid)
	return friend_profile(email,data)

# view friends' profile with buttons to view their photos
@app.route("/friendProfile")
def friend_profile(email, data):
	uid = getUserIdFromEmail(email)
	name = getNameFromUserId(uid)
	if (name == None):
		name = email
	return render_template('friendProfile.html', name=name, photos=getUsersPhotos(uid), data=data, base64=base64)

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

# recommends friends (top 10 friends of friends, sorts by how many times the user is found in other friend lists)
def friends_of_friends():
	email = flask_login.current_user.id
	uid = getUserIdFromEmail(flask_login.current_user.id)
	friends = get_friends(uid)
	mutual_friends = {}

	for i in friends: # runs through all friends of user
		fid = getUserIDFromEmail(i)
		cursor = conn.cursor()
		cursor.execute("SELECT sub_user_id FROM Friends WHERE super_user_id = '{0}'".format(fid))
		if cursor.rowcount > 0:
			for j in cursor: # nested loop checks for duplicates, adds to count of how many times a user has been found
				mfid = j[0] # friend of friend's id
				user = getEmailFromUserId(mfid)
				if (user != email) and (user not in friends) :
					try:
						mutual_friends[user] += 1
					except:
						mutual_friends[user] = 1
						
	mutual_friends_sorted = dict(sorted(mutual_friends.items(), key = lambda x:x[1], reverse = True)) # sort by value

	return list(mutual_friends_sorted)[:10]

def added_by():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	cursor = conn.cursor() 
	cursor.execute("SELECT super_user_id FROM Friends WHERE sub_user_id= '{0}'".format(uid))
	added = []
	for i in cursor:
		fid = i[0]
		if not alreadyFriends(uid, fid):
			added.append(getEmailFromUserId(fid))
	return added


######## END FRIEND METHODS #########
	

######## ALBUM METHODS ###########

@app.route("/album", methods=['GET'])
@flask_login.login_required
def album():
	uid = getUserIdFromEmail(flask_login.current_user.id)
	albums = view_albums(uid)
	return render_template('album.html', data=albums)

@app.route("/album", methods=['POST', 'GET'])
@flask_login.login_required
def album_handler():
	cmd = request.form.get("cmd")
	album = request.form.get('album') 
	uid = getUserIdFromEmail(flask_login.current_user.id)
	if cmd == "View":
		return viewAlbumPage(album, "", uid)
	elif cmd == "Delete":
		return delete_album(album)
	else:
		return create_album()


@app.route("/viewAlbum")
def viewAlbumPage(album, message, uid, name = None):
	album_id = getAlbumId(album)
	photos=getUsersPhotosFromAlbum(uid, album_id)
	return render_template('viewAlbum.html', album_name=album, message=message, photos=photos, name=name, base64=base64)

@app.route("/album")
def delete_album(album):
	album_id = getAlbumId(album)
	uid = getUserIDFromAlbumID(album_id)
	cursor = conn.cursor()
	print(cursor.execute("DELETE FROM Albums WHERE album_id = '{0}'".format(int(album_id))))
	conn.commit()
	return render_template('album.html', message="deleted", data=view_albums(uid))

def getUserIDFromAlbumID(album_id):
	cursor = conn.cursor()
	cursor.execute("SELECT owner_id FROM Albums WHERE album_id = '{0}'".format(album_id))
	return cursor.fetchone()[0]

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
		return render_template('album.html', message = 'album created', data=view_albums(uid))
	else:
		return render_template('album.html', message='album under same name already exists', data=view_albums(uid))

def view_albums(uid):
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
	if cursor.execute("SELECT album_name FROM Albums WHERE (album_name = '{0}' AND owner_id = '{1}')".format(album_name, uid)):
		#this means there are greater than zero entries with that album name for this user
		return True
	else:
		return False

def getAlbumId(album_name):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Albums WHERE album_name = '{0}'".format(album_name))
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
	cursor.execute("SELECT user_id, SUM(posts_or_comments) as Total FROM (SELECT user_id, COUNT(*) as posts_or_comments FROM pictures WHERE user_id IS NOT NULL GROUP BY user_id UNION ALL SELECT user_id, COUNT(*) as posts_or_comments FROM comments WHERE user_id IS NOT NULL GROUP BY user_id) as combinted_table GROUP BY user_id ORDER BY Total DESC LIMIT 3")
	activity_dict = {}
	for i in cursor:
		activity_dict[getEmailFromUserId(i[0])] = i[1] 
	return render_template('activity.html', data=activity_dict, number='3')


# adds buttons to view friends' profiles
@app.route("/activity", methods=['POST', 'GET'])
def activity_handler():
	email = request.form.get('hidden') 
	uid = getUserIdFromEmail(email)
	data = view_albums(uid)
	return friend_profile(email, data)

@app.route("/friendProfile", methods=['Post','GET'])
def friendProfile_handler():
	picture_id = request.form.get('hidden')
	album = request.form.get('album')

	cmd = request.form.get('cmd')
	if cmd == "View":
		album_id = getAlbumId(album)
		profile_uid = getUserIDFromAlbumID(album_id)
		name = getNameFromUserId(profile_uid)
		return viewAlbumPage(album, "", profile_uid, name)
	else:
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
	# load in likes and users
	num_likes, users_liked = count_likes(picture_id)
	owner = (getUserIDFromPictureID(picture_id) == getUserIDFromEmail(flask_login.current_user.id))
	user_id = getUserIDFromPictureID(picture_id)
	return render_template('picture.html', photo=photo, name = name, comment=comment, user_id=user_id, num_likes=num_likes, users_liked=users_liked, owner = owner, tags=tags, base64=base64)

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

@app.route("/picture")
def delete_photo():
	picture_id = request.form.get('hidden')
	album_id = getAlbumIDFromPhotoID(picture_id)
	uid = getUserIDFromEmail(flask_login.current_user.id)
	album = getAlbumNameFromAlbumID(album_id)
	cursor = conn.cursor()
	print(cursor.execute("DELETE FROM Pictures WHERE picture_id = '{0}'".format(int(picture_id))))
	conn.commit()
	return viewAlbumPage(album, "Photo deleted!", uid)

def getAlbumIDFromPhotoID(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT album_id FROM Pictures WHERE picture_id = '{0}'".format(int(picture_id)))
	return cursor.fetchone()[0]

def getAlbumNameFromAlbumID(album_id):
	cursor = conn.cursor()
	cursor.execute("SELECT album_name FROM Albums WHERE album_id = '{0}'".format(int(album_id)))
	return cursor.fetchone()[0]

### PICTURE METHODS END ###

### COMMENT METHODS ###
	
@app.route("/picture")
def insert_comment():
	# fields to update with comments
	picture_id = request.form.get('hidden')
	text = request.form.get('comment')

	if (flask_login.current_user.id == "Anonymous"):
		uid = None
	else: 
		uid = getUserIDFromEmail(flask_login.current_user.id)
	doc = date.today()

	photo = getPhotoFromPictureID(picture_id)
	name = getNameFromPictureID(picture_id)
	tags = retrieve_tags(picture_id)
	num_likes, users_liked = count_likes(picture_id)
	owner = (getUserIDFromPictureID(picture_id) == getUserIDFromEmail(flask_login.current_user.id))

	# check if user is trying to comment on their own picture
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Pictures WHERE picture_id = '{0}'".format(picture_id))
	owner_id = cursor.fetchone()[0]
	if (owner_id == uid): 
		comment = retrieve_comments(picture_id)
		return render_template('picture.html', err_message='You cannot comment on your own picture.', owner=owner, photo=photo, name=name, comment=comment, tags=tags, users_liked=users_liked, num_likes=num_likes, base64=base64)
	# retrieve original fields 
	# insert into database if the passes conditional
	if (uid != None): 
		print(cursor.execute("INSERT INTO Comments (picture_id, user_id, text_comment, date_of_comment) VALUES ('{0}','{1}','{2}','{3}')".format(picture_id, uid, text, doc)))
	else: 
		print(cursor.execute("INSERT INTO Comments (picture_id, text_comment, date_of_comment) VALUES ('{0}','{1}','{2}')".format(picture_id, text, doc)))
	conn.commit()

	# update new comments page
	comment = retrieve_comments(picture_id)
	print(comment)
	return render_template('picture.html', owner=owner, photo=photo, name=name, comment=comment, tags=tags, users_liked=users_liked, num_likes=num_likes, base64=base64)

@app.route("/picture", methods=['GET'])
def retrieve_comments(picture_id):
	picture_id = picture_id
	cursor = conn.cursor()
	cursor.execute("SELECT user_id, text_comment, date_of_comment FROM Comments WHERE picture_id = '{0}'".format(picture_id))
	comment = []
	for i in cursor: 
		if (i[0] == None):
			comment.append(('Anonymous',i[1],i[2]))
		else:
			comment.append((getEmailFromUserId(i[0]),i[1],i[2]))
	return comment

### COMMENT METHODS END ###

### LIKE METHODS ###

def count_likes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Liked_by WHERE picture_id = '{0}'".format(picture_id))
	conn.commit()
	users_liked = []
	num_likes = 0
	for i in cursor:
		fid = i[0]
		users_liked.append(getEmailFromUserId(fid))
		num_likes += 1
	return (num_likes, users_liked)

@app.route("/picture")
def like_photo():
	picture_id = request.form.get('hidden')
	uid = getUserIDFromEmail(flask_login.current_user.id)
	cursor = conn.cursor()
	if already_liked(picture_id, uid): 
		photo = getPhotoFromPictureID(picture_id)
		name = getNameFromPictureID(picture_id)
		num_likes, users_liked =count_likes(picture_id)
		comment = retrieve_comments(picture_id)
		tags = retrieve_tags(picture_id)
		owner = (getUserIDFromPictureID(picture_id) == getUserIDFromEmail(flask_login.current_user.id))
		user_id = getUserIDFromPictureID(picture_id)
		return render_template('picture.html', err_message='Already Liked!', owner=owner, photo=photo, name=name, user_id = user_id, comment=comment, tags=tags, users_liked=users_liked, num_likes=num_likes, base64=base64)
	cursor.execute("INSERT INTO Liked_by (user_id, picture_id) VALUES ('{0}', '{1}')".format(uid, picture_id))
	conn.commit()
	return picture(picture_id)

def already_liked(picture_id, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT picture_id  FROM Liked_by WHERE (picture_id = '{0}' AND user_id = '{1}')".format(picture_id, uid)):
		#this means there are greater than zero entries with that album name for this user
		return True
	else:
		return False
	
@app.route("/picture", methods=['POST', 'GET'])
def picture_handler():
	cmd = request.form.get("cmd")
	user_id = request.form.get("user_id")
	print('hi')
	print(user_id)
	if cmd == "Like":
		return like_photo()
	elif cmd == "Delete Photo":
		return delete_photo()
	else: 
		# check to see if a tag is clicked on
		tag = request.form.get("tag")
		if (tag != None):
			return tagPictures(tag, user_id)
		else:
	 		return insert_comment() # hit button to submit comment
	
### RECOMMENDED USERS ###
@app.route("/pictureRecommend", methods=['GET'])
def recommendation():
	conn.cursor()
	cursor.execute("SELECT uid FROM friends INNER JOIN user on friends.")

### COMMENT SEARCH ###
@app.route("/commentSearch", methods=['GET', 'POST'])
def commentSearch():
	search = request.form.get('search')
	conn.cursor()
	cursor.execute("SELECT user_id, COUNT(*) AS comment_count FROM Comments WHERE text_comment='{0}' AND user_id IS NOT NULL GROUP BY user_id ORDER BY comment_count DESC".format(search))
	users = {}
	for i in cursor:
		users[getNameFromUserId(i[0])] = (getEmailFromUserId(i[0]), i[1])
	return render_template('commentSearch.html', name=search, users = users)

### END OF COMMENT SEARCH ###

### TAG VIEW ###

# view tags by clicking on them in the picture page
@app.route("/tagPictures")
def tagPictures(tag_description, user_id):
	conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption, user_id FROM Pictures WHERE user_id = '{0}' AND picture_id IN (SELECT picture_id FROM photo_contain WHERE tag_id IN (SELECT tag_id FROM Tags WHERE tag_description = '{1}'))".format(user_id, tag_description))
	data = cursor.fetchall()
	personal = getNameFromUserId(user_id)
	return render_template('tagPictures.html', photos = data, personal=personal, name = tag_description, base64 = base64)


def getTagIdFromDescription(tag_description):
	conn.cursor()
	cursor.execute("SELECT picture_id FROM photo_contain WHERE tag_id IN (SELECT tag_id FROM Tags WHERE tag_description = '{0}')".format(tag_description))
	return cursor.fetchall()[0]

@app.route("/tagPictures", methods=['GET', 'POST'])
def tagPicture_handler():
	picture_id = request.form.get('hidden')
	return picture(picture_id)

# handle different buttons on tagSearch page
@app.route("/tagSearch", methods=['GET', 'POST'])
def tagSearch_handler():
	try:
		cmd = request.form.get("cmd")
		tag = request.form.get("tag")
		search = request.form.get("search")
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	# split the potential string of tags into a list

	if (cmd == "Search"):
		if (search != ""):
			search = search.split(',')
		return displayAllPhotos(search)
	elif (tag != None): 
		return displayAllPhotos([tag])
	else:
		return getTopTags()
	
# refresh page with all the photos that have the tag
@app.route("/tagSearch")
def displayAllPhotos(tag_description):
	# combine into tuples of string ex "Hello","World"
	tag_list = []
	for tag in tag_description:
		tag_list.append("'" + tag + "'")
	size_list = len(tag_list)
	tag_list = ",".join(tag_list)

	conn.cursor()
	cursor.execute(''' 
					   SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id IN
					   (SELECT picture_id FROM photo_contain 
					   JOIN tags on photo_contain.tag_id = tags.tag_id 
					   WHERE tags.tag_description in ({0}) GROUP BY photo_contain.picture_id 
					   HAVING COUNT(DISTINCT tags.tag_id) =  {1} )'''.format(tag_list, size_list))
	data = cursor.fetchall()
	return render_template('tagSearch.html', photos = data, name = tag_list, base64 = base64)

def findAllPictureIDs(tag_list, size_list):
	conn.cursor()
	cursor.execute(''' 
					   SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id IN
					   (SELECT picture_id FROM photo_contain 
					   JOIN tags on photo_contain.tag_id = tags.tag_id 
					   WHERE tags.tag_description in ({0}) GROUP BY photo_contain.picture_id 
					   HAVING COUNT(DISTINCT tags.tag_id) =  {1} )'''.format(tag_list, size_list))
	return cursor.fetchall()

# return top 3 most used tags
def getTopTags():
	conn.cursor()
	cursor.execute("SELECT tag_description, COUNT(*) AS tag_count FROM Tags WHERE tag_id IN (SELECT tag_id FROM photo_contain) GROUP BY tag_description ORDER BY tag_count DESC LIMIT 3")
	tags = {}
	for i in cursor:
		tags[i[0]] = i[1]
	return render_template('tagSearch.html', tags = tags)


### END TAG VIEW ###

### PHOTO RECOMMENDATIONS ###




### end of new stuff