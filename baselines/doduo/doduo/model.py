# coding=utf-8
# Copyright 2018 The Google AI Language Team Authors and The HuggingFace Inc. team.
# Copyright (c) 2018, NVIDIA CORPORATION.  All rights reserved.
#
# Copyright (c) 2022, Megagon Labs, Inc.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""PyTorch BERT model. """

from packaging import version

import torch
import torch.nn as nn
from torch.nn import CrossEntropyLoss, MSELoss

import transformers
from transformers import BertPreTrainedModel

if version.parse(transformers.__version__) < version.parse("4.1.1"):
    from transformers.modeling_bert import BertEmbeddings, BertEncoder
else:
    from transformers.models.bert.modeling_bert import BertEmbeddings, BertEncoder


class BertMultiPooler(nn.Module):

    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states):
        # We "pool" the model by simply taking the hidden state corresponding
        # to the first token.
        #token_tensor = torch.index_select(hidden_states, 1,
        #                                  cls_indexes)
        # Apply
        #pooled_outputs = self.dense(token_tensor)
        pooled_outputs = self.dense(hidden_states)
        pooled_outputs = self.activation(pooled_outputs)
        return pooled_outputs


class BertMultiPairPooler(nn.Module):

    def __init__(self, config):
        super().__init__()
        self.dense = nn.Linear(config.hidden_size * 2, config.hidden_size)
        self.activation = nn.Tanh()

    def forward(self, hidden_states):
        # We "pool" the model by simply taking the hidden state corresponding
        # to the first token.
        #token_tensor = torch.index_select(hidden_states, 1,
        #                                  cls_indexes)
        # Apply
        #pooled_outputs = self.dense(token_tensor)
        hidden_states_first_cls = hidden_states[:, 0].unsqueeze(1).repeat(
            [1, hidden_states.shape[1], 1])
        pooled_outputs = self.dense(
            torch.cat([hidden_states_first_cls, hidden_states], 2))
        pooled_outputs = self.activation(pooled_outputs)

        return pooled_outputs


