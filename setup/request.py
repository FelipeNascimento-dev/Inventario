import logging
import httpx


logger = logging.getLogger()


async def log_request_result(prefix, endpoint, method, request_data, res):
    logger.info(
        f"{prefix} | request_method: {method} | request_url: {endpoint!r} | request_body: {request_data} | response_code: {res.status_code} | response_body {res.text}"
    )


class RequestClient:
    def __init__(self, method, url: str, headers, request_data: dict = None, timeout: int = 100) -> None:
        self.method = method
        self.url = url
        self.request_data = request_data
        self.headers = headers
        self.timeout = timeout
        # inject(carrier=self.headers)

    def send_api_request(self):
        logger.info(f"Sending a {self.method} request to: {self.url}")
        logger.info(f"Request body/params: {self.request_data}")
        logger.info(f"Request HEADERS: {self.headers}")

        with httpx.Client(timeout=self.timeout) as client:
            try:
                request = httpx.Request(self.method.upper(), url=self.url,
                                        **{f"{'params' if self.method == 'get' else 'json'}": self.request_data},
                                        headers=self.headers)
                response = client.send(request)
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                log_request_result('request_error', self.url,
                                   self.method, self.request_data, response)
                raise exc

            log_request_result('request_success', self.url,
                               self.method, self.request_data, response)
            return response.json()