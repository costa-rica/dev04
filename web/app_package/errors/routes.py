from flask import Blueprint, render_template, current_app

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def error_404(error):
    error_message = "Web page not found - check what you typed in the address bar"
    return render_template('errors.html', error_number="404", error_message=error_message), 404


@errors.app_errorhandler(401)
def error_401(error):
    error_message = "Web page is restricted"
    return render_template('errors.html', error_number="401", error_message=error_message), 401


@errors.app_errorhandler(400)
def error_400(error):
    error_message = "Bad request"
    return render_template('errors.html', error_number="400", error_message=error_message), 400


@errors.app_errorhandler(500)
def error_500(error):
    error_message = f"Something wrong with webiste. Either try again or send email to {current_app.config['MAIL_USERNAME']}."
    return render_template('errors.html', error_number="500", error_message=error_message), 500

# @errors.app_errorhandler(AttributeError)
# def error_attribute(AttributeError):
#     error_message = f"If you're logged in already or think something else is wrong email {current_app.config['MAIL_USERNAME']}."
#     return render_template('errors.html', error_number="Did you login?", error_message=error_message)

@errors.app_errorhandler(KeyError)
def error_key(KeyError):
    error_message = f"Something is wrong with the site. Send a screen shot or the address you tried to access to {current_app.config['MAIL_USERNAME']}. Thank you"
    return render_template('errors.html', error_number="Did you login?", error_message=error_message)