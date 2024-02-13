import datetime
from flask import redirect, session, url_for, abort, flash
from functools import wraps
from sqlalchemy import func
from models import db, Users, Privileges, Reporters, Cards, Days, Ingests



def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """ Decorate routes to require admin privilege """
    
    @wraps(f)
    def decorated_function(*args, **kwargs):

        """
        Get current user indormation, using session["user_id"], and admin privilege
        from the database. If user and admin privileges don't match, deny access
        and redirect user to dashboard page.
        """
        
        user = Users.query.filter_by(id=session.get("user_id")).first()
        admin_privilege = Privileges.query.filter_by(name="Admin").first()

        # If privileges match  
        if user.role == admin_privilege:
            return f(*args, **kwargs)
        
        # If user tries to enter without privilege, return 404
        return abort(404)

    return decorated_function


def original_admin_required(f):
    """ Decorate routes to require orignal admin user """
    
    @wraps(f)
    def decorated_function(*args, **kwargs):

        """
        Get current user indormation, and original admin user
        from the database. If user is not original admin return 404.
        """
        
        user = Users.query.filter_by(id=session.get("user_id")).first()
        admin = Users.query.filter_by(username="admin").first()

        if user == admin :
            return f(*args, **kwargs)
        

        return abort(404)

    return decorated_function



def spectator_not_allowed(f):
    """ Decorate routes to deny access to users with spectator privilege """
    
    @wraps(f)
    def decorated_function(*args, **kwargs):

        """
        Get current user indormation, using session["user_id"], and spectator 
        privilege from the database. If user and spectator privileges match, 
        deny access and redirect user to dashboard page. 
        """

        user = Users.query.filter_by(id=session.get("user_id")).first()
        spectator_privilege = Privileges.query.filter_by(name="Spectator").first()
        if user.role == spectator_privilege:
            
            return abort(404)

        return f(*args, **kwargs)

    return decorated_function


def create_privileges():
    """ 
    Function to add user roles/privileges to Privileges table.

    """
    
    count = db.session.query(func.count(Privileges.id)).scalar()
    if not count:
        roles = ["Admin", "Ingest", "Spectator"]
        try:
            for role in roles:
                privilege = Privileges(name=role)
                db.session.add(privilege)
                
            db.session.commit()
            return print(" - Privileges created")
        
        except Exception as e:
            return print(f" - Problem occured! Privileges not added!\n - Error:\n {e}")

    return print(" - Privileges exist!")


def create_admin():
    """ 
    Function to add original admin user to the database. Requires user Privileges to be set.
    Run create_privileges() function before this.
    """

    admin = db.session.query(Users).filter_by(username="admin").first()
    if admin:
        return print(" - Admin user exists!")
    
    privilege = db.session.query(Privileges).filter_by(name="Admin").first()
    if not privilege:
        return print(" - Missing privileges!")

    try:
        admin = Users(name='Admin', username='admin', password='admin', privilege=privilege.id)
        db.session.add(admin)
        db.session.commit()
        return print(" - Admin user added!")
    
    except Exception as e:
        return print(f" - Problem occured! Couldn't add admin user!\n - Error:\n {e}")
    


def add_cards(label, type, qty):
    '''
    Function to add "qty" cards of "type" with "label"  
    '''

    card_label = label
    card_type = type
    qty = int(qty)
    
    # If type not video or audio flash warning
    if card_type not in ["video", "audio"]:
        return flash(f"Cannot add cards of type {card_type}!", "warning")
    
    qty += 1
    start = 1
    # If label already exists increment from last card number with the same label
    count = db.session.query(func.count(Cards.id)).filter_by(card_label=card_label.upper()).scalar()
    if count:
        # Get last card added
        last_card = Cards.query.filter_by(card_label=card_label.upper()).order_by(Cards.card_number.desc()).first() 
        # Set last card number as a start and add that number to quantity of cards to create 
        start += last_card.card_number
        qty += start - 1

    try:
        # Add cards and commit changes
        for n in range(start, qty):
            card = Cards(card_number=n,
                        card_label=card_label.upper(),
                        card_type=card_type,
                        card_location=None)

            db.session.add(card)
        
        db.session.commit()
        return flash(f"{qty - start} cards with label {card_label.upper()} added successfully!", "success")
    
    except:
        db.session.rollback()
        return flash("Something went wrong! Please try again..", "danger")


