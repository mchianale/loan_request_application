import logging
from spyne import rpc, ServiceBase
import requests
from bs4 import BeautifulSoup
from loanObject import CreditInformation, ErrorObj, CreditCheckInformation, CreditCheckObj
logging.basicConfig(level=logging.DEBUG)



url = "https://www.empruntis.com/financement/actualites/barometres_regionaux.php"
def get_taux(region_value="0"):
    # Simulate a POST request to select the region
    form_data = {
        "reg_select": region_value
    }
    
    response = requests.post(url, data=form_data)
    
    # Parse the HTML response
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the section containing the rates (meilleure et moyenne)
    # You may need to adjust this part depending on the exact HTML structure
    taux_section = soup.find("div", class_="map_taux")  # Adjust based on the actual HTML
    if taux_section:
        # Extract the rates based on duration
        rows = taux_section.find_all("tr")
        rates = {}
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                duration = cols[0].text.strip()
                best_rate = cols[1].text.strip()
                avg_rate = cols[2].text.strip()
                # convert
                int_duration = int(''.join(filter(str.isdigit, duration)))
                best_rate_float = best_rate.replace(',', '.')
                best_rate_float = best_rate_float.replace('%', '')
                best_rate_float = float(best_rate_float)
                avg_rate_float = avg_rate.replace(',', '.')
                avg_rate_float = avg_rate_float.replace('%', '')
                avg_rate_float = float(avg_rate_float)

                rates[int_duration] = {
                    "meilleure_taux": best_rate_float/100,
                    "moyenne_taux": avg_rate_float/100
                }
       
        return rates
    else:
        return None
    
class CreditCheckService(ServiceBase):
        # each start of this service will retrieve using requests taux informations in France
        regions = {
            "National": "0",
            "Auvergne-Rhône-Alpes": "101",
            "Bourgogne-Franche-Comté": "102",
            "Bretagne": "103",
            "Centre-Val de Loire": "104",
            "Corse": "105",
            "Grand Est": "106",
            "Hauts-de-France": "107",
            "Île-de-France": "108",
            "Normandie": "109",
            "Nouvelle-Aquitaine": "110",
            "Occitanie": "111",
            "Pays de la Loire": "112",
            "Provence-Alpes-Côte d'Azur": "113"
        }
        all_rates = {}
        cities = None
        @classmethod
        def setRatesInformations(cls):
            for region, region_value in cls.regions.items():
                rates = get_taux(region_value=region_value)
                if rates is None and region != "National":
                    cls.all_rates[region] = cls.all_rates["National"]
                elif rates is None:
                     raise 'Failed to load National rates'
                else:
                    cls.all_rates[region] = rates
            logging.info(f'Load successfully {cls.all_rates}')

        @classmethod
        def set_cities_dataframe(cls, cities):
            cls.cities = cities

        @classmethod
        def yearToMonth(cls, year : float):
            return year * 12
        
        @classmethod
        def getYearlyRate(cls, duree_pret : float, zip_code : float = None):
            '''
                return rate based on duree_pret in years and zip code
            '''
            rate_region = 'National'
            
            region = list(cls.cities[cls.cities['zip_codes'] == zip_code]['regions'])
     
            if region:
                region = region[0]
                if region in cls.all_rates:
                    rate_region = region 
           
            durations = list(cls.all_rates[rate_region].keys())
            diff_ = [(duration ,abs(duration - duree_pret)) for duration in durations]
            rate = sorted(diff_, key=lambda item: item[1])[0][0]
            rate = cls.all_rates[rate_region][rate]["moyenne_taux"]
            
            return rate_region, rate
                    
                 
        @classmethod
        def getMonthlyPayment(cls, K : float, Tm : float, n : int):
                """
                Input:
                    - K : montant demandé
                    - Tm : taux mensuel
                    - n : nombre de mois total de l'emprunt
                """
                if Tm == 0:  # Si le taux est 0, la mensualité est simplement K / n
                    return K / n
        
                # Calcul de la mensualité avec la formule de l'annuité constante
                m = (K * Tm) / (1 - (1 + Tm) ** -n)
                return m
        
        @classmethod
        def getDebtRatio(cls, montlyPay : float, revenu_mensuel : float, depense_mensuel : float):
            res = (montlyPay + depense_mensuel)/revenu_mensuel
            return round(res * 100, 2)
        
        @rpc(CreditInformation, _returns=CreditCheckObj)
        def getCreditScore(ctx, creditInformation : CreditInformation):
                # get number of month = duree_pret
                duree_pret_month = CreditCheckService.yearToMonth(year=creditInformation.duree_pret)
                # retrive the most relevant rate for the request
                region_rate, yearly_rate = CreditCheckService.getYearlyRate(duree_pret=creditInformation.duree_pret,
                                                                zip_code=creditInformation.zip_code_logement)
                monthly_rate = (yearly_rate /12)
                # get the most relevant paid that the customer which he will have to pay for this loan 
                monthly_pay = CreditCheckService.getMonthlyPayment(K=creditInformation.montant_pret,
                                                                Tm=monthly_rate, n=duree_pret_month)
                # finally retrive le taux de rendement 
                debt_ratio = CreditCheckService.getDebtRatio(montlyPay=monthly_pay, 
                                                    revenu_mensuel=creditInformation.revenu_mensuel,
                                                    depense_mensuel=creditInformation.depense_mensuel)
                return CreditCheckObj(
                    creditCheckInformation = CreditCheckInformation(
                        duree_pret_year = creditInformation.duree_pret,
                        duree_pret_month = duree_pret_month,
                        region_rate = region_rate,
                        yearly_rate = yearly_rate*100,
                        monthly_rate = monthly_rate*100,
                        monthly_pay = monthly_pay,
                        debt_ratio = debt_ratio
                    ),
                    error = ErrorObj(
                        content=f'debt ratio {debt_ratio} is not properly computed !' if debt_ratio < 0  else None
                    )
                    
                )
            


