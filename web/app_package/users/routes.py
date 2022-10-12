from flask import Blueprint
from flask import render_template, url_for, redirect, flash, request, \
    abort, session, Response, current_app, send_from_directory
import bcrypt
from wsh_models import sess, Users, login_manager, Oura_token, Locations, \
    Weather_history, User_location_day, Oura_sleep_descriptions
from flask_login import login_required, login_user, logout_user, current_user
import requests
#Oura
from app_package.users.utils import oura_sleep_call, oura_sleep_db_add
#Location
from app_package.users.utils import call_location_api, location_exists, \
    add_weather_history, gen_weather_url, add_new_location
#Email
from app_package.users.utils import send_reset_email, send_confirm_email

from sqlalchemy import func
from datetime import datetime, timedelta
import time


salt = bcrypt.gensalt()


users = Blueprint('users', __name__)

@users.route('/', methods=['GET', 'POST'])
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dash.dashboard'))
    if request.method == 'POST':
        formDict = request.form.to_dict()
        if formDict.get('login'):
            return redirect(url_for('users.login'))
        elif formDict.get('register'):
            return redirect(url_for('users.register'))

    return render_template('home.html')

@users.route('/login', methods = ['GET', 'POST'])
def login():
    print('* in login *')
    if current_user.is_authenticated:
        return redirect(url_for('dash.dashboard'))
    page_name = 'Login'
    if request.method == 'POST':
        formDict = request.form.to_dict()
        print('**** formDict ****')
        print(formDict)
        email = formDict.get('email')

        user = sess.query(Users).filter_by(email=email).first()
        print('user for logging in:::', user)
        # verify password using hash
        password = formDict.get('password_text')

        if user:
            if password:
                if bcrypt.checkpw(password.encode(), user.password):
                    print("match")
                    login_user(user)
                    flash('Logged in succesfully', 'info')

                    return redirect(url_for('dash.dashboard'))
                else:
                    flash('Password or email incorrectly entered', 'warning')
            else:
                flash('Must enter password', 'warning')
        elif formDict.get('btn_login_as_guest'):
            print('GUEST EMAIL::: ', current_app.config['GUEST_EMAIL'])
            user = sess.query(Users).filter_by(id=2).first()
            login_user(user)
            flash('Logged in succesfully as Guest', 'info')

            return redirect(url_for('dash.dashboard'))
        else:
            flash('No user by that name', 'warning')

        # if successsful login_something_or_other...


    
    return render_template('login.html', page_name = page_name)

@users.route('/register', methods = ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dash.dashboard'))
    page_name = 'Register'
    if request.method == 'POST':
        formDict = request.form.to_dict()
        new_email = formDict.get('email')
        check_email = sess.query(Users).filter_by(email = new_email)
        hash_pw = bcrypt.hashpw(formDict.get('password_text').encode(), salt)
        new_user = Users(email = new_email, password = hash_pw)
        sess.add(new_user)
        sess.commit()
        flash(f'Succesfully registerd: {new_email}', 'info')
        return redirect(url_for('users.login'))

    return render_template('register.html', page_name = page_name)


@users.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('users.home'))


