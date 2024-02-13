# CS50 Final Project - Book of Ingest 
#### Description:
 
Book of Ingest is a responsive **Flask** web application that can be used to keep ingest logs and manage SD cards inventory for your project. It should be useful to **Loggers** and **Data Imaging Technicians** in charge of ingesting and archiving footage, whether they work in a postproduction fascility or on the set.

This app was developed as a final project for HarvardX CS50’s Introduction to Computer Science.

## Project Idea
My current job is working as a DIT for a video production company. We had this this project, a reality show, that was shot in a rural area and postproduction fascility was pretty far from the set. 

During this project, on each shooting day, five to ten crews (each consisting of one reporter, camera operator and sound operator) would first send the **Reporter** to the Base to get assigned **SD cards** for camera and sound. These cards would be labeled with **' V(number) '** or **' A(number) '**, indicating that they should be used for video or audio footage, and given to the camera and sound operators.

During crews shift, after cards storage was full or at designated times, reporters would give these cards to runners, who would get it to the postproduction fascility, where footage was ingested and archived. 

The assigning of cards and ingest logs were written by hand in some kind of a **book**, thus the idea was born. I'm certain there is much better software out there, but this is what I managed to do on my own, for the time being.  

## Getting Started
Book of Ingest is created with multiple tools, extensions and libraries. SQLAlchemy and Flask-SQLalchemy is used for connection with the database, queries and adding or deleting data. WTForms and Flask-WTF are used for creating forms to submit data. Bootstrap is there for easy positioning, collapsing forms and general responsivnes of the app. It is further styled using Sass and JQuery and DataTables are used to responsively present and prioritaze presented data in tables accross all viewports.

