from datetime import datetime
from flask import Flask, session, render_template, flash, request, url_for, redirect, jsonify, abort
from flask_session import Session
from werkzeug.security import check_password_hash
from sqlalchemy import func
from forms import LoginForm, UsersForm, AddCardsForm, ReportersForm, DaysForm, IngestForm
from models import db, Users, Privileges, Cards, Reporters, Days, Ingests

from helpers import login_required, admin_required, spectator_not_allowed, original_admin_required, create_admin, create_privileges, add_cards, add_reporters, add_days, add_ingests



# Configure app
app = Flask(__name__)
app.secret_key = "e042dc730051bd84a56328c1c8ad738247641e2896d6c1a1"


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
sess = Session(app)


# Configure SQLAlchemy and initialize database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///ingest.sqlite3"
db.init_app(app)
app.app_context().push()


''' ROUTES '''
''' Index - Book of Ingest '''
@app.route("/")
@app.route("/book", methods=["GET", "POST"])
@login_required
def book():
    # Set days and search data to None
    days = None
    search_data = []

    # Count days to get latest day page and check if days exist
    latest_day_page = db.session.query(func.count(Days.id)).scalar()  
    if latest_day_page:
        # Get page and set default to latest day page if none
        page = request.args.get('page', latest_day_page, type=int)

        # Get user query
        q = request.args.get('search')

        # Query for all days and append each as dict {day name: day row} to search_data - used for user search datalist options 
        days = Days.query.order_by(Days.id).all()
        for i in range(len(days)):
            day = { days[i].name: i + 1 }
            search_data.append(day)
            
            
        # If user submitted a query check if page exists or if day is in the database 
        if q:
            # User submitted a page number
            if q.isdigit():
                # Check if page exists and update
                if int(q) in range(1, latest_day_page + 1):
                    page = int(q)
                # Page doesn't exist - flash info
                else:
                    flash("Page doesn't exist!", "info")
            
            # User submitted a day
            else:
                # Set query to upper chars and bool for day in database to False
                q = q.upper()
                day_in_db = False
                
                # Check search_data days for user query
                for data in search_data:
                    # If query is in search_data, set day in database to True and set page to queried day page
                    if q in data:
                        day_in_db = True
                        page = int(data[q])
                # Day not in the database - flash info   
                if not day_in_db:
                    flash("No such day in the book!", "info")        

        # Paginate days - one day per page
        days = Days.query.order_by(Days.id).paginate(per_page=1, page=page, error_out=True)
    
    return render_template("book.html", days=days, search_data=search_data)


''' Ingest '''
@app.route('/ingest', methods=["GET", "POST"])
@login_required
@spectator_not_allowed
def ingest():
    form = DaysForm()

    # Validate submitted data
    if form.validate_on_submit():
        name = form.name.data.upper()

        # Check if day already exists
        name_exists = Days.query.filter_by(name=name).first()
        if name_exists:
            flash("Day with the same name already exists! Please try another name...", "warning")
            return redirect(url_for("ingest"))
        
        # Check if date already exists
        date_exists = Days.query.filter_by(date=form.date.data).first()
        if date_exists:
            flash("Day with the same date already exists! Please choose another date...", "warning")
            return redirect(url_for("ingest"))
        
        # Add day and clear form
        day = Days(name = name,
                   date = form.date.data)
        
        db.session.add(day)

        form.name.data = ''
        form.date.data = ''

        # Commit changes
        try:
            db.session.commit()
            flash("Day successfuly created!", "success")
        except:
            db.session.rollback()
            flash("Something went wrong! Please try again...", "danger")

        return redirect(url_for("ingest"))
    
    # Flash form errors as messages
    if form.errors:
        for error in form.errors:
            for message in form.errors[error]:
                flash(f"{message}", "warning")

    # Get days count and data
    days = None
    count = db.session.query(func.count(Days.id)).scalar()
    if count:
        days = Days.query.order_by(Days.id)


    return render_template("ingest.html", form=form, days=days, count=count)


