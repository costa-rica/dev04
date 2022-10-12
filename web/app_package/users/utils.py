from flask import current_app, url_for
from flask_login import current_user
import json
import requests
from datetime import datetime, timedelta
from wsh_models import sess, Users, Locations, Weather_history, \
    Oura_token, Oura_sleep_descriptions, User_location_day
import time
from flask_mail import Message
from app_package import mail
from wsh_config import ConfigDev

config = ConfigDev()

def send_reset_email(user):
    token = user.get_reset_token()
    print('Let s try email::::')
    print('config.EMAIL: ', config.MAIL_USERNAME)
    msg = Message('Password Reset Request',
                  sender=config.MAIL_USERNAME,
                  recipients=[user.email])
    msg.body = f'''To reset your password, visit the following link:
{url_for('users.reset_token', token=token, _external=True)}

If you did not make this request, ignore email and there will be no change
'''

    mail.send(msg)


def send_confirm_email(email):
    msg = Message('Registration Confirmation',
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[email])
    msg.body = 'You have succesfully been registered to What-Sticks.'
    mail.send(msg)



def call_location_api(user):
#2-1b-1) call weather API
    api_token = current_app.config['WEATHER_API_KEY']
    # base_url = 'http://api.weatherapi.com/v1'#TODO: put this address in config
    base_url = current_app.config['WEATHER_API_URL_BASE']
    history = '/history.json'#TODO: put this address in config
    payload = {}
    payload['q'] = f"{user.lat}, {user.lon}"
    payload['key'] = api_token
    yesterday = datetime.today() - timedelta(days=1)
    payload['dt'] = yesterday.strftime('%Y-%m-%d')
    payload['hour'] = 0

#2-1b) if new location is new add location to Locations
    print('* --> start location data process')
    # new_location = Locations()
    try:
        r_history = requests.get(base_url + history, params = payload)
        
        if r_history.status_code == 200:
            print('Location API response code: ', r_history.status_code)
            #2) for each id call weather api
            return r_history.json()
        else:
            return f'Problem connecting with Weather API. Response code: {r_history.status_code}'
    except:
        return 'Error making call to Weather API. No response.'


def gen_weather_url(location_id, date):
    api_token = current_app.config['VISUAL_CROSSING_TOKEN']
    date_time = datetime.strptime(date + " 13:00:00", "%Y-%m-%d %H:%M:%S").isoformat()
    loc = sess.query(Locations).get(location_id)
    lat = loc.lat
    lon = loc.lon
    weather_call_url =f"{current_app.config['VISUAL_CROSSING_BASE_URL']}{str(lat)},{str(lon)}/{str(date_time)}?key={api_token}&include=current"
    print('Weather_call:::')
    print(weather_call_url)
    return weather_call_url


def add_new_location(location_api_response):
    new_location = Locations(
        city = location_api_response.get('location').get('name'),
        region = location_api_response.get('location').get('region'),
        country = location_api_response.get('location').get('country'),
        lat = location_api_response.get('location').get('lat'),
        lon = location_api_response.get('location').get('lon'),
        tz_id = location_api_response.get('location').get('tz_id')
        )
    sess.add(new_location)
    sess.commit()
    location_id = new_location.id
    print(f'***** New location added, id: {location_id} ****')
    return location_id


def add_weather_history(weather_api_response, location_id):

    upload_dict ={ key: value for key, value in weather_api_response.json().get('days')[0].items()}
    del upload_dict['stations']
    del upload_dict['source']
    upload_dict['location_id'] = location_id

    
    upload_dict_keys = list(upload_dict.keys())
    for key in upload_dict_keys:
        if isinstance(upload_dict[key], list):# <--- There have been some values that have return lists but most are text or float
            upload_dict[key] = upload_dict[key][0]
        if key not in Weather_history.__table__.columns.keys():# <--- keys are strange names, this removes any unexpected
            del upload_dict[key]

    try:
        new_data = Weather_history(**upload_dict)
        sess.add(new_data)
        sess.commit()
        return "successfully added to weather histrory"
    except:
        return "failed to add weather history"


def oura_sleep_call(new_token):

    url_sleep='https://api.ouraring.com/v1/sleep?start=2020-03-11&end=2020-03-21?'
    response_sleep = requests.get(url_sleep, headers={"Authorization": "Bearer " + new_token})
    sleep_dict = response_sleep.json()
    print('response_code: ',response_sleep.status_code)
    if response_sleep.status_code !=200:
        print('*** Error With Token ****')
        return 'Error with Token'
    else:
        return sleep_dict

def oura_sleep_db_add(sleep_dict, oura_token_id):
    # Add oura dictionary response to database
    startTime_db_oura_add = time.time()
    deleted_elements = 0 
    
    for sleep_session in sleep_dict['sleep']:
        sleep_session_exists = sess.query(Oura_sleep_descriptions).filter_by(
            bedtime_end = sleep_session.get('bedtime_end'),
            user_id = current_user.id).first()
        if not sleep_session_exists:

            # delete any dict element whose key is not in column list
            for element in list(sleep_session.keys()):
                if element not in Oura_sleep_descriptions.__table__.columns.keys():
                    # print('element to delete: ', element)
                    
                    del sleep_session[element]
                    deleted_elements += 1

            sleep_session['user_id'] = current_user.id
            sleep_session['token_id'] = oura_token_id
            #check if existing sleep bedtime_end exists if yes skip
            existing_sleep_bedtime_end = sess.query(Oura_sleep_descriptions).filter_by(
                user_id = current_user.id,
                bedtime_end = sleep_session['bedtime_end']
            ).first()
            if not existing_sleep_bedtime_end:
                new_sleep = Oura_sleep_descriptions(**sleep_session)
                sess.add(new_sleep)
                sess.commit()
    
    executionTime = (time.time() - startTime_db_oura_add)
    print('Add Oura Data Execution time in seconds: ' + str(executionTime))
    print(f'Number of eleements deleted {deleted_elements}')


def location_exists(user):
    
    min_loc_distance_difference = 1000

    locations_unique_list = sess.query(Locations).all()
    for loc in locations_unique_list:
        lat_diff = abs(user.lat - loc.lat)
        lon_diff = abs(user.lon - loc.lon)
        loc_dist_diff = lat_diff + lon_diff
        # print('** Differences **')
        # print('lat_difference:', lat_diff)
        # print('lon_diff:', lon_diff)

        if loc_dist_diff < min_loc_distance_difference:
            min_loc_distance_difference = loc_dist_diff
            location_id = loc.id

    if min_loc_distance_difference > .1:
        print('-----> loc_dist_diff is less than min required')
        location_id = 0
    
    # returns location_id = 0 if there is no location less than sum of .1 degrees
    return location_id

