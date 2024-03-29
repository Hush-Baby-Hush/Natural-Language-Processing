#!/usr/bin/env python
# coding: utf-8

# # CS 447 Homework 3 $-$ Neural Machine Translation
# In this homework we are going to perform machine translation using two deep learning approaches: a Recurrent Neural Network (RNN) and Transformer.
# 
# Specifically, we are going to train sequence to sequence models for Spanish to English translation. In this assignment you only need to implement the neural network models, we implement all the data loading for you. Please **refer** to the following resources for more details:
# 
# 1.   https://papers.nips.cc/paper/5346-sequence-to-sequence-learning-with-neural-networks.pdf
# 2.   https://pytorch.org/tutorials/intermediate/seq2seq_translation_tutorial.html
# 3. https://arxiv.org/pdf/1409.0473.pdf
# 
# We suggest that you select "GPU" as your runtime type. You can find this by going to <TT>Runtime > Change Runtime Type</TT> and select "GPU" from the dropdown menu.
# 
# 

# # Step 1: Download & Prepare the Data

# In[324]:


### DO NOT EDIT ###

import pandas as pd
import unicodedata
import re
from torch.utils.data import Dataset
import torch
import random
import os


# ## Helper Functions
# This cell contains helper functions for the dataloader.

# In[325]:


### DO NOT EDIT ###

# Converts the unicode file to ascii
def unicode_to_ascii(s):
    """Normalizes latin chars with accent to their canonical decomposition"""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def preprocess_sentence(w):
    '''
    Preprocess the sentence to add the start, end tokens and make them lower-case
    '''
    w = unicode_to_ascii(w.lower().strip())
    w = re.sub(r'([?.!,¿])', r' \1 ', w)
    w = re.sub(r'[" "]+', ' ', w)

    w = re.sub(r'[^a-zA-Z?.!,¿]+', ' ', w)
    
    w = w.rstrip().strip()
    w = '<start> ' + w + ' <end>'
    return w


def pad_sequences(x, max_len):
    padded = np.zeros((max_len), dtype=np.int64)
    if len(x) > max_len:
        padded[:] = x[:max_len]
    else:
        padded[:len(x)] = x
    return padded


def preprocess_data_to_tensor(dataframe, src_vocab, trg_vocab):
    # Vectorize the input and target languages
    src_tensor = [[src_vocab.word2idx[s if s in src_vocab.vocab else '<unk>'] for s in es.split(' ')] for es in dataframe['es'].values.tolist()]
    trg_tensor = [[trg_vocab.word2idx[s if s in trg_vocab.vocab else '<unk>'] for s in eng.split(' ')] for eng in dataframe['eng'].values.tolist()]

    # Calculate the max_length of input and output tensor for padding
    max_length_src, max_length_trg = max(len(t) for t in src_tensor), max(len(t) for t in trg_tensor)
    print('max_length_src: {}, max_length_trg: {}'.format(max_length_src, max_length_trg))

    # Pad all the sentences in the dataset with the max_length
    src_tensor = [pad_sequences(x, max_length_src) for x in src_tensor]
    trg_tensor = [pad_sequences(x, max_length_trg) for x in trg_tensor]

    return src_tensor, trg_tensor, max_length_src, max_length_trg


def train_test_split(src_tensor, trg_tensor):
    '''
    Create training and test sets.
    '''
    total_num_examples = len(src_tensor) - int(0.2*len(src_tensor))
    src_tensor_train, src_tensor_test = src_tensor[:int(0.75*total_num_examples)], src_tensor[int(0.75*total_num_examples):total_num_examples]
    trg_tensor_train, trg_tensor_test = trg_tensor[:int(0.75*total_num_examples)], trg_tensor[int(0.75*total_num_examples):total_num_examples]

    return src_tensor_train, src_tensor_test, trg_tensor_train, trg_tensor_test


# ## Download and Visualize the Data
# 
# Here we will download the translation data. We will learn a model to translate Spanish to English.

# In[326]:


### DO NOT EDIT ###

if __name__ == '__main__':
    os.system("wget http://www.manythings.org/anki/spa-eng.zip")
    os.system("unzip -o spa-eng.zip")


# Now we visualize the data.

# In[327]:


### DO NOT EDIT ###

if __name__ == '__main__':
    lines = open('spa.txt', encoding='UTF-8').read().strip().split('\n')
    total_num_examples = 50000 
    original_word_pairs = [[w for w in l.split('\t')][:2] for l in lines[:total_num_examples]]
    random.seed(42)
    random.shuffle(original_word_pairs)
    dat = pd.DataFrame(original_word_pairs, columns=['eng', 'es'])
    print(dat) # Visualize the data


# Next we preprocess the data.

# In[328]:


### DO NOT EDIT ###

if __name__ == '__main__':
    data = dat.copy()
    data['eng'] = dat.eng.apply(lambda w: preprocess_sentence(w))
    data['es'] = dat.es.apply(lambda w: preprocess_sentence(w))
    print(data) # visualizing the data


# ## Vocabulary & Dataloader Classes
# 
# First we create a class for managing our vocabulary as we did in Homework 2. In this homework, we have a separate class for the vocabulary as we need 2 different vocabularies $-$ one for English and one for Spanish.
# 
# Then we prepare the dataloader and make sure it returns the source sentence and target sentence.
# 
# We will instantiate these classes later on when we have created our pretrained embeddings.

# In[329]:


### DO NOT EDIT ###

class Vocab_Lang():
    def __init__(self, vocab):
        self.word2idx = {'<pad>': 0, '<unk>': 1}
        self.idx2word = {0: '<pad>', 1: '<unk>'}
        self.vocab = vocab
        
        for index, word in enumerate(self.vocab):
            self.word2idx[word] = index + 2 # +2 because of <pad> and <unk> token
            self.idx2word[index + 2] = word
        

class MyData(Dataset):
    def __init__(self, X, y):
        self.length = torch.LongTensor([np.sum(1 - np.equal(x, 0)) for x in X])
        self.data = torch.LongTensor(X)
        self.target = torch.LongTensor(y)
    
    def __getitem__(self, index):
        x = self.data[index]
        y = self.target[index]
        return x, y

    def __len__(self):
        return len(self.data)


