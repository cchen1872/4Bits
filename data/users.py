"""
This module interfaces with user data.
"""

# import data.food
import random
from string import ascii_uppercase
# import requests
import data.db_connect as con
from PIL import Image
import pytesseract
import datetime
from google.oauth2 import id_token
from google.auth.transport import requests

TEST_USERNAME_LENGTH = 6
TEST_NAME_LENGTH = 6

NAME = 'Name'
PANTRY = 'Pantry'
USERNAME = "Username"
SAVED_RECIPES = 'Saved_Recipes'
INSTACART_USR = 'Instacart_User_Info'
GROCERY_LIST = 'Grocery List'
ALLERGENS = 'Allergens'
AUTH_EXPIRES = "Auth_Exp"


class AuthTokenExpired(Exception):
    pass


def _get_test_username():
    con.connect_db()
    username = ''.join(random.choices(ascii_uppercase, k=TEST_USERNAME_LENGTH))
    while user_exists(username):
        username = ''.join(random.choices(
            ascii_uppercase, k=TEST_USERNAME_LENGTH))
    return username


def _get_test_name():
    con.connect_db()
    name = ''.join(random.choices(ascii_uppercase, k=TEST_NAME_LENGTH))

    return name


def _get_test_exp():
    return datetime.datetime.now() + datetime.timedelta(hours=1)


def user_exists(username):
    con.connect_db()
    try:
        con.fetch_one(con.USERS_COLLECTION, {USERNAME: username})
        res = True
    except ValueError:
        res = False
    return res


def _create_test_user():
    username = _get_test_username()
    name = _get_test_name()
    exp = _get_test_exp()
    print(username, name, exp)
    test_user = create_user(username, name, exp)
    return test_user


def get_users():
    con.connect_db()
    users = con.fetch_all(con.USERS_COLLECTION)
    for user in users:
        user[con.MONGO_ID] = str(user[con.MONGO_ID])
    return users


def get_user(username: str) -> str:
    con.connect_db()
    try:
        res = con.fetch_one(con.USERS_COLLECTION, {USERNAME: username})
        res[con.MONGO_ID] = str(res[con.MONGO_ID])
    except ValueError:
        raise ValueError(f'User {username} does not exist')

    return res


def auth_expired(username: str) -> bool:
    exp = con.fetch_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {AUTH_EXPIRES: 1, con.MONGO_ID: 0}
    )

    return exp[AUTH_EXPIRES] <= datetime.datetime.now().timestamp()


def valid_authentication(google_id_token):
    # Add check for CLIENT ID for app that accesses authentication
    # Maybe save valid CLIENT ID to check against in os.environ()
    idinfo = id_token.verify_oauth2_token(google_id_token, requests.Request())
    exp = idinfo['exp']
    if exp < datetime.datetime.now().timestamp():
        raise AuthTokenExpired("Expired token")
    return idinfo


def auth_user(google_id_token):
    try:
        id_info = valid_authentication(google_id_token)
        username = id_info['email']
        if not user_exists(username):
            raise ValueError("User associated with token does not exist")

        exp = datetime.datetime(id_info['exp'])
        con.update_one(
            con.USERS_COLLECTION,
            {USERNAME: username},
            {AUTH_EXPIRES: exp}
        )

    except ValueError as ex:
        # Invalid token
        raise ex


def create_user(username: str, name: str, expires: datetime.datetime) -> dict:
    con.connect_db()
    if len(username) < 5:
        raise ValueError(f'Username {username} is too short')

    if user_exists(username):
        raise ValueError(f'User {username} already exists')

    print(type(username))
    print(type(name))

    new_user = {
        USERNAME: username,
        NAME: name,
        PANTRY: [],
        SAVED_RECIPES: {},
        INSTACART_USR: None,
        GROCERY_LIST: [],
        ALLERGENS: [],
        AUTH_EXPIRES: int(expires.timestamp()),
    }
    print(f'{new_user=}')

    add_ret = con.insert_one(con.USERS_COLLECTION, new_user)
    print(f'{add_ret}')
    return new_user


def remove_user(username):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    del_res = con.del_one(con.USERS_COLLECTION, {USERNAME: username})

    print(f'{del_res}')
    return f'Successfully deleted {username}'


def get_pantry(username):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    pantry_res = con.fetch_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {PANTRY: 1, con.MONGO_ID: 0}
    )

    return pantry_res


def add_to_pantry(username: str, food: list[str]) -> str:
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    con.update_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {"$push": {PANTRY: {"$each": food}}}
    )
    return f'Successfully added {food}'


def get_recipes(username):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    recipes_res = con.fetch_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {SAVED_RECIPES: 1, con.MONGO_ID: 0}
    )

    return recipes_res


def generate_recipe(username, query):
    app_key = '274c6a9381c49bc303a30cebb49c84d4'
    app_id = '29bf3511'
    query_string = 'https://api.edamam.com/api/recipes\
        /v2?type=public&q=' + query + '&app_id=' + app_id +\
        '&app_key=' + app_key
    x = requests.get(query_string)
    return x  # return full recipe response body


def add_to_recipes(username, recipe):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    con.update_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {"$push": {SAVED_RECIPES: {recipe: 0}}}
    )

    return f'Successfully added {recipe}'


def made_recipe(username, recipe):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    con.update_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {"$inc": {f'{SAVED_RECIPES}.{recipe}': 1}}
    )

    return f'Successfully incremented streak counter for {recipe}'


def remove_recipe(username, recipe):
    con.connect_db()
    if not user_exists(username):
        raise ValueError(f'User {username} does not exist')

    con.update_one(
        con.USERS_COLLECTION,
        {USERNAME: username},
        {"$pull": {SAVED_RECIPES: recipe}}
    )

    return f'Successfully removed {recipe}'


def recognize_receipt(image_path=None, image=None):
    if (image_path and not image):
        # Load the image from the specified path
        image = Image.open(image_path)
    elif (not image):  # neither the path nor image is provided
        return None
    # Perform OCR using pytesseract
    text = pytesseract.image_to_string(image)
    # Print or save the extracted text
    print(text)
    # Optionally, save the text to a file
    # with open('extracted_text.txt', 'w', encoding='utf-8') as file:
    #     file.write(text)
    return text
