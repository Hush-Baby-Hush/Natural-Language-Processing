# -*- coding: utf-8 -*-
"""â€œhwk2.ipynbâ€çš„å‰¯æœ¬

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1OMjA6RpQt3EwGqWvHikohFtZB4yzWdjg

# CS 447 Homework 2 $-$ Text Clasification with Neural Networks
In this homework, you will build machine learning models to detect the sentiment of movie reviews using the IMDb movie reviews dataset. Specifically, you will implement classifiers based on Convolutional Neural Networks (CNN's) and Recurrent Neural Networks (RNN's).

We highly recommend that you take a look at the PyTorch tutorials before starting this assignment:
<ul>
<li>https://pytorch.org/tutorials/beginner/pytorch_with_examples.html
<li>https://pytorch.org/tutorials/beginner/data_loading_tutorial.html
<li>https://github.com/yunjey/pytorch-tutorial
</ul>

We suggest that you select "GPU" as your runtime type, as this will speed up the training of your models. You can find this by going to <TT>Runtime > Change Runtime Type</TT> and select "GPU" from the dropdown menu.
"""

# Don't import any other libraries
from collections import defaultdict
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils import data
import torchtext 
import random

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

if __name__=='__main__':
    print('Using device:', device)

"""# Step 1: Download the Data
First we will download the dataset using [torchtext](https://torchtext.readthedocs.io/en/latest/index.html), which is a package that supports NLP for PyTorch. The following cell will get you `train_data` and `test_data`. It also does some basic tokenization.

*   To access the list of textual tokens for the *i*th example, use `train_data[i][1]`
*   To access the label for the *i*th example, use `train_data[i][0]`


"""

### DO NOT EDIT ###

def preprocess(review):
    '''
    Simple preprocessing function.
    '''
    res = []
    for x in review.split(' '):
        remove_beg=True if x[0] in {'(', '"', "'"} else False
        remove_end=True if x[-1] in {'.', ',', ';', ':', '?', '!', '"', "'", ')'} else False
        if remove_beg and remove_end: res += [x[0], x[1:-1], x[-1]]
        elif remove_beg: res += [x[0], x[1:]]
        elif remove_end: res += [x[:-1], x[-1]]
        else: res += [x]
    return res

if __name__=='__main__':
    train_data = torchtext.datasets.IMDB(root='.data', split='train')
    train_data = list(train_data)
    train_data = [(x[0], preprocess(x[1])) for x in train_data]
    train_data, test_data = train_data[0:10000] + train_data[12500:12500+10000], train_data[10000:12500] + train_data[12500+10000:], 

    print('Num. Train Examples:', len(train_data))
    print('Num. Test Examples:', len(test_data))

    print("\nSAMPLE DATA:")
    for x in random.sample(train_data, 5):
        print('Sample text:', x[1])
        print('Sample label:', x[0], '\n')

"""# Step 2: Create Dataloader [20 points]

## <font color='red'>TODO:</font> Define the Dataset Class [20 Points]

In the following cell, we will define the <b>dataset</b> class. The dataset contains the tokenized data for your model. You need to implement the following functions: 

*   <b>` build_dictionary(self)`:</b>  <b>[10 points]</b> Creates the dictionaries `idx2word` and `word2idx`. You will represent each word in the dataset with a unique index, and keep track of this in these dictionaries. Use the hyperparameter `threshold` to control which words appear in the dictionary: a training wordâ€™s frequency should be `>= threshold` to be included in the dictionary.

* <b>`convert_text(self)`:</b> Converts each review in the dataset to a list of indices, given by your `word2idx` dictionary. You should store this in the `textual_ids` variable, and the function does not return anything. If a word is not present in the  `word2idx` dictionary, you should use the `<UNK>` token for that word. Be sure to append the `<END>` token to the end of each review.

*   <b>` get_text(self, idx) `:</b> Return the review at `idx` in the dataset as an array of indices corresponding to the words in the review. If the length of the review is less than `max_len`, you should pad the review with the `<PAD>` character up to the length of `max_len`. If the length is greater than `max_len`, then it should only return the first `max_len` words. The return type should be `torch.LongTensor`.

*   <b>`get_label(self, idx) `</b>: Return the value `1` if the label for `idx` in the dataset is `positive`, and should return `0` if it is `negative`. The return type should be `torch.LongTensor`.

*  <b> ` __len__(self) `:</b> Return the total number of reviews in the dataset as an `int`.

*   <b>` __getitem__(self, idx)`:</b> <b>[10 points]</b> Return the (padded) text, and the label. The return type for both these items should be `torch.LongTensor`. You should use the ` get_label(self, idx) ` and ` get_text(self, idx) ` functions here.


<b>Note:</b> You should convert all words to lower case in your functions.

<b>Autograder Hint:</b> Make sure that you use instance variables such as `self.threshold` throughout your code, rather than the global variable `THRESHOLD` (defined later on). The variable `THRESHOLD` will not be known to the autograder, and the use of it within the class will cause an autograder error.
"""

