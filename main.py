from flask import Flask, render_template, redirect, url_for, flash, abort, request, flash,send_from_directory

from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_wtf.file import FileField, FileRequired
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import LoginForm, RegisterForm, CreatePostForm, CommentForm
from flask_gravatar import Gravatar
import os
import psycopg2
from PIL import Image

from werkzeug.utils import secure_filename

UPLOAD_FOLDER = '../FlaskBlogProject/static/img/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#connecting postregs database with environmental variables
#app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
#app.config["SQLALCHEMY_DATABASE_URI"] =  os.getenv('DB')

ckeditor = CKEditor(app)
Bootstrap(app)
gravatar = Gravatar(app, size=100, rating='g', default='retro', force_default=False, force_lower=False, use_ssl=False, base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///TravelBlog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'



db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


##CONFIGURE TABLE
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))
    posts = relationship("BlogPost", back_populates="author")
    comments = relationship("Comment", back_populates="comment_author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)

    start = db.Column(db.String(250), nullable=False)
    end = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_local = db.Column(db.String(250))
   # img_url = db.Column(db.String(250), nullable=True)
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)

class Photos(db.Model):
    __tablename__ = "photos"
    id = db.Column(db.Integer, primary_key=True)
    img = db.Column(db.String(250), nullable=True)

with app.app_context():
    db.create_all()


def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.id != 1:
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, current_user=current_user)


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first():
            print(User.query.filter_by(email=form.email.data).first())
            #User already exists
            flash("You've already signed up with that email, log in instead!")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            form.password.data,
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=form.email.data,
            name=form.name.data,
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("That email does not exist, please try again.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('Password incorrect, please try again.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)


    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
            return redirect(url_for("login"))

        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()

    return render_template("post.html", post=requested_post, form=form, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)



    #todo 1: add submit for the uploaded that saves upload in img local
'''
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        source = f'../FlaskBlogProject/static/img/uploads/{filename}'

        # convert file smaller and delete the original one
        image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image.save(source, 'JPEG', quality=30)
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # f.save(dst="FlaskBlogProject/static/uploads",secure_filename(f.filename))
        # f.save(secure_filename(f.filename))

        # todo 1. DB hinzufügen die die Bilder speicher
        # todo 2. DB werden die Adresse der Bilder hinzufgefügt als String
        # todo 3. Bild an post knüpfen
        place = "img/uploads/" + filename
        new_photo = Photos(
            img=place
        )

       # db.session.add(new_photo)
       # db.session.commit()

        # todo file pfad aus db bekommen


'''
###
# todo wenn du upload edits kommen manchmal nicht die bilder an im post. Warum ist das so denn in der Gallerie sieht alles gut aus??
###

@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        photo = form.img_local.data
        filename = secure_filename(photo.filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
       # math.ran
        #os.rename()
        image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        source = f'../FlaskBlogProject/static/img/uploads/{filename}'
        image.save(source, 'JPEG', quality=30)

        # todo 1. upload
        # todo 2. rename to something dynamic if not not exists
        # todo 3. save in db img_local

        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        place = "img/uploads/" + filename
        print(place)
        print(source)
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            start=form.start.data,
            end=form.end.data,
            body=form.body.data,
            #img_url=form.img_url.data,
            img_local = place,
            author=current_user,

        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form, current_user=current_user)




@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)

    #todo delete old photo
    img_old = post.img_local


    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
       # img_url=post.img_url,
        img_local=post.img_local,
        start = post.start,
        end = post.end,
        author=current_user,
        body=post.body
    )
    #
    if edit_form.validate_on_submit():
        #photo =  edit_form.img_local.data.filename
        #old_name = old_name.split("/")

       # if  old_name[2] !=photo:


         #   print(photo)

          #  print(old_name[2])

           # os.rename(remo, "old")
            #os.remove(remo)
            # todo wenn es ungleich ist dann haben wir ein neues phot und löschen also
            # rename new_photo to old_photo

          #  post.img_local =photo

        photo = edit_form.img_local.data
        filename = edit_form.img_local.data.filename
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        source = f'../FlaskBlogProject/static/img/uploads/{filename}'
        image.save(source, 'JPEG', quality=30)
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        place = "img/uploads/" + filename


        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.subtitle = edit_form.subtitle.data
       # post.img_url = edit_form.img_url.data
       # post.img_local = edit_form.img_local.data.

       # place = "img/uploads/" + filename
        post.img_local = place
        post.start = edit_form.start.data
        post.end = edit_form.end.data
        post.body = edit_form.body.data
        db.session.commit()

        remo = f"../FlaskBlogProject/static/{img_old}"
        os.remove(remo)
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))



@app.route("/author/<name>",methods = ["GET", "POST"])
def show_author(name):
    author_posts = BlogPost.query.all()
    return render_template("author.html", all_posts=author_posts, author = name, current_user=current_user)

    # alle posts des authors anzeigen
     
    #author_posts = db.session.query(BlogPost).filter(BlogPost.author.name == name).all()
    


@app.route("/gallery",methods = ["GET", "POST"])
def show_gallery():
    main = db.session.query(BlogPost).all()

    return render_template("gallery.html", main = main, current_user=current_user)

app.add_url_rule(
    "/uploads/<name>", endpoint="download_file", build_only=True
)



##old testing route
@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        file = request.files['file']
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        source = f'../FlaskBlogProject/static/img/uploads/{filename}'

        # convert file smaller and delete the original one
        image = Image.open(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        image.save(source,'JPEG', quality=30)
        full_filename = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        #f.save(dst="FlaskBlogProject/static/uploads",secure_filename(f.filename))
      #f.save(secure_filename(f.filename))

        #todo 1. DB hinzufügen die die Bilder speicher
        #todo 2. DB werden die Adresse der Bilder hinzufgefügt als String
        #todo 3. Bild an post knüpfen
        place = "img/uploads/" + filename
        new_photo = Photos(
            img = place
        )

        db.session.add(new_photo)
        db.session.commit()


        #todo file pfad aus db bekommen

        return render_template('uploaded.html', show = place)

    return render_template('upload.html')



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