class BertModelMultiOutput(BertPreTrainedModel):
    """

    The model can behave as an encoder (with only self-attention) as well
    as a decoder, in which case a layer of cross-attention is added between
    the self-attention layers, following the architecture described in `Attention is all you need`_ by Ashish Vaswani,
    Noam Shazeer, Niki Parmar, Jakob Uszkoreit, Llion Jones, Aidan N. Gomez, Lukasz Kaiser and Illia Polosukhin.

    To behave as an decoder the model needs to be initialized with the
    :obj:`is_decoder` argument of the configuration set to :obj:`True`; an
    :obj:`encoder_hidden_states` is expected as an input to the forward pass.

    .. _`Attention is all you need`:
        https://arxiv.org/abs/1706.03762

    """

    def __init__(self, config):
        super().__init__(config)
        self.config = config

        self.embeddings = BertEmbeddings(config)
        self.encoder = BertEncoder(config)
        # self.pooler = BertPooler(config)

        self.pooler = BertMultiPooler(config)
        #self.pooler = BertMultiPairPooler(config)
        """If this returns error, below is another solution.
        multi_pooler = BertMultiPooler(model.config)
        multi_pooler.dense = model.pooler.dense
        multi_pooler.activation = model.pooler.activation
        """
        self.init_weights()

    def get_input_embeddings(self):
        return self.embeddings.word_embeddings

    def set_input_embeddings(self, value):
        self.embeddings.word_embeddings = value

    def _prune_heads(self, heads_to_prune):
        """ Prunes heads of the model.
            heads_to_prune: dict of {layer_num: list of heads to prune in this layer}
            See base class PreTrainedModel
        """
        for layer, heads in heads_to_prune.items():
            self.encoder.layer[layer].attention.prune_heads(heads)

    #@add_start_docstrings_to_callable(BERT_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids=None,
        #cls_indexes=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        encoder_hidden_states=None,
        encoder_attention_mask=None,
    ):
        r"""
    Return:
        :obj:`tuple(torch.FloatTensor)` comprising various elements depending on the configuration (:class:`~transformers.BertConfig`) and inputs:
        last_hidden_state (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, sequence_length, hidden_size)`):
            Sequence of hidden-states at the output of the last layer of the model.
        pooler_output (:obj:`torch.FloatTensor`: of shape :obj:`(batch_size, hidden_size)`):
            Last layer hidden-state of the first token of the sequence (classification token)
            further processed by a Linear layer and a Tanh activation function. The Linear
            layer weights are trained from the next sentence prediction (classification)
            objective during pre-training.

            This output is usually *not* a good summary
            of the semantic content of the input, you're often better with averaging or pooling
            the sequence of hidden-states for the whole input sequence.
        hidden_states (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_hidden_states=True``):
            Tuple of :obj:`torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer)
            of shape :obj:`(batch_size, sequence_length, hidden_size)`.

            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_attentions=True``):
            Tuple of :obj:`torch.FloatTensor` (one for each layer) of shape
            :obj:`(batch_size, num_heads, sequence_length, sequence_length)`.

            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.

    Examples::

        from transformers import BertModel, BertTokenizer
        import torch

        tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        model = BertModel.from_pretrained('bert-base-uncased')

        input_ids = torch.tensor(tokenizer.encode("Hello, my dog is cute", add_special_tokens=True)).unsqueeze(0)  # Batch size 1
        outputs = model(input_ids)

        last_hidden_states = outputs[0]  # The last hidden-state is the first element of the output tuple

        """

        if input_ids is not None and inputs_embeds is not None:
            raise ValueError(
                "You cannot specify both input_ids and inputs_embeds at the same time"
            )
        elif input_ids is not None:
            input_shape = input_ids.size()
        elif inputs_embeds is not None:
            input_shape = inputs_embeds.size()[:-1]
        else:
            raise ValueError(
                "You have to specify either input_ids or inputs_embeds")

        device = input_ids.device if input_ids is not None else inputs_embeds.device

        if attention_mask is None:
            attention_mask = torch.ones(input_shape, device=device)
        if token_type_ids is None:
            token_type_ids = torch.zeros(input_shape,
                                         dtype=torch.long,
                                         device=device)

        # We can provide a self-attention mask of dimensions [batch_size, from_seq_length, to_seq_length]
        # ourselves in which case we just need to make it broadcastable to all heads.
        if attention_mask.dim() == 3:
            extended_attention_mask = attention_mask[:, None, :, :]
        elif attention_mask.dim() == 2:
            # Provided a padding mask of dimensions [batch_size, seq_length]
            # - if the model is a decoder, apply a causal mask in addition to the padding mask
            # - if the model is an encoder, make the mask broadcastable to [batch_size, num_heads, seq_length, seq_length]
            if self.config.is_decoder:
                batch_size, seq_length = input_shape
                seq_ids = torch.arange(seq_length, device=device)
                causal_mask = seq_ids[None, None, :].repeat(
                    batch_size, seq_length, 1) <= seq_ids[None, :, None]
                causal_mask = causal_mask.to(
                    attention_mask.dtype
                )  # causal and attention masks must have same type with pytorch version < 1.3
                extended_attention_mask = causal_mask[:,
                                                      None, :, :] * attention_mask[:,
                                                                                   None,
                                                                                   None, :]
            else:
                extended_attention_mask = attention_mask[:, None, None, :]
        else:
            raise ValueError(
                "Wrong shape for input_ids (shape {}) or attention_mask (shape {})"
                .format(input_shape, attention_mask.shape))

        # Since attention_mask is 1.0 for positions we want to attend and 0.0 for
        # masked positions, this operation will create a tensor which is 0.0 for
        # positions we want to attend and -10000.0 for masked positions.
        # Since we are adding it to the raw scores before the softmax, this is
        # effectively the same as removing these entirely.
        extended_attention_mask = extended_attention_mask.to(
            dtype=next(self.parameters()).dtype)  # fp16 compatibility
        extended_attention_mask = (1.0 - extended_attention_mask) * -10000.0

        # If a 2D ou 3D attention mask is provided for the cross-attention
        # we need to make broadcastabe to [batch_size, num_heads, seq_length, seq_length]
        if self.config.is_decoder and encoder_hidden_states is not None:
            encoder_batch_size, encoder_sequence_length, _ = encoder_hidden_states.size(
            )
            encoder_hidden_shape = (encoder_batch_size,
                                    encoder_sequence_length)
            if encoder_attention_mask is None:
                encoder_attention_mask = torch.ones(encoder_hidden_shape,
                                                    device=device)

            if encoder_attention_mask.dim() == 3:
                encoder_extended_attention_mask = encoder_attention_mask[:,
                                                                         None, :, :]
            elif encoder_attention_mask.dim() == 2:
                encoder_extended_attention_mask = encoder_attention_mask[:,
                                                                         None,
                                                                         None, :]
            else:
                raise ValueError(
                    "Wrong shape for encoder_hidden_shape (shape {}) or encoder_attention_mask (shape {})"
                    .format(encoder_hidden_shape,
                            encoder_attention_mask.shape))

            encoder_extended_attention_mask = encoder_extended_attention_mask.to(
                dtype=next(self.parameters()).dtype)  # fp16 compatibility
            encoder_extended_attention_mask = (
                1.0 - encoder_extended_attention_mask) * -10000.0
        else:
            encoder_extended_attention_mask = None

        # Prepare head mask if needed
        # 1.0 in head_mask indicate we keep the head
        # attention_probs has shape bsz x n_heads x N x N
        # input head_mask has shape [num_heads] or [num_hidden_layers x num_heads]
        # and head_mask is converted to shape [num_hidden_layers x batch x num_heads x seq_length x seq_length]
        if head_mask is not None:
            if head_mask.dim() == 1:
                head_mask = head_mask.unsqueeze(0).unsqueeze(0).unsqueeze(
                    -1).unsqueeze(-1)
                head_mask = head_mask.expand(self.config.num_hidden_layers, -1,
                                             -1, -1, -1)
            elif head_mask.dim() == 2:
                head_mask = (head_mask.unsqueeze(1).unsqueeze(-1).unsqueeze(-1)
                             )  # We can specify head_mask for each layer
            head_mask = head_mask.to(dtype=next(self.parameters(
            )).dtype)  # switch to fload if need + fp16 compatibility
        else:
            head_mask = [None] * self.config.num_hidden_layers

        embedding_output = self.embeddings(input_ids=input_ids,
                                           position_ids=position_ids,
                                           token_type_ids=token_type_ids,
                                           inputs_embeds=inputs_embeds)
        encoder_outputs = self.encoder(
            embedding_output,
            attention_mask=extended_attention_mask,
            head_mask=head_mask,
            encoder_hidden_states=encoder_hidden_states,
            encoder_attention_mask=encoder_extended_attention_mask,
        )
        sequence_output = encoder_outputs[0]

        # =====================================================
        # pooled_output = self.pooler(sequence_output)
        #pooled_output = self.pooler(sequence_output, cls_indexes).squeeze(0) # (1, k, 768) => (k, 768): k = num_col
        pooled_output = self.pooler(sequence_output).squeeze(
            0)  # (1, N, 768) => (N, 768): N token_length
        # =====================================================

        outputs = (
            sequence_output,
            pooled_output,
        ) + encoder_outputs[
            1:]  # add hidden_states and attentions if they are here
        return outputs  # sequence_output, pooled_output, (hidden_states), (attentions)


