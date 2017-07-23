"""
Provides a class to read and write passwords and their attributes to the database,
and functions to retrieve other information from the db, such as dictionary words.
Created on Feb 24, 2012

@author: Rafa
"""

import MySQLdb.cursors
# import pymysql.cursors
import threading
import query
import random
import util
from timer import Timer

def connection():
    credentials = util.dbcredentials()
    return MySQLdb.connect(host = credentials["host"],  # your host, usually localhost
                 user = credentials["user"],   # your username
                 passwd = credentials["password"],  # your password
                 db = "passwords",
                 cursorclass = MySQLdb.cursors.SSDictCursor)  # stores result in the server. records as dict

def names():
    cursor = connection().cursor()
    cursor.execute(query.names)
    return [row['dict_text'] for row in cursor.fetchall()]


class PwdDb():
    """ A few notes:
    Caching is implemented for saving and reading.
    @params:
        test       - Optional : if None get all passwords within password set.
                                If True of False, filter by test.
        samplesize - Optional : fetches a limited sample. The MySQLDb docs mention:
                                "you MUST retrieve the entire result set and
                                close() the cursor before additional queries can be
                                peformed on the connection." If you don't retrieve
                                the entire result set before calling finish(), it
                                will take forever to close the connection.
        random - Optional : fetch a random list of @samplesize length.
    """

    def __init__(self, pwset_id, samplesize=None, random=False, save_cachesize=100000, \
        offset=0, exceptions=None, test=None):

        self.savebuffer_size = save_cachesize
        self.readbuffer_size = 100000
        self.pwset_id = pwset_id
        self.pwset_size = self.pwset_size()
        self.test = test
        self.readbuffer = []
        self.savebuffer  = []
        self.row = None        # holds the next row to be retrieved by nextPwd(),
        self.readpointer = -1  # always points to the last row read from readbuffer by fetchone.
        self.random_ids = []
        self.samplesize = samplesize

        # different connections for reading and saving
        self._init_read_cursor(pwset_id, offset, samplesize, random, exceptions, test)
        self._init_save_cursor()

    def _init_read_cursor(self, pwset_id, offset, samplesize, random, exceptions, test):
        self.conn_read = connection()
        self.readcursor = self.conn_read.cursor()

        self.random_ids = None
        if random:
            extent = self.id_extent_parsed(pwset_id) # min and max pass_id to sample from
            self.random_ids = self.random_sample(extent[0], extent[1], samplesize)
            samplesize = None # already used to draw random ids

        print 'Fetching password segments...'
        self.readcursor.execute(query.segments(pwset_id, samplesize,
            offset, self.random_ids, exceptions))
        print 'Password segments fetched.'

        # fetching the first password
        self.fill_buffer()
        self.row = self.fetchone()

    def is_sample(self):
        return bool(self.samplesize)

    def sample_ids(self):
        """The ids of sampled passwords"""
        return self.random_ids

    def pwset_size(self):
        # getting number of 'sets' (or segments)
        cur = connection().cursor()
        cur.execute(query.pwset_size(self.pwset_id))
        size = cur.fetchone()["count"]
        cur.close()

        return size


    def fill_buffer(self):
        self.readbuffer  = self.readcursor.fetchmany(self.readbuffer_size)
#         self.readbuffer  = [self.readcursor.fetchone()]
        self.readpointer = -1

    def fetchone(self):
        try:
            self.readpointer += 1
            return self.readbuffer[self.readpointer]
        except:
            #print "Refilling buffer..."
            self.fill_buffer()
            if len(self.readbuffer) < 1:
                self.readcursor.close()
                return None
            else:
                self.readpointer += 1
                return self.readbuffer[self.readpointer]

    def random_sample(self, min, max, size):
        return random.sample(range(min, max), size)

    def id_extent_parsed(self, pwset_id):
        """ Returns the minimum and maximum pass_id (that have been parsed)
        from a group of passwords (determined by pwset_id). If no passwords have been parsed
        from the group, this will return (None, None).

        returns a tuple for the form (min, max)
        """
        c = self.conn_read.cursor()
        c.execute(query.extent_parsed(pwset_id))
        first_record = c.fetchone()
        max = first_record['max']
        min = first_record['min']
        return min, max

    def _init_save_cursor(self):
        self.conn_save = connection()
        self.savecursor = self.conn_save.cursor()


    def nextPwd(self):
        if self.row is None:
            return None

        pwd_id = old_pwd_id = self.row["set_id"]
        pwd = []

        while pwd_id == old_pwd_id:
            f = Fragment(self.row["set_contains_id"], self.row["dictset_id"],
                self.row["dict_text"], self.row["pos"], self.row["pass_text"],
                self.row["s_index"], self.row["e_index"], self.row["test"])

            pwd.append(f)

            self.row = self.fetchone()
            if self.row is None:
                break
            else:
                pwd_id = self.row["set_id"]

        return pwd

    def save(self, wo, cache=False):
        if cache:
            self.savebuffer.append((wo.pos, wo.id))
            if len(self.savebuffer) >= self.savebuffer_size:
                self.flush_save()
        else:
            self.savecursor.execute("UPDATE set_contains set pos=%s, where id=%s;",
                (wo.pos, wo.id))

