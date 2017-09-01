.. image:: https://travis-ci.org/jbn/brittle_wit_core.svg?branch=master
    :target: https://travis-ci.org/jbn/brittle_wit_core
.. image:: https://ci.appveyor.com/api/projects/status/69kj3prrrieyp8q2/branch/master?svg=true
    :target: https://ci.appveyor.com/project/jbn/brittle_wit_core/branch/master 
.. image:: https://coveralls.io/repos/github/jbn/brittle_wit_core/badge.svg?branch=master
    :target: https://coveralls.io/github/jbn/brittle_wit_core?branch=master 
.. image:: https://img.shields.io/pypi/dm/brittle_wit_core.svg
    :target: https://pypi.python.org/pypi/brittle_wit_core
.. image:: https://img.shields.io/pypi/v/brittle_wit_core.svg
    :target: https://pypi.python.org/pypi/brittle_wit_core
.. image:: https://img.shields.io/badge/license-MIT-blue.svg
    :target: https://raw.githubusercontent.com/jbn/brittle_wit_core/master/LICENSE
.. image:: https://img.shields.io/pypi/pyversions/brittle_wit_core.svg
    :target: https://pypi.python.org/pypi/brittle_wit_core

-------------------------------------------------------------------------------

=============
What is this?
=============

This package contains the core of ``brittle_wit``, a twitter lib for python. 
It works with Python 2.7, whereas ``brittle_wit`` does not. It's extracted from 
the main library so that you can reuse this core code for authentication 
flows (e.g. on GAE).

--------------------------------------------
Sample Authentication Flow with ``requests``
--------------------------------------------

.. code:: python

    import request
    from brittle_wit_core import (AppCredentials,
                                  obtain_request_token,
                                  extract_access_token,
                                  redirect_url,
                                  obtain_access_token,
                                  extract_request_token)

    # Loads via TWITTER_APP_KEY, TWITTER_APP_SECRET environmental variables.
    APP_CRED = AppCredentials.load_from_env()

    # Get an access token.
    twitter_req, headers = obtain_request_token(APP_CRED)
    resp = request(twitter_req.method,
                   twitter_req.url,
                   params=twitter_req.params,
                   headers=headers)
    oauth_token, oauth_secret = extract_request_token(resp.status_code,
                                                      resp.content.decode('utf8'))

    # Redirect the user to a PIN page.
    url = redirect_url(oauth_token)
    print(url)
    pin = input("PIN: ").strip()


    # Turn their pin response into an access token.
    twitter_req, headers = obtain_access_token(APP_CRED, oauth_token, pin)

    resp = request(twitter_req.method,
                   twitter_req.url,
                   params=twitter_req.params,
                   headers=headers)
    d = extract_access_token(resp.status_code, resp.content.decode('utf8'))
    print(d)
