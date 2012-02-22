from tag_util import backoff_tagger
from nltk.tag.sequential import DefaultTagger, BigramTagger, TrigramTagger
from nltk.corpus import treebank
from nltk.tag import UnigramTagger
from nltk.corpus import brown
import csv
from synth_dataset import sentences
from taggers import WordNetTagger

#phrases = [['holiday'],['I', 'love', 'erin'],['better', 'off'],['i', 'love', 'many'],
#           ['punk','rocker'], ['baby', 'love'], ['sex','me'], ['fuck', 'off'],
#           ['kill', 'yourself'], ['fuck', 'hoes']]

phrases = sentences()

train_sents = brown.tagged_sents()
#train_sents = treebank.tagged_sents()

default_tagger = DefaultTagger('KK')

wn_tagger = WordNetTagger(default_tagger)

tagger  = backoff_tagger(train_sents, [UnigramTagger, BigramTagger, TrigramTagger], 
                           backoff=wn_tagger)

for p in phrases :
    print(tagger.tag(p))

