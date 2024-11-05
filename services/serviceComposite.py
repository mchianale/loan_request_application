import logging
import threading
from suds.client import Client
import pandas as pd
import requests
from loanObject import LoanApplication, ErrorObj, toDict, extractObjDict, creditCheckObjDict, propertyValuationObjDict, approvalDecisionObjDict, CreditInformation, PropertyInformation
from serviceManager import ServiceManager
from serviceExtraction import ServiceExtraction
from creditCheckService import CreditCheckService
from propertyValuationService import PropertyValuationService
from approvalDecisionService import ApprovalDecisionService
from datetime import datetime

logging.basicConfig(level=logging.DEBUG)


class ServiceComposite:
    def __init__(self, tns_name, services_informations, model_config : dict, score_rules : dict, url_root):
        self.tns_name = tns_name
        self.services_informations = services_informations
        # laod just one time csv cities use in several service
        cities = pd.read_csv('services/features/data/cities.csv')
        # set service extraction use model
        ServiceExtraction.set_model(model_config=model_config)
        ServiceExtraction.set_cities_dataframe(cities=cities)
        # set the rates information 
        CreditCheckService.setRatesInformations()
        CreditCheckService.set_cities_dataframe(cities=cities)
        # set cities dataframe to
        PropertyValuationService.set_cities_dataframe(cities=cities)
        # set the rules for the last service
        ApprovalDecisionService.setScoreRules(score_rules=score_rules)
        # store active services threads {Service name : (service_tread, client)}
        self.active_services = {}  # Dictionary to store running services and clients
        self.lock = threading.Lock()
        
        # API
        self.url_root = url_root

    def start_service(self, service_class):
        service_name = service_class.__name__
        if service_name not in self.active_services:
            assigned_port = self.services_informations[service_name]['port']
            service_manager = ServiceManager(service_class, assigned_port, self.tns_name)
            service_thread = threading.Thread(target=service_manager.run)
            service_thread.start()
            logging.info(f'Started {service_name} on port {assigned_port}')
            client = Client(f'http://0.0.0.0:{assigned_port}/{service_name}?wsdl')

            with self.lock:
                self.active_services[service_name] = (service_thread, client)
                
        return True

    def stop_all_services(self):
        logging.info("Stopping all active services...")
        for service_name, (service_thread, _) in self.active_services.items():
            service_thread.join()  # Ensure the service thread finishes cleanly
            logging.info(f'Stopped {service_name}')

    def run_services(self):
        # Start all necessary services once
        class_ = [ServiceExtraction, CreditCheckService, PropertyValuationService, ApprovalDecisionService]
        for c in class_:
            self.start_service(c)

    def update_status(self, _id, status, user_id, error=None):
        url = self.url_root + '/pending/update_status'
        if not error:
            payload = {
                'user_id' : user_id,
                'pending_id' : _id,
                'status' : status
            }
        else:
            payload = {
                'user_id' : user_id,
                'pending_id' : _id,
                'status' : status,
                'error' : error.content

            }
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            return
        raise Exception(f"Issue pending {_id} doesn't exist !")
        
    def add_loan_request(self, loan_request):
        url = self.url_root + '/request/add'
        payload = {'loan_request' : loan_request}
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            return
        raise Exception(f"Probleme d'ajout {loan_request['_id']} existe deja !")
     

    def remove_loan_pending(self, _id, user_id):
        url = self.url_root + '/pending/delete'
        payload = {
            'user_id' : user_id,
            'pending_id' : _id,
            'forced' : False
        }
        response = requests.post(url, json=payload)
        if response.status_code == 201:
            return
        raise Exception(f"Can't delete {_id} !")
       

def runCreditCheckService(serviceComposite : ServiceComposite, loanApplication : LoanApplication, creditInformation : CreditInformation, result : dict):
    _, CreditCheckServiceClient = serviceComposite.active_services['CreditCheckService']  
    creditCheckObj = CreditCheckServiceClient.service.getCreditScore(creditInformation)
    result['creditCheckObj'] = creditCheckObj
    return True


def runPropertyValuationService(serviceComposite : ServiceComposite, loanApplication : LoanApplication, propertyInformation : PropertyInformation, result : dict):
    _, PropertyValuationServiceClient = serviceComposite.active_services['PropertyValuationService'] 
    propertyValuationObj = PropertyValuationServiceClient.service.getPropertyEvaluation(propertyInformation)
    result['propertyValuationObj'] = propertyValuationObj 
    return True

def run_loan_application(serviceComposite : ServiceComposite, loanApplication : LoanApplication):
    # status Pending => Start => Load => Evaluation => Finished
    # ServiceExtraction
    _ , ServiceExtractionClient = serviceComposite.active_services['ServiceExtraction']
    
    extractObj = ServiceExtractionClient.service.extract(loanApplication.request)
    
    # udpate status
    serviceComposite.update_status(_id=loanApplication._id, status='Load', user_id=loanApplication.user_id, error=extractObj.error)
    # manage error
    if extractObj.error:
        # failed to extract must have attributs
        return False
   

    # run creditCheckService and propertyValuationService at the same time
    # Create threads for both services
    result = {'creditCheckObj' : None, 'propertyValuationObj' : None}
    credit_check_thread = threading.Thread(target=runCreditCheckService, args=(serviceComposite, loanApplication, extractObj.creditInformation, result))
    property_valuation_thread = threading.Thread(target=runPropertyValuationService, args=(serviceComposite, loanApplication, extractObj.propertyInformation, result))
    # Start both threads
    credit_check_thread.start()
    property_valuation_thread.start()
    # Wait for both threads to complete
    credit_check_thread.join()
    property_valuation_thread.join()
    creditCheckObj, propertyValuationObj = result['creditCheckObj'], result['propertyValuationObj']  
    # manage error
    if creditCheckObj.error or propertyValuationObj.error:
        # issue with computation
        error = ErrorObj(content='Failed Evaluation')
        # udpate status
        serviceComposite.update_status(_id=loanApplication._id, status='Evaluation', user_id=loanApplication.user_id,  error=error)
        return False
    # udpate status
    serviceComposite.update_status(_id=loanApplication._id, status='Evaluation',user_id=loanApplication.user_id, )
    

    # ApprovalDecisionService
    _, ApprovalDecisionClient = serviceComposite.active_services['ApprovalDecisionService']
    
    approvalDecisionObj = ApprovalDecisionClient.service.getScoring(extractObj, 
                                                                creditCheckObj.creditCheckInformation, 
                                                                propertyValuationObj.propertyValuationInformation)
   
    approvalDecisionObj_dict = approvalDecisionObjDict(approvalDecisionObj)
     
    # udpate status
    serviceComposite.update_status(_id=loanApplication._id, status='Finished', user_id=loanApplication.user_id, error=approvalDecisionObj.error)
    # manage error
    if approvalDecisionObj.error:
        return False
    # create loan_request
    approvalDecisionObj_dict['user_id'] = loanApplication.user_id
    approvalDecisionObj_dict['_id'] = loanApplication._id
    approvalDecisionObj_dict['request'] = loanApplication.request
    # get the date
    approvalDecisionObj_dict['date'] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    
    serviceComposite.add_loan_request(loan_request=approvalDecisionObj_dict)
    serviceComposite.remove_loan_pending(_id=loanApplication._id, user_id=loanApplication.user_id)
    return True
        