PAD = '<PAD>'
END = '<END>'
UNK = '<UNK>'

class TextDataset(data.Dataset):
    def __init__(self, examples, split, threshold, max_len, idx2word=None, word2idx=None):

        self.examples = examples
        assert split in {'train', 'val', 'test'}
        self.split = split
        self.threshold = threshold
        self.max_len = max_len

        # Dictionaries
        self.idx2word = idx2word
        self.word2idx = word2idx
        if split == 'train':
            self.build_dictionary()
        self.vocab_size = len(self.word2idx)
        
        # Convert text to indices
        self.textual_ids = []
        self.convert_text()

    
    def build_dictionary(self): 
        '''
        Build the dictionaries idx2word and word2idx. This is only called when split='train', as these
        dictionaries are passed in to the __init__(...) function otherwise. Be sure to use self.threshold
        to control which words are assigned indices in the dictionaries.
        Returns nothing.
        '''
        assert self.split == 'train'
        
        # Don't change this
        self.idx2word = {0:PAD, 1:END, 2: UNK}
        self.word2idx = {PAD:0, END:1, UNK: 2}

        ##### TODO #####
        # Count the frequencies of all words in the training data (self.examples)
        # Assign idx (starting from 3) to all words having word_freq >= self.threshold
        # Make sure you call word.lower() on each word to convert it to lowercase

        dic = {}
        for i in range(len(self.examples)):
          for j in range(len(self.examples[i][1])):
            temp = self.examples[i][1][j].lower()
            self.examples[i][1][j] = temp
            dic[temp] = dic.get(temp, 0) + 1
        idx = 3
        for k in dic.keys():
          if dic[k] >= self.threshold:
            self.word2idx[k] = idx
            self.idx2word[idx] = k
            idx += 1
    
    def convert_text(self):
        '''
        Convert each review in the dataset (self.examples) to a list of indices, given by self.word2idx.
        Store this in self.textual_ids; returns nothing.
        '''

        ##### TODO #####
        # Remember to replace a word with the <UNK> token if it does not exist in the word2idx dictionary.
        # Remember to append the <END> token to the end of each review.
        for item in self.examples:
            lower = [x.lower() for x in item[1]]
            idx_ = []
            for word in lower:
                if word in self.word2idx:
                    idx_.append(self.word2idx[word])
                else:
                    idx_.append(self.word2idx['<UNK>'])
            idx_.append(self.word2idx['<END>'])
            self.textual_ids.append(idx_)

    def get_text(self, idx):
        '''
        Return the review at idx as a long tensor (torch.LongTensor) of integers corresponding to the words in the review.
        You may need to pad as necessary (see above).
        '''
        ##### TODO #####
        idx_ = self.textual_ids[idx]
        ans = idx_.copy()
        while len(ans) < self.max_len:
          ans.append(self.word2idx['<PAD>'])

        if len(ans) > self.max_len:
          ans = ans[:self.max_len]


        return torch.LongTensor(ans)



    
    def get_label(self, idx):
        '''
        This function should return the value 1 if the label for idx in the dataset is 'positive', 
        and 0 if it is 'negative'. The return type should be torch.LongTensor.
        '''
        ##### TODO #####
        label = self.examples[idx][0].strip()
        if label == 'pos':
          return torch.squeeze(torch.LongTensor([1]))
        else:
          return torch.squeeze(torch.LongTensor([0]))
        # return None

    def __len__(self):
        '''
        Return the number of reviews (int value) in the dataset
        '''
        ##### TODO #####
        return len(self.examples)
    
    def __getitem__(self, idx):
        '''
        Return the review, and label of the review specified by idx.
        '''
        ##### TODO #####
        idx_ = self.get_text(idx)
        label_ = self.get_label(idx)
        idx_tensor = torch.LongTensor(idx_)
        return idx_tensor, label_