@users.route('/account', methods = ['GET', 'POST'])
@login_required
def account():
    page_name = 'Account Page'
    email = current_user.email

    existing_oura_token =sess.query(Oura_token, func.max(
        Oura_token.id)).filter_by(user_id=current_user.id).first()[0]
    
    # other_users_email_list = [i.email for i in sess.query(Users).filter(Users.id != current_user.id).all()]
    # print('*****  Not current user  ***')
    print('Current User: ', current_user.email)
    # print('All other users: ', other_users_email_list)

    user = sess.query(Users).filter_by(id = current_user.id).first()
    

    print('Current user Latitude: ', user.lat)
    if user.lat == None or user.lat == '':
        existing_coordinates = ''
    else:
        existing_coordinates = f'{user.lat}, {user.lon}'
        
    
    if existing_oura_token:
        oura_token = current_user.oura_token_id[-1].token
        existing_oura_token_str = str(existing_oura_token.token)
    else:
        oura_token = ''
        existing_oura_token_str = ''


    if request.method == 'POST':
        if current_user.id == 2:
            flash('Guest can enter any values but they will not change the database', 'info')
            return redirect(url_for('users.account'))
        else:
            startTime_post = time.time()
            formDict = request.form.to_dict()
            new_token = formDict.get('oura_token')
            new_location = formDict.get('location_text')
            email = formDict.get('email')
            user = sess.query(Users).filter_by(id = current_user.id).first()
            yesterday = datetime.today() - timedelta(days=1)
            yesterday_formatted =  yesterday.strftime('%Y-%m-%d')
            user_loc_days = sess.query(User_location_day).filter_by(user_id=current_user.id).all()
            user_loc_days_date_dict = {i.date : i.id for i in user_loc_days}

            #1) User adds Oura_token data
                #a cases oura_token was blank and not it is not
                #b case oura_token was not blank and not it is different than before
            if new_token != existing_oura_token_str:#<-- if new token is different 
                print('------ New token detected ------')
                #1-1a) if user has token replace it
                if existing_oura_token:
                    existing_oura_token.token = new_token
                    sess.commit()
                    oura_token_id = existing_oura_token.id

                #1-1b) else add new token
                else:
                    
                    new_oura_token = Oura_token(user_id = current_user.id,
                        token = new_token)
                    sess.add(new_oura_token)
                    sess.commit()

                    oura_token_id = new_oura_token.id

                #1-1b-1) check if user has oura data yesterday
                oura_yesterday = sess.query(Oura_sleep_descriptions).filter_by(
                    user_id = current_user.id,
                    summary_date = yesterday_formatted).first()
                
                # --> 1-1b-1a) if yes, nothing 


                # --> 1-1b-1b) if no, call API
                if not oura_yesterday:
                    print('---- no data detected yesterday for this user')
                    print('oura_yesterday::')
                    print(oura_yesterday)
                    url_sleep=current_app.config['OURA_API_URL_BASE']#TODO: put this address in config
                    response_sleep = requests.get(url_sleep, headers={"Authorization": "Bearer " + new_token})
                    if response_sleep.status_code ==200:
                        sleep_dict = response_sleep.json()

                # --> 1-1b-2)Response data add to OUra_sleep_desciprtions for each session in response
                        user_sleep_sessions = sess.query(Oura_sleep_descriptions).filter_by(user_id = current_user.id).all()
                        user_sleep_end_list = [i.bedtime_end for i in user_sleep_sessions]
                # -------> 1-1b-2a) if endsleep exists, skip
                
                # -------> 1-1b-2b) if  endsleep NOT exists, add row
                        sessions_added = 0
                        for session in sleep_dict.get('sleep'):
                            if session.get('bedtime_end') not in user_sleep_end_list:

                                for element in list(session.keys()):
                                    if element not in Oura_sleep_descriptions.__table__.columns.keys():
                                        del session[element]

                                #CHECKED check this reference of new_oura_token works????? 
                                #CHECKED 9/16/2022 and it seems to be working fine here
                                session['token_id'] = oura_token_id
                                session['user_id'] = current_user.id

                                # new_oura_session_date = session['summary_date']
                                # new_oura_session_score = session['score']
                                
                                try:
                                    new_oura_session = Oura_sleep_descriptions(**session)
                                    sess.add(new_oura_session)
                                    sess.commit()
                                    # oura_add_successfully = True
                                    sessions_added +=1
                                    
                                except:
                                    print(f"Failed to add oura data row for sleepend: {session.get('bedtime_end')}")
                                    # oura_add_successfully = False
                        flash(f'Successfully added {sessions_added} sleep sesions and updated user Oura Token', 'info')
                    else:
                        print("response_sleep.status_code::", response_sleep.status_code)
                        print('did not add oura data for user becuause token is not accpeted by OUra')
                        flash('Unable to get data from Oura API becuase does not recognize this token', 'warning')
                else:
                    print('-- date detected yesterday for this user')
                    print(oura_yesterday)
                #### NO need to add oura to User_loc_day anymore --> primarily used for tracking users location, but since weather should follow we add weather as well.
                #1-1b-3) Update/add to User_loc_day: For each user row in sleep_descript
         

            #2) User adds location data
                #a case location was blank and now it is not anymore
                #b case location is different than it was before
            if new_location != existing_coordinates:
                if new_location == '':                          #<--- clear old locations
                    user.lat = None
                    user.lon = None
                    sess.commit()
                    flash('User coordinates removed succesfully','info')
                
                else:                                           #<-- location has latitude and longitude
                    # add lat/lon to users table
                    user.lat = formDict.get('location_text').split(',')[0]
                    user.lon = formDict.get('location_text').split(',')[1]
                    sess.commit()
                    print('---- Added new coordinates for user ----')

                    location_id = location_exists(user)
                    if location_id > 0:                             #<--- locations already exists in database
                        print('--- location already exists ----')
                        new_user_loc_day = User_location_day(user_id=current_user.id,
                            location_id = location_id,
                            date = yesterday_formatted,
                            local_time = f"{str(datetime.now().hour)}:{str(datetime.now().minute)}",
                            row_type='user input')
                        sess.add(new_user_loc_day)
                        sess.commit()
                        flash(f"Updated user's location and add weather history", 'info')

                    else:                                               #<--- Location is completely new
                        print('--- location does not exist, in process of adding ---')
                        location_api_response = call_location_api(user)
                        if isinstance(location_api_response,dict):
                            location_id = add_new_location(location_api_response)
                            

                #Add User_Loc_day
                            yesterday = datetime.today() - timedelta(days=1)
                            yesterday_formatted =  yesterday.strftime('%Y-%m-%d')
                            new_user_loc_day = User_location_day(
                                user_id = user.id,
                                location_id = location_id,
                                local_time = f"{str(datetime.now().hour)}:{str(datetime.now().minute)}",
                                date = yesterday_formatted,
                                row_type = 'user input'
                            )
                            sess.add(new_user_loc_day)
                            sess.commit()

            #new #2-1b-2) call weather history 
                            # call_weather_api(location_id, today)
                            weather_api_response = requests.get(gen_weather_url(location_id, yesterday_formatted))
                            print('weather_api_response status code: ', weather_api_response.status_code)
                            
                            if weather_api_response.status_code == 200:
                    #2-1b-2) use response to populate yesterday's history in WEather_history
                                print('** Adding weather history')
                                add_weather_history(weather_api_response, location_id)
                            else:
                                print('** FAILING to adding weather history')
                                flash(f"Unable to add weather history - problem communicating with Visual Crossing", 'warning')



            #3) User changes email
            if email != user.email:
                
                #check that not blank
                if email == '':
                    flash('Must enter a valid email.', 'warning')
                    return redirect(url_for('users.account'))

                #check that email doesn't alreay exist outside of current user
                other_users_email_list = [i.email for i in sess.query(Users).filter(Users.id != current_user.id).all()]

                if email in other_users_email_list:
                    flash('That email is being used by another user. Please choose another.', 'warning')
                    return redirect(url_for('users.account'))
                
                #update user email
                user.email = email
                sess.commit()
                flash('Email successfully updated.', 'info')
                return redirect(url_for('users.account'))

            #END of POST
            executionTime = (time.time() - startTime_post)
            print('POST time in seconds: ' + str(executionTime))
            return redirect(url_for('users.account'))
            
    
    return render_template('account.html', page_name = page_name, email=email,
         oura_token = oura_token, location_coords = existing_coordinates)



