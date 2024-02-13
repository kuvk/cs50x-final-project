from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, SelectField, IntegerField, DateField
from wtforms.validators import DataRequired, EqualTo
from wtforms.widgets import TextArea, NumberInput

''' Forms '''

# Login Form
class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(message='Username field is required!')])
    password = PasswordField("Password", validators=[DataRequired(message='Password field is required!')])
    sign_in = SubmitField("Sign In")


# Users Form
class UsersForm(FlaskForm):
    name = StringField("Name")
    username = StringField("Username", validators=[DataRequired(message='Username field is required!')])
    password = PasswordField("Password", validators=[DataRequired(message='Password field is required!'), EqualTo('confirm', message='Passwords must match!')])
    confirm = PasswordField("Confirm password", validators=[DataRequired(message='Confirm password field is required!')])
    privilege = SelectField("Role", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Submit")


# Cards Form
class AddCardsForm(FlaskForm):
    card_label = StringField("Label", validators=[DataRequired(message="Card Label field is required!")])
    card_type = SelectField("Type", choices=[("video", "Video"), ("audio", "Audio")], validators=[DataRequired(message="Please select card type from offered options!")])
    card_qty = IntegerField("Qty", validators=[DataRequired(message="Quantity field is required!")])
    submit = SubmitField("Submit")


# Reporters Form
class ReportersForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired("Name field is required!")])
    submit = SubmitField("Submit")


# Days Form
class DaysForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(message='Name field is required!')])
    date = DateField("Date", format="%Y-%m-%d", validators=[DataRequired(message="Date field is required")])
    submit = SubmitField("Submit")


# Ingest Form
class IngestForm(FlaskForm):
    reporter = SelectField("Reporter", coerce=int)
    card = SelectField("Card", coerce=int)
    group = IntegerField("Group")
    equipment = StringField("Equip Label")
    info = StringField("Additional Information", widget=TextArea())
    operator = StringField("Equip Operator")
    clip_start = IntegerField("Clip Start", widget=NumberInput(min=1, max=9999))
    clip_end = IntegerField("Clip End", widget=NumberInput(min=1, max=9999))
    submit = SubmitField("Submit")
