"""General Utility Functions."""

from uuid import uuid4

import aiohttp

from aiohttp import web

from ..config import CONFIG
from .logging import LOG


def ssl_context():
    """Handle application security."""
    return None


async def generate_state():
    """Generate a state for authentication request and return the value for use."""
    LOG.debug('Generate a new state for authentication request.')
    return str(uuid4())


async def get_from_cookies(request, key):
    """Get a desired value from cookies."""
    LOG.debug(f'Retrieve value for {key} from cookies.')

    try:
        LOG.debug(f'Returning cookie value for: {key}.')
        return request.cookies[key]
    except KeyError as e:
        LOG.error(f'Cookies has no value for {key}: {e}.')
        raise web.HTTPUnauthorized(text='401 Uninitialised session.')
    except Exception as e:
        LOG.error(f'Failed to retrieve cookie: {e}')
        raise web.HTTPInternalServerError(text=f'500 Session has failed: {e}')


async def save_to_cookies(response, key='key', value='value', http_only=True, lifetime=300):
    """Save a given value to cookies."""
    LOG.debug(f'Save a value for {key} to cookies.')

    response.set_cookie(key,
                        value,
                        domain=CONFIG.cookie['domain'],
                        max_age=lifetime,
                        secure=CONFIG.cookie['secure'],
                        httponly=http_only)

    return response


async def request_token(code):
    """Request token from AAI."""
    LOG.debug('Requesting token.')

    auth = aiohttp.BasicAuth(login=CONFIG.aai['client_id'], password=CONFIG.aai['client_secret'])
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': CONFIG.aai['url_callback']
    }

    # Set up client authentication for request
    async with aiohttp.ClientSession(auth=auth) as session:
        # Send request to AAI
        async with session.post(CONFIG.aai['url_token'], data=data) as response:
            LOG.debug(f'AAI response status: {response.status}.')
            # Validate response from AAI
            if response.status == 200:
                # Parse response
                result = await response.json()
                # Look for access token
                if 'access_token' in result:
                    LOG.debug('Access token received.')
                    return result['access_token']
                else:
                    LOG.error('AAI response did not contain an access token.')
                    raise web.HTTPBadRequest(text='AAI response did not contain an access token.')
            else:
                LOG.error(f'Token request from AAI failed: {response}.')
                LOG.error(await response.json())
                raise web.HTTPBadRequest(text=f'Token request from AAI failed: {response.status}.')


async def query_params(request):
    """Parse query string params from path."""
    LOG.debug('Parse query params from AAI response.')

    desired_params = ['state', 'code']
    params = {k: v for k, v in request.rel_url.query.items() if k in desired_params}

    # Response from AAI must have the query params `state` and `code`
    if 'state' in params and 'code' in params:
        LOG.debug('AAI response contained the correct params.')
        return params
    else:
        LOG.error(f'AAI response is missing mandatory params, received: {params}')
        raise web.HTTPBadRequest(text='AAI response is missing mandatory parameters.')