if __name__=='__main__':
    # Sample item
    Ds = TextDataset(train_data, 'train', threshold=10, max_len=150)
    print('Vocab size:', Ds.vocab_size)

    text, label = Ds[random.randint(0, len(Ds))]
    print('Example text:', text)
    print('Example label:', label)

"""# Step 3: Train a Convolutional Neural Network (CNN) [40 points]

## <font color='red'>TODO:</font> Define the CNN Model [20 points]
Here you will define your convolutional neural network for text classification. We provide you with the CNN class, you need to fill in parts of the `__init__(...)` and `forward(...)` functions. Each of these functions is worth 10 points.

We have provided you with instructions and hints in the comments. In particular, pay attention to the desired shapes; you may find it helpful to print the shape of the tensors as you code. It may also help to keep PyTorch documentation open for the modules & functions you are using, since they describe input and output dimensions.
"""

class CNN(nn.Module):
    def __init__(self, vocab_size, embed_size, out_channels, filter_heights, stride, dropout, num_classes, pad_idx):
        super(CNN, self).__init__()
        
        ##### TODO #####
        # Create an embedding layer (https://pytorch.org/docs/stable/generated/torch.nn.Embedding.html)
        #   to represent the words in your vocabulary. Make sure to use vocab_size, embed_size, and pad_idx here.
        self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx= pad_idx)


        # Define multiple Convolution layers (nn.Conv2d) with filter (kernel) size [filter_height, embed_size] based on your 
        #   different filter_heights.
        # Input channels will be 1 and output channels will be out_channels (these many different filters will be trained 
        #   for each convolution layer)
        # If you want, you can store a list of modules inside nn.ModuleList.
        # Note: even though your conv layers are nn.Conv2d, we are doing a 1d convolution since we are only moving the filter 
        #   in one direction
        

        # Create a dropout layer (nn.Dropout) using dropout

        # Define a linear layer (nn.Linear) that consists of num_classes units 


        #   and takes as input the concatenated output for all cnn layers (out_channels * num_of_cnn_layers units)
        self.conv1 = nn.Sequential(
            nn.Conv2d(1, out_channels, (filter_heights[0], embed_size)),
            nn.InstanceNorm2d(out_channels),
            nn.Dropout(dropout),
            nn.ReLU(inplace=True)
        )

        self.conv2 = nn.Sequential(
            nn.Conv2d(1, out_channels, (filter_heights[1], embed_size)),
            nn.InstanceNorm2d(out_channels),
            nn.Dropout(dropout),
            nn.ReLU(inplace=True)
        )

        self.conv3 = nn.Sequential(
            nn.Conv2d(1, out_channels, (filter_heights[2], embed_size)),
            nn.InstanceNorm2d(out_channels),
            nn.Dropout(dropout),
            nn.ReLU(inplace=True)
        )


        self.linear = nn.Sequential(
            nn.Linear(out_channels * 3, 100),
            nn.Dropout(dropout),
            nn.Linear(100, num_classes)
        )


    def forward(self, texts):
        """
        texts: LongTensor [batch_size, max_len]
        
        Returns output: Tensor [batch_size, num_classes]
        """
        ##### TODO #####

        # Pass texts through your embedding layer to convert from word ids to word embeddings
        #   Resulting: shape: [batch_size, max_len, embed_size]
        

        # Input to conv should have 1 channel. Take a look at torch's unsqueeze() function
        #   Resulting shape: [batch_size, 1, MAX_LEN, embed_size]
        
        
        # Pass these texts to each of your conv layers and compute their output as follows:
        #   Your cnn output will have shape [batch_size, out_channels, *, 1] where * depends on filter_height and stride
        #   Convert to shape [batch_size, out_channels, *] (see torch's squeeze() function)
        #   Apply non-linearity on it (F.relu() is a commonly used one. Feel free to try others)
        #   Take the max value across last dimension to have shape [batch_size, out_channels]
        # Concatenate (torch.cat) outputs from all your cnns [batch_size, (out_channels*num_of_cnn_layers)]
        #

        

        # Let's understand what you just did:
        #   Since each cnn is of different filter_height, it will look at different number of words at a time
        #     So, a filter_height of 3 means your cnn looks at 3 words (3-grams) at a time and tries to extract some information from it
        #   Each cnn will learn out_channels number of features from the words it sees at a time
        #   Then you applied a non-linearity and took the max value for all channels
        #     You are essentially trying to find important n-grams from the entire text
        # Everything happens on a batch simultaneously hence you have that additional batch_size as the first dimension

        # Apply dropout
        

        # Pass your output through the linear layer and return its output 
        #   Resulting shape: [batch_size, num_classes]
        

        ##### NOTE: Do not apply a sigmoid or softmax to the final output - done in training method!

        x = self.embedding(texts)
        x = torch.unsqueeze(x, 1)

        x1 = torch.max(torch.squeeze(self.conv1(x), 3), 2)[0]
        x2 = torch.max(torch.squeeze(self.conv1(x), 3), 2)[0]
        x3 = torch.max(torch.squeeze(self.conv1(x), 3), 2)[0]

        output = torch.cat((x1, x2, x3), 1)
        output = self.linear(output)
        return output

