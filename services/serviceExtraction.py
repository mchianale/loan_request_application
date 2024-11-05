import logging
from spyne import rpc, ServiceBase, Unicode
from geopy.geocoders import Nominatim
import re
from datetime import datetime
from features.tokenClassifier import TokenClassifier
from loanObject import ExtractObj, UserInformation, PropertyInformation, CreditInformation, ErrorObj
logging.basicConfig(level=logging.DEBUG)


class ServiceExtraction(ServiceBase):
    modelInstance = None
    ent_types = {
        "user_name" : {'canBeNull' : False}, #Unicode
        "user_mail" : {'canBeNull' : False}, #Unicode
        "user_num" :  {'canBeNull' : False}, #Unicode
        "user_address" : {'canBeNull' : True}, #Unicode
        "user_situation" : {'canBeNull' : True}, #Unicode
        "revenu_mensuel" : {'canBeNull' : False}, #Float
        "depense_mensuel" : {'canBeNull' : False}, #Float
        "montant_pret" : {'canBeNull' : False}, #Float
        "apport" : {'canBeNull' : True, 'nullValue' : 0}, #Float
        "duree_pret": {'canBeNull' : False}, #Float
        "logement_address" : {'canBeNull' : True}, #Unicode
        "zip_code_logement" : {'canBeNull' : True}, #Float
        "code_insee_logement" : {'canBeNull' : True},
        "type_logement" : {'canBeNull' : True} #Unicode
    }
    geolocator = Nominatim(user_agent="address_formatter")
    puncts = [',', '.', ';', ':', '%', '?', '!', '$', '€', '(', ')', '"']
    months = {
        'janvier': 1,
        'fevrier': 2,
        'février': 2,
        'mars': 3,
        'avril': 4,
        'mai': 5,
        'juin': 6,
        'juillet': 7,
        'aout': 8,
        'août': 8,
        'septembre': 9,
        'octobre': 10,
        'novembre': 11,
        'decembre': 12,
        'décembre': 12
    }
    # Get the current date
    current_date = datetime.now()
    cities = None
    patterns = {'a_b_year_month': {'year': 0, 'month': 1},
            'a_b_month_year': {'year': 1, 'month': 0},
            'a_year_b_month': {'year': 0, 'month': 1},
            'a_year_month_b': {'year': 0, 'month': 1},
            'a_month_b_year': {'year': 1, 'month': 0},
            'a_month_year_b': {'year': 1, 'month': 0},
            'year_a_b_month': {'year': 0, 'month': 1},
            'year_a_month_b': {'year': 0, 'month': 1},
            'year_month_a_b': {'year': 0, 'month': 1},
            'month_a_b_year': {'year': 1, 'month': 0},
            'month_a_year_b': {'year': 1, 'month': 0},
            'month_year_a_b': {'year': 1, 'month': 0},
            'month_a': {'year': None, 'month': 0},
            'a_month': {'year': None, 'month': 0},
            'year_a': {'year': 0, 'month': None},
            'a_year': {'year': 0, 'month': None},
            'a': {'year': 0, 'month': None},
            'a_year_month' : {'year': 0, 'month': None},
            'a_month_year' : {'year': None, 'month': 0},
            'month_a_year' : {'year': 0, 'month': None},
            'month_year_a' : {'year': 0, 'month': None},
            'year_month_a' : {'year': None, 'month': 0},
            'year_a_month' : {'year': None, 'month': 0},
    }
    # set the model (one time)
    @classmethod
    def set_model(cls, model_config):
        logging.info(f"Currently load {model_config} model...")
        cls.modelInstance = TokenClassifier(config=model_config)
        cls.modelInstance.load_model()
        cls.modelInstance.load_data_processor()
        logging.info('Loaded the model successfully!')
    @classmethod
    def set_cities_dataframe(cls, cities):
        cls.cities = cities
    # Prétraitement du Texte
    @classmethod
    def preProcess(cls, text):
        text = text.replace('\n', ' ')
        tokens = []
        current_words = ''
        i = 0 
        while i < len(text):
            if text[i] == ' ':
                if current_words:
                    tokens.append(current_words)
                current_words = ''
            elif text[i] in cls.puncts:
                if current_words:
                    tokens.append(current_words)
                tokens.append(text[i])
                current_words = ''
            else:
                current_words += text[i]
            i += 1
        # Append the last word if exists
        if current_words:
            tokens.append(current_words)
        
        return tokens # preTokens
    # clean extracted entities features
    @classmethod
    def cleanString(cls, tokens):
        txt = ' '.join(tokens)
        for punct in cls.puncts:
            txt = txt.replace(punct, ' ')
        txt = ' '.join(txt.strip().split())
        if txt == '':
            return None
        return txt
    @classmethod
    def cleanName(cls, tokens):
        tokens = [t[0].upper() + t[1:].lower() for t in tokens if t not in cls.puncts]
        try:
            tokens = [t[0].upper() + t[1:].lower() for t in tokens if t not in cls.puncts]
        except:
            return None
        txt = ' '.join(tokens)
        txt = ' '.join(txt.strip().split())
        if txt == '':
            return None
        return txt   
    @classmethod
    def cleanMail(cls, tokens):
        txt = ''.join(tokens)
        txt = ' '.join(txt.strip().split())
        if txt == '':
            return None
        index = txt.find('@')
        if index == -1:
            return None
        try:
            index = txt[index+1:].find('.')
        except:
            return None
        if index == -1:
            return None
        return txt
    @classmethod
    def cleanPhone(cls, tokens):
        phone = ''.join(tokens).lower()
        phone =  ''.join(filter(str.isdigit, phone))  
        if len(phone) < 9:
                return None
        phone = '+33' + phone[-9:]
        if len(phone) != 12:
            return None
        return phone
    @classmethod
    def cleanPrice(cls, tokens):
        price = ''.join(tokens).lower()
        if price == '':
            return None
        k = price.find('k')
        if k >= 1:
            mille = price[:k]
            mille =  ''.join(filter(str.isdigit, mille))
            if k != len(price)-1:
                cent = price[k+1:]
                cent =  ''.join(filter(str.isdigit, cent))
            else:
                cent = 0
            try:
                price = int(mille)*1000
            except:
                return None
            try:
                price += int(cent)
                return price
            except:
                return price
        price =  ''.join(filter(str.isdigit, price))
        return int(price)
    @classmethod
    def calculate_year_difference(cls, year, month):
        # Create a date object for the input year and month (day set to 1)
        input_date = datetime(year, month, 1) 
        # Calculate the difference in years
        year_diff =  input_date.year - cls.current_date.year
        # Adjust if the current month/day is earlier than the input month/day
        if (cls.current_date.month, cls.current_date.day) < (input_date.month, 1):
            year_diff -= 1
        return year_diff
    @classmethod
    def cleanAddress_V0(cls, input_address=None, tokens=None):
        if not input_address and not tokens:
            return None
        if not input_address:
            input_address = cls.cleanString(tokens)
            if not input_address:
                return None
        patterns = [r'\b\d{4}\b', r'\b\d{5}\b']
        # find potentials zip_code
        potential_postal_codes = []
        for pattern in patterns:
            potential_postal_codes += re.findall(pattern, input_address)
        for zip_code in potential_postal_codes:
            filtered_df = cls.cities[cls.cities['zip_codes'] == float(zip_code)]
            city = list(filtered_df['cities'])
            if len(city) >= 1:
                city = city[0]
                code_insee = list(filtered_df['code_insee'])[0]
                return f"{zip_code}, {city}, France", float(zip_code), code_insee
        return None
    @classmethod       
    def cleanAddress_V1(cls, tokens):
        input_address = cls.cleanString(tokens)
        if not input_address:
            return None
        input_address += ', France'
        try:
            # Geocode the input address
            location = cls.geolocator.geocode(input_address)
            if location:
                # Return the formatted address
                zip_code = float(location.address.split(',')[-2][1:])
                filtered_df = cls.cities[cls.cities['zip_codes'] == zip_code]
                code_insee = list(filtered_df['code_insee'])
                if len(code_insee) >= 1:
                    return location.address, zip_code, code_insee[0]
            else:
                return cls.cleanAddress_V0(input_address)
        except:
            return cls.cleanAddress_V0(input_address)
    # retrive valid duree pret based on year - mm
    @classmethod
    def cleanDureeV0(cls, tokens):
        tokens = [t for t in tokens if t not in ['.', ',', ';']]
        txt  = ' '.join(tokens).lower()
        aindex = txt.find('an')
        mindex = txt.find('mo')
        numbers = re.findall(r'\d+', txt)
        if len(numbers) == 0 or len(numbers) > 2:
            return None 
        if len(numbers) == 2:
            a, b = numbers[0], numbers[-1]  
        else:
            a = numbers[0]
            b = None
        naindex = txt.find(a)
        nmindex = None
        if b:
            nmindex = txt.find(b)
        pattern = {'a' : naindex}
        if nmindex:
            pattern['b'] = nmindex
        if aindex != -1:
            pattern['year'] = aindex
        if mindex != -1:
            pattern['month'] = mindex
        
        pattern =  dict(sorted(pattern.items(), key=lambda item: item[1]))
        pattern = '_'.join(pattern)
        if pattern not in cls.patterns:
            return None
        res_pattern = cls.patterns[pattern]
        year = int(numbers[res_pattern['year']]) if res_pattern['year'] is not None else 0
        month = int(numbers[res_pattern['month']]) if res_pattern['month'] is not None else 0
        return year + (month / 12)
    @classmethod
    def cleanDureeV1(cls, tokens):
        year, month = None, None
        txt = ''.join(tokens).lower()
        for m,v in cls.months.items():
            if m in txt:
                month = v
                break
        numbers = re.findall(r'\d+', txt)
        for number in numbers:
            if not month and len(number) == 1:
                month = int(number)
            elif len(number) == 4:
                year = int(number)
            if month and year:
                break
        if not year:
            for token in tokens:
                txt = token.lower()
                for m,v in cls.months.items():
                    if m in txt:
                        month = v
                        break
                digit = ''.join(filter(str.isdigit, txt))
                if len(digit) == 4:
                    year = int(digit)
                if len(digit) == 1:
                    month = int(digit)
                
                if month and year:
                    break
               
        if not year:
            year = cls.current_date.year + 1
        if not month or month < 1 and month > 12:
            month = 1
    
        duree = cls.calculate_year_difference(year, month)
        if duree <= 0:
            return None
        
        return duree

    
    # Analyse Linguistique & Identification des Entités
    @classmethod
    def extractEntities(cls, preTokens):
        informations = {'error' : ''}
        predictedEntities = cls.modelInstance.predictOne(input=preTokens)
        if predictedEntities is None:
            informations['error'] += 'Doc too long !'
        else:
            # sorted ent bases on then score 
            predictedEntities = sorted(predictedEntities, key=lambda x: x['score'], reverse=True)
            for ent in predictedEntities:
                ent_type = ent['type']
                if ent_type in informations and informations[ent_type]:
                    continue
                tokens = preTokens[ent['start']:ent['end']]
                if ent_type == 'user_name':
                    informations[ent_type] = cls.cleanName(tokens)
                if ent_type == 'user_mail':
                    informations[ent_type] = cls.cleanMail(tokens)
                if ent_type == 'logement_address':
                    output_ = cls.cleanAddress_V0(tokens=tokens) # use this because we don't wait that the user give the reight address for the property he want to buy
                    if not output_:
                        informations[ent_type] = None
                    else:
                        informations[ent_type], informations['zip_code_logement'], informations['code_insee_logement'] = output_
                if ent_type == 'user_address':
                    output_ = cls.cleanAddress_V1(tokens)
                    if not output_:
                        informations[ent_type] = None
                    else:
                        informations[ent_type], _, _ = output_

                if ent_type == 'user_num':
                    informations[ent_type] = cls.cleanPhone(tokens)
                if ent_type in ['revenu_mensuel', 'depense_mensuel', 'montant_pret', 'apport']:
                    informations[ent_type]  = cls.cleanPrice(tokens)
                if ent_type in ['type_logement', 'user_situation']:
                    informations[ent_type] = cls.cleanString(tokens)
                if ent_type == 'duree_pret':
                    informations[ent_type] = cls.cleanDureeV0(tokens)
                if ent_type == 'duree_pret_year':
                    informations['duree_pret'] = cls.cleanDureeV1(tokens)

        for ent_type  in cls.ent_types.keys():
            if ent_type not in informations:
                informations[ent_type] = None 
            if informations["error"] == 'Doc too long !':
                continue
            if informations[ent_type] is None:
                informations[ent_type] = cls.ent_types[ent_type]['nullValue'] if 'nullValue' in cls.ent_types[ent_type] else None
                if not cls.ent_types[ent_type]['canBeNull']:
                    informations['error'] += f"didn't manage to extract {ent_type}\n"
                
        informations['error'] = informations['error'] if informations['error'] != '' else None
        return informations

    @rpc(Unicode, _returns=ExtractObj)
    def extract(ctx, request: str):
        # clean the request input
        preTokens = ServiceExtraction.preProcess(request)
        # extract entities from the request input
        request_informations = ServiceExtraction.extractEntities(preTokens)
        
        clientInfo = ExtractObj(
            userInformation=UserInformation(
                user_name = request_informations['user_name'],
                user_mail = request_informations['user_mail'],
                user_num = request_informations['user_num'],
                user_address = request_informations['user_address'],
                user_situation = request_informations['user_situation'],
            ),
            creditInformation=CreditInformation(
                revenu_mensuel = request_informations['revenu_mensuel'],
                depense_mensuel = request_informations['depense_mensuel'],
                montant_pret = request_informations['montant_pret'],
                duree_pret = request_informations['duree_pret'],
                zip_code_logement = request_informations['zip_code_logement']
            ),
            propertyInformation=PropertyInformation(
                logement_address = request_informations['logement_address'],
                code_insee_logement = request_informations['code_insee_logement'],
                type_logement = request_informations['type_logement'],
                montant_pret = request_informations['montant_pret'],
                apport = request_informations['apport']
            ),
            error=ErrorObj(
                content=request_informations['error']  
            )
        )
        return clientInfo