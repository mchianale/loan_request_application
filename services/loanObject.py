from spyne import Unicode, ComplexModel, Float, Boolean

# defined all class which we will used
class ContentPathObject:
    def __init__(self, request_path, payment_history_path):
        self.request = request_path
        self.payment_history_path = payment_history_path

class LoanApplication:
    def __init__(self, loan_pending : dict):
        self._id = loan_pending['_id']
        self.user_id = loan_pending['user_id']
        self.request = loan_pending['request']

def toDict(obj : ComplexModel):
    if obj:
        return dict(obj)
    return None



# manage error separetly
class ErrorObj(ComplexModel):
    content = Unicode

# track user global informations
class UserInformation(ComplexModel):
    user_name = Unicode 
    user_mail = Unicode
    user_num = Unicode
    user_address = Unicode # can be Null
    user_situation = Unicode # can be Null
   
# input to creditCheckService
class CreditInformation(ComplexModel):
    revenu_mensuel = Float
    depense_mensuel = Float
    montant_pret = Float
    duree_pret = Float
    zip_code_logement = Float # can be Null

# property evaluation service
class PropertyInformation(ComplexModel):
    logement_address = Unicode # can be Null
    type_logement = Unicode  # can be Null
    code_insee_logement = Unicode  # can be Null
    apport = Float # can be Null
    montant_pret = Float   
    
class ExtractObj(ComplexModel):
    userInformation = UserInformation
    creditInformation = CreditInformation
    propertyInformation = PropertyInformation
    error = ErrorObj

def extractObjDict(extractObj : ExtractObj):
        return {
            'userInformation': toDict(extractObj.userInformation),
            'creditInformation': toDict(extractObj.creditInformation),
            'propertyInformation': toDict(extractObj.propertyInformation),
            'error': toDict(extractObj.error) 
        }

class CreditCheckInformation(ComplexModel):
    duree_pret_year = Float #CreditInformation.duree_pret
    duree_pret_month = Float #CreditInformation.duree_pret
    region_rate = Unicode #CreditInformation.zip_code_logement & #CreditInformation.duree_pret, if not CreditInformation.zip_code_logement => default National
    yearly_rate = Float 
    monthly_rate = Float
    monthly_pay = Float
    debt_ratio = Float

class CreditCheckObj(ComplexModel):
    creditCheckInformation = CreditCheckInformation
    error = ErrorObj

def creditCheckObjDict(creditCheckObj : CreditCheckObj):
    return {
            'creditCheckInformation': toDict(creditCheckObj.creditCheckInformation),
            'error': toDict(creditCheckObj.error) 
        }
  

class PropertyValuationInformation(ComplexModel):
    logement_address = Unicode # can be Null
    code_insee_logement = Unicode # can be Null
    type_logement = Unicode  # can be Null
    gen_type_logement_v0 = Unicode #PropertyInformation.type_logement, if null => default Maison
    gen_type_logement_v1 = Unicode #PropertyInformation.type_logement, if null => default appartement-loyer-m2
    mean_surface_m2 = Float #PropertyInformation.code_insee, if null => null
    default_mean_surface_m2 = Boolean
    mean_loyer_m2 = Float  #PropertyInformation.code_insee, if null => null
    mean_yearly_loyer = Float # mean_surface_m2 & mean_loyer_m2, if null => null
    rental_yield_score = Float # by deduction can be Null
    
class PropertyValuationObj(ComplexModel):
    propertyValuationInformation = PropertyValuationInformation
    error = ErrorObj

def propertyValuationObjDict(propertyValuationObj : PropertyValuationObj):
    return {
        'propertyValuationInformation' : toDict(propertyValuationObj.propertyValuationInformation),
        'error' : toDict(propertyValuationObj.error)
    }

    
class ApprovalDecisionInformation(ComplexModel):
    # user information 
    user_name = Unicode 
    user_mail = Unicode
    user_num = Unicode
    user_address = Unicode # can be Null
    user_situation = Unicode # can be Null

    # loan information
    revenu_mensuel = Float
    depense_mensuel = Float
    montant_pret = Float
    apport = Float # can be Null
    duree_pret = Float
    logement_address = Unicode # can be Null
    type_logement = Unicode  # can be Null

    # loan information deduction
    # 1. CreditCheckObj
    monthly_pay = Float
    yearly_rate = Float
    region_rate = Unicode
    # 2. PropertyValuationObj
    mean_surface_m2 = Float  
    mean_monthly_loyer = Float # deduced by mean_yearly_loyer

    # score
    # 1. CreditCheckObj
    debt_ratio = Float
    # 2. PropertyValuationObj
    rental_yield_score = Float
    # 3. compute at this service
    confidence = Float
    monthly_cash_flow = Float
    monthly_cash_flow_score = Float
    user_situation_score = Float
    # Global
    user_score = Float
    weight_user_score = Float
    property_score = Float # can be Null
    weight_property_score = Float
    global_score = Float     
    approve = Boolean
    message_approve = Unicode

class ApprovalDecisionObj(ComplexModel): 
    approvalDecisionInformation = ApprovalDecisionInformation
    error = ErrorObj

def approvalDecisionObjDict(approvalDecisionObj : ApprovalDecisionObj):
    return {
        'approvalDecisionInformation' : toDict(approvalDecisionObj.approvalDecisionInformation),
        'error' : toDict(approvalDecisionObj.error)
    }