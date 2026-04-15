from config import SECRET_KEY
from flask import Flask

from routes.pt_routes import pt_blueprint
from routes.auth_routes import auth_blueprint
from routes.home_routes import home_blueprint

app = Flask(__name__)
app.secret_key = SECRET_KEY

if __name__ == '__main__':
    app.register_blueprint(pt_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(home_blueprint)

    app.run(debug=True)