# # Step 2: Create Pretrained Embeddings [10 points]
# 
# The embedding used in Homework 2 was initialized with random vectors and learned while training. Here we will use the FastText embedding method proposed by Facebook's AI Research lab to improve our translation result. Particularly, we will use an implementation from the gensim library to train the embedding of our corpus.
# 
# You can read more about FastText and gensim liberary:
# https://radimrehurek.com/gensim/models/fasttext.html#gensim.models.fasttext.FastText

# In[330]:


### DO NOT EDIT ###

from gensim.models import FastText
import numpy as np
import random
from torch.utils.data import DataLoader


# ## <font color='red'>TODO:</font> Train FastText Embeddings [10 points]

# In[331]:


def compute_FastText_embeddings(pd_dataframe, embedding_dim):
    """
    Given dataset (pd.DataFrame as used in the beginning), train FastText embeddings
    Return FastText trained model and embeddings vectors (np array [2 + vocab_size, embedding_dim])
    """
    
    print('Computing FastText Embeddings...')
    sentences = [sen.split() for sen in pd_dataframe]
    model, embedding_vec = None, None
    
    ### TODO ###

    # (1) Create FastText model to learn `embedding_dim` sized embedding vectors
    # (2) Build vocab from sentences
    # (3) Train model on sentences for 10 epochs
    # (4) The sentences that we used to train the embedding don't contain '<pad>', or '<unk>' 
    #     so add two all-zero or random rows in the beginning of the embedding np array for '<pad>' and '<unk>'
    
    model = FastText(size=embedding_dim)
    model.build_vocab(sentences)
    model.train(sentences, total_examples=model.corpus_count, 
                total_words=model.corpus_total_words, epochs=10)
    embedding_vec = model.wv.vectors
    embedding_vec = np.concatenate([np.zeros([2, embedding_dim]), 
                                    embedding_vec])

    

    return model, embedding_vec


# In[332]:


### DO NOT EDIT ###

if __name__ == '__main__':
    # HYPERPARAMETERS (You may change these if you want, though you shouldn't need to)
    BATCH_SIZE = 64
    EMBEDDING_DIM = 256

    fasttext_model_src, embedding_src = compute_FastText_embeddings(data['es'], EMBEDDING_DIM)
    fasttext_model_trg, embedding_trg = compute_FastText_embeddings(data['eng'], EMBEDDING_DIM)


# ## Instantiate Datasets
# 
# Now that we have our pretrained embeddings, we can instantiate our training and validation datasets.

# In[333]:


### DO NOT EDIT ###

if __name__ == '__main__':
    src_vocab = Vocab_Lang(fasttext_model_src.wv.vocab)
    trg_vocab = Vocab_Lang(fasttext_model_trg.wv.vocab)
    src_tensor, trg_tensor, max_length_src, max_length_trg = preprocess_data_to_tensor(data, src_vocab, trg_vocab)
    src_tensor_train, src_tensor_val, trg_tensor_train, trg_tensor_val = train_test_split(src_tensor, trg_tensor)

    # create train and val datasets
    train_dataset = MyData(src_tensor_train, trg_tensor_train)
    train_dataset = DataLoader(train_dataset, batch_size=BATCH_SIZE, drop_last=True, shuffle=True)

    test_dataset = MyData(src_tensor_val, trg_tensor_val)
    test_dataset = DataLoader(test_dataset, batch_size=BATCH_SIZE, drop_last=True, shuffle=False)


# In[334]:


### DO NOT EDIT ###

if __name__ == '__main__':
    idxes = random.choices(range(len(train_dataset.dataset)), k=5)
    src, trg =  train_dataset.dataset[idxes]
    print('Source:', src)
    print('Target:', trg)


# In[335]:


### DO NOT EDIT ###

import torch.nn as nn
import torch.nn.functional as F
import time
from tqdm.notebook import tqdm
import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction, corpus_bleu


# # Step 3: Train a Recurrent Neural Network (RNN) [45 points]
# 
# Here you will write a recurrent model for machine translation, and then train and evaluate its results.
# 
# Here are some links that you may find helpful:
# 1. Attention paper: https://arxiv.org/pdf/1409.0473.pdf
# 2. Explanation of LSTM's & GRU's: https://towardsdatascience.com/illustrated-guide-to-lstms-and-gru-s-a-step-by-step-explanation-44e9eb85bf21
# 3. Attention explanation: https://towardsdatascience.com/attention-in-neural-networks-e66920838742 
# 4. Another attention explanation: https://towardsdatascience.com/attention-and-its-different-forms-7fc3674d14dc
# 

# ## <font color='red'>TODO:</font> Encoder Model [10 points]
# 
# First we build a recurrent encoder model, which will be very similar to what you did in Homework 2. However, instead of using a fully connected layer as the output, you should the return a sequence of outputs of your GRU as well as the final hidden state. These will be used in the decoder.
# 
# In this cell, you should implement the `__init(...)` and `forward(...)` functions, each of which is <b>5 points</b>.

# In[336]:


class RnnEncoder(nn.Module):
    def __init__(self, pretrained_emb, vocab_size, embedding_dim, hidden_units):
        super(RnnEncoder, self).__init__()
        """
        Args:
            pretrained_emb: np.array, the pre-trained source embedding computed from compute_FastText_embeddings
            vocab_size: int, the size of the source vocabulary
            embedding_dim: the dimension of the embedding
            hidden_units: The number of features in the GRU hidden state
        """

        ### TODO ###
        
        # Convert pretrained_emb from np.array to torch.FloatTensor
        pretrained_emb = torch.from_numpy(pretrained_emb)

        # Initialize embedding layer with pretrained_emb
        # (see: https://pytorch.org/docs/stable/generated/torch.nn.Embedding.html)
        self.embedding = nn.Embedding.from_pretrained(pretrained_emb)
        
        # Initialize a single directional GRU with 1 layer and batch_first=False
        self.gru = nn.GRU(input_size=embedding_dim, hidden_size=hidden_units, 
                          num_layers=1, batch_first=False)
        
        
    def forward(self, x):
        """
        Args:
            X: source texts, [max_len, batch_size]

        Returns:
            output: [max_len, batch_size, hidden_units]
            hidden_state: [1, batch_size, hidden_units] 
        
        Pseudo-code:
        - Pass x through an embedding layer and pass the results through the recurrent net
        - Return output and hidden states from the recurrent net
        """
        output, hidden_state = None, None

        ### TODO ###
        x = self.embedding(x)
        #print('embed', x.shape)
        output, hidden_state = self.gru(x.float())
        #print('gru output', output.shape)
        #print('gru hidden', hidden_state.shape)
        #output, _ = pad_packed_sequence(output, batch_first=False)
        #print('packed', output)
        
        return output, hidden_state


