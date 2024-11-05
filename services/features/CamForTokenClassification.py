import torch
from torch import nn as nn
from transformers import CamembertModel,CamembertPreTrainedModel
import torch.nn.functional as F


class FFNClassifier(nn.Module):
    def __init__(self, input_dim, hidden_dim, output_dim, dropout_prob):
        super(FFNClassifier, self).__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, output_dim)
        self.dropout = nn.Dropout(dropout_prob)
    
    def forward(self, x):
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout(x)
        x = self.fc2(x)
        return x


class CamembertForTokenClassification(CamembertPreTrainedModel):
    VERSION = '1.1'

    def __init__(self, 
                config,
                # independent entity classifier
                entity_types: int,
                # dependent entity classifier
                prop_drop: float, 
                freeze_transformer: bool,
                ):
        
        super(CamembertForTokenClassification, self).__init__(config)
        # BERT model
        self.bert = CamembertModel(config)
       
        # layers
        # entity classifier (Token classification)
        self.entity_classifier = FFNClassifier(config.hidden_size, config.hidden_size, entity_types, prop_drop)

        # weight initialization
        self.init_weights()

        if freeze_transformer:
            print("Freeze transformer weights")
            # freeze all transformer weights
            for param in self.bert.parameters():
                param.requires_grad = False
    

    def _forward_train(self, encodings: torch.tensor, context_masks: torch.tensor):
        # get contextualized token embeddings from last transformer layer
        encodings = encodings.to(self.bert.device)
        context_masks = context_masks.to(self.bert.device)
        context_masks = context_masks.float()
        h = self.bert(input_ids=encodings, attention_mask=context_masks)['last_hidden_state']
        # classify entities
        entity_logits = self.entity_classifier(h)
        return entity_logits
    

    def forward(self, *args, inference=False, **kwargs):
        if not inference:
            return self._forward_train(*args, **kwargs)
        else:
            return self._forward_inference(*args, **kwargs)

    
        
    def _forward_inference(self, encodings: torch.tensor, context_masks: torch.tensor, input_tokens: list, entity_types : dict):
        
        # use correct device 
        encodings = encodings.to(self.bert.device)
        context_masks = context_masks.to(self.bert.device)
        # get contextualized token embeddings from last transformer layer
        context_masks = context_masks.float()
        h = self.bert(input_ids=encodings, attention_mask=context_masks)['last_hidden_state']

        # classify entities
        entity_logits = self.entity_classifier(h)
        entity_clf = torch.softmax(entity_logits, dim=-1)
        entity_logits = entity_clf.argmax(dim=-1)
        
        # retrieve entities
        classified_entities = self.get_batch_ents(entity_clf, entity_logits, input_tokens, context_masks, entity_types)
        return classified_entities
                          
 

    def get_ents(self,entity_clf, entity_logits, input_tokens,context_masks,entity_types):
        ctx_size = (context_masks == 1).sum().item()
        entity_logits = entity_logits[:ctx_size]
        entity_clf = entity_clf[:ctx_size]
        starts = ((entity_logits % 2 != 0)).nonzero(as_tuple=False)
        classified_entities = []
        if starts.size(0) == 0:
            return classified_entities # pas d'entites
        # si les conditions ne sont pas respectees, l'entrainement n'a pas suffit
        if starts[0].item() == 0:
            return classified_entities
        if starts[-1].item() == ctx_size - 1:
            return classified_entities
    
        limit = torch.tensor([ctx_size]).to(starts.device)
        limit = limit.view(-1,1)
        starts = torch.cat((starts,limit ),dim=0)
        # pour ce cas, les spans avec des 0 disperses sont comme meme consideres comme des entites, ex: [1,2,2,0,2,2] 
        # mais normalement le modele doit predire [1,2,2,2,2,2], depend de l'entrainement
        #ends = ((entity_logits % 2 == 0) & (entity_logits != 0) & (entity_logits != self.eos_tag_id)).nonzero(as_tuple=False)
        # pour ce cas seul [1,2,2] est conside comme entite et non [1,2,2,0,2,2] 
        ends = ((entity_logits % 2 == 0)).nonzero(as_tuple=False)
        for i in range(starts.size(0)-1):
            start = starts[i].item()
            start_label = entity_logits[start].item()
            current_ends = ends[(ends > start) & (ends < starts[i+1])]
            end = start 
            for pot_end in current_ends:
                if entity_logits[pot_end].item() != start_label + 1:
                    break
                end = pot_end.item()
            
            if end == ctx_size - 1: # si les conditions ne sont pas respectees, l'entrainement n'a pas suffit
                return classified_entities
            end += 1
            
            # get the mean 'prob'
            max_values, _ = torch.max(entity_clf[start:end], dim=1)
            mean_prob = max_values.mean()
            real_start, real_end = input_tokens[start], input_tokens[end-1] + 1
            type = entity_types[start_label][2:]
    
            classified_entities.append({
                'id' : i,
                'start': real_start,
                'end': real_end,
                'type': type,
                'score' : mean_prob.item()
            })
                          
        return classified_entities 

        
    def get_batch_ents(self,entity_clf, entity_logits, input_tokens, context_masks, entity_types):
        batch_size = entity_logits.shape[0]
        classified_entities = [[] for _ in range(batch_size)]
        for batch_index in range(batch_size):
            # retrieve information about ind entities
            current_classified_entities = self.get_ents(entity_clf[batch_index], entity_logits[batch_index], input_tokens[batch_index],context_masks[batch_index],entity_types)
            if current_classified_entities:
                classified_entities[batch_index] += current_classified_entities
    
        return classified_entities
            

# Model access

_MODELS = {
    'token_classifier': CamembertForTokenClassification
}


def get_model(name):
    return _MODELS[name]
