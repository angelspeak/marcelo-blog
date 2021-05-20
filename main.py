from flask import Flask, render_template, redirect, url_for, flash, request
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import flask
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
LOGIN_DISABLED = False

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("VAR_NAME")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


##CONFIGURE TABLES

class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)
    name = db.Column(db.String(250), unique=True, nullable=False)
    #This will act like a List of BlogPost objects attached to each User.
    #The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    #Create Foreign Key, "users.id" the users refers to the __tablename__ of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    #Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    #This will act like a List of Comment objects attached to each BlogPost.
    #The "post" refers to the post property in the Comment class.
    comments = relationship("Comment", back_populates="post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    #Create Foreign Key, "blog_posts.id" the users refers to the __tablename__ of User.
    blog_post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    comment_text = db.Column(db.Text, nullable=False)
    #Create reference to the BlogPost object, the "comments" refers to the comments property in the Blogpost class.
    post = relationship("BlogPost", back_populates="comments")


db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, user=current_user)


#admin only decorator
def admin_only(f):
    def decorated_function(*args, **kwargs):
        print(current_user)
        if current_user is None:
            flask.abort(403)
        else:
            if current_user.id != 1:
                flask.abort(403)
        return f(*args, **kwargs)

    return decorated_function


@app.route('/register', methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if request.method == "POST":
        if form.validate_on_submit():
            password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
            new_user = User(
                id=None,
                email=form.email.data,
                password=password,
                name=form.name.data
            )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('get_all_posts'))
    return render_template('register.html', form=form)


# called by the login manager. it queries the user by id in the database,
# it returns None if none are found
@login_manager.user_loader
def load_user(id):
    try:
        user = User.query.get(id)
        return user
    except:
        return None


# if the user tries to access a page or a resource whose access is
# restricted by the @login_required decorator, he/she is redirected
# to the login page instead of getting an "Unauthorized" message.
@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login')


@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if request.method == "POST":
        if form.validate_on_submit():
            email = request.form["email"]
            password = request.form["password"]
            try:
                user = db.session.query(User).filter(User.email == email).one()
            except:
                return flask.render_template('login.html')
            pwhash = user.password
            if check_password_hash(pwhash=pwhash, password=password):
                login_user(user)
                return redirect(url_for('get_all_posts'))
    return render_template("login.html", form=form)


# logout_user() logs the user out. logout() then redirects the user
# to the home page (get_all_posts)
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)

    if comment_form.validate_on_submit():
        new_comment = Comment(
            comment_text=comment_form.comment_text.data,
            blog_post_id=post_id
        )
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("get_all_posts"))

    return render_template("post.html", post=requested_post, current_user=current_user, form=comment_form)

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@admin_only
@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@admin_only
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@admin_only
@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))





if __name__ == "__main__":
    # app.run(host='127.0.0.1', port=5000)
    app.run(debug=True)