''' Ingest Day '''
@app.route('/ingest/day/<int:id>')
@login_required
@spectator_not_allowed
def ingest_day(id):
    # Get day from the database
    day = Days.query.get_or_404(id)
    
    # Edit day form
    form = DaysForm()
    form.name.data = day.name
    form.date.data = day.date
    
    # Add ingest form
    ingest_form = IngestForm()
    ingest_form.reporter.choices = [(0, "None")]
    ingest_form.card.choices = [(0, "None")]

    # If there are any reporters with cards in their inventory, add them as select options for Ingest Form reporter choices
    available_reporters = db.session.query(func.count(Reporters.id)).filter(Reporters.inventory!=None).scalar()
    if available_reporters:
        reporters = Reporters.query.order_by(Reporters.id).filter(Reporters.inventory!=None)
        ingest_form.reporter.choices += [(reporter.id, reporter.name) for reporter in reporters]

    # Get ingest log for day
    ingests = None
    if day.day_ingests:
        ingests = Ingests.query.order_by(Ingests.number).filter_by(for_day=day.id)


    return render_template("ingest_day.html", 
                           day=day, 
                           ingests=ingests, 
                           form=form, 
                           ingest_form=ingest_form, 
                           available_reporters=available_reporters)


''' Ingest - Reporter inventory - get cards and return as JSON '''
@app.route('/ingest/<int:reporter_id>/cards')
@login_required
@spectator_not_allowed
def get_cards(reporter_id):
    cardsArray = []

    # If choice is None
    if reporter_id == 0:
        cardObj = {}
        cardObj["id"] = 0
        cardObj["label"] = "None"
        
        cardsArray.append(cardObj)

    else:
        # Get reporter data
        reporter = Reporters.query.get_or_404(reporter_id)

        # Add assigned cards as select options
        for card in reporter.inventory:
            cardObj = {}
            cardObj["id"] = card.id
            cardObj["label"] = f"{card}"

            cardsArray.append(cardObj) 

    return jsonify({'cards' : cardsArray})


''' Ingest - Add Ingest '''
@app.route('/ingest/day/<int:id>/add', methods=["POST"])
@login_required
@spectator_not_allowed
def add_ingest(id):
    day = Days.query.get_or_404(id)
    form = IngestForm()
    
    # Get user submitted data
    number = form.group.data
    reporter = Reporters.query.get(form.reporter.data)
    card = Cards.query.get(form.card.data)
    equip_label = form.equipment.data.upper()
    equip_operator = form.operator.data.upper()
    clip_start = form.clip_start.data
    clip_end = form.clip_end.data
    info = form.info.data.capitalize()

    ''' Validate submitted data '''  
    # Check if reporter and card data is in the database 
    if not reporter or not card:
        flash("Cannot add ingest! Submitted data invalid!", "danger")
        return redirect(url_for("ingest_day", id=day.id))
    
    # Chek if card is assigned to reporter
    if card not in reporter.inventory:
        flash("Cannot add ingest! Submitted data invalid!", "danger")
        return redirect(url_for("ingest_day", id=day.id))
    
    # Check if Ingest Group and Equipment Label are submitted:
    if not number or not equip_label or not equip_operator:
        flash("Cannot add ingest! All fields are required!", "danger")
        return redirect(url_for("ingest_day", id=day.id))
    
    # Check if Clip start and end are min=1 and max=10000
    if clip_start not in range(1, 10000) or clip_end not in range(1, 10000):
        flash("Cannot add ingest! Submitted data invalid!", "danger")
        return redirect(url_for("ingest_day", id=day.id))
    
    # Check if ingest group already exists and submitted reporter is same as group reporter
    group = Ingests.query.filter_by(number=number).first()
    if group:
        if group.reporter != reporter: 
            flash(f"Cannot add ingest! Same ingest group already exists for reporter: {group.reporter}!", "danger")
            return redirect(url_for("ingest_day", id=day.id))
    
    # Add ingest and reassign card to Base
    ingest = Ingests(for_day=day.id,
                     by_reporter=reporter.id,
                     card_used=card.id,
                     number=number,
                     equip_label=equip_label,
                     equip_operator=equip_operator,
                     clip_start=clip_start,
                     clip_end=clip_end,
                     info=info,
                     time=datetime.now())
    
    db.session.add(ingest)
    card.card_location = None

    # Commit changes
    try:
        db.session.commit()
        flash("Ingest added successfully!", "success")
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")
    
    return redirect(url_for("ingest_day", id=day.id))


