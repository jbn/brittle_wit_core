__title__ = "brittle_wit_core"
__description__ = "Version-agnostic core for brittle_wit package"
__uri__ = "https://github.com/jbn/brittle_wit_core"
__doc__ = __description__ + " <" + __uri__ + ">"
__license__ = "MIT"
__copyright__ = "Copyright (c) 2017 John Bjorn Nelson"
__version__ = "0.0.1"
__author__ = "John Bjorn Nelson"
__email__ = "jbn@abreka.com"


from brittle_wit_core.common import (GET, POST, PUT, HEAD, DELETE,
                                     ELIDE,
                                     TwitterRequest,
                                     Cursor,
                                     TwitterResponse,
                                     BrittleWitError,
                                     TwitterError,
                                     WrappedException)

from brittle_wit_core.oauth import (AppCredentials,
                                    ClientCredentials,
                                    generate_req_headers,
                                    obtain_request_token,
                                    extract_request_token,
                                    redirect_url,
                                    obtain_access_token,
                                    extract_access_token)
