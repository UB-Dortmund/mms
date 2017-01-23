from jose import jwt
from jose.exceptions import JWTClaimsError

try:
    import local_api_secrets as secrets
except ImportError:
    import api_secrets as secrets


def is_token_valid(token=''):

    try:
        jwt.decode(token, secrets.API_SECRET, audience=secrets.API_JWT_AUD, algorithms=['HS256'])
        return True
    except JWTClaimsError:
        return False

payload = {
    'sub': 'MMS REST API',
    'name': 'Sandbox Access',
    'admin': 'true',
    'iss': 'api.ub@tu-dortmund.de',
    'aud': 'dev.ub@tu-dortmund.de'
}

token = jwt.encode(payload, secrets.API_SECRET, algorithm='HS256')

print(token)

print(is_token_valid(token))
