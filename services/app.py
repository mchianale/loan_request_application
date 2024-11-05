import logging
import threading
import json
import time
from twisted.internet import reactor
from serviceComposite import ServiceComposite, run_loan_application
from loanObject import LoanApplication
import requests


logging.basicConfig(level=logging.DEBUG)
CONFIG_PATH = 'config.json'

class LoanApplicationAPP:
    def __init__(self, config):    
        self.url_root = f"http://backend_service:{config['backend_service']['port']}/api/"
        # composite service 
        self.composite = ServiceComposite(tns_name=config['tns_name'], 
                                        services_informations=config['services'], 
                                        model_config=config['camembert_model'],
                                        score_rules=config['score_rules'],
                                        url_root=self.url_root)
        # store active threads and their corresponding ports
        self.active_threads = []
        self.lock = threading.Lock()  # Lock to prevent race conditions when managing threads and ports

    def stop_all(self):
        logging.info("Stopping application...")
        # Continuously check if all threads have Finished
        while any(t.is_alive() for t in self.active_threads):
            logging.info("Waiting for all threads to finish...")
            time.sleep(1)  # Sleep for a while before checking again
        logging.info("All threads (loan applications) have Finished.")
        # Stopping all services
        self.composite.stop_all_services()

    # 8, 6, 1
    def run(self):
        # run all services
        self.composite.run_services()
        # continusly run using watchdogs
        try:
            while True: 
                url = self.url_root + 'pending/all_pendings'
                try:
                    response = requests.get(url)
                    loan_pendings = response.json()['loan_pendings']
                    for loan_pending in loan_pendings:
                        new_loan_application = LoanApplication(loan_pending=loan_pending)
                        t = threading.Thread(target=run_loan_application, args=(self.composite, new_loan_application, ))
                        t.start()
                        # udpate status
                        self.loan_pendings.update_one(
                            {"_id": loan_pending['_id']},
                            {"$set": {"status": "Start"}}
                        )
                        with self.lock:
                            # Add thread and loan_application to the active threads list
                            self.active_threads.append(t)
                            # Clean up finished threads
                            self.active_threads = [t for t in self.active_threads if t.is_alive()]         
                except:
                    # the backend is maybe not ready
                    time.sleep(1)          
                time.sleep(1)
            

        except KeyboardInterrupt:
            # in this case we check that are no more alive compiste service
            self.stop_all()
            reactor.stop()
        

if __name__ == "__main__":
    #read config
    config = json.load(open(CONFIG_PATH, encoding='utf-8'))
    app = LoanApplicationAPP(config=config)
    app.run()