@users.route('/reset_password', methods = ["GET", "POST"])
def reset_password():
    page_name = 'Request Password Change'
    if current_user.is_authenticated:
        return redirect(url_for('dash.dashboard'))
    # form = RequestResetForm()
    # if form.validate_on_submit():
    if request.method == 'POST':
        formDict = request.form.to_dict()
        email = formDict.get('email')
        user = sess.query(Users).filter_by(email=email).first()
        if user:
        # send_reset_email(user)
            print('Email reaquested to reset: ', email)
            send_reset_email(user)
            flash('Email has been sent with instructions to reset your password','info')
            # return redirect(url_for('users.login'))
        else:
            flash('Email has not been registered with What Sticks','warning')

        return redirect(url_for('users.reset_password'))
    return render_template('reset_request.html', page_name = page_name)


@users.route('/reset_password/<token>', methods = ["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('dash.dashboard'))
    user = Users.verify_reset_token(token)
    print('user::', user)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('users.reset_password'))
    if request.method == 'POST':
        
        formDict = request.form.to_dict()
        if formDict.get('password_text') != '':
            hash_pw = bcrypt.hashpw(formDict.get('password_text').encode(), salt)
            user.password = hash_pw
            sess.commit()
            flash('Password successfully updated', 'info')
            return redirect(url_for('users.login'))
        else:
            flash('Must enter non-empty password', 'warning')
            return redirect(url_for('users.reset_token', token=token))

    return render_template('reset_request.html', page_name='Reset Password')

@users.route('/about_us')
def about_us():
    page_name = 'About us'
    return render_template('about_us.html', page_name = page_name)

@users.route('/privacy')
def privacy():
    page_name = 'Privacy'
    return render_template('privacy.html', page_name = page_name)

@users.route('/YouTube_OAuth_Cred_Request')
def youtube_request():
    page_name = 'YouTub OAuth 2.0 Credentials Request'
    return render_template('youtube.html', page_name = page_name)