"""## Train CNN Model

First, we initialize the train and test <b>dataloaders</b>. A dataloader is responsible for providing batches of data to your model. Notice how we first instantiate datasets for the train and test data, and that we use the training vocabulary for both.

You do not need to edit this cell.
"""

if __name__=='__main__':
    THRESHOLD = 5 # Don't change this
    MAX_LEN = 100 # Don't change this
    BATCH_SIZE = 32 # Feel free to try other batch sizes

    train_Ds = TextDataset(train_data, 'train', THRESHOLD, MAX_LEN)

    train_loader = torch.utils.data.DataLoader(train_Ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, drop_last=True)

    test_Ds = TextDataset(test_data, 'test', THRESHOLD, MAX_LEN, train_Ds.idx2word, train_Ds.word2idx)
    test_loader = torch.utils.data.DataLoader(test_Ds, batch_size=1, shuffle=False, num_workers=1, drop_last=False)


"""Now we provide you with a function that takes your model and trains it on the data.

You do not need to edit this cell. However, you may want to write code to save your model periodically, as Colab connections are not permanent. See the tutorial here if you wish to do this: https://pytorch.org/tutorials/beginner/saving_loading_models.html.
"""

### DO NOT EDIT ###

from tqdm.notebook import tqdm

def train_model(model, num_epochs, data_loader, optimizer, criterion):
    print('Training Model...')
    model.train()
    for epoch in tqdm(range(num_epochs)):
        epoch_loss = 0
        epoch_acc = 0
        for texts, labels in data_loader:
            texts = texts.to(device) # shape: [batch_size, MAX_LEN]
            #print(texts.shape)
            labels = labels.to(device) # shape: [batch_size]

            optimizer.zero_grad()

            output = model(texts)
            acc = accuracy(output, labels)
            
            loss = criterion(output, labels)
            loss.backward()
            optimizer.step()

            epoch_loss += loss.item()
            epoch_acc += acc.item()
        print('[TRAIN]\t Epoch: {:2d}\t Loss: {:.4f}\t Train Accuracy: {:.2f}%'.format(epoch+1, epoch_loss/len(data_loader), 100*epoch_acc/len(data_loader)))
    print('Model Trained!\n')

"""Here are some other helper functions we will need."""

### DO NOT EDIT ###

def count_parameters(model):
    """
    Count number of trainable parameters in the model
    """
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def accuracy(output, labels):
    """
    Returns accuracy per batch
    output: Tensor [batch_size, n_classes]
    labels: LongTensor [batch_size]
    """
    preds = output.argmax(dim=1) # find predicted class
    correct = (preds == labels).sum().float() # convert into float for division 
    acc = correct / len(labels)
    return acc

"""Now you can instantiate your model. We provide you with some recommended hyperparameters; you should be able to get the desired accuracy with these, but feel free to play around with them."""

if __name__=='__main__':
    cnn_model = CNN(vocab_size = train_Ds.vocab_size, # Don't change this
                embed_size = 128, 
                out_channels = 64, 
                filter_heights = [2, 3, 4], 
                stride = 1, 
                dropout = 0.5, 
                num_classes = 2, # Don't change this
                pad_idx = train_Ds.word2idx[PAD]) # Don't change this


    # Put your model on the device (cuda or cpu)
    cnn_model = cnn_model.to(device)
    
    print('The model has {:,d} trainable parameters'.format(count_parameters(cnn_model)))

"""Next, we create the **criterion**, which is our loss function: it is a measure of how well the model matches the empirical distribution of the data. We use cross-entropy loss (https://en.wikipedia.org/wiki/Cross_entropy).

We also define the **optimizer**, which performs gradient descent. We use the Adam optimizer (https://arxiv.org/pdf/1412.6980.pdf), which has been shown to work well on these types of models.
"""

