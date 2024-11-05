import torch
import json
import random

MAX_SPAN_SIZE_RATIO = 20 # max_span_size += (max_span_size * MAX_SPAN_SIZE_RATIO) // 100
def read_data(data_path):
    data_file = open(data_path, 'r', encoding='utf-8')
    data = json.load(data_file)
    random.shuffle(data)
    data = data[:5000]
    data_file.close()
    return data

class DataProcessor:
    def __init__(self,tokenizer,input_max_length):
        self.input_max_length = input_max_length
        self.max_potenial_length = 0
            
        # tokenizer information
        self.tokenizer = tokenizer
        self.start_token = tokenizer.cls_token
        self.end_token = tokenizer.sep_token
        self.unk_token = tokenizer.unk_token

    def tokenize(self, pre_tokens):
        # encoding
        tokens = []
        input_tokens = [-1]
        tokens_by_id = {}
        start = 0
        for i, pre_token in enumerate(pre_tokens):
            current_tokens = self.tokenizer.tokenize(pre_token)
            if len(current_tokens) == 0:
                current_tokens = [self.unk_token]

            tokens_by_id[i] = {'tokens': current_tokens, 'start': start, 'end': start + len(current_tokens)}
            start += len(current_tokens)
            tokens = tokens + current_tokens
            input_tokens += [i] * len(current_tokens)
            if self.input_max_length and len(tokens) > self.input_max_length:
                return None
           
        tokens = [self.start_token] + tokens + [self.end_token]
        if self.input_max_length and len(tokens) > self.input_max_length:
            return None
        
        return {
            'tokens': tokens,
            'tokens_by_id': tokens_by_id,
            'input_tokens': input_tokens
        }

    def createItem(self, sequence):
        pre_tokens = sequence
        output = self.tokenize(sequence)
        if not output:
            return None
        tokens, tokens_by_id = output['tokens'], output['tokens_by_id']
        # create encoding
        context_size = len(tokens)
        encoding_ = self.tokenizer.convert_tokens_to_ids(tokens)
        encoding = torch.tensor(encoding_, dtype=torch.long)
        context_masks = torch.ones(context_size, dtype=torch.bool)
        # stack as we will compute one item in one batch
        encoding = torch.stack([encoding])
        context_masks = torch.stack([context_masks])
        
        doc_ = dict({
                'pre_tokens': [pre_tokens],
                'tokens_by_id': [tokens_by_id],
                'input_tokens': [output['input_tokens']],
                'encodings': encoding,
                'context_masks' : context_masks
        })
        return doc_
        
        
     
   
     