''' Ingest - Edit Day '''
@app.route('/ingest/day/<int:id>/edit', methods=["POST"])
@login_required
@spectator_not_allowed
def edit_day(id):
    # Get day to edit and submitted data 
    day = Days.query.get_or_404(id)
    form = DaysForm()
    
    ''' Validate submitted data '''
    if form.validate_on_submit():
        name = form.name.data.upper()

        # Check if same day name already exists and is not the name of the day to edit
        name_exists = Days.query.filter_by(name=name).first()
        if day.name != name and name_exists:
            flash("Day with the same name already exists! Please try another name...", "warning")
            return redirect(url_for("ingest_day", id=day.id))
        
        # Update day and clear form
        day.name = name
        day.date = form.date.data
        form.name.data = ''
        form.date.data = ''

        # Commit changes
        try:
            db.session.commit()
            flash("Day data updated successfuly!", "success")
        except:
            db.session.rollback()
            flash("Something went wrong! Please try again...", "danger")


    # Flash form errors as messages
    if form.errors:
        for error in form.errors:
            for message in form.errors[error]:
                flash(f"{message}", "warning")

    
    return redirect(url_for("ingest_day", id=day.id))


''' Ingest Day - Delete ingest '''
@app.route('/ingest/delete/<day>/<ingest>')
@login_required
@spectator_not_allowed
def delete_ingest(day,ingest):
    # Query for day and ingest
    day = Days.query.get_or_404(day)
    ingest = Ingests.query.get_or_404(ingest)
    
    # If ingest is not in ingest log for day return 404
    if ingest not in day.day_ingests:
        return abort(404)
    
    try:
        db.session.delete(ingest)
        db.session.commit()
        flash("Ingest deleted successfully", "success")
    
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")

    return redirect(url_for('ingest_day', id=day.id))


''' Ingest Day - Delete all ingests for day '''
@app.route('/ingest/delete/<day>/log')
@login_required
@spectator_not_allowed
def delete_log(day):
    # Query the databese for day
    day = Days.query.get_or_404(day)

    try:
        # Delete ingest log for day
        for ingest in day.day_ingests:
            db.session.delete(ingest)

        # Commit changes
        db.session.commit()
        flash("Ingest Log cleared successfully!", "success")

    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")

    return redirect(url_for('ingest_day', id=day.id))


''' Ingest - Delete Day '''
@app.route('/ingest/day/<id>/delete')
@login_required
@spectator_not_allowed
def delete_day(id):
    # Get day to delete
    day = Days.query.get_or_404(id)
    
    try:
        # Delete ingest log for day and commit changes
        for ingest in day.day_ingests:
            db.session.delete(ingest)

        db.session.commit()

        # Delete day and commit changes
        db.session.delete(day)
        db.session.commit()
        flash("Day deleted successfully!", "success")

    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")
        
    return redirect(url_for('ingest'))


''' Ingest - Delete All Days '''
@app.route('/ingest/delete/all')
@login_required
@spectator_not_allowed
def clear_days():
    try:
        # Delete all ingests and commit changes 
        Ingests.query.delete()
        db.session.commit()

        # Delete all days and commit changes 
        Days.query.delete()
        db.session.commit()
        flash("All Days successfully deleted!", "success")
        
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")
        
    return redirect(url_for("ingest"))


''' Inventory '''
@app.route('/inventory', methods=["GET", "POST"])
@login_required
@spectator_not_allowed
def inventory():
    # Form for adding cards
    form = AddCardsForm()
    
    if request.method == "POST":
        # Only admin users can add new cards
        if session.get('privilege') != "Admin":
            return abort(405)
        
        # Validate form
        if form.validate_on_submit():

            # Add cards
            add_cards(form.card_label.data, form.card_type.data, form.card_qty.data)
            
            # Clear form
            form.card_label.data = ''
            form.card_type.data = ''
            form.card_qty.data = ''
            
            return redirect(url_for("inventory"))
            
        # Flash form errors as messages
        if form.errors:
            for error in form.errors:
                for message in form.errors[error]:
                    flash(f"{message}", "warning")
        

        return redirect(url_for("inventory"))


    # Check if there are cards in the database
    cards = None
    count = db.session.query(func.count(Cards.id)).scalar()
    if count:
        # Get all cards from the database
        cards = Cards.query.order_by(Cards.card_label).order_by(Cards.card_number)
        
       
    return render_template("inventory.html", form=form, cards=cards, count=count)