# ## <font color='red'>TODO:</font> Decoder Model [15 points]
# We will implement a Decoder model that uses an attention mechanism, as provided in https://arxiv.org/pdf/1409.0473.pdf. We have broken this up into three functions that you need to implement: `__init__(self, ...)`, `compute_attention(self, dec_hs, enc_output)`, and `forward(self, x, dec_hs, enc_output)`:
# 
# * <b>`__init__(self, ...)`: [5 points]</b> Instantiate the parameters of your model, and store them in `self` variables.
# 
# * <b>`compute_attention(self, dec_hs, enc_output)` [5 points]</b>: Compute the <b>context vector</b>, which is a weighted sum of the encoder output states. Suppose the decoder hidden state at time $t$ is $\mathbf{h}_t$, and the encoder hidden state at time $s$ is $\mathbf{\bar h}_s$. The pseudocode is as follows:
# 
#   1. <b>Attention scores:</b> Compute real-valued scores for the decoder hidden state $\mathbf{h}_t$ and each encoder hidden state $\mathbf{\bar h}_s$: $$\mathrm{score}(\mathbf{h}_t, \mathbf{\bar h}_s)=
#       \mathbf{v}_a^T \tanh(\mathbf{W}_1 \mathbf{h}_t +\mathbf{W}_2 \mathbf{\bar h}_s)
# $$
#    Here you should implement the scoring function. A higher score indicates a stronger "affinity" between the decoder state and a specific encoder state. Note that the matrices $\mathbf{W}_1$, $\mathbf{W}_2$ and the vector $\mathbf{v_a}$ can all be implemented with `nn.Linear(...)` in Pytorch.
# 
#  2. <b>Attention weights:</b> Normalize the attention scores to obtain a valid probability distribution: $$\alpha_{ts} = \frac{\exp \big (\mathrm{score}(\mathbf{h}_t, \mathbf{\bar h}_s) \big)}{\sum_{s'=1}^S \exp \big (\mathrm{score}(\mathbf{h}_t, \mathbf{\bar h}_{s'}) \big)}$$ Notice that this is just the softmax function, and can be implemented with `torch.softmax(...)` in Pytorch.
# 
#  3. <b>Context vector:</b> Compute a context vector $\mathbf{c}_t$ that is a weighted average of the encoder hidden states, where the weights are given by the attention weights you just computed: $$\mathbf{c}_t=\sum_{s=1}^S \alpha_{ts} \mathbf{\bar h}_s$$
# 
#  You should return this context vector, along with the attention weights.
# 
# 
# 
# * <b>`forward(self, x, dec_hs, enc_output)`: [5 points]</b> Run a <b>single</b> decoding step, resulting in a distribution over the vocabulary for the next token in the sequence. Pseudocode can be found in the docstrings below.
# 
# <b>Implementation Hint:</b> You should be able to implement all of this <b>without any for loops</b> using the Pytorch library. Also, remember that these operations should operate in parallel for each item in your batch.

# In[351]:


class RnnDecoder(nn.Module):
    def __init__(self, pretrained_emb, vocab_size, embedding_dim, hidden_units):
        super(RnnDecoder, self).__init__()
        """
        Args:
            pretrained_emb: The pre-trained target embedding computed from compute_FastText_embeddings (np.array)
            vocab_size: The size of the target vocabulary
            embedding_dim: The dimension of the embedding
            hidden_units: The number of features in the GRU hidden state
        """

        ### TODO ###

        # Convert pretrained_emb from np.array to torch.FloatTensor
        pretrained_emb = torch.from_numpy(pretrained_emb)

        # Initialize embedding layer with pretrained_emb
        self.embedding = nn.Embedding.from_pretrained(pretrained_emb)
        
        # Initialize layers to compute attention score
        self.w1 = nn.Linear(hidden_units, hidden_units)
        self.w2 = nn.Linear(hidden_units, hidden_units)
        self.v = nn.Linear(hidden_units, 1)
        
        # Initialize a single directional GRU with 1 layer and batch_first=True
        # NOTE: Input to your RNN will be the concatenation of your embedding vector and the context vector
        self.gru = nn.GRU(embedding_dim + hidden_units , hidden_units, 
                          num_layers=1, batch_first=True)
        
        # Initialize fully connected layer
        #print('vocab_size', vocab_size)
        self.fc = nn.Linear(hidden_units, vocab_size)
    
    def compute_attention(self, dec_hs, enc_output):
        '''
        This function computes the context vector and attention weights.

        Args:
            dec_hs: Decoder hidden state; [1, batch_size, hidden_units]
            enc_output: Encoder outputs; [max_len_src, batch_size, hidden_units]

        Returns:
            context_vector: Context vector, according to formula; [batch_size, hidden_units]
            attention_weights: The attention weights you have calculated; [batch_size, max_len_src, 1]

        Pseudo-code:
            (1) Compute the attention scores for dec_hs & enc_output
                    - Hint: You may need to permute the dimensions of the tensors in order to pass them through linear layers
                    - Output size: [batch_size, max_len_src, 1]
            (2) Compute attention_weights by taking a softmax over your scores to normalize the distribution
                    - Output size: [batch_size, max_len_src, 1]
            (3) Compute context_vector from attention_weights & enc_output
                    - Hint: You may find it helpful to use torch.sum & element-wise multiplication (* operator)
            (4) Return context_vector & attention_weights
        '''    
        context_vector, attention_weights = None, None
        
        ### TODO ###
        dec_hs = dec_hs.permute(1, 0, 2)
        enc_output = enc_output.permute(1, 0, 2)# [batch_size, max_len_src, hidden_units]
        
        scores = self.v(torch.tanh(self.w1(dec_hs) + self.w2(enc_output))) #[batch_size, max_len_src, 1]
        
        attention_weights = torch.softmax(scores, dim=1) #[batch_size, max_len_src, 1]
        #print('attention_weights', attention_weights.shape)
        
        context_vector = torch.sum(attention_weights * enc_output, dim=1, keepdim=True) #[batch_size, 1, hidden_units]
        #print('context_vector', context_vector.shape)
        context_vector = context_vector.squeeze(1)
        #print(context_vector.shape)
        
        return context_vector, attention_weights

    def forward(self, x, dec_hs, enc_output):
        '''
        This function runs the decoder for a **single** time step.

        Args:
            x: Input token; [batch_size, 1]
            dec_hs: Decoder hidden state; [1, batch_size, hidden_units]
            enc_output: Encoder outputs; [max_len_src, batch_size, hidden_units]

        Returns:
            fc_out: (Unnormalized) output distribution [batch_size, vocab_size]
            dec_hs: Decoder hidden state; [1, batch_size, hidden_units]
            attention_weights: The attention weights you have learned; [batch_size, max_len_src, 1]

        Pseudo-code:
            (1) Compute the context vector & attention weights by calling self.compute_attention(...) on the appropriate input
            (2) Obtain embedding vectors for your input x
                    - Output size: [batch_size, 1, embedding_dim]             
            (3) Concatenate the context vector & the embedding vectors along the appropriate dimension
            (4) Feed this result through your RNN (along with the current hidden state) to get output and new hidden state
                    - Output sizes: [batch_size, 1, hidden_units] & [1, batch_size, hidden_units] 
            (5) Feed the output of your RNN through linear layer to get (unnormalized) output distribution (don't call softmax!)
            (6) Return this output, the new decoder hidden state, & the attention weights
        '''
        fc_out, attention_weights = None, None

        ### TODO ###
        context_vector, attention_weights = self.compute_attention(dec_hs, enc_output)
        
        embedding = self.embedding(x) #[batch_size, 1, embedding_dim] 
        #print('embedding size', embedding.shape)
        
        temp = context_vector.unsqueeze(dim=1)
        #print(temp.shape)
        concate = torch.cat((temp, embedding.float()), dim=2) #[batch_size，1, hidden_size + embedding_size]
        
        output, dec_hs = self.gru(concate, dec_hs)
        #print('output', output.shape)
        #print('dec_hs', dec_hs.shape)
        
        fc_out = self.fc(output.squeeze(1))
        

        return fc_out, dec_hs, attention_weights


