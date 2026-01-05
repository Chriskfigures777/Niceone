"""SSL certificate configuration for macOS compatibility"""
import logging
import os
import ssl
import certifi
import aiohttp

logger = logging.getLogger("agent-Alex-2f2")


def configure_ssl() -> None:
    """Configure SSL certificates for macOS compatibility"""
    cert_path = certifi.where()
    os.environ["SSL_CERT_FILE"] = cert_path
    os.environ["REQUESTS_CA_BUNDLE"] = cert_path
    _default_context = ssl.create_default_context(cafile=cert_path)
    ssl._create_default_https_context = lambda: _default_context

    _original_connector_init = aiohttp.TCPConnector.__init__
    
    def _patched_connector_init(self, *args, **kwargs):
        if 'ssl' not in kwargs:
            kwargs['ssl'] = ssl.create_default_context(cafile=cert_path)
        elif kwargs.get('ssl') is True:
            kwargs['ssl'] = ssl.create_default_context(cafile=cert_path)
        elif isinstance(kwargs.get('ssl'), ssl.SSLContext):
            try:
                kwargs['ssl'].load_verify_locations(cert_path)
            except Exception:
                kwargs['ssl'] = ssl.create_default_context(cafile=cert_path)
        return _original_connector_init(self, *args, **kwargs)
    
    aiohttp.TCPConnector.__init__ = _patched_connector_init
    logger.info(f"SSL certificates configured: {cert_path}")