''' Inventory - Return card/cards to Base '''
@app.route('/inventory/return/<int:card>')
@login_required
@spectator_not_allowed
def return_cards(card):
    # Query the database for card to return
    reassign = Cards.query.get_or_404(card)

    try:
        # Reassign card to Base
        reassign.card_location = None
        flash(f"Card {reassign} successfully reassigned to Base!", "success")

        # Commit changes
        db.session.commit()
                
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")

    return redirect(url_for("inventory"))


''' Inventory - Delete Card '''
@app.route('/inventory/delete/card/<id>')
@login_required
@admin_required
def delete_card(id):
    # Query the database for card to delete
    card = Cards.query.get_or_404(id)
    
    try:
        # Delete ingests assosiated with the card and commit changes
        for ingest in card.card_ingests:
            db.session.delete(ingest)
        db.session.commit()

        # Delete card and commit changes
        db.session.delete(card)
        db.session.commit()
        flash("Card deleted successfully!", "success")
        
    except:
        # Rollback and flash error
        db.session.rollback()
        flash("Something went wrong! Please try again...", "warning")
    
    return redirect(url_for("inventory"))


''' Inventory - Delete all Cards '''
@app.route('/inventory/delete/all')
@login_required
@admin_required
def clear_inventory():
    try:
        # Delete all ingests and commit
        Ingests.query.delete()
        db.session.commit()

        # Delete all cards and commit
        Cards.query.delete()
        db.session.commit()
        flash("Inventory successfully cleared! All cards deleted!", "success")
    
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "warning")
        
    return redirect(url_for("inventory"))

''' Reporters '''
@app.route('/reporters', methods=["GET", "POST"])
@login_required
@spectator_not_allowed
def reporters():
    form = ReportersForm()
    
    if request.method == "POST":
        # Only admin users can add new reporters
        if session.get('privilege') != "Admin":
            return abort(405)
        
        # Validate form
        if form.validate_on_submit():
            # Get submitted name and clear form
            name = form.name.data.title()
            form.name.data = ''

            # If reporter with the same name already exists
            name_exists = Reporters.query.filter_by(name=name).first()
            if name_exists:
                flash("Name already exists! Reporter name must be unique!", "warning")
                return redirect(url_for("reporters"))

            # Add reporter
            reporter = Reporters(name=name)
            db.session.add(reporter)

            # Commit changes
            try:    
                db.session.commit()
                flash("Reporter added successfully", "success")

            except:
                db.session.rollback()
                flash("Something went wrong! Please try again...", "danger")
            
        # Flash errors as messages
        if form.errors:
            for error in form.errors:
                for message in form.errors[error]:
                    flash(f"{message}", "warning")
        

        return redirect(url_for("reporters"))

    # Get reporters from the database
    reporters = None
    count = db.session.query(func.count(Reporters.id)).scalar()
    if count:
        reporters = Reporters.query.order_by(Reporters.id).all()
        
    return render_template("reporters.html", form=form, reporters=reporters, count=count)


