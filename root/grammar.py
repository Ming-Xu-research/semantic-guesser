#!/usr/bin/env python

"""
This script generates a context-free grammar
that captures the semantic patterns of a list of
passwords.

It's based on Weir (2009)*.

*http://dl.acm.org/citation.cfm?id=1608146

Created on Apr 18, 2013

"""
from database import Fragment

__author__ = 'rafa'

import database
import semantics
from cut import wagner
import sys
import traceback
from nltk.probability import FreqDist, ConditionalFreqDist
from timer import Timer
import re
import argparse
import shutil
import os

#-----------------------------------------
# Initializing module variables
#-----------------------------------------

nouns_tree = None
verbs_tree = None
node_index = None

def select_treecut(pwset_id):
    global nouns_tree, verbs_tree, node_index

    nouns_tree = semantics.load_semantictree('n', pwset_id)
    verbs_tree = semantics.load_semantictree('v', pwset_id)
    
    cut = wagner.findcut(nouns_tree, 5000)
    for c in cut: c.cut = True
    
    cut = wagner.findcut(verbs_tree, 5000)
    for c in cut: c.cut = True
    
    flat = nouns_tree.flat() + verbs_tree.flat()
    
    node_index = dict()
    for node in flat:
        if node.key not in node_index:
            node_index[node.key] = node 

#-------------------------------------------

class DictionaryTag:
    map = {10: 'month',
           20: 'fname',
           30: 'mname',
           40: 'surname',
           50: 'country',
           60: 'city',
           200: 'number',
           201: 'num+special',
           202: 'special',
           203: 'char',
           204: 'all_mixed'}
    
    _gaps = None
    
    @classmethod
    def get(cls, id):
        return DictionaryTag.map[id] if id in DictionaryTag.map else None
    
    @classmethod
    def gaps(cls):
        if not DictionaryTag._gaps:
            DictionaryTag._gaps = [ v for k, v in DictionaryTag.map.items() if DictionaryTag.is_gap(k)]
    
        return DictionaryTag._gaps
    
    @classmethod
    def is_gap(cls, id):
        return id > 90


def generalize(synset):
    """ Generalizes a synset based on a tree cut. """

    if synset.pos not in ['v', 'n']:
        return None

    # an internal node is split into a node representing the class and other
    # representing the sense. The former's name starts with 's.'
    key = synset.name if is_leaf(synset) else 's.' + synset.name
    
    try:    
        node = node_index[key]
    except KeyError:
        sys.stderr.write("{} could not be generalized".format(key))
        return None
    
    path = node.path()
    
    # given the hypernym path of a synset, selects the node that belongs to the cut
    for parent in path:
        if parent.cut:
            return parent.key
        

def is_leaf(synset):
    return not bool(synset.hyponyms())


def refine_gap(segment):
    return DictionaryTag.map[segment.dictset_id] + str(len(segment.word))


def classify(segment):

    if DictionaryTag.is_gap(segment.dictset_id):
        tag = refine_gap(segment)
    elif segment.pos in ['np', 'np1', 'np2', None] and segment.dictset_id in DictionaryTag.map:
        tag = DictionaryTag.map[segment.dictset_id]
    else:
        synset = semantics.synset(segment.word, segment.pos)
        # only tries to generalize verbs and nouns
        if synset is not None and synset.pos in ['v', 'n']:
            # TODO: sometimes generalize is returning None. #fixit 
            tag = '{}_{}'.format(segment.pos, generalize(synset)) 
        else:
            tag = segment.pos

    return tag


def stringify_pattern(tags):
    return ''.join(['({})'.format(tag) for tag in tags])


def pattern(segments):
    return stringify_pattern([classify(s) for s in segments])


def sample(db):
    """ I wrote this function to output data for a table
    that shows words, the corresponding synsets, and their generalizations."""
    
    while db.hasNext():
        segments = db.nextPwd()
        for s in segments:
            tag = classify(s)
            if re.findall(r'.+\..+\..+', tag): # test if it's a synset
                synset = semantics.synset(s.word, s.pos)
            else:
                synset = None
            print "{}\t{}\t{}\t{}".format(s.password, s.word, tag, synset)


