CREATE DATABASE IF NOT EXISTS photoshare;
USE photoshare;

CREATE TABLE Users (
    user_id int4 AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE,
    password varchar(255),
	dob DATE,
    first_name CHAR(27),
    last_name CHAR(27),
    hometown VARCHAR(255),
    gender VARCHAR(255),
	CONSTRAINT users_pk PRIMARY KEY (user_id)
);


CREATE TABLE Albums( 
	album_id int4 AUTO_INCREMENT, 
    owner_id int4,
    album_name VARCHAR(255),
    date_of_creation DATE,
    CONSTRAINT album_pk PRIMARY KEY (album_id),
	FOREIGN KEY (owner_id) REFERENCES Users(user_id) ON DELETE CASCADE

);

CREATE TABLE Pictures
(
  picture_id int4  AUTO_INCREMENT,
  user_id int4,
  num_likes INT,
  album_id int4,
  imgdata longblob ,
  caption VARCHAR(255),
  INDEX upid_idx (user_id),
  CONSTRAINT pictures_pk PRIMARY KEY (picture_id),
  FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE CASCADE,
  CONSTRAINT num_likes_check CHECK (num_likes >= 0)
);

CREATE TABLE Comments(
	comment_id int4,
    picture_id int4,
    user_id int4, 
    text_comment VARCHAR(255), 
    date_of_comment DATE,
	CONSTRAINT comment_pk PRIMARY KEY (comment_id),
	FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id) ON DELETE CASCADE
);

CREATE TABLE Tags(
	tag_id int4,
    tag_description VARCHAR(255),
    CONSTRAINT tags_pk PRIMARY KEY (tag_id)
);

CREATE TABLE Photo_contain(
	picture_id int4,
	tag_id int4, 
    PRIMARY KEY (picture_id, tag_id),
    FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id),
    FOREIGN KEY (tag_id) REFERENCES Tags(tag_id)
);

CREATE TABLE Liked_by(
	user_id int4,
    picture_id int4,
    PRIMARY KEY (user_id, picture_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (picture_id) REFERENCES Pictures(picture_id)
);

CREATE TABLE Friends(
	super_user_id int4,
    sub_user_id int4,
    PRIMARY KEY (super_user_id, sub_user_id),
    CONSTRAINT friendship_super FOREIGN KEY (super_user_id) REFERENCES Users(user_id),
    CONSTRAINT friendship_sub FOREIGN KEY (sub_user_id) REFERENCES Users(user_id)
);