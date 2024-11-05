import logging
from spyne import rpc, ServiceBase
import requests
from loanObject import ErrorObj, PropertyInformation, PropertyValuationInformation, PropertyValuationObj
logging.basicConfig(level=logging.DEBUG)

class PropertyValuationService(ServiceBase):
    cities = None
    url = 'https://api.cquest.org/dvf?code_commune='
    map_type_logement_v0 = {
        'default' : 'Appartement',

        'résidence' : 'Maison',
        'villa' : 'Maison',
        'pavillon' : 'Maison',
        'terrain' : 'Maison',
        'propriété' : 'Maison',
        'propriete' : 'Maison',
        'auberge' : 'Maison',
        'hôtel' : 'Maison',
        'hotel' : 'Maison',
        'manoir' : 'Maison'
    }
    ['appartement-loyer-m2', 'appartement12-loyer-m2', 'appartement3-loyer-m2', 'maison-loyer-m2']
    map_type_logement_v1 = {
        'default' : 'appartement-loyer-m2',

        'résidence' : 'maison-loyer-m2',
        'villa' : 'maison-loyer-m2',
        'pavillon' : 'maison-loyer-m2',
        'terrain' : 'maison-loyer-m2',
        'propriété' : 'maison-loyer-m2',
        'propriete' : 'maison-loyer-m2',
        'auberge' : 'maison-loyer-m2',
        'hôtel' : 'maison-loyer-m2',
        'hotel' : 'maison-loyer-m2',
        'manoir' : 'maison-loyer-m2',

        't1' : 'appartement12-loyer-m2',
        't2' : 'appartement12-loyer-m2',
        'studio' : 'appartement12-loyer-m2',
        'duplex' : 'appartement12-loyer-m2',
        'caravane' : 'appartement12-loyer-m2',

        't3' : 'appartement3-loyer-m2',
        'loft' : 'appartement3-loyer-m2'
    }
    '''
            Pour un appartement (toutes typologies confondues) : surface de 52 m² et surface moyenne par pièce de 22,2 m²
            Pour appartement type T1-T2 : surface de 37 m² et surface moyenne par pièce de 23,0 m²
            Pour appartement type T3 et plus : surface de 72 m² et surface moyenne par pièce de 21,2 m²
            Pour une maison : surface de 92 m² et surface moyenne par pièce de 22,4 m²
            https://www.data.gouv.fr/fr/datasets/carte-des-loyers-indicateurs-de-loyers-dannonce-par-commune-en-2023/#/resources
    '''
    map_mean_surface_m2 = {
        'appartement-loyer-m2' : 52,
        'appartement12-loyer-m2' : 37,
        'appartement3-loyer-m2' : 72,
        'maison-loyer-m2' : 92
    }
    ratio_seuil = 20
    @classmethod
    def set_cities_dataframe(cls, cities):
        cls.cities = cities

    @classmethod
    def get_gen_type_logement_v0(cls, type_logement):
        if not type_logement:
            return cls.map_type_logement_v0['default']
        type_logement = type_logement.lower()
        for k,v in cls.map_type_logement_v0.items():
            if k in type_logement:
                return v 
        return cls.map_type_logement_v0['default']
    
    @classmethod
    def get_gen_type_logement_v1(cls, type_logement):
        if not type_logement:
            return cls.map_type_logement_v1['default']
        type_logement = type_logement.lower()
        for k,v in cls.map_type_logement_v1.items():
            if k in type_logement:
                return v 
        return cls.map_type_logement_v1['default']

    @classmethod
    def get_mean_m2_surface(cls, code_insee, gen_type_logement_v0, montant_pret, apport):
        if not code_insee:
            return None
        url = cls.url + code_insee
        response = requests.get(url)
        # Vérifier si la requête est réussie (statut 200)
        if response.status_code == 200:
            # Convertir la réponse en JSON
            sales = response.json()['resultats']
            count = 0
            mean_m2 = 0
            potential_valeur_fonciere = montant_pret + apport
            seuil = (potential_valeur_fonciere*cls.ratio_seuil)/100
            min_potential_valeur_fonciere, max_potential_valeur_fonciere = max(0, potential_valeur_fonciere-seuil), potential_valeur_fonciere + seuil
            for sale in sales:
                if sale['type_local'] and sale['type_local'] == gen_type_logement_v0:
                    continue
                if sale['valeur_fonciere'] and sale['surface_relle_bati'] and sale['valeur_fonciere'] >= min_potential_valeur_fonciere and sale['valeur_fonciere'] <= max_potential_valeur_fonciere:
                    count += 1
                    mean_m2 += sale['surface_relle_bati']
            if count == 0:
                return None
            return mean_m2/count
        else:
            return None

    @classmethod
    def simplify_mean_m2_surface(cls, gen_type_logement_v1):
        return cls.map_mean_surface_m2[gen_type_logement_v1]
       

    @classmethod
    def getPotentialLoyer(cls, code_insee, gen_type_logement_v1):
        if not code_insee:
            return None
        filtered = list(cls.cities[cls.cities['code_insee'] == code_insee][gen_type_logement_v1])
        if len(filtered) == 0:
            return None 
        return filtered[0]

    @classmethod
    def getYearlyLoyer(cls, mean_loyer_m2, mean_surface_m):
        if not mean_loyer_m2 or not mean_surface_m:
            return None 
        return mean_loyer_m2 * mean_surface_m * 12
    @classmethod
    def getRentalYieldScore(cls, montant_pret, apport, loyer_annuel):
        if loyer_annuel:
            return (loyer_annuel/(montant_pret + apport)) * 100
        return None
    
    @rpc(PropertyInformation, _returns=PropertyValuationObj)
    def getPropertyEvaluation(ctx, propertyInformation : PropertyInformation):
        gen_type_logement_v0 = PropertyValuationService.get_gen_type_logement_v0(type_logement=propertyInformation.type_logement)
        gen_type_logement_v1 = PropertyValuationService.get_gen_type_logement_v1(type_logement=propertyInformation.type_logement)

        default_mean_surface_m2 = False
        mean_surface_m2 = PropertyValuationService.get_mean_m2_surface(code_insee=propertyInformation.code_insee_logement,
                                                                    gen_type_logement_v0=gen_type_logement_v0,
                                                                    montant_pret=propertyInformation.montant_pret,
                                                                    apport=propertyInformation.apport)
        
        if not mean_surface_m2:
            # either empty code_insee or missing inromations for this code_insee and gen_type_logement_v0
            # so we simplfy by mean surface in depends of gen_type_logement_v1
            mean_surface_m2 = PropertyValuationService.simplify_mean_m2_surface(gen_type_logement_v1=gen_type_logement_v1
                                                                                )
            default_mean_surface_m2 = True
        mean_loyer_m2 = PropertyValuationService.getPotentialLoyer(code_insee=propertyInformation.code_insee_logement,
                                                                gen_type_logement_v1=gen_type_logement_v1)
        
        mean_yearly_loyer = PropertyValuationService.getYearlyLoyer(mean_loyer_m2=mean_loyer_m2, mean_surface_m=mean_surface_m2)

        rental_yield_score = PropertyValuationService.getRentalYieldScore(montant_pret=propertyInformation.montant_pret,
                                                                    apport=propertyInformation.apport,
                                                                    loyer_annuel=mean_yearly_loyer)
        error_content = None 
        if rental_yield_score is not None and rental_yield_score < 0:
            error_content = f'rental_yield_score {rental_yield_score} is not properly computed !' 
        return PropertyValuationObj(
            propertyValuationInformation = PropertyValuationInformation(
                logement_address = propertyInformation.logement_address, # can be Null
                code_insee_logement = propertyInformation.code_insee_logement, # can be Null
                type_logement = propertyInformation.type_logement, # can be Null
                gen_type_logement_v0 = gen_type_logement_v0, #PropertyInformation.type_logement, if null => default Maison
                gen_type_logement_v1 = gen_type_logement_v1, #PropertyInformation.type_logement, if null => default appartement-loyer-m2
                mean_surface_m2 = mean_surface_m2, #PropertyInformation.code_insee, if null => null
                default_mean_surface_m2 = default_mean_surface_m2 ,
                mean_loyer_m2 = mean_loyer_m2,  #PropertyInformation.code_insee, if null => null
                mean_yearly_loyer = mean_yearly_loyer, # mean_surface_m2 & mean_loyer_m2, if null => null
                rental_yield_score = rental_yield_score
            ),
            error = ErrorObj(
                content=error_content
            )
        )