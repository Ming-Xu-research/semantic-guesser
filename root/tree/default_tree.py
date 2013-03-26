""" Left child, right sibling tree.
Inspired by Cormen's Introduction to Algorithms 3rd edition (p. 247).

@author: Rafa

"""

from abstract import Tree, TreeNode
import json
from math import log


class DefaultTreeNode (TreeNode):
    
    def __init__(self, key):
        self.leftchild    = None
        self.rightsibling = None
        self.key          = key
        self.value        = 0
        self._entropy     = 0
    
    def __str__(self):
        return self.key
    
    def print_nested(self, indent_level):
        s = indent_level*'\t' + self.key + ' ' + str(self.value) +  '\n'
        for c in self.children():
            s += c.print_nested(indent_level + 1)
        return s
        
    def children(self):
        children = list()
        c = self.leftchild # c is the current child
        # moving to the right until the last child
        while c is not None :
            children.append(c)
            c = c.rightsibling
        return children
    
    def insert(self, key=None, node=None):
        '''Inserts a child to this node.
        If it already exists, do nothing...
        In both cases, returns the child.
        '''
        newchild = DefaultTreeNode(key) if key is not None else node
        
        if self.leftchild is None :
            self.leftchild = newchild
        else :
            c = self.leftchild # c is the current child
            
            while True:
                # if key is already there, do nothing
                if c.key == key :
                    #c.value += 1
                    return c
                if c.rightsibling is None : # if reached the last child
                    # add the key as right sibling of the last child
                    c.rightsibling = newchild
                    break
                    
                c = c.rightsibling # moving to the right
        
        return newchild 
    
    def child (self, key):
        """Returns the child corresponding to the key
        or None. 
        """
        c = self.leftchild # current child
        while c is not None :
            if c.key == key :
                return c
            else :
                c = c.rightsibling
        return None
    
    def entropy(self):
        self._entropy = 0
        total = self.value
        
        for c in self.children():
            p = float(c.value)/total
            self._entropy -= p * log(p,2)
        
        return self._entropy
     
    def leaves(self):
        count = 0
        for c in self.children():
            if c.is_leaf():
                count += 1
            else:
                count += c.leaves()

        return count
    
    def wrap(self):
        """ Returns a representation of this node (including all children)
        as a single object, JSON-style.
        """
        children = list()
        for child in self.children() :
            children.append(child.wrap())
        if len(children) == 0 :
            return {'key': self.key, 'value': self.value}
        else :    
            return {'key': self.key, 'value': self.value, 
                    'children': children, 'entropy': self._entropy}
            
    def __repr__(self):
        return self.__str__()


class DefaultTree (Tree):
    
    def __init__(self):
        self.root = DefaultTreeNode('root')
        self.root.value = 0
        
    def insert(self, path, freq=1):
        """Insert a subtree.
        Increments the value of the last node (leaf in this path), 
        regardless it will be a leaf in this tree.
        
        Args:
            path: a list of keys, from root to leaf, e.g.:
                ['connect', 'join', 'copulate', 'sleep_together']
            freq: frequency of the leaf    
        """

        currNode = self.root
        
        # insert all keys into the tree, increasing their value
        for key in path :
            currNode.value += freq
            currNode = currNode.insert(key=key)
        
        # increments the count of the leaf
        currNode.value += freq

    def updateEntropy(self, node=None):
        """ The __entropy of the nodes is not updated
        every time the structure changes cause it can be
        too expensive. You need to update this attribute
        manually by calling this method.
        
        """
        if node is None:
            self.updateEntropy(self.root)
        else:
            node.entropy() # calculates entropy
            for c in node.children():
                self.updateEntropy(c)

    def toJSON(self):   
        return json.dumps(self.root.wrap())
    

#tree = DefaultTree()
#tree.insert(['object', 'automobile', 'car'])
#tree.insert(['object', 'automobile', 'truck'])
#tree.insert(['house'])
#tree.insert(['building'])
#tree.insert(['car'])
#tree.insert(['six'])
#tree.insert(['seven'])
#tree.insert(['eight'])
#tree.insert(['nine'])
#tree.insert(['ten'])
#tree.updateEntropy()
#print tree.toJSON()