''' Reporters - Manage Reporter '''
@app.route('/reporters/manage/<int:id>', methods=["GET", "POST"])
@login_required
@spectator_not_allowed
def manage_reporter(id):
    # Get reporter data and set form for updating name
    reporter = Reporters.query.get_or_404(id)
    form = ReportersForm(name=reporter.name)

    if request.method == "POST":
        # Only admin users can edit reporter data
        if session.get('privilege') != "Admin":
            return abort(405)
        # Validate Reporters Form
        if form.validate_on_submit():
            name = form.name.data.title()

            # If reporter with the same name already exists, and is not the name of the current reporter
            name_exists = Reporters.query.filter_by(name=name).first()
            if reporter.name != name and name_exists:
                flash("Name already exists! Reporter name must be unique!", "warning")
                return redirect(url_for("manage_reporter", id=reporter.id))
            
            # Update reporter name and clear form
            reporter.name = form.name.data
            form.name.data = ''

            # Commit changes
            try:
                db.session.commit()
                flash("Reporter name successfully updated!", "success")
                return redirect(url_for("manage_reporter", id=reporter.id))
            except:
                db.session.rollback()
                flash("Something went wrong! Please try again...", "danger")
                return redirect(url_for("manage_reporter", id=reporter.id))

        # Flash errors as messages
        if form.errors:
            for error in form.errors:
                for message in form.errors[error]:
                    flash(f"{message}", "warning")
    
        return redirect(url_for("manage_reporter", reporter=reporter.id))


    # Get cards that can be assigned 
    cards = None
    cards_exists = db.session.query(func.count(Cards.id)).filter_by(card_location=None).scalar()   
    if cards_exists:
        cards = Cards.query.filter_by(card_location=None).order_by(Cards.card_label).order_by(Cards.card_number)


    return render_template("manage_reporter.html", 
                           form=form,  
                           reporter=reporter, 
                           cards=cards)


''' Reporters - Assign Cards '''
@app.route('/reporters/manage/<int:id>/assign', methods=["POST"])
@login_required
@spectator_not_allowed
def assign_cards(id):
    # Get reporter and cards to assign 
    reporter = Reporters.query.get_or_404(id)
    cards = request.form.getlist('assign_card')
    
    ''' Validate and assign cards '''
    # If none of the cards were checked
    if cards == []:
        flash("Please check the cards you wish to add first!", "warning")
        return redirect(url_for("manage_reporter", id=reporter.id))
    
    # Check if any submitted card is already assigned or doesn't exist  
    for card_id in cards:
        card = Cards.query.get_or_404(card_id)
        
        # Assign card to reporter 
        if not card.owner:
            card.card_location = reporter.id
        # If card is already assigned
        else:
            flash(f"Problem assigning cards! Card {card} already assigned to {card.owner}!", "warning")
    
    # Commit changes
    try:
        db.session.commit()
        flash("Cards successfully assigned!", "success")
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "warning")
    
    return redirect(url_for("manage_reporter", id=reporter.id))


''' Reporters - Remove all cards from reporter inventory'''
@app.route('/reporters/manage/<reporter>/return/<card>')
@login_required
@spectator_not_allowed
def return_reporter_cards(reporter, card):
    # Query the database for reporter
    reporter = Reporters.query.get_or_404(reporter)

    # Check if reporter has any cards in the inventory
    if reporter.inventory == []:
        flash("No cards to return! Reporter inventory is already empty!", "info")
        return redirect(url_for("manage_reporter", id=reporter.id))
    
    try:
        # Reassign all cards to Base
        if card == 'all':
            reporter.inventory = []
            flash("Reporter inventory cleared. All cards reassigned to Base!", "success")
        # Reassign card to Base
        else:
            reassign = Cards.query.get(card)
            reassign.card_location = None
            flash(f"Card {reassign} successfully reassigned to Base!", "success")

        # Commit changes
        db.session.commit()
                
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")

    return redirect(url_for("manage_reporter", id=reporter.id))


''' Reporters - Delete Reporter '''
@app.route('/reporters/delete/<int:id>')
@login_required
@admin_required
def delete_reporter(id):
    # Query the database for reporter to delete 
    reporter = Reporters.query.get_or_404(id)
    
    try:
        # Delete ingests assosiated with reporter and commit changes
        for ingest in reporter.reporter_ingests:
            db.session.delete(ingest)
        
        db.session.commit()

        # Delete reporter and commit changes
        db.session.delete(reporter)
        db.session.commit()
        
        flash("Reporter deleted successfully!", "success")
        return redirect(url_for("reporters"))
    
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "warning")
        return redirect(url_for("reporters"))
    