# ## Train RNN Model
# 
# We will train the encoder and decoder using cross-entropy loss.

# In[352]:


### DO NOT EDIT ###

def loss_function(real, pred):
    mask = real.ge(1).float() # Only consider non-zero inputs in the loss
    
    loss_ = F.cross_entropy(pred, real) * mask 
    return torch.mean(loss_)

def train_rnn_model(encoder, decoder, dataset, optimizer, trg_vocab, device, n_epochs):
    batch_size = dataset.batch_size
    for epoch in range(n_epochs):
        start = time.time()
        n_batch = 0
        total_loss = 0
        
        encoder.train()
        decoder.train()
        
        for src, trg in tqdm(dataset):
            n_batch += 1
            loss = 0
            
            enc_output, enc_hidden = encoder(src.transpose(0,1).to(device))
            dec_hidden = enc_hidden
            
            # use teacher forcing - feeding the target as the next input (via dec_input)
            dec_input = torch.tensor([[trg_vocab.word2idx['<start>']]] * batch_size)
        
            # run code below for every timestep in the ys batch
            for t in range(1, trg.size(1)):
                predictions, dec_hidden, _ = decoder(dec_input.to(device), dec_hidden.to(device), enc_output.to(device))
                loss += loss_function(trg[:, t].to(device), predictions.to(device))
                dec_input = trg[:, t].unsqueeze(1)
        
            batch_loss = (loss / int(trg.size(1)))
            total_loss += batch_loss
            
            optimizer.zero_grad()
            
            batch_loss.backward()

            ### update model parameters
            optimizer.step()
        
        ### TODO: Save checkpoint for model (optional)
        print('Epoch:{:2d}/{}\t Loss: {:.4f} \t({:.2f}s)'.format(epoch + 1, n_epochs, total_loss / n_batch, time.time() - start))

    print('Model trained!')


# In[353]:


### DO NOT EDIT ###

if __name__ == '__main__':
    # HYPERPARAMETERS - feel free to change
    LEARNING_RATE = 0.001
    HIDDEN_UNITS=256
    N_EPOCHS=10

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
  
    src_vocab_size = len(src_vocab.word2idx)
    trg_vocab_size = len(trg_vocab.word2idx)

    rnn_encoder = RnnEncoder(embedding_src, src_vocab_size, EMBEDDING_DIM, HIDDEN_UNITS).to(device)
    rnn_decoder = RnnDecoder(embedding_trg, trg_vocab_size, EMBEDDING_DIM, HIDDEN_UNITS).to(device)

    rnn_model_params = list(rnn_encoder.parameters()) + list(rnn_decoder.parameters())
    optimizer = torch.optim.Adam(rnn_model_params, lr=LEARNING_RATE)

    print('Encoder and Decoder models initialized!')


# In[354]:


### DO NOT EDIT ###

if __name__ == '__main__':
    train_rnn_model(rnn_encoder, rnn_decoder, train_dataset, optimizer, trg_vocab, device, N_EPOCHS)


# In[ ]:


### DO NOT EDIT ###

def decode_rnn_model(encoder, decoder, src, max_decode_len, trg_vocab, device):
    """
    Args:
        encoder: Your RnnEncoder object
        decoder: Your RnnDecoder object
        src: [max_src_length, batch_size] the source sentences you wish to translate
        max_decode_len: The maximum desired length (int) of your target translated sentences
        trg_vocab: The Vocab_Lang object for the target language
        device: the device your torch tensors are on (you may need to call x.to(device) for some of your tensors)

    Returns:
        curr_output: [batch_size, max_decode_len] containing your predicted translated sentences
        curr_predictions: [batch_size, max_decode_len, trg_vocab_size] containing the (unnormalized) probabilities of each
            token in your vocabulary at each time step

    Pseudo-code:
    - Obtain encoder output and hidden state by encoding src sentences
    - For 1 ≤ t ≤ max_decode_len:
        - Obtain your (unnormalized) prediction probabilities and hidden state by feeding dec_input (the best words 
          from the previous time step), previous hidden state, and encoder output to decoder
        - Save your (unnormalized) prediction probabilities in curr_predictions at index t
        - Obtain your new dec_input by selecting the most likely (highest probability) token
        - Save dec_input in curr_output at index t
    """

    # Initialize variables
    batch_size = src.size(1)
    curr_output = torch.zeros((batch_size, max_decode_len))
    curr_predictions = torch.zeros((batch_size, max_decode_len, len(trg_vocab.idx2word)))

    # We start the decoding with the start token for each example
    dec_input = torch.tensor([[trg_vocab.word2idx['<start>']]] * batch_size)
    curr_output[:, 0] = dec_input.squeeze(1)
    
    enc_output, enc_hidden = encoder(src)
    dec_hidden = enc_hidden

    # At each time step, get the best prediction and save it
    for t in range(1, max_decode_len):
        predictions, dec_hidden, _ = decoder(dec_input.to(device), dec_hidden.to(device), enc_output.to(device))
        curr_predictions[:,t,:] = predictions
        dec_input = torch.argmax(predictions, dim=1).unsqueeze(1)
        curr_output[:, t] = dec_input.squeeze(1)
    return curr_output, curr_predictions