#    def flush_save(self):
#        print "updating {} records on the database...".format(len(self.savsave_buffer#
#    u = Updater("UPDATE set_contains set pos=%s, sentiment=%s, synset=%s where id=%s;",
# self.savesave_bufferf.cachelimit, self.conn_save, self.savecursor)
#        u.start()

    def flush_save (self):
        print "updating {} records on the database...".format(len(self.savebuffer))

        self.conn_save.ping(True) # if connection has died, ressurect it

        util.set_innodb_checks(self.savecursor, False)

        self.savecursor.executemany("UPDATE set_contains set pos=%s where id=%s;",
                                    self.savebuffer)
        self.conn_save.commit()

        util.set_innodb_checks(self.savecursor, True)

        self.savebuffer = []

    def saveCategory(self, wo):
        self.savecursor.execute("UPDATE set_contains set pos=%s where id=%s;",
                             (wo.pos, wo.id))

    def hasNext(self):
        return self.row is not None

    def finish(self):
        if len(self.savebuffer) > 0:
            self.flush_save()
        self.readcursor.close()
        self.savecursor.close()
        self.conn_save.close()
        self.conn_read.close()


class Fragment():

    def __init__(self, ident, dictset_id, word, pos=None,
                password=None, s_index=None, e_index=None,
                test=None):
        self.id = ident
        self.dictset_id = dictset_id
        self.word = word
        self.pos = pos
        self.password = password
        self.s_index = s_index
        self.e_index = e_index
        self.test = test

    def __str__(self):
        return self.word

    def __repr__(self):
        return self.word

    def is_gap(self):
        return self.dictset_id > 90


def word_freqdist(pwset_id):
    conn = connection()
    cur  = conn.cursor()
    query = """SELECT dictset_id, dict_text, pos, count FROM dictionary
        RIGHT JOIN
            (SELECT dict_id, pos, count(*) AS count FROM set_contains
                WHERE pwset_id = {}
                GROUP BY set_contains.dict_id, pos) sub
        ON sub.dict_id = dictionary.dict_id;""".format(pwset_id)
    cur.execute()


class WordFreqIterator():
    def __init__(self, pwset_id, subset=None):
        self.conn = connection()
        self.cur  = self.conn.cursor()
        self.pwset_id = pwset_id

        if subset:
            query = """SELECT dictset_id, dict_text, pos, count FROM dictionary
                RIGHT JOIN
                    (SELECT dict_id, pos, count(*) AS count FROM set_contains
                        JOIN sets ON sets.set_id = set_contains.set_id
                        WHERE set_contains.pwset_id = {}
                        AND pass_id in ({})
                        GROUP BY set_contains.dict_id, pos) sub
                ON sub.dict_id = dictionary.dict_id""" \
                .format(pwset_id, str(subset)[1:-1])
        else:
            query = """SELECT dictset_id, dict_text, pos, count FROM dictionary
                RIGHT JOIN
                    (SELECT dict_id, pos, count(*) AS count FROM set_contains
                        WHERE pwset_id = {}
                        GROUP BY set_contains.dict_id, pos) sub
                ON sub.dict_id = dictionary.dict_id""".format(pwset_id)

        self.cur.execute(query)

    def __iter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        self.cur.close()
        self.conn.close()
        return True


    def next(self):
        row = self.cur.fetchone()
        if row is None:
            raise StopIteration
        else:
            return (row['dict_text'], row['pos'], row['count'], row['dictset_id'])

#db = PwdDb(1)
#i = 0
#with Timer("iterating"):
#    while db.hasNext():
#        i += 1
#        if i % 1000000 == 0:
#            print "{} passwords have been read...".format(i)
#        db.nextPwd()


#pos = 'a'
#senti = None
#synsets = None
#id = 1
#
#wo = Fragment(id, "rafa", pos, senti, synsets)
#db.save(wo)
#db.finish()
#db = PwdDb()

#print names()