''' Reporters - Delete all Reporters '''
@app.route('/reporters/delete/all')
@login_required
@admin_required
def clear_reporters():
    # Get all assigned cards
    cards = Cards.query.filter(Cards.card_location.is_not(None))

    try:
        # Reassign cards to Base
        for card in cards:
            card.card_location = None

        # Delete all ingests and reporters
        Ingests.query.delete()
        Reporters.query.delete()

        # Commit changes
        db.session.commit()
        flash("All reporters deleted successfully!", "success")

    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "warning")
    
    return redirect(url_for("reporters"))


''' Users '''
@app.route('/users', methods=["GET", "POST"])
@login_required
@admin_required
def users():
    form = UsersForm()
    privileges = None

    # Check if user requesting the page is original admin user
    admin = Users.query.order_by(Users.id).first()

    # If original admin requested the page, query for all privilges
    if session.get('user_id') == admin.id:    
        privileges = Privileges.query.order_by(Privileges.id)
    # Else skip admin privilege 
    else:
        privileges = Privileges.query.order_by(Privileges.id).offset(1)

    # Add privileges as role select options
    form.privilege.choices = [(privilege.id, privilege.name) for privilege in privileges]

    # Validate submitted form    
    if form.validate_on_submit():

        # Query the database for user with the same username as submitted one
        user = Users.query.filter_by(username=form.username.data).first()

        # Check if username already exists     
        if user:
            flash("Username already exists! Please choose another username.", 'warning')
            return redirect(url_for("users"))

        # Add user  
        user = Users(name=form.name.data.title(), 
                    username=form.username.data, 
                    password=form.password.data,
                    privilege=form.privilege.data)
        db.session.add(user)

        # Commit changes and clear the form
        try:
            db.session.commit()

            form.name.data = ""
            form.username.data = ""
            form.password.data = ""
            form.confirm.data = ""
            form.privilege.data = ""
            flash(f"User added successfully!", "success")
            
        except:
            db.session.rollback()
            flash("Something went wrong! Please try again...", "danger")
        
    # Flash form errors as warning messages
    if form.errors:
        for error in form.errors:
            for message in form.errors[error]:
                flash(f"{message}", "warning")

    # Get count of users in database 
    count = db.session.query(func.count(Users.id)).scalar()

    # If users, other then original admin, exist, pass as existing users to the page
    users = None
    if count > 1:
        users = Users.query.order_by(Users.id).offset(1)
    count -= 1

    return render_template("users.html", form=form, users=users, count=count)


''' Users - Manage User '''
@app.route('/users/manage/<int:id>', methods=["GET", "POST"])
@login_required
@admin_required
def manage_user(id):
    # Query the database for user to manage
    user = Users.query.get_or_404(id, description="Invalid user!")

    # Use Users Form with privilege selection option set to managed user's privilege
    form = UsersForm(privilege=user.role.id)

    # Make sure managed user is not original admin user
    admin = Users.query.filter_by(username="admin").first()
    if user == admin:
        return abort(404)
    
    # Get privileges from database and add as form select options for user's privilege field 
    privileges = Privileges.query.order_by(Privileges.id)
    form.privilege.choices = [(privilege.id, privilege.name) for privilege in privileges ]

    # Validate form
    if request.method == "POST":
        # If user to manage has admin privilege and is not original admin or the current admin user
        if user.role.name == "Admin" and session.get('user_id') != admin.id and user.username != session.get('username'):
            flash("Only original administrator can edit another admin user!", "warning")
            return redirect(url_for("users"))

        # Check if username is submitted
        if not form.username.data:
            flash("Username field is required!", "warning")
            return redirect(url_for("manage_user", id=user.id))
        
        # Check the database for existing username
        check = Users.query.filter_by(username=form.username.data).first()

        # Username already exists and is not the same as the currently managed user's username
        if check and check != user:
            flash("Username already exists! Please try another...", "warning")
            return redirect(url_for("manage_user", id=user.id))

        # Ensure user's privilege is selected from valid choices
        role = Privileges.query.filter_by(id=form.privilege.data).first()    
        if role not in privileges:
            flash("Please select a valid role!", "warning")
            return redirect(url_for("manage_user", id=user.id))
        
        # Update user information and clear form
        user.name = form.name.data.title()
        user.username = form.username.data
        user.role = role
        form.name.data = ''
        form.username.data = ''
        form.privilege.data = ''

        # Commit changes and clear the form
        try:
            db.session.commit()
            flash("User information successfully updated!", "success")
            return redirect(url_for("manage_user", id=user.id))
        
        except:
            flash("Something went wrong! Please try again...", "warning")
            return redirect(url_for("manage_user", id=user.id))

    return render_template("manage_user.html", 
                        form=form, 
                        user=user)

    