# You can run the cell below to qualitatively compare some of the sentences your model generates with the some of the correct translations.

# In[ ]:


### DO NOT EDIT ###

if __name__ == '__main__':
    idxes = random.choices(range(len(test_dataset.dataset)), k=5)
    src, trg =  train_dataset.dataset[idxes]
    curr_output, _ = decode_rnn_model(rnn_encoder, rnn_decoder, src.transpose(0,1).to(device), trg.size(1), trg_vocab, device)
    for i in range(len(src)):
        print("Source sentence:", ' '.join([x for x in [src_vocab.idx2word[j.item()] for j in src[i]] if x != '<pad>']))
        print("Target sentence:", ' '.join([x for x in [trg_vocab.idx2word[j.item()] for j in trg[i]] if x != '<pad>']))
        print("Predicted sentence:", ' '.join([x for x in [trg_vocab.idx2word[j.item()] for j in curr_output[i]] if x != '<pad>']))
        print("----------------")


# ## Evaluate RNN Model [20 points]
# 
# We provide you with a function to run the test set through the model and calculate BLEU scores. We expect your BLEU scores to satisfy the following conditions:  
# 
# *   BLEU-1 > 0.290
# *   BLEU-2 > 0.082
# *   BLEU-3 > 0.060
# *   BLEU-4 > 0.056
# 
# Read more about Bleu Score at :
# 
# 1.   https://en.wikipedia.org/wiki/BLEU
# 2.   https://www.aclweb.org/anthology/P02-1040.pdf

# In[145]:


### DO NOT EDIT ###

def get_reference_candidate(target, pred, trg_vocab):
    def _to_token(sentence):
        lis = []
        for s in sentence[1:]:
            x = trg_vocab.idx2word[s]
            if x == "<end>": break
            lis.append(x)
        return lis
    reference = _to_token(list(target.numpy()))
    candidate = _to_token(list(pred.numpy()))
    return reference, candidate

def compute_bleu_scores(target_tensor_val, target_output, final_output, trg_vocab):
    bleu_1 = 0.0
    bleu_2 = 0.0
    bleu_3 = 0.0
    bleu_4 = 0.0

    smoother = SmoothingFunction()
    save_reference = []
    save_candidate = []
    for i in range(len(target_tensor_val)):
        reference, candidate = get_reference_candidate(target_output[i], final_output[i], trg_vocab)
    
        bleu_1 += sentence_bleu(reference, candidate, weights=(1,), smoothing_function=smoother.method1)
        bleu_2 += sentence_bleu(reference, candidate, weights=(1/2, 1/2), smoothing_function=smoother.method1)
        bleu_3 += sentence_bleu(reference, candidate, weights=(1/3, 1/3, 1/3), smoothing_function=smoother.method1)
        bleu_4 += sentence_bleu(reference, candidate, weights=(1/4, 1/4, 1/4, 1/4), smoothing_function=smoother.method1)

        save_reference.append(reference)
        save_candidate.append(candidate)
    
    bleu_1 = bleu_1/len(target_tensor_val)
    bleu_2 = bleu_2/len(target_tensor_val)
    bleu_3 = bleu_3/len(target_tensor_val)
    bleu_4 = bleu_4/len(target_tensor_val)

    scores = {"bleu_1": bleu_1, "bleu_2": bleu_2, "bleu_3": bleu_3, "bleu_4": bleu_4}
    print('BLEU 1-gram: %f' % (bleu_1))
    print('BLEU 2-gram: %f' % (bleu_2))
    print('BLEU 3-gram: %f' % (bleu_3))
    print('BLEU 4-gram: %f' % (bleu_4))

    return save_candidate, scores

def evaluate_rnn_model(encoder, decoder, test_dataset, target_tensor_val, trg_vocab, device):
    batch_size = test_dataset.batch_size
    n_batch = 0
    total_loss = 0

    encoder.eval()
    decoder.eval()
    
    final_output, target_output = None, None

    with torch.no_grad():
        for batch, (src, trg) in enumerate(test_dataset):
            n_batch += 1
            loss = 0
            curr_output, curr_predictions = decode_rnn_model(encoder, decoder, src.transpose(0,1).to(device), trg.size(1), trg_vocab, device)
            for t in range(1, trg.size(1)):
                loss += loss_function(trg[:, t].to(device), curr_predictions[:,t,:].to(device))

            if final_output is None:
                final_output = torch.zeros((len(target_tensor_val), trg.size(1)))
                target_output = torch.zeros((len(target_tensor_val), trg.size(1)))
            final_output[batch*batch_size:(batch+1)*batch_size] = curr_output
            target_output[batch*batch_size:(batch+1)*batch_size] = trg
            batch_loss = (loss / int(trg.size(1)))
            total_loss += batch_loss

        print('Loss {:.4f}'.format(total_loss / n_batch))
    
    # Compute BLEU scores
    return compute_bleu_scores(target_tensor_val, target_output, final_output, trg_vocab)


# In[146]:


### DO NOT EDIT ###

if __name__ == '__main__':
    rnn_save_candidate, rnn_scores = evaluate_rnn_model(rnn_encoder, rnn_decoder, test_dataset, trg_tensor_val, trg_vocab, device)


# # Step 4: Train a Transformer [45 points]
# 
# Here you will write a transformer model for machine translation, and then train and evaluate its results. Here are some helpful links:
# <ul>
# <li> Original transformer paper: https://arxiv.org/pdf/1706.03762.pdf
# <li> Helpful tutorial: http://jalammar.github.io/illustrated-transformer/
# <li> Another tutorial: http://peterbloem.nl/blog/transformers
# </ul>

# In[152]:


### DO NOT EDIT ###

import math