def expand_gaps(segments):
    """
    If the password has segments of the type "MIXED_ALL" or "MIXED_NUM_SC",
    break them into "alpha", "digit" and "symbol" segments.
    This function provides more resolution in the treatment of non-word segments.
    This should be done in the parsing phase, so this is more of a quick fix.
    """
    temp = []
    
    for s in segments:
        if s.dictset_id == 204 or s.dictset_id == 201:
            temp += segment_gaps(s.word)
        else:
            temp.append(s)
    
    return temp


def segment_gaps(pwd):
    """
    Segments a string into alpha, digit and "symbol" fragments.
    """
    regex = r'\d+|[a-zA-Z]+|[^a-zA-Z0-9]+'
    segments = re.findall(regex, pwd)
    segmented = []
    for s in segments:
        if s[0].isalpha():
            f = Fragment(0, 203, s)
        elif s[0].isdigit():
            f = Fragment(0, 200, s)
        else:
            f = Fragment(0, 202, s) 
        
        segmented.append(f)
    
    return segmented    
        

def main(db, pwset_id):
    # tags_file = open('grammar/debug.txt', 'w+')
    
    patterns_dist = FreqDist()  # distribution of patterns
    segments_dist = ConditionalFreqDist()  # distribution of segments, grouped by semantic tag
    
    counter = 0
    
    while db.hasNext():
        segments = db.nextPwd()
        password = ''.join([s.word for s in segments])
        tags = []

        segments = expand_gaps(segments)
        
        for s in segments:  # semantic tags
            tag = classify(s)
            tags.append(tag)
            segments_dist[tag].inc(s.word)
            
        pattern = stringify_pattern(tags)
        
        patterns_dist.inc(pattern)
        
        # outputs the classification results for debugging purposes
        # for i in range(len(segments)):
        #     tags_file.write("{}\t{}\t{}\t{}\n".format(password, segments[i].word, tags[i], pattern))

        counter += 1
        if counter % 100000 == 0:
            print "{} passwords processed so far ({:.2%})... ".format(counter, float(counter)/db.sets_size)
         
#     tags_file.close()

    pwset_id = str(pwset_id)
    
    # remove previous grammar
    try:
        shutil.rmtree(os.path.join('grammar', pwset_id))
    except OSError: # in case the above folder does not exist 
        pass
    
    # recreate the folders empty
    os.makedirs(os.path.join('grammar', pwset_id, 'nonterminals'))

    with open(os.path.join('grammar', pwset_id, 'rules.txt'), 'w+') as f:
        total = patterns_dist.N()
        for pattern, freq in patterns_dist.items():
            f.write('{}\t{}\n'.format(pattern, float(freq)/total))
    
    for tag in segments_dist.keys():
        total = segments_dist[tag].N()
        with open(os.path.join('grammar', pwset_id, 'nonterminals', tag+'.txt'), 'w+') as f:
            for k, v in segments_dist[tag].items():
                f.write("{}\t{}\n".format(k, float(v)/total))


def options():
    parser = argparse.ArgumentParser()
    
    parser.add_argument('password_set', default=1, type=int, help='the id of the collection of passwords to be processed')

    parser.add_argument('-s', '--sample', default=None, type=int, help="Sample size")
    parser.add_argument('-d', '--dryrun', action='store_true', help="Does not override the grammar folder. "
                                                                    "Enables the verbose mode.")

    # db_group = parser.add_argument_group('Database Connection Arguments')
    # db_group.add_argument('--user', type=str, default='root', help="db username for authentication")
    # db_group.add_argument('--pwd',  type=str, default='', help="db pwd for authentication")
    # db_group.add_argument('--host', type=str, default='localhost', help="db host")
    # db_group.add_argument('--port', type=int, default=3306, help="db port")

    return parser.parse_args()


# TODO: Option for online version (calculation of everything on the fly) and from db
if __name__ == '__main__':
    opts = options()
    
    select_treecut(opts.password_set)

    try:
        with Timer('grammar generation'):
            #db = PwdDb(sample=10000, random=True)
            db = database.PwdDb(opts.password_set, sample=opts.sample)
            try:
                main(db, opts.password_set)
#                sample(db)
            except KeyboardInterrupt:
                db.finish()
                raise
    except:
        e = sys.exc_info()[0]
        traceback.print_exc()
        sys.exit(1)
