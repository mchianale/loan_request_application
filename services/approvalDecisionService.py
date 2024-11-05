import logging
from spyne import rpc, ServiceBase
import json
from loanObject import ErrorObj, ExtractObj, CreditCheckInformation, PropertyValuationInformation, ApprovalDecisionInformation, ApprovalDecisionObj
logging.basicConfig(level=logging.DEBUG)

class ApprovalDecisionService(ServiceBase):
    score_rules = None
    '''
        services/features/data/profession_scores.json :
        Professions stables comme les CDI et les fonctionnaires ont un score élevé (100%), car elles sont perçues comme très sûres.
        Entrepreneurs et freelances ont un score plus bas (65-70%) en raison de l'incertitude liée à la stabilité de leur revenu.
        Professions précaires comme les stagiaires, intérimaires, et saisonniers ont un score plus bas (40-50%).
        Les professions sans revenu stable ou associées à une instabilité économique (par exemple chômage, étudiant, retraité) obtiennent un score de 0%.
    '''
    map_user_profession_scores = json.load(open('services/features/data/profession_scores.json', encoding='utf-8'))
    map_letters = {
        'é': 'e',
        'è': 'e',
        'à': 'a',
        'â': 'a',
        'ê': 'e',
        'î': 'i',
        'ï': 'i',
        'ô': 'o',
        'ù': 'u',
        'ç': 'c'
    }
    @classmethod
    def setScoreRules(cls, score_rules):
        for score_name in ['user_score', 'property_score', 'global_score']:
            for k,v in score_rules[score_name].items():
                try:
                    v = float(v)
                    if v <= 0 or v > 1:
                        raise Exception(f" weight {k} of scoring {score_name} : {v} need to > 0 and <= 1")
                except:
                    raise Exception(f"Invalid format for weight {k} of scoring {score_name}")
        cls.score_rules = score_rules

    @classmethod
    def getUserSituationScore(cls, user_situation):
        if not user_situation:
            return True, cls.map_user_profession_scores['default']
        # clean to match 
        user_situation = user_situation.lower()
        clean_user_situation = ''
        for c in user_situation:
            if c in cls.map_letters:
                clean_user_situation += cls.map_letters[c]
            else:
                clean_user_situation += c
        # check matching job
        for k,v in cls.map_user_profession_scores.items():
            if k in clean_user_situation:
                return False, v
        return True, cls.map_user_profession_scores['default']

    @classmethod
    def getMontlyCashFlow(cls, revenu_mensuel, mean_monthly_loyer, monthly_pay, depense_mensuel):
        if not mean_monthly_loyer:
            return None
        return revenu_mensuel + mean_monthly_loyer - monthly_pay - depense_mensuel
    
    @classmethod
    def score_cash_flow(cls, cash_flow):
        """
        Attribue un score au cash flow mensuel en fonction de seuils dynamiques.
        """
        if not cash_flow:
            return None
        if cash_flow >= 3000:
            return 100  # Excellent score
        elif cash_flow >= 1000:
            return 80  # Bon score
        elif cash_flow >= 500:
            return 60  # Moyen
        elif cash_flow >= 0:
            return 40  # Faible mais positif
        elif cash_flow >= -500:
            return 20  # Négatif léger
        else:
            return 0  # Négatif sévère
    
    @classmethod
    def getConfidence(cls, region_rate, default_mean_surface_m2, debt_ratio, rental_yield_score, monthly_cash_flow, default_user_situation_score):
        confidence, count = 0, 0
        confidence_user_score, confidence_property_score = 0, 0

        if region_rate != 'National':
            confidence += 1
        count += 1

        if not default_mean_surface_m2:
            confidence += 1
            confidence_property_score += 1
        count += 1

        if debt_ratio is not None:
            confidence += 1
            confidence_user_score += 1
        count += 1

        if rental_yield_score is not None:
            confidence += 1
            confidence_property_score += 1
        count += 1

        if monthly_cash_flow is not None:
            confidence += 1
            confidence_property_score += 1
            # monthly_cash_flow is used for property score but it depends of revenu et depense of user
            confidence_user_score += 1
        count += 1

        if not default_user_situation_score:
            confidence += 1
            confidence_user_score += 1

        confidence_user_score /= 3
        confidence_property_score /= 3
        
        count += 1
        return (confidence*100) / count, confidence_user_score, confidence_property_score

    @rpc(ExtractObj, CreditCheckInformation, PropertyValuationInformation,  _returns=ApprovalDecisionObj)
    def getScoring(ctx, extractObj : ExtractObj, creditCheckInformation : CreditCheckInformation, propertyValuationInformation : PropertyValuationInformation):
        # compute cash flow
        mean_monthly_loyer = propertyValuationInformation.mean_yearly_loyer / 12 if propertyValuationInformation.mean_yearly_loyer else None
        monthly_cash_flow = ApprovalDecisionService.getMontlyCashFlow(
                                                            revenu_mensuel=extractObj.creditInformation.revenu_mensuel,
                                                            mean_monthly_loyer=mean_monthly_loyer,
                                                            monthly_pay=creditCheckInformation.monthly_pay,
                                                            depense_mensuel=extractObj.creditInformation.depense_mensuel
                                                        )
        monthly_cash_flow_score = ApprovalDecisionService.score_cash_flow(cash_flow=monthly_cash_flow)
        # get user_situation_score
        default_user_situation_score, user_situation_score = ApprovalDecisionService.getUserSituationScore(user_situation=extractObj.userInformation.user_situation)
        
        # get confidence score 
        confidence, confidence_user_score, confidence_property_score = ApprovalDecisionService.getConfidence(
            region_rate=creditCheckInformation.region_rate,
            default_mean_surface_m2=propertyValuationInformation.default_mean_surface_m2,
            debt_ratio=creditCheckInformation.debt_ratio,
            rental_yield_score=propertyValuationInformation.rental_yield_score,
            monthly_cash_flow=monthly_cash_flow,
            default_user_situation_score=default_user_situation_score
        )
        # get user score based on debt_ratio (min) and user_situation_score (max)
        w0, w1 = ApprovalDecisionService.score_rules['user_score']['debt_ratio_weight'], ApprovalDecisionService.score_rules['user_score']['user_situation_score_weight']
        user_score = (w0*max(0, 100-creditCheckInformation.debt_ratio) + w1*user_situation_score)/(w0 + w1) # don't need to check if it is between 0 and 100 %

        # get property_score based on rental_yield_score (max) and monthly_cash_flow_score (max)
        property_score = None 
        w0 = ApprovalDecisionService.score_rules['property_score']['rental_yield_score_weight'] if propertyValuationInformation.rental_yield_score is not None else 0
        w1 = ApprovalDecisionService.score_rules['property_score']['monthly_cash_flow_score_weight'] if monthly_cash_flow_score is not None else 0
        if w0 + w1 != 0:
            property_score = (w0 * min(100, propertyValuationInformation.rental_yield_score) + w1 * monthly_cash_flow_score)/(w0 + w1)

        # get global score based on user score and property_score, based on input weights * confidence of each score
        global_score = None
        w0 = ApprovalDecisionService.score_rules['global_score']['user_score_weight'] if user_score is not None else 0
        w1 = ApprovalDecisionService.score_rules['global_score']['property_score_weight'] if property_score is not None else 0
        w0 *= confidence_user_score
        w1 *= confidence_property_score
        if w0 + w1 != 0:
            property_score_ = property_score if property_score else 0
            # not necessary for user_score because can't be null
            global_score = (w0 * user_score + w1 * property_score_)/(w0 + w1)

        # Now decided if the request is approve or not, and return a relevant message
        approve, message_approve = True, ""
        values_to_check = {
            'confidence' : confidence,
            'debt_ratio' : creditCheckInformation.debt_ratio,
            'global_score' : global_score
        }
        # attention order count in config rules
        for rule, value in ApprovalDecisionService.score_rules['rules'].items():
            rule_ = rule.split('_')
            cond = rule_[-1]
            value_to_check = '_'.join(rule_[:-1])
            if cond == 'max' and values_to_check[value_to_check] >= value:
                approve = False        
            elif cond == 'min' and values_to_check[value_to_check] <= value:
                approve = False

            if not approve:
                message_approve = ApprovalDecisionService.score_rules["message_not_approve"][value_to_check]
                break 

        if approve:
            messages = []
            values_to_check = {
                'user_score' : [user_score, confidence_user_score, 'Évaluation de votre profil : '],
                'property_score' : [property_score, confidence_property_score, 'Évaluation du bien immobilier : ']
            }
            for value_name, v in values_to_check.items():
                score_, confidence_, title = v[0], v[1], v[2]
                if confidence_ == 0:
                    mess = title + ApprovalDecisionService.score_rules["message_approve"]["confidence_null"][value_name]
                    messages.append(mess)
                    continue 
                
                if score_ <= 33:
                    seuil_score  = 'low'
                elif score_ <= 66:
                    seuil_score  = 'mid'
                else:
                    seuil_score = 'high'
                
                if confidence_ <= 33:
                    seuil_confidence = 'low'
                elif confidence_ <= 66:
                    seuil_confidence = 'mid'
                else:
                    seuil_confidence = 'high'
                
                # deduced the message
                mess = title + ApprovalDecisionService.score_rules["message_approve"][value_name][seuil_score][seuil_confidence]
                messages.append(mess)
            message_approve = ApprovalDecisionService.score_rules["message_approve"]["sep_message"].join(messages)

        approvalDecisionInformation = ApprovalDecisionInformation(
            # user information 
            user_name = extractObj.userInformation.user_name,
            user_mail = extractObj.userInformation.user_mail,
            user_num = extractObj.userInformation.user_num,
            user_address = extractObj.userInformation.user_address,
            user_situation = extractObj.userInformation.user_situation,

            # loan information
            revenu_mensuel = extractObj.creditInformation.revenu_mensuel,
            depense_mensuel = extractObj.creditInformation.depense_mensuel,
            montant_pret = extractObj.creditInformation.montant_pret,
            apport = extractObj.propertyInformation.apport,
            duree_pret = creditCheckInformation.duree_pret_year,
            logement_address = propertyValuationInformation.logement_address,
            type_logement = propertyValuationInformation.type_logement,

            # loan information deduction
            # 1. CreditCheckObj
            monthly_pay = creditCheckInformation.monthly_pay,
            yearly_rate = creditCheckInformation.yearly_rate,
            region_rate = creditCheckInformation.region_rate,
            # 2. PropertyValuationObj
            mean_surface_m2 = propertyValuationInformation.mean_surface_m2,  
            mean_monthly_loyer = mean_monthly_loyer,

            # score
            # 1. CreditCheckObj
            debt_ratio = creditCheckInformation.debt_ratio,
            # 2. PropertyValuationObj
            rental_yield_score = propertyValuationInformation.rental_yield_score,
            # 3. compute at this service
            confidence = confidence,
            monthly_cash_flow = monthly_cash_flow,
            monthly_cash_flow_score = monthly_cash_flow_score,
            user_situation_score = user_situation_score,
            # global
            user_score = user_score,
            weight_user_score = w0,
            property_score = property_score,
            weight_property_score = w1,
            global_score = global_score,
            approve = approve, 
            message_approve = message_approve
            
        )

        # manage error
        error_content = ''
        if confidence is None or confidence > 100 or confidence < 0:
            error_content = '- issue to compute confidence !\n'
        # for user_situation_score, as is read in a json file, need to check if value is a float and in %
        incorrect_user_situation_score = False
        try:
            float(user_situation_score)
            if user_situation_score < 0 or user_situation_score > 100:
                incorrect_user_situation_score = True
        except:
            incorrect_user_situation_score = True
        if incorrect_user_situation_score:
            error_content += '- incorrect_user_situation_score !\n'
        # for property_score
        if property_score is not None and (property_score < 0 or property_score > 100):
            error_content += '- incorrect property_score !\n'
        # for global_score
        if global_score is None:
            error_content += "- din't manage to compute global_score\n"
        error = ErrorObj(
            content=error_content[:-1] if error_content != '' else None
        )
        return ApprovalDecisionObj(
            approvalDecisionInformation=approvalDecisionInformation,
            error=error
        )


 
 
 