if __name__=='__main__':    
    LEARNING_RATE = 5e-4 # Feel free to try other learning rates

    # Define the loss function
    criterion = nn.CrossEntropyLoss().to(device)

    # Define the optimizer
    optimizer = optim.Adam(cnn_model.parameters(), lr=LEARNING_RATE)

"""Finally, we can train the model."""

if __name__=='__main__':    
    N_EPOCHS = 20 # Feel free to change this
    
    # train model for N_EPOCHS epochs
    train_model(cnn_model, N_EPOCHS, train_loader, optimizer, criterion)

"""## Evaluate CNN Model [20 points]

Now that we have trained a model for text classification, it is time to evaluate it. We have provided you with a function to do this; you do not need to modify anything.

To pass the autograder for the CNN, you will need to achieve **73% accuracy** on the test set. Note that Gradescope uses a different test set; however, it is very similar, and the accuracies between the two datasets should be comparable.
"""

### DO NOT EDIT ###

import random

def evaluate(model, data_loader, criterion):
    print('Evaluating performance on the test dataset...')
    model.eval()
    epoch_loss = 0
    epoch_acc = 0
    all_predictions = []
    print("\nSOME PREDICTIONS FROM THE MODEL:")
    for texts, labels in tqdm(data_loader):
        texts = texts.to(device)
        labels = labels.to(device)
        
        output = model(texts)
        acc = accuracy(output, labels)
        pred = output.argmax(dim=1)
        all_predictions.append(pred)
        
        loss = criterion(output, labels)
        
        epoch_loss += loss.item()
        epoch_acc += acc.item()

        if random.random() < 0.0015:
            print("Input: "+' '.join([data_loader.dataset.idx2word[idx] for idx in texts[0].tolist() if idx not in {data_loader.dataset.word2idx[PAD], data_loader.dataset.word2idx[END]}]))
            print("Prediction:", pred.item(), '\tCorrect Output:', labels.item(), '\n')

    full_acc = 100*epoch_acc/len(data_loader)
    full_loss = epoch_loss/len(data_loader)
    print('[TEST]\t Loss: {:.4f}\t Accuracy: {:.2f}%'.format(full_loss, full_acc))
    predictions = torch.cat(all_predictions)
    return predictions, full_acc, full_loss

if __name__=='__main__':
    evaluate(cnn_model, test_loader, criterion) # Compute test data accuracy

"""# Step 4: Train a Recurrent Neural Network (RNN) [40 points]
You will now build a text clasification model that is based on **recurrences**.

## <font color='red'>TODO:</font> Define the RNN Model [20 points]

First, you will define the RNN. As with the CNN, we provide you with the skeleton of the class, and you need to fill in parts of the `__init__(...)` and `forward(...)` methods. Each of these functions is worth 10 points.
"""

class RNN(nn.Module):
    def __init__(self, vocab_size, embed_size, hidden_size, num_layers, bidirectional, dropout, num_classes, pad_idx):
      super(RNN, self).__init__()
      self.hidden_size = hidden_size
      self.num_layers = num_layers

        ##### TODO #####
      if bidirectional: 
        direct = 2
      else: 
        direct = 1
        # Create an embedding layer (https://pytorch.org/docs/stable/generated/torch.nn.Embedding.html)
        #   to represent the words in your vocabulary. Make sure to use vocab_size, embed_size, and pad_idx here.
      self.embedding = nn.Embedding(vocab_size, embed_size, padding_idx= pad_idx)
        # Create a recurrent network (use nn.GRU, not nn.LSTM) with batch_first = True
        # Make sure you use hidden_size, num_layers, dropout, and bidirectional here.
      self.rnn = nn.GRU(input_size = embed_size, hidden_size = hidden_size, num_layers = num_classes,batch_first = True, dropout = dropout, bidirectional = bidirectional)
        # Create a dropout layer (nn.Dropout) using dropout


        # Define a linear layer (nn.Linear) that consists of num_classes units 
        #   and takes as input the output of the last timestep. In the bidirectional case, you should concatenate
        #   the output of the last timestep of the forward direction with the output of the last timestep of the backward direction).
      self.linear = nn.Sequential(
          nn.Linear(hidden_size * direct, 100),
          nn.Dropout(dropout),
          nn.Linear(100, num_classes)
      )


    def forward(self, texts):
        """
        texts: LongTensor [batch_size, MAX_LEN]
        
        Returns output: Tensor [batch_size, num_classes]
        """
        ##### TODO #####

        # Pass texts through your embedding layer to convert from word ids to word embeddings
        #   Resulting: shape: [batch_size, max_len, embed_size]
        

        # Pass the result through your recurrent network
        #   See PyTorch documentation for resulting shape for nn.GRU
        
        
        # Concatenate the outputs of the last timestep for each direction (see torch.cat(...))
        #   This depends on whether or not your model is bidirectional.
        #   Resulting shape: [batch_size, num_dirs*hidden_size]
        
        # Apply dropout
        

        # Pass your output through the linear layer and return its output 
        #   Resulting shape: [batch_size, num_classes]
        

        ##### NOTE: Do not apply a sigmoid or softmax to the final output - done in training method!
        
        return None



