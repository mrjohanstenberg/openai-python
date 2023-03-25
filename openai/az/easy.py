import logging
import typing

if typing.TYPE_CHECKING:
    from azure.core.credentials import TokenCredential

try:
    from requests import PreparedRequest, Response
    from requests.adapters import HTTPAdapter
except ModuleNotFoundError:
    print(
        "You have to install the `requests` library (pip install requests) in order to use easyaz.requests"
    )
    exit(-1)

log = logging.getLogger(__name__)


class AzHttpAdapter(HTTPAdapter):
    def __init__(
        self,
        *,
        credential: "TokenCredential",
        scopes: list[str] | str,
        **kwargs: typing.Any,
    ):
        super().__init__(**kwargs)
        self.credential = credential
        self.scopes = [scopes] if isinstance(scopes, str) else scopes
        self.cached_token: str | None = None
        self.max_recurse = 1

    def send(
        self,
        request: PreparedRequest,
        stream: bool = ...,
        timeout: None | float | tuple[float, float] | tuple[float, None] = ...,
        verify: bool | str = ...,
        cert: None | bytes | str | tuple[bytes | str, bytes | str] = ...,
        proxies: typing.Mapping[str, str] | None = ...,
        *,
        recurse: int = 0,
    ) -> Response:
        if not self.cached_token:
            self.cached_token = self.credential.get_token(*self.scopes).token

        request.headers.setdefault("Authorization", "Bearer " + self.cached_token)

        initial_response = super().send(request, stream, timeout, verify, cert, proxies)
        if initial_response.status_code != 401 or recurse > self.max_recurse:
            # Only do the auth dance if we are challenged...
            self.cached_token = None
            return initial_response

        # Drain response
        initial_response.content

        # ... and build a new request clearing out the old authorization header...
        new_request = request.copy()
        new_request.headers.pop("Authorization")

        # Clear out the old token 'cause it clearly didn't work last time around
        self.cached_token = None  # TODO: Fish out possible challenges from response and grab a new token...

        return self.send(
            new_request, stream, timeout, verify, cert, proxies, recurse=recurse + 1
        )
