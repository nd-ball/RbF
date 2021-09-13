'''
This code demonstrates how RbF (see below) can be used to train any
neural network. RbF is inspired by the broad evidence in psychology
that shows human ability to retain information improves with repeated 
exposure and exponentially decays with delay since last exposure. It 
works based on spaced repetition in which training instances are 
repeatedly presented to the network on a schedule determined by a spaced 
repetition algorithm. RbF shorten or lengthen review intervals for 
training instances with respect to loss of instances and current 
performance of network on validation data.

To use this code, you just need to load your data (lines 47-56), design
your favorite network architecture (lines 61-67), and choose the type of
training paradigm you'd like to use (lines 77-83 for standard training 
and lines 88-96 for Rbf). If you are using only one of these training
paradigms, edit/comment out lines 101-107.  

https://scholar.harvard.edu/hadi/RbF 
Please see the above address for most recent update on RbF. 

Citation
Amiri, et al., Repeat before Forgetting: Spaced Repetition for Efficient 
and Effective Training of Neural Networks. EMNLP 2017.

Contact
Hadi Amiri


9/2021: forked for BERT experiments
'''

import numpy as np
import time

from rbf_keras.preprocessing import sequence
from rbf_keras.models import Sequential
from rbf_keras.layers import Dense, Activation, Embedding
from rbf_keras.layers import LSTM
from rbf_keras.datasets import imdb
from rbf_keras.models import load_model

import tensorflow as tf
from datasets import load_dataset
from transformers import AutoTokenizer, TFAutoModelForSequenceClassification




# PART 0. parameters setting
## Set parameters based on your network architecture. 
nb_epoch = 10 # number of training iterations
max_features = 1000 # max number of features to use
maxlen = 100  # cut texts after this number of words
hidden_size = 4 # size of hidden layer! 
embedding_dims = 4 # size of embedding layer
batch_size = 1 # batch size. Greater values treat all instances in a batch similarly for scheduling.


# PART 1. load some data 
print('Loading data...')
#(X_train, y_train), (X_test, y_test) = imdb.load_data(nb_words=max_features)
#print(len(X_train), 'train sequences')
#print(len(X_test), 'test sequences')
#print('Pad sequences (samples x time)')
#X_train = sequence.pad_sequences(X_train, maxlen=maxlen)
#X_test = sequence.pad_sequences(X_test, maxlen=maxlen)
#print('X_train shape:', X_train.shape)
#print('X_test shape:', X_test.shape)

datasets = load_dataset('glue', 'mrpc')
tokenizer = AutoTokenizer.from_pretrained("bert-base-cased")


def tokenize_function(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True)

tokenized_datasets = datasets.map(tokenize_function, batched=True)

full_train_dataset = tokenized_datasets["train"]
full_eval_dataset = tokenized_datasets["test"]

tf_train_dataset = full_train_dataset.remove_columns(["text"]).with_format("tensorflow")
tf_eval_dataset = full_eval_dataset.remove_columns(["text"]).with_format("tensorflow")


train_features = {x: tf_train_dataset[x].to_tensor() for x in tokenizer.model_input_names}
train_tf_dataset = tf.data.Dataset.from_tensor_slices((train_features, tf_train_dataset["label"]))
train_tf_dataset = train_tf_dataset.shuffle(len(tf_train_dataset)).batch(8)

eval_features = {x: tf_eval_dataset[x].to_tensor() for x in tokenizer.model_input_names}
eval_tf_dataset = tf.data.Dataset.from_tensor_slices((eval_features, tf_eval_dataset["label"]))
eval_tf_dataset = eval_tf_dataset.batch(8)



# PART 2. create a neural network
print('Build model...')
model = TFAutoModelForSequenceClassification.from_pretrained("bert-base-cased", num_labels=2)


#model = Sequential()
#model.add(Embedding(max_features, embedding_dims))
#model.add(LSTM(hidden_size))  # try using a GRU instead, for fun
#model.add(Dense(1))
#model.add(Activation('sigmoid'))  # sigmoid works better for binary classification  
#model.compile(loss='binary_crossentropy', optimizer='adam', metrics=['accuracy'])
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=5e-5),
    loss=tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True),
    metrics=tf.metrics.SparseCategoricalAccuracy(),
)

# PART 3. save the model
model.save('my_model.h5') 
del model 


# PART 4. load the model and train it with standard training 
print('-------------------------------')
print('rote or standard training')
model = load_model('my_model.h5')
start = time.time()
history = model.fit(train_tf_dataset, batch_size=batch_size, nb_epoch=nb_epoch, validation_data=eval_tf_dataset)
rote_time = time.time() - start
del model


# PART 5. load the model and train it with rbf kernels 
print('-------------------------------')
kern = 'gau' # type of kernel function, it could be any kernel in ['gau', 'lap', 'lin', 'cos', 'qua', 'sec'] which represent gaussian, laplace, linear, cosine, quadratic, and secant functions respectively
nu = 0.5  # recall confidence, RbF scheduler estimates the maximum delay such that instances can be recalled with this confidence in the future iterations, nu takes a value in (0,1)  
print('rbf training with kern = ', kern, ', nu = ', nu)             
model = load_model('my_model.h5')
start = time.time()
history, tipe = model.fit(train_tf_dataset, batch_size=batch_size, nb_epoch=nb_epoch, validation_data=eval_tf_dataset, kern=kern, nu=nu)
rbf_time = time.time() - start
del model


# PART 6. compare the rbf and standard training 
print('===============================')
print('rote time(sec)', '{0:.3f}'.format(rote_time))
print('rbf time(sec)', '{0:.3f}'.format(rbf_time))

print('rbf stats')
print ('{0:.3f}'.format(rote_time / float(rbf_time)) , 'times faster than standard training')            
print('{0:.3f}'.format(1. - tipe), ' less data per epoch than standard training')