torch.LongTensor(10*np.ones(10))

torch.LongTensor(100)

"""## Train RNN Model
First, we initialize the train and test dataloaders.
"""

if __name__=='__main__':
    THRESHOLD = 5 # Don't change this
    MAX_LEN = 100 # Don't change this
    BATCH_SIZE = 32 # Feel free to try other batch sizes

    train_Ds = TextDataset(train_data, 'train', THRESHOLD, MAX_LEN)
    train_loader = torch.utils.data.DataLoader(train_Ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, drop_last=True)

    test_Ds = TextDataset(test_data, 'test', THRESHOLD, MAX_LEN, train_Ds.idx2word, train_Ds.word2idx)
    test_loader = torch.utils.data.DataLoader(test_Ds, batch_size=1, shuffle=False, num_workers=1, drop_last=False)

"""Now you can instantiate your model. We provide you with some recommended hyperparameters; you should be able to get the desired accuracy with these, but feel free to play around with them."""

if __name__=='__main__':
    rnn_model = RNN(vocab_size = train_Ds.vocab_size, # Don't change this
                embed_size = 128, 
                hidden_size = 128, 
                num_layers = 2,
                bidirectional = True,
                dropout = 0.5,
                num_classes = 2, # Don't change this
                pad_idx = train_Ds.word2idx[PAD]) # Don't change this

    # Put your model on device
    rnn_model = rnn_model.to(device)

    print('The model has {:,d} trainable parameters'.format(count_parameters(rnn_model)))

"""Here, we create the criterion and optimizer; as with the CNN, we use cross-entropy loss and Adam optimization."""

if __name__=='__main__':    
    LEARNING_RATE = 5e-4 # Feel free to try other learning rates

    # Define your loss function
    criterion = nn.CrossEntropyLoss().to(device)

    # Define your optimizer
    optimizer = optim.Adam(rnn_model.parameters(), lr=LEARNING_RATE)

"""Finally, we can train the model. We use the same `train_model(...)` function that we defined for the CNN."""

if __name__=='__main__':    
    N_EPOCHS = 15 # Feel free to change this
    
    # train model for N_EPOCHS epochs
    train_model(rnn_model, N_EPOCHS, train_loader, optimizer, criterion)

"""## Evaluate RNN Model [20 points]

Now we can evaluate the RNN. 

To pass the autograder for the RNN, you will need to achieve **75% accuracy** on the test set. Note that Gradescope uses a different test set; however, it is very similar, and the accuracies between the two datasets should be comparable.
"""

if __name__=='__main__':    
    evaluate(rnn_model, test_loader, criterion) # Compute test data accuracy

"""# What You Need to Submit

To submit the assignment, download this notebook as a <TT>.py</TT> file. You can do this by going to <TT>File > Download > Download .py</TT>. Then rename it to `hwk2.py`.

You will also need to save the `cnn_model` and `rnn_model`. You can run the cell below to do this. After you save the files to your Google Drive, you need to manually download the files to your computer, and then submit them to the autograder.

You will submit the following files to the autograder:
1.   `hwk2.py`, the download of this notebook as a `.py` file (**not** a `.ipynb` file)
1.   `cnn.pt`, the saved version of your `cnn_model`
1.   `rnn.pt`, the saved version of your `rnn_model`
"""

### DO NOT EDIT ###

if __name__=='__main__':
    from google.colab import drive
    drive.mount('/content/drive')
    print()

    try:
        cnn_model is None
        cnn_exists = True
    except:
        cnn_exists = False

    try:
        rnn_model is None
        rnn_exists = True
    except:
        rnn_exists = False

    if cnn_exists:
        print("Saving CNN model....") 
        torch.save(cnn_model, "drive/My Drive/cnn.pt")
    if rnn_exists:
        print("Saving RNN model....") 
        torch.save(rnn_model, "drive/My Drive/rnn.pt")
    print("Done!")