class BertForMultiOutputClassification(BertPreTrainedModel):

    def __init__(self, config):
        super().__init__(config)
        self.num_labels = config.num_labels

        #self.bert = BertModel(config)
        self.bert = BertModelMultiOutput(config)
        self.dropout = nn.Dropout(config.hidden_dropout_prob)
        self.classifier = nn.Linear(config.hidden_size, self.config.num_labels)

        self.init_weights()

    # @add_start_docstrings_to_callable(BERT_INPUTS_DOCSTRING)
    def forward(
        self,
        input_ids=None,
        #cls_indexes=None,
        attention_mask=None,
        token_type_ids=None,
        position_ids=None,
        head_mask=None,
        inputs_embeds=None,
        labels=None,
    ):
        r"""
        labels (:obj:`torch.LongTensor` of shape :obj:`(batch_size,)`, `optional`, defaults to :obj:`None`):
            Labels for computing the sequence classification/regression loss.
            Indices should be in :obj:`[0, ..., config.num_labels - 1]`.
            If :obj:`config.num_labels == 1` a regression loss is computed (Mean-Square loss),
            If :obj:`config.num_labels > 1` a classification loss is computed (Cross-Entropy).
    Returns:
        :obj:`tuple(torch.FloatTensor)` comprising various elements depending on the configuration (:class:`~transformers.BertConfig`) and inputs:
        loss (:obj:`torch.FloatTensor` of shape :obj:`(1,)`, `optional`, returned when :obj:`label` is provided):
            Classification (or regression if config.num_labels==1) loss.
        logits (:obj:`torch.FloatTensor` of shape :obj:`(batch_size, config.num_labels)`):
            Classification (or regression if config.num_labels==1) scores (before SoftMax).
        hidden_states (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_hidden_states=True``):
            Tuple of :obj:`torch.FloatTensor` (one for the output of the embeddings + one for the output of each layer)
            of shape :obj:`(batch_size, sequence_length, hidden_size)`.
            Hidden-states of the model at the output of each layer plus the initial embedding outputs.
        attentions (:obj:`tuple(torch.FloatTensor)`, `optional`, returned when ``config.output_attentions=True``):
            Tuple of :obj:`torch.FloatTensor` (one for each layer) of shape
            :obj:`(batch_size, num_heads, sequence_length, sequence_length)`.
            Attentions weights after the attention softmax, used to compute the weighted average in the self-attention
            heads.
    Examples::
        from transformers import BertTokenizer, BertForSequenceClassification
        import torch
        tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        model = BertForSequenceClassification.from_pretrained('bert-base-uncased')
        input_ids = torch.tensor(tokenizer.encode("Hello, my dog is cute", add_special_tokens=True)).unsqueeze(0)  # Batch size 1
        labels = torch.tensor([1]).unsqueeze(0)  # Batch size 1
        outputs = model(input_ids, labels=labels)
        loss, logits = outputs[:2]
        """

        # BertModelMultiOutput
        outputs = self.bert(
            input_ids,
            #cls_indexes,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            position_ids=position_ids,
            head_mask=head_mask,
            inputs_embeds=inputs_embeds,
        )

        # Note: returned tensor contains pooled_output of all tokens (to make the tensor size consistent)
        pooled_output = outputs[1]  # (N, 768)

        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)

        outputs = (logits, ) + outputs[
            2:]  # add hidden states and attention if they are here

        if labels is not None:
            if self.num_labels == 1:
                #  We are doing regression
                loss_fct = MSELoss()
                loss = loss_fct(logits.view(-1), labels.view(-1))
            else:
                loss_fct = CrossEntropyLoss()
                loss = loss_fct(logits.view(-1, self.num_labels),
                                labels.view(-1))
            outputs = (loss, ) + outputs

        return outputs  # (loss), logits, (hidden_states), (attentions)


if __name__ == "__main__":
    from transformers import BertTokenizer
    tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")
    #model = BertModelMultiOutput.from_pretrained("bert-base-uncased")
    model = BertForMultiOutputClassification.from_pretrained(
        "bert-base-uncased",  # <= BertModelMultiOutput
        num_labels=78,
        output_attentions=False,
        output_hidden_states=False,
    )