def add_reporters(qty):
    ''' 
    Function to add quantity of Reporters. 
    All reporter names start with "Reporter ", followed by different numbers.
    '''

    # Set quantity to create and starting quantity for range - so numbers increment from 1
    qty += 1
    start = 1
    # Check if there are any reporters in the database:
    count = db.session.query(func.count(Reporters.id)).scalar()
    if count:
        # Update starting quantity and quanitity to create 
        start += count
        qty += start -1

    try:
        # Add reporters and commit    
        for i in range(start, qty):
            # Append reporter name with number to avoid conflicts
            name = f"Reporter {i}"
            reporter = Reporters(name=name)
            db.session.add(reporter)

        db.session.commit()
        return flash(f"{qty - start} reporters added successfully!", "success")
    
    except:
        db.session.rollback()
        return flash("Something went wrong! Please try again..", "danger")


def add_days(qty):
    ''' 
    Function to add quantity of Days. 
    All day names start with "DAY ", followed by incremented numbers.
    Dates start with today, and increment by one day.
    '''
    day_name = "DAY "
    day_date = datetime.datetime.now()
    try:
        for i in range(qty):
            day = Days(name=day_name + str(i + 1), date=day_date) 
            day_date += datetime.timedelta(days=1)
            db.session.add(day)
        db.session.commit()
        return flash(f"{qty} days added!", "success")
    except:
        db.session.rollback()
        return flash("Problem adding days!", "danger")
    

def add_ingests():
    ''' 
    Function to add ingests. It will add 10 ingests for each day, using 5 same reporters for each day.
    Two ingests will be added per reporter, one for video card, one for audio. 
    If using the fill button in 'settings' route, please use reset button first, login, and then use fill button ONCE.
    '''

    # Get days and 5 reporters
    days = Days.query.all()
    reporters = Reporters.query.limit(5).all()

    # Set offset and ingest group
    o = 0
    group = 1
    
    # Add ingests for each day and each reporter - two cards per reporter
    try:
        for day in days:
            for reporter in reporters:
                if o:
                    video = Cards.query.filter_by(card_type="video").offset(o).first()
                    audio = Cards.query.filter_by(card_type="audio").offset(o).first()
                    o += 1
                else:
                    video = Cards.query.filter_by(card_type="video").first()
                    audio = Cards.query.filter_by(card_type="audio").first()
                    o += 1
                # Video card ingest
                ingest1 = Ingests(for_day=day.id,
                                by_reporter=reporter.id,
                                card_used = video.id,
                                number=group,
                                equip_label="CAM" + str(group),
                                equip_operator="CAMERA CREW " + str(group),
                                clip_start = 1,
                                clip_end= 100,
                                info="Additional info",
                                time=datetime.datetime.now()
                                )
                # Audio card ingest
                ingest2 = Ingests(for_day=day.id,
                                by_reporter=reporter.id,
                                card_used = audio.id,
                                number=group,
                                equip_label="MIX" + str(group),
                                equip_operator="SOUND CREW " + str(group),
                                clip_start = 1,
                                clip_end= 15,
                                info=None,
                                time=datetime.datetime.now()
                                )
                # Add ingests and increment group number
                db.session.add(ingest1)
                db.session.add(ingest2)
                group += 1
            
            # Commit changes
            db.session.commit()
            # Reset offset and ingest group number for next day
            o = 0
            group = 1

        return flash("Ingests successfuly added!", "success")
    
    except Exception as e:
        db.session.rollback()
        return flash(f"Problem adding ingests! Error: {e}", "danger")


               
   
