from transformers import CamembertTokenizer, CamembertConfig
import torch
import os
import json 

from features.dataProcessing import DataProcessor
from features.CamForTokenClassification import CamembertForTokenClassification

def read_config(config_path):
    config_file = open(config_path, 'r')
    config = json.load(config_file)
    config_file.close()
    return config

class TokenClassifier:
    def __init__(self, config):
        self.model_name = config['model_path']
        self.input_max_length = config['max_length']
        # retrieve informations from the model
        train_config = read_config(os.path.join(self.model_name, 'config.json'))
        # encoding information
        tokenizer_path = train_config['_name_or_path']
        self.lowercase = train_config['lowercase']   
        # model information
        self.crf = train_config['crf'] if 'crf' in train_config else False
        self.freeze_transformer = train_config['freeze_transformer']
        self.prop_drop = train_config['prop_drop']
        # entities informations
        self.entity_types = train_config['entity_types']
        self.reverse_entity_types = {value: key for key, value in self.entity_types.items()} 
        # tokenizer
        self.tokenizer = CamembertTokenizer.from_pretrained(tokenizer_path, do_lower_case=self.lowercase)     
        # device
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def load_model(self):
        config = CamembertConfig.from_pretrained(self.model_name)
        self.model = CamembertForTokenClassification.from_pretrained(
                self.model_name,
                config=config,
                prop_drop=self.prop_drop,
                freeze_transformer=self.freeze_transformer,
                # entity information
                entity_types=len(self.entity_types)+1
            )
        self.model.to(self.device)
    
    def load_data_processor(self):
        self.dataProcessor = DataProcessor(self.tokenizer, self.input_max_length)

    def predictOne(self, input):
        batchItem = self.dataProcessor.createItem(input)
        if not batchItem:
            return None # doc to long
        with torch.no_grad():
            self.model.eval()
            pred_entities =  self.model(
                encodings=batchItem['encodings'], 
                context_masks=batchItem['context_masks'],
                input_tokens=batchItem['input_tokens'],
                entity_types=self.reverse_entity_types,
                inference=True
            )[0] # unBatch

        return pred_entities

     