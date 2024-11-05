import logging
from spyne import Application 
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication
from twisted.internet import reactor
from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site

class ServiceManager:
    def __init__(self, service_class, port, tns_name):
        self.port = port
        self.application = Application(
            [service_class],
            tns=tns_name,
            in_protocol=Soap11(),
            out_protocol=Soap11()
        )
        self.wsgi_app = WsgiApplication(self.application)

        # Wrap the WSGI app in a Twisted resource
        self.resource = WSGIResource(reactor, reactor.getThreadPool(), self.wsgi_app)
        self.site = Site(self.resource)

        # Set a custom name for the service in the WSDL
        self.service_name = service_class.__name__

    def run(self):
        try:
            # Start the service with a specific path
            reactor.listenTCP(self.port, self.site)
            logging.info('-'*100)
            logging.info(f"Starting {self.service_name} on port {self.port} at path /{self.service_name}")
            logging.info('-'*100)
            reactor.run()  # Run the Twisted reactor
        except Exception as e:
            logging.error(f'Failed to load {self.service_name}: {e}')
            raise  # Re-raise the exception for handling if needed

    def stop(self):
        logging.info('-'*100)
        logging.info(f"Stopping {self.service_name} on port {self.port}...")
        logging.info('-'*100)
        # Stop the reactor only if this is the main instance running
        reactor.callWhenRunning(lambda: reactor.stop())