### Tools, libraries and extensions used:
- [SQLAlchemy](https://docs.sqlalchemy.org/en/20/)

- [Flask-SQLalchemy](https://flask-sqlalchemy.palletsprojects.com/en/3.1.x/)

- [WTForms](https://wtforms.readthedocs.io/en/3.1.x/)

- [Flask-WTF](https://flask-wtf.readthedocs.io/en/1.2.x/)

- [Bootstrap 5](https://getbootstrap.com/docs/5.3/getting-started/introduction/)

- [Sass](https://sass-lang.com/)

- [JQuery](https://jquery.com/)

- [DataTables](https://datatables.net/)

### App Structure
```

static/
  css/
  img/
  js/
  node_modules/
  sass/
templates/
  base/
  error_pages/
app.py
forms.py
helpers.py
models.py
README.md
requirements.txt

```

### Installation
To run the app, either:
- Download the files as zip by clicking first on **<> Code** above the list of files at this repository's main page and then **Download ZIP** at the bottom. Extract the files at the directory of your choosing, `cd <directory>`  and follow the rest of the steps. 

**OR**

- Open up a terminal, navigate to the directory of your choosing and run the command bellow.

  ```
  git clone https://github.com/kuvk/cs50x-final-project.git
  ```
<br>

After following one of the steps above:

1. Open up a terminal in the cloned or unzipped directory and run the commands bellow to create a virtual environment for the project and activate it.

    ```
    python3 -m venv venv
    source venv/bin/activate
    ```

2. Run the command to install requirements.

    ```
    pip install -r requirements.txt
    ```

3. Start the app

    ```
    python app.py
    ```
App will start in debug mode, to turn it off, open `app.py` and go to the bottom of the file and remove `debug=True`.

```python
if __name__ == "__main__":
    db.create_all()
    create_privileges()
    create_admin()
    app.run(debug=True)
``` 
Now open a browser of your choosing and go to `127.0.0.1:5000/`. You will be redirected to the login page.

<br> 

## Users
### Login
After running `python app.py` for the first time, all **database models** will be created, **three levels of privileges** will be added and **orignal admin** user will be created with **Username:** `admin`  and **Password:** `admin`. You can use these credentials to sign in, and have full access to app's features.

**Original admin** user cannot be edited or deleted, and will not appear in the `Users` page. They can create other users choosing one of three levels of privilege: **Admin**, **Ingest** or **Spectator**. All passwords are stored as hashes and checked upon login.

### Users Model
```python
class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100))
    pw_hash = db.Column(db.String(200), nullable=False)
    privilege = db.Column(db.Integer, db.ForeignKey("privileges.id"))
    date = db.Column(db.DateTime, default=datetime.now())

    @property
    def password(self):
        raise AttributeError("Password is not readable attribute!")
    
    @password.setter
    def password(self, password):
        self.pw_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.pw_hash, password)

    def __repr__(self) -> str:
        return self.username
```

### Privileges Model
```python
class Privileges(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    users = db.relationship("Users", backref="role")

    def __repr__(self) -> str:
        return self.name
```

### Admin
Admin users have almost the same access as original admin. They have full access to `Reporters`, `Inventory` and `Ingest`, but they can only create and manage users with privilege **Ingest** or **Spectator**. They cannot edit or delete other admin users, but can edit their own information.

### Ingest
Ingest users have full access to **Ingest** and limited access to **Inventory** and **Reporters**. Limited in a way they cannot delete or edit reporters and cards, they can only assign cards to reporters, or return those cards to Base. Full access to Ingest means they can add, edit or delete days and ingest logs for those days.

### Spectators
Spectator users only have access to the homepage, or the `Book` page, where they can check any days ingest log.

## Reporters
Accessing the reporters page, admin users can add reporters by submitting a unique name for each reporter. They can also edit, delete or assign cards to the reporter. Ingest users can only assign cards to reporters or return them back to Base. 

### Reporters Model
Reporters model have a database relationship with Cards and Ingests models. Reporters can have multiple cards and ingests assoisiated with them.

```python
class Reporters(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    inventory = db.relationship('Cards', backref='owner')
    reporter_ingests = db.relationship('Ingests', backref='reporter')

    def __repr__(self) -> str:
        return self.name
```

## Inventory
Accessing the inventory page, admin users can add multiple cards by submitting a **Card type** (video or audio), **Card Label** and **Quantity** of cards to add. 

### Cards Model
```python
class Cards(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_number = db.Column(db.Integer)
    card_label = db.Column(db.String(10), nullable=False)
    card_type = db.Column(db.String(5), nullable=False)
    card_location = db.Column(db.Integer, db.ForeignKey("reporters.id"))
    card_ingests = db.relationship('Ingests', backref='card')

    def __repr__(self) -> str:
        return self.card_label + str(self.card_number)
```

`card_number` column depends on **Quantity** the user chose. If user chooses to add 10 cards of type **Video** and label **V**, cards number will increment from 1 to 10 (V1, V2, V3 and so on). Adding again cards of the same label and type will continue adding cards from the last card number of that label.

`card_location` is used for assigning cards to reporters, and card can be assigned to only one reporter. After adding an ingest `card_location` will be updated to `None`, indicating that the card is returned to Base. 

Users with Admin or Ingest privilege can return assigned card, either by logging an ingest with the card, or going to the Inventory page and clicking return button next to card, or by clicking on the reporter name next to card, which will take them to that reporter's page, where users can return all or some cards assigned to that reporter.

## Ingest
Ingest page can be fully accessed by users with either Admin or Ingest privilege. To log an ingest, first a shooting day must be created by submitting a unique day name and date.

### Days Model
Days have a database relationship with ingests.
```python
class Days(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    date = db.Column(db.DateTime, nullable=False)
    day_ingests = db.relationship('Ingests', backref='day')

    def __repr__(self) -> str:
        return self.name
```
After creating a day, there must be at least one reporter, with at least one card assigned to them, to log an ingest. 

### Ingests Model
```python
class Ingests(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    for_day = db.Column(db.Integer, db.ForeignKey("days.id"), nullable=False)
    by_reporter = db.Column(db.Integer, db.ForeignKey("reporters.id"), nullable=False)
    card_used = db.Column(db.Integer, db.ForeignKey("cards.id"), nullable=False)
    time = db.Column(db.DateTime, default=datetime.now())
    info = db.Column(db.Text, default=None)
    number = db.Column(db.Integer, nullable=False)
    equip_label = db.Column(db.String(20), nullable=False)
    clip_start = db.Column(db.Integer, nullable=False)
    clip_end = db.Column(db.Integer, nullable=False)
    equip_operator = db.Column(db.String(20), nullable=False)

    def __repr__(self) -> str:
        return f"{self.day} - {self.reporter} - {self.card}"
```

`for_day` column is used to indicate for which shooting day an ingest is added

`by_reporter` column indicates which reporter sent the material that is being ingested

`card_used` column tells us which card reporter used

`time` column tells us when an ingest was logged

`number` column acts as ingest group. Entering existing group number for two or more ingest from the same reporter will link ingests in the ingest log tables, indicating that material in all ingests is connected somehow (eg. video material from one card, and audio from another, both received from the same reporter).

`clip_start` and `clip_end` columns tells us how much material was ingested from a card

`equip_label` and `equip_operator` columns indicate which camera or mixer was used and who handled the equipment

`info` is there in case there is any additional info for the ingest


## Book
All users have access to the **Book** page, which will present all days and ingest logs for those days as book pages. Each page will show one day and ingest log for that day.

This is done using `pagination` on `Days` query, which paginates one day per page. Further, that days ingests are iterated with **Jinja** and presented as Ingest Log tables with **DataTables** and **JQuery**.

Users can search for a specific day or page in the search form in the upper right corner, in the book header.

Ingest logs for days, or any table in the app for that matter, can be searched for data in the columns if columns are relevant to search.

## Settings
Settings part of the app is underdeveloped and it only has two buttons (made to quickly test the app), one that **Resets the Database** and another one that **Fills the Database**.

Reset - will delete all data and tables, then create all tables and add privileges and original admin.

Fill - will add 20 cards in total, 10 video (5 labeled V - 5 labeled VB) and 10 audio (5 labeled A - 5 labeled AB). It will also add 10 reporters and 10 days and populate those days ingest logs with 10 ingests each, 2 ingests per reporter.

## Notes
Looking up to `login_required(f)` function in `helpers.py` from CS50 pset 9 Finance, I created three additional functions:

- `admin_required(f)` - which decorates routes to require **admin** privilege

- `original_admin_required(f)` - which decorates routes to require **original admin** privilege

- `spectator_not_allowed(f)` - which decorates routes to deny access to users with **spectator** privilege

<br>

Further, I created functions `create_privileges()` and `create_admin()` which are used to add three levels of privileges and original admin user after initaly running the app, or after reseting the database with **RESET** button in Settings. Then I created functions `add_cards(label, type, qty)`, `add_reporters(qty)`, `add_days(qty)` and `add_ingests()` to use for the **FILL** button in settings.

All forms created with Flask-WTF and WTForms can be found in `forms.py`

All models created with Flask-SQLAlchemy can be found in `models.py` 

During app development `Flask-Migrate` was used with local `postgre` database for easier database changing, upgrading and downgrading. When all models were considered finished for the time being, the `['SQLALCHEMY_DATABASE_URI']` was changed back to `["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ingest.sqlite3"` for easier use on other devices.

## Thank you
I just wish to thank professor Malan and all of CS50 staff members for this amazing journey and an opportunity to learn from such individuals. Thank you all!
