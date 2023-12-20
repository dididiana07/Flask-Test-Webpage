from datetime import date
import sqlalchemy.exc
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from forms import CreatePostForm, RegisterForms, LoginForms, CommentForms

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap5(app)

# CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///posts.db'
db = SQLAlchemy()

db.init_app(app)

gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

# LOGIN MANAGER

login_manager = LoginManager(app)
login_manager.login_view = "login.html"

# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, unique=False)
    username = db.Column(db.String, nullable=False, unique=True)
    email = db.Column(db.String,  nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    user_comments = db.relationship('Comments', backref='users', lazy=True)



class Comments(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    article_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))



@login_manager.user_loader
def load_usee(user_id):
    return Users.query.filter_by(id=user_id).first()

@app.route('/register', methods=["POST", "GET"])
def register():
    try:
        if current_user.is_authenticated:
            return redirect(url_for("get_all_posts"))
    except AttributeError:
        pass
    forms = RegisterForms()
    if forms.validate_on_submit():
        username = forms.username.data
        name = forms.name.data
        email = forms.email.data
        password = forms.password.data
        new_user = Users(name=name,
                         username=username,
                         email=email,
                         password=generate_password_hash(password))
        db.session.add(new_user)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            abort(400, f"{email} already in use.")
        else:
            login_user(new_user)
            return redirect(url_for("get_all_posts"))
    return render_template("register.html", forms=forms)



@app.route('/login', methods=["GET", 'POST'])
def login():
    try:
        if current_user.is_authenticated:
            return redirect(url_for("get_all_posts"))
    except AttributeError:
        pass
    else:
        forms = LoginForms()
        if forms.validate_on_submit():
            email = forms.email.data
            password = forms.password.data
            try:
                user = Users.query.filter_by(email=email).first()
                password_hash = user.password
                if check_password_hash(password_hash, password):
                    login_user(user)
                    return redirect(url_for("get_all_posts"))
            except AttributeError:
                abort(404,"User Not Found")
        return render_template("login.html", forms=forms)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()
    if current_user.is_authenticated:
        flash(f"{current_user.name} welcome!")
    return render_template("index.html", all_posts=posts)



@app.route("/post/<int:post_id>", methods=["POST", "GET"])
def show_post(post_id):
    requested_post = db.get_or_404(BlogPost, post_id)
    comments = CommentForms()
    all_comments = Comments.query.filter_by(article_id=post_id).all()
    if comments.validate_on_submit():
        new_comment = Comments(comment=comments.comment.data,
                               username=current_user.username,
                               article_id=post_id,
                               user_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for("show_post", post_id=post_id))
    return render_template("post.html", post=requested_post, forms=comments, comments=all_comments)



@app.route("/new-post", methods=["GET", "POST"])
def add_new_post():
    try:
        if current_user.is_authenticated and current_user.id != 1:
            return redirect(url_for("get_all_posts"))
    except AttributeError:
        pass
    else:
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
        return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    try:
        if current_user.is_authenticated and current_user.id != 1:
            return redirect(url_for("get_all_posts"))
    except AttributeError:
        pass
    else:
        post = db.get_or_404(BlogPost, post_id)
        edit_form = CreatePostForm(
                title=post.title,
                subtitle=post.subtitle,
                img_url=post.img_url,
                author=post.author,
                body=post.body
            )
        if edit_form.validate_on_submit():
            post.title = edit_form.title.data
            post.subtitle = edit_form.subtitle.data
            post.img_url = edit_form.img_url.data
            post.author = current_user
            post.body = edit_form.body.data
            db.session.commit()
            return redirect(url_for("show_post", post_id=post.id))
        return render_template("make-post.html", form=edit_form, is_edit=True)



@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    try:
        if current_user.is_authenticated and current_user.id != 1:
            return redirect(url_for("get_all_posts"))
    except AttributeError:
        pass
    else:
        post_to_delete = db.get_or_404(BlogPost, post_id)
        db.session.delete(post_to_delete)
        db.session.commit()
        return redirect(url_for('get_all_posts'))

@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


if __name__ == "__main__":
    app.run(debug=True, port=5002)