''' Users - Delete User '''
@app.route('/users/delete/<int:id>')
@login_required
@admin_required
def delete_user(id):
    # Query the database for user to delete
    user = Users.query.get_or_404(id)

    # Make sure user to delete is not original admin user
    admin = Users.query.order_by(Users.id).first()
    if user == admin:
        return abort(404)
    
    # If user to delete has admin privilege, and user that requested the route is not original admin
    if user.role.name == "Admin" and session.get('user_id') != admin.id:
        flash("Only original administrator can delete another admin user!", "warning")
        return redirect(url_for("users"))
    
    # Delete user and commit changes to the database
    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    
    except:
        db.session.rollback()
        flash("Something went wrong! Please try again...", "danger")
    
    return redirect(url_for("users"))


''' Users - Delete all Users '''
@app.route('/users/delete/all')
@login_required
@original_admin_required
def clear_users():
    # Query the database for all users except original admin
    users = Users.query.order_by(Users.id).offset(1)
    
    try:
        # Delete all users and commit changes
        for user in users:
            db.session.delete(user)

        db.session.commit()

        flash("All users deleted successfully!", "success")
        return redirect(url_for("users"))
    
    except Exception as e:
        db.session.rollback()
        flash(f"Something went wrong! Please try again... Error: {e}", "warning")
        return redirect(url_for("users"))


''' Settings '''
@app.route('/settings')
@login_required
@original_admin_required
def settings():
    return render_template("settings.html")


''' Settings - Reset '''
@app.route('/settings/reset')
@login_required
@original_admin_required
def reset():
    try:
        # Close database session
        db.session.close()

        # Delete, then create all tables
        db.drop_all()
        db.create_all()

        # Add roles and original admin user
        create_privileges()
        create_admin()

        # Clear session and redirect to login
        session.clear()
        flash("Database reset successfull!", "success")
        return redirect(url_for('login'))
    
    except Exception as e:
        flash(f"Something went wrong! Error: {e}")
        return redirect(url_for('settings'))


''' Settings - fill database with cards and reporters '''
@app.route('/settings/fill')
@login_required
@original_admin_required
def fill():
    # Set card types as list of labels
    video = ["v", "vb"]
    audio = ["a", "ab"]

    # Set cards quantity
    cards_qty = 5

    # Add video
    for label in video:
        add_cards(label, "video", cards_qty)

    # Add audio
    for label in audio:
        add_cards(label, "audio", cards_qty)

    # Add reporters, days and ingests
    add_reporters(10)
    add_days(10)
    add_ingests()

    return redirect(url_for('settings'))


''' Login '''
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    # Validate submitted form
    if form.validate_on_submit():
        
        # Query the database for submitted username
        check = Users.query.filter_by(username=form.username.data).first()

        # If user exists check password hash
        if check and check_password_hash(check.pw_hash, form.password.data):

            # Set user session, clear the form and redirect to index
            try:
                session["user_id"] = check.id
                session["username"] = check.username
                session["privilege"] = check.role.name
                form.username.data = ''
                form.password.data = ''
                flash(f"Login successfull ! Welcome {check.name}!", "success")
                return redirect(url_for("book"))
            
            except:
                flash ("Something went wrong! Please try again...")
        
        else:
            flash("Invalid credentials!", "warning")
    
    # Flash form errors as messages
    if form.errors:
        for error in form.errors:
            for message in form.errors[error]:
                flash(f"{message}", "warning")

    return render_template("login.html", form=form)


''' Logout '''
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


''' Not Found '''
@app.errorhandler(404)
def page_not_found(e):
    return render_template("error_pages/404.html", description=e), 404


if __name__ == "__main__":
    db.create_all()
    create_privileges()
    create_admin()
    app.run(debug=True)