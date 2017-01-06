

names = "SELECT dict_text FROM dictionary where dictset_id = 20 or dictset_id = 30;"


def segments(pwset_id, limit, offset, pass_ids=None, exception=None):
    """ Returns all the segments.

	@params:
    pwset_id  - the id of the password set to be gathered (Int)
    limit     - a limit on the number of records (Int)
    offset    - number of records to skip (Int)
    pass_ids  - list of password ids whose segments will be fetched (List(Int))
    exception - list of password ids to be ignored (List(int))

    """

    q = "SELECT sets.set_id AS set_id, "\
        "set_contains.id AS set_contains_id, dict_text, dictset_id, "\
        "pos, sentiment, synset, category, dictset_id, pass_text, s_index, e_index "\
        "FROM passwords "\
        "JOIN sets on sets.pass_id = passwords.pass_id "\
        "JOIN set_contains ON set_contains.set_id = sets.set_id "\
        "JOIN dictionary ON set_contains.dict_id = dictionary.dict_id "\
        "WHERE passwords.pwset_id = {} ".format(pwset_id)

    if exception:
        q = q + "AND passwords.pass_id NOT IN {} ".format(tuple(exception))

    if pass_ids:
        q = q + "AND sets.pass_id in ({}) ".format(str(pass_ids)[1:-1])
    
    if limit:
        q = q + "LIMIT {} ".format(limit)
    if offset:
        q = q + "OFFSET {} ".format(offset)
    
    #print q
    return q


def n_sets(pwset_id):
    """ Retrieves the number of sets (segmentations) associated with a certain group
    of passwords.

    pwset_id - the id of the target group of passwords
    """

    return "SELECT COUNT(*) as count FROM sets LEFT JOIN passwords on sets.pass_id = passwords.pass_id " \
           "WHERE passwords.pwset_id = {}".format(pwset_id)


def extent_parsed(pwset_id):
    """ Returns the SQL string to query the minimum and maximum pass_id (that have been parsed)
        from a group of passwords (determined by pwset_id). If no passwords have been parsed
        from the group, this query will return empty.
    """
    return "SELECT MAX(p.pass_id) as max, MIN(p.pass_id) as min FROM sets LEFT JOIN passwords p on sets.pass_id = p.pass_id " \
            "WHERE p.pwset_id = {}".format(pwset_id)