# ## <font color='red'>TODO:</font> Positional Embeddings [5 points]
# 
# Similar to the RNN, we start with the Encoder model. A key component of the encoder is the Positional Embedding. As we know, word embeddings encode words in such a way that words with similar meaning have similar vectors. Because there are no recurrences in a Transformer, we need a way to tell the transformer the relative position of words in a sentence: so will add a positional embedding to the word embeddings. Now, two words with a similar embedding will both be close in meaning and occur near each other in the sentence.
# 
# You will create a positional embedding matrix of size $(max\_len, embed\_dim)$ using the following formulae:
# <br>
# $\begin{align*} pe[pos,2i] &= \sin \Big (\frac{pos}{10000^{2i/embed\_dim}}\Big )\\pe[pos,2i+1] &= \cos \Big (\frac{pos}{10000^{2i/embed\_dim}}\Big ) \end{align*}$

# In[203]:


def create_positional_embedding(max_len, embed_dim):
    '''
    Args:
        max_len: The maximum length supported for positional embeddings
        embed_dim: The size of your embeddings
    Returns:
        pe: [max_len, 1, embed_dim] computed as in the formulae above
    '''
    pe = None

    ### TODO ###
    pe = np.zeros([max_len, 1, embed_dim+1])
    ite = math.floor((embed_dim + 1) / 2)
    for i in range(ite):
        pe[:, 0, 2*i] = np.sin(np.arange(max_len) / (1e4 ** (2*i/embed_dim)))
        pe[:, 0, 2*i+1] = np.cos(np.arange(max_len) / (1e4 ** (2*i/embed_dim)))
    
    pe = torch.from_numpy(pe[:, :, :embed_dim])
    
    return pe


# ## <font color='red'>TODO:</font> Encoder Model [10 points]
# 
# Now you will create the Encoder model for the transformer.
# 
# In this cell, you should implement the `__init(...)` and `forward(...)` functions, each of which is <b>5 points</b>.

# In[306]:


class TransformerEncoder(nn.Module):
    def __init__(self, pretrained_emb, src_vocab_size, embedding_dim, num_heads,
        num_layers, dim_feedforward, max_len_src, device):
        super(TransformerEncoder, self).__init__()
        self.device = device
        """
        Args:
            pretrained_emb: np.array, the pre-trained source embedding computed from compute_FastText_embeddings
            src_vocab_size: int, the size of the source vocabulary
            embedding_dim: the dimension of the embedding (also the number of expected features for the input of the Transformer)
            num_heads: The number of features in the GRU hidden state
            num_layers: the number of Transformer Encoder layers
            dim_feedforward: the dimension of the feedforward network models in the Transformer
            max_len_src: maximum length of the source sentences
            device: the working device (you may need to map your postional embedding to this device)
        """

        # Create positional embedding matrix
        self.position_embedding = create_positional_embedding(max_len_src, embedding_dim).to(device)
        self.register_buffer('positional_embedding', self.position_embedding) # this informs the model that position_embedding is not a learnable parameter

        ### TODO ###

        # Convert pretrained_emb from np.array to torch.FloatTensor
        pretrained_emb = torch.from_numpy(pretrained_emb)

        # Initialize embedding layer with pretrained_emb
        self.embedding = nn.Embedding.from_pretrained(pretrained_emb)

        # Dropout layer
        self.dropout = nn.Dropout()

        # Initialize a nn.TransformerEncoder model (you'll need to use embedding_dim,
        # num_layers, num_heads, & dim_feedforward here)
        encoder_layer = nn.TransformerEncoderLayer(d_model=embedding_dim,
                                                   dim_feedforward=dim_feedforward, 
                                                   nhead=num_heads)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layer, num_layers)
        

    def make_src_mask(self, src):
        src_mask = src.transpose(0, 1) == 0 # padding idx
        return src_mask.to(self.device) # (batch_size, max_src_len)

    def forward(self, x):
        """
        Args:
            x: [max_len, batch_size]
        Returns:
            output: [max_len, batch_size, embed_dim]
        Pseudo-code:
        - Pass x through the word embedding
        - Add positional embedding to the word embedding, then apply dropout
        - Call make_src_mask(x) to compute a mask: this tells us which indexes in x
          are padding, which we want to ignore for the self-attention
        - Call the encoder, with src_key_padding_mask = src_mask
        """
        output = None

        ### TODO ###
        x2 = self.embedding(x) #[max_len, batch_size, embed_dim])
        #print('word embedding', x2.shape)
        
        x2 += self.position_embedding
        
        x2 = self.dropout(x2)
        
        src_mask = self.make_src_mask(x)
        #print('src_mask', src_mask.shape)
        
        output = self.transformer_encoder.forward(x2.float(), src_key_padding_mask=src_mask)
        #print('output', output.shape)

        return output    


# ## <font color='red'>TODO:</font> Decoder Model [10 points]
# Now we implement a Decoder model. Unlike the RNN, you do not need to explicitly compute inter-attention with the encoder; you will use the nn.TransformerDecoder model, which takes care of this for you.
# 
# In this cell, you should implement the `__init(...)` and `forward(...)` functions, each of which is <b>5 points</b>.

# In[312]:


class TransformerDecoder(nn.Module):
    def __init__(self, pretrained_emb, trg_vocab_size, embedding_dim, num_heads,
        num_layers, dim_feedforward, max_len_trg, device):
        super(TransformerDecoder, self).__init__()
        self.device = device
        """
        Args:
            pretrained_emb: np.array, the pre-trained target embedding computed from compute_FastText_embeddings
            trg_vocab_size: int, the size of the target vocabulary
            embedding_dim: the dimension of the embedding (also the number of expected features for the input of the Transformer)
            num_heads: The number of features in the GRU hidden state
            num_layers: the number of Transformer Decoder layers
            dim_feedforward: the dimension of the feedforward network models in the Transformer
            max_len_trg: maximum length of the target sentences
            device: the working device (you may need to map your postional embedding to this device)
        """

        # Create positional embedding matrix
        self.position_embedding = create_positional_embedding(max_len_trg, embedding_dim).to(device)
        self.register_buffer('positional_embedding', self.position_embedding) # this informs the model that positional_embedding is not a learnable parameter

        ### TODO ###

        # Convert pretrained_emb from np.array to torch.FloatTensor
        pretrained_emb = torch.from_numpy(pretrained_emb)

        # Initialize embedding layer with pretrained_emb
        self.embedding = nn.Embedding.from_pretrained(pretrained_emb)

        # Dropout layer
        self.dropout = nn.Dropout()

        # Initialize a nn.TransformerDecoder model (you'll need to use embedding_dim,
        # num_layers, num_heads, & dim_feedforward here)
        decoder_layer = nn.TransformerDecoderLayer(d_model=embedding_dim, 
                                   dim_feedforward=dim_feedforward,
                                   nhead=num_heads)
        self.transformer_decoder = nn.TransformerDecoder(decoder_layer, num_layers)
        

        # Final fully connected layer
        self.fc = nn.Linear(embedding_dim, trg_vocab_size)
        

    def generate_square_subsequent_mask(self, sz):
        """Generate a square mask for the sequence. The masked positions are filled with float('-inf').
            Unmasked positions are filled with float(0.0).
        """
        mask = (torch.triu(torch.ones(sz, sz)) == 1).transpose(0, 1)
        mask = mask.float().masked_fill(mask == 0, float('-inf')).masked_fill(mask == 1, float(0.0))
        return mask

    def forward(self, dec_in, enc_out):
        """
        Args:
            dec_in: [sequence length, batch_size]
            enc_out: [max_len, batch_size, embed_dim]
        Returns:
            output: [sequence length, batch_size, trg_vocab_size]
        Pseudo-code:
        - Compute input word and positional embeddings in similar manner to encoder
        - Call generate_square_subsequent_mask() to compute a mask: this time,
          the mask is to prevent the decoder from attending to tokens in the "future".
          In other words, at time step i, the decoder should only attend to tokens
          1 to i-1.
        - Call the decoder, with trg_mask = trg_mask
        - Run the output through the fully-connected layer and return it
        """
        output = None

        ### TODO ###
        x2 = self.embedding(dec_in) 
        #print('embedding', x2.shape)
        
        sequence_length = dec_in.shape[0]
        
        x2 += self.position_embedding[:sequence_length, :, :]
        #print('position', x2.shape)
        x2 = self.dropout(x2)
        
        trg_mask = self.generate_square_subsequent_mask(sequence_length)
        
        x2 = self.transformer_decoder.forward(x2.float(), memory=enc_out, tgt_mask=trg_mask)
        
        output = self.fc(x2)
        #print('output', output.shape)
        return output    


# ## Train Transformer Model
# 
# Like the RNN, we train the encoder and decoder using cross-entropy loss.

# In[313]:


### DO NOT EDIT ###

def train_transformer_model(encoder, decoder, dataset, optimizer, device, n_epochs):
    encoder.train()
    decoder.train()
    criterion = nn.CrossEntropyLoss(ignore_index=0)
    for epoch in range(n_epochs):
        start = time.time()
        losses = []

        for src, trg in tqdm(train_dataset):
            
            src = src.to(device).transpose(0,1) # [max_src_length, batch_size]
            trg = trg.to(device).transpose(0,1) # [max_trg_length, batch_size]

            enc_out = encoder(src)
            output = decoder(trg[:-1, :], enc_out)

            output = output.reshape(-1, output.shape[2])
            trg = trg[1:].reshape(-1)

            optimizer.zero_grad()

            loss = criterion(output, trg)
            losses.append(loss.item())

            loss.backward()

            # Clip to avoid exploding grading issues
            torch.nn.utils.clip_grad_norm_(encoder.parameters(), max_norm=1)
            torch.nn.utils.clip_grad_norm_(decoder.parameters(), max_norm=1)

            optimizer.step()

        mean_loss = sum(losses) / len(losses)
        print('Epoch:{:2d}/{}\t Loss:{:.4f} ({:.2f}s)'.format(epoch + 1, n_epochs, mean_loss, time.time() - start))


# In[314]:


### DO NOT EDIT ###

if __name__ == '__main__':
    # HYPERPARAMETERS - feel free to change
    LEARNING_RATE = 0.001
    DIM_FEEDFORWARD=512
    N_EPOCHS=10
    N_HEADS=2
    N_LAYERS=2

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    transformer_encoder = TransformerEncoder(embedding_src, src_vocab_size, EMBEDDING_DIM, N_HEADS, 
                                 N_LAYERS,DIM_FEEDFORWARD,
                                 max_length_src, device).to(device)
    transformer_decoder = TransformerDecoder(embedding_trg, trg_vocab_size, EMBEDDING_DIM, N_HEADS, 
                              N_LAYERS,DIM_FEEDFORWARD,
                              max_length_trg, device).to(device)

    transformer_model_params = list(transformer_encoder.parameters()) + list(transformer_decoder.parameters())
    optimizer = torch.optim.Adam(transformer_model_params, lr=LEARNING_RATE)

    print('Encoder and Decoder models initialized!')


# In[315]:


### DO NOT EDIT ###

if __name__ == '__main__':
    train_transformer_model(transformer_encoder, transformer_decoder, train_dataset, optimizer, device, N_EPOCHS)


# ## Inference (Decoding) Function
# 
# Now that we have trained the model, we can use it on test data.
# 
# We provide you with an inference function that takes your trained transformer model and a source sentence (Spanish), and returns its translation (English sentence). Like the RNN, we use the prediction of the decoder as the input to the decoder for the sequence of outputs. For the RNN, at time step $t_i$ the decoder takes the hidden state $h_{i-1}$ and the previous prediction $w_{i-1}$ at each time step. However, because the transformer does not use recurrences, we do not pass a hidden state; instead, at time step $t_i$ we pass $w_1,w_2 \cdots w_{i-1}$, which is the entire sequence predicted so far.

# In[316]:


### DO NOT EDIT ###

def decode_transformer_model(encoder, decoder, src, max_decode_len, trg_vocab, device):
    """
    Args:
        encoder: Your RnnEncoder object
        decoder: Your RnnDecoder object
        src: [max_src_length, batch_size] the source sentences you wish to translate
        max_decode_len: The maximum desired length (int) of your target translated sentences
        trg_vocab: The Vocab_Lang object for the target language
        device: the device your torch tensors are on (you may need to call x.to(device) for some of your tensors)

    Returns:
        curr_output: [batch_size, max_decode_len] containing your predicted translated sentences
        curr_predictions: [batch_size, max_decode_len, trg_vocab_size] containing the (unnormalized) probabilities of each
            token in your vocabulary at each time step

    Pseudo-code:
    - Obtain encoder output by encoding src sentences
    - For 1 ≤ t ≤ max_decode_len:
        - Obtain dec_input as the best words so far for previous time steps (you can get this from curr_output)
        - Obtain your (unnormalized) prediction probabilities by feeding dec_input and encoder output to decoder
        - Save your (unnormalized) prediction probabilities in curr_predictions at index t
        - Calculate the most likely (highest probability) token and save in curr_output at timestep t
    """

    # Initialize variables
    batch_size = src.size(1)
    curr_output = torch.zeros((batch_size, max_decode_len))
    curr_predictions = torch.zeros((batch_size, max_decode_len, len(trg_vocab.idx2word)))

    # We start the decoding with the start token for each example
    dec_input = torch.tensor([[trg_vocab.word2idx['<start>']]] * batch_size).transpose(0,1)
    curr_output[:, 0] = dec_input.squeeze(1)
    
    enc_output = encoder(src)

    # At each time step, get the best prediction and save it
    for t in range(1, max_decode_len):
        dec_input = curr_output[:,:t].transpose(0,1)
        output = decoder(dec_input.int().to(device), enc_output)
        output = output[-1]
        curr_predictions[:,t,:] = output
        predictions = torch.argmax(output, dim=1)
        curr_output[:, t] = predictions

    return curr_output, curr_predictions


# You can run the cell below to qualitatively compare some of the sentences your model generates with the some of the correct translations.

# In[317]:


### DO NOT EDIT ###

if __name__ == '__main__':
    idxes = random.choices(range(len(test_dataset.dataset)), k=5)
    src, trg =  train_dataset.dataset[idxes]
    curr_output, _ = decode_transformer_model(transformer_encoder, transformer_decoder, src.transpose(0,1).to(device), trg.size(1), trg_vocab, device)
    for i in range(len(src)):
        print("Source sentence:", ' '.join([x for x in [src_vocab.idx2word[j.item()] for j in src[i]] if x != '<pad>']))
        print("Target sentence:", ' '.join([x for x in [trg_vocab.idx2word[j.item()] for j in trg[i]] if x != '<pad>']))
        print("Predicted sentence:", ' '.join([x for x in [trg_vocab.idx2word[j.item()] for j in curr_output[i]] if x != '<pad>']))
        print("----------------")


# ## Evaluate Transformer Model [20 points]
# 
# Now we can run the test set through the transformer model. We expect your BLEU scores to satisfy the following conditions: 
# 
# *   BLEU-1 > 0.290
# *   BLEU-2 > 0.082
# *   BLEU-3 > 0.060
# *   BLEU-4 > 0.056
# 

# In[318]:


### DO NOT EDIT ###

def evaluate_model(encoder, decoder, test_dataset, target_tensor_val, trg_vocab, device):
    batch_size = test_dataset.batch_size
    n_batch = 0
    total_loss = 0

    encoder.eval()
    decoder.eval()
    criterion = nn.CrossEntropyLoss(ignore_index=0)

    losses=[]
    final_output, target_output = None, None

    with torch.no_grad():
        for batch, (src, trg) in enumerate(test_dataset):
            n_batch += 1
            loss = 0
            
            src, trg = src.transpose(0,1).to(device), trg.transpose(0,1).to(device)
            curr_output, curr_predictions = decode_transformer_model(encoder, decoder, src, trg.size(0), trg_vocab, device)

            for t in range(1, trg.size(0)):
                loss += criterion(curr_predictions[:,t,:].to(device), trg[t,:].reshape(-1).to(device))

            if final_output is None:
                final_output = torch.zeros((len(target_tensor_val), trg.size(0)))
                target_output = torch.zeros((len(target_tensor_val), trg.size(0)))

            final_output[batch*batch_size:(batch+1)*batch_size] = curr_output
            target_output[batch*batch_size:(batch+1)*batch_size] = trg.transpose(0,1)
            losses.append(loss.item() / (trg.size(0)-1))

        mean_loss = sum(losses) / len(losses)
        print('Loss {:.4f}'.format(mean_loss))
    
    # Compute Bleu scores
    return compute_bleu_scores(target_tensor_val, target_output, final_output, trg_vocab)


# In[319]:


### DO NOT EDIT ###

if __name__ == '__main__':
    transformer_save_candidate, transformer_scores = evaluate_model(transformer_encoder, transformer_decoder, test_dataset, trg_tensor_val, trg_vocab, device)


# # What You Need to Submit
# 
# To submit the assignment, download this notebook as a <TT>.py</TT> file. You can do this by going to <TT>File > Download > Download .py</TT>. Then rename it to `hwk3.py`.
# 
# You will also need to save the `rnn_encoder`, `rnn_decoder`, `transformer_encoder` and `transformer_decoder`. You can run the cell below to do this. After you save the files to your Google Drive, you need to manually download the files to your computer, and then submit them to the autograder.
# 
# You will submit the following files to the autograder:
# 1.   `hwk3.py`, the download of this notebook as a `.py` file (**not** a `.ipynb` file)
# 1.   `rnn_encoder.pt`, the saved version of your `rnn_encoder`
# 1.   `rnn_decoder.pt`, the saved version of your `rnn_decoder`
# 1.   `transformer_encoder.pt`, the saved version of your `transformer_encoder`
# 1.   `transformer_decoder.pt`, the saved version of your `transformer_decoder`

# In[320]:


### DO NOT EDIT ###

import pickle


# In[323]:


### DO NOT EDIT ###

if __name__=='__main__':
    #from google.colab import drive
    #drive.mount('/content/drive')
    print()
    if rnn_encoder is not None and rnn_encoder is not None:
        print("Saving RNN model....") 
        torch.save(rnn_encoder, 'drive/My Drive/rnn_encoder.pt')
        torch.save(rnn_decoder, 'drive/My Drive/rnn_decoder.pt')
        #torch.save(rnn_encoder, 'rnn_encoder.pt')
        #torch.save(rnn_decoder, 'rnn_decoder.pt')
    if transformer_encoder is not None and transformer_decoder is not None:
        print("Saving Transformer model....") 
        torch.save(transformer_encoder, 'drive/My Drive/transformer_encoder.pt')
        torch.save(transformer_decoder, 'drive/My Drive/transformer_decoder.pt')
        #torch.save(transformer_encoder, 'transformer_encoder.pt')
        #torch.save(transformer_decoder, 'transformer_decoder.pt')
        
        


# In[ ]:




