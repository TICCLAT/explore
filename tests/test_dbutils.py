import pytest
import os
import sqlite3
import shutil

import numpy as np
import pandas as pd

from sqlalchemy import and_

from ticclat.ticclat_schema import Wordform, Lexicon, Anahash, \
    WordformLinkSource, MorphologicalParadigm
from ticclat.utils import read_json_lines, read_ticcl_variants_file
from ticclat.dbutils import bulk_add_wordforms, add_lexicon, \
    get_word_frequency_df, bulk_add_anahashes, \
    connect_anahashes_to_wordforms, update_anahashes, get_wf_mapping, \
    add_lexicon_with_links, write_wf_links_data, add_morphological_paradigms, \
    empty_table, add_ticcl_variants

from . import data_dir


# Make sure np.int64 are inserted into the testing database as integers and
# not binary data.
# Source: https://stackoverflow.com/questions/38753737
sqlite3.register_adapter(np.int64, int)


def test_bulk_add_wordforms_all_new(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wordforms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wordforms) == len(wfs['wordform'])
    assert [wf.wordform for wf in wordforms] == list(wfs['wordform'])


def test_bulk_add_wordforms_some_new(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wfs['wordform'] = ['wf3', 'wf4', 'wf5']
    wfs['wordform_lowercase'] = ['wf3', 'wf4', 'wf4']

    n = bulk_add_wordforms(dbsession, wfs)

    assert n == 2

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 5
    assert [w.wordform for w in wrdfrms] == ['wf1', 'wf2', 'wf3', 'wf4', 'wf5']


def test_bulk_add_wordforms_not_unique(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf1', 'wf2']

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 2


def test_bulk_add_wordforms_whitespace(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1 ', '  wf2', ' ', '    \t']

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 2
    assert wrdfrms[0].wordform == 'wf1'
    assert wrdfrms[1].wordform == 'wf2'


def test_bulk_add_wordforms_drop_empty_and_nan(dbsession):
    wfs = pd.DataFrame()
    wfs["wordform"] = ["wf1", "", "wf2", np.NaN]

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 2
    assert wrdfrms[0].wordform == "wf1"
    assert wrdfrms[1].wordform == "wf2"


def test_bulk_add_wordforms_replace_spaces(dbsession):
    wfs = pd.DataFrame()
    wfs["wordform"] = ["wf 1", "wf2"]

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 2
    assert wrdfrms[0].wordform == "wf_1"
    assert wrdfrms[1].wordform == "wf2"


def test_bulk_add_wordforms_replace_underscores(dbsession):
    wfs = pd.DataFrame()
    wfs["wordform"] = ["wf_1", "wf 2"]

    print(dbsession)

    bulk_add_wordforms(dbsession, wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 2
    assert wrdfrms[0].wordform == "wf*1"
    assert wrdfrms[1].wordform == "wf_2"


def test_add_lexicon(dbsession):
    name = 'test lexicon'

    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    add_lexicon(dbsession, lexicon_name=name, vocabulary=True, wfs=wfs)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert len(wrdfrms) == 3

    lexicons = dbsession.query(Lexicon).all()

    assert len(lexicons) == 1
    assert lexicons[0].lexicon_name == name
    assert len(lexicons[0].lexicon_wordforms) == 3

    wrdfrms = sorted([w.wordform for w in lexicons[0].lexicon_wordforms])
    assert wrdfrms == list(wfs['wordform'])


def test_get_word_frequency_df(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    bulk_add_wordforms(dbsession, wfs)

    freq_df = get_word_frequency_df(dbsession)

    expected = pd.DataFrame({'wordform': ['wf1', 'wf2', 'wf3'],
                             'frequency': [1, 1, 1]}).set_index('wordform')

    assert freq_df.equals(expected)


def test_get_word_frequency_df_empty(dbsession):
    freq_df = get_word_frequency_df(dbsession)

    assert freq_df is None


def test_bulk_add_anahashes(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    bulk_add_wordforms(dbsession, wfs)

    a = pd.DataFrame({'wordform': ['wf1', 'wf2', 'wf3'],
                      'anahash': [1, 2, 3]}).set_index('wordform')

    bulk_add_anahashes(dbsession, a)

    ahs = dbsession.query(Anahash).order_by(Anahash.anahash_id).all()

    print(ahs[0])

    assert [a.anahash for a in ahs] == list(a['anahash'])


def test_connect_anahashes_to_wordforms(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    bulk_add_wordforms(dbsession, wfs)

    wfs = get_word_frequency_df(dbsession, add_ids=True)
    wf_mapping = wfs['wordform_id'].to_dict()

    a = pd.DataFrame({'wordform': ['wf1', 'wf2', 'wf3'],
                      'anahash': [1, 2, 3]}).set_index('wordform')

    bulk_add_anahashes(dbsession, a)

    connect_anahashes_to_wordforms(dbsession, a, wf_mapping)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert [wf.anahash.anahash for wf in wrdfrms] == list(a['anahash'])


def test_connect_anahashes_to_wordforms_empty(dbsession):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    bulk_add_wordforms(dbsession, wfs)

    a = pd.DataFrame({'wordform': ['wf1', 'wf2', 'wf3'],
                      'anahash': [1, 2, 3]}).set_index('wordform')

    bulk_add_anahashes(dbsession, a)

    connect_anahashes_to_wordforms(dbsession, a, a['anahash'].to_dict())

    # nothing was updated the second time around (the values didn't change)
    # (and there is no error when running this)
    connect_anahashes_to_wordforms(dbsession, a, a['anahash'].to_dict())

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert [wf.anahash.anahash for wf in wrdfrms] == list(a['anahash'])


@pytest.mark.skipif(shutil.which('TICCL_anahash') is not None, reason='Install TICCL before testing this.')
@pytest.mark.datafiles(os.path.join(data_dir(), 'alphabet'))
def test_update_anahashes(dbsession, datafiles):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf-a', 'wf-b', 'wf-c']

    alphabet_file = datafiles.listdir()[0]

    bulk_add_wordforms(dbsession, wfs)

    anahashes = dbsession.query(Anahash).order_by(Anahash.anahash_id).all()
    assert len(anahashes) == 0

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()
    for w in wrdfrms:
        assert(w.anahash) is None

    update_anahashes(dbsession, alphabet_file)

    # If we don't commit here, the anahashes won't be updated when we do the
    # tests.
    dbsession.commit()

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()
    anahashes = dbsession.query(Anahash).order_by(Anahash.anahash_id).all()

    # Three anahashes were added
    assert len(anahashes) == 3

    # The anahashes are connected to the correct wordforms
    for wf, a in zip(wrdfrms, (3, 2, 1)):
        assert wf.anahash_id == a


@pytest.mark.skipif(shutil.which('TICCL_anahash') is not None, reason='Install TICCL before testing this.')
@pytest.mark.datafiles(os.path.join(data_dir(), 'alphabet'))
def test_update_anahashes_empty_wf(dbsession, datafiles):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf-a', 'wf-b', 'wf-c', ' ']

    alphabet_file = datafiles.listdir()[0]

    bulk_add_wordforms(dbsession, wfs)

    # make sure ticcl doesn't choke on the empty wordform (it must not be added
    # to the database)
    update_anahashes(dbsession, alphabet_file)


@pytest.mark.datafiles(os.path.join(data_dir(), 'alphabet'))
def test_update_anahashes_nothing_to_update(dbsession, datafiles):
    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    bulk_add_wordforms(dbsession, wfs)

    a = pd.DataFrame({'wordform': ['wf1', 'wf2', 'wf3'],
                      'anahash': [1, 2, 3]}).set_index('wordform')

    bulk_add_anahashes(dbsession, a)

    connect_anahashes_to_wordforms(dbsession, a, a['anahash'].to_dict())
    alphabet_file = datafiles.listdir()[0]
    update_anahashes(dbsession, alphabet_file)

    wrdfrms = dbsession.query(Wordform).order_by(Wordform.wordform_id).all()

    assert [wf.anahash.anahash for wf in wrdfrms] == list(a['anahash'])


def test_get_wf_mapping_lexicon(dbsession):
    name = 'test lexicon'

    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    lex = add_lexicon(dbsession, lexicon_name=name, vocabulary=True, wfs=wfs)

    wf_mapping = get_wf_mapping(dbsession, lexicon=lex)

    for w in wfs['wordform']:
        assert w in wf_mapping.keys()


def test_get_wf_mapping_lexicon_no_id(dbsession):
    name = 'test lexicon'

    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    lex = Lexicon(lexicon_name=name)

    with pytest.raises(ValueError):
        get_wf_mapping(dbsession, lexicon=lex)


def test_get_wf_mapping_lexicon_id(dbsession):
    name = 'test lexicon'

    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3']

    print(dbsession)

    lex = add_lexicon(dbsession, lexicon_name=name, vocabulary=True, wfs=wfs)
    lexicon_id = lex.lexicon_id

    wf_mapping = get_wf_mapping(dbsession, lexicon_id=lexicon_id)

    for w in wfs['wordform']:
        assert w in wf_mapping.keys()


def test_write_wf_links_data(dbsession, fs):
    wfl_file = 'wflinks'
    wfls_file = 'wflsources'

    name = 'linked test lexicon'

    wfs = pd.DataFrame()
    wfs['wordform'] = ['wf1', 'wf2', 'wf3', 'wf1s', 'wf2s', 'wf3s']

    lex = add_lexicon(dbsession, lexicon_name=name, vocabulary=True, wfs=wfs)

    wfs = pd.DataFrame()
    wfs['lemma'] = ['wf1', 'wf2', 'wf3']
    wfs['variant'] = ['wf1s', 'wf2s', 'wf3s']

    wfm = get_wf_mapping(dbsession, lexicon=lex)

    links_file = open(wfl_file, 'w')
    sources_file = open(wfls_file, 'w')

    num_l, num_s = write_wf_links_data(
        dbsession,
        wf_mapping=wfm,
        links_df=wfs,
        wf_from_name='lemma',
        wf_to_name='variant',
        lexicon_id=lex.lexicon_id,
        wf_from_correct=True,
        wf_to_correct=True,
        links_file=links_file,
        sources_file=sources_file,
    )

    links_file.close()
    sources_file.close()

    links_file = open(wfl_file, 'r')
    sources_file = open(wfls_file, 'r')

    assert num_l == 3 * 2
    assert num_s == 3 * 2

    wflinks = []
    for wf1, wf2 in zip(wfs['lemma'], wfs['variant']):
        wflinks.append({"wordform_from": wfm[wf1], "wordform_to": wfm[wf2]})
        wflinks.append({"wordform_from": wfm[wf2], "wordform_to": wfm[wf1]})

    wflsources = []
    for wfl in wflinks:
        wflsources.append({"wordform_from": wfl['wordform_from'],
                           "wordform_to": wfl['wordform_to'],
                           "lexicon_id": lex.lexicon_id,
                           "wordform_from_correct": True,
                           "wordform_to_correct": True})

    for wfls1, wfls2 in zip(read_json_lines(sources_file), wflsources):
        assert wfls1 == wfls2

    links_file.close()
    sources_file.close()


def test_add_lexicon_with_links(dbsession):
    name = 'linked test lexicon'

    wfs = pd.DataFrame()
    wfs['lemma'] = ['wf1', 'wf2', 'wf3']
    wfs['variant'] = ['wf1s', 'wf2s', 'wf3s']

    add_lexicon_with_links(dbsession, lexicon_name=name, vocabulary=True,
                           wfs=wfs, from_column='lemma', to_column='variant',
                           from_correct=True, to_correct=True)

    lex = dbsession.query(Lexicon).filter(Lexicon.lexicon_name == name).first()

    assert lex.vocabulary
    assert len(lex.lexicon_wordforms) == 6

    for w1, w2 in zip(wfs['lemma'], wfs['variant']):
        wf1 = dbsession.query(Wordform).filter(Wordform.wordform == w1).first()
        wf2 = dbsession.query(Wordform).filter(Wordform.wordform == w2).first()

        # check wordform links
        links = [w.linked_to for w in wf1.links]
        assert wf2 in links

        links = [w.linked_to for w in wf2.links]
        assert wf1 in links

        # check wordform link sources
        wfl = dbsession.query(WordformLinkSource) \
            .filter(and_(WordformLinkSource.wordform_from == wf1.wordform_id,
                         WordformLinkSource.wordform_to == wf2.wordform_id)) \
            .first()
        assert wfl is not None
        assert wfl.wfls_lexicon == lex

        wfl = dbsession.query(WordformLinkSource) \
            .filter(and_(WordformLinkSource.wordform_from == wf2.wordform_id,
                         WordformLinkSource.wordform_to == wf1.wordform_id)) \
            .first()
        assert wfl is not None
        assert wfl.wfls_lexicon == lex


def test_add_lexicon_with_links_preprocessing(dbsession):
    name = 'linked test lexicon'

    # Please note that wfs is updated with preprocessed wordforms during
    # add_lexicon_with_links. So, for this test, we don't have to explicitly
    # preprocess wfs.
    wfs = pd.DataFrame()
    wfs['lemma'] = ['wf 1', 'wf_2', 'wf3']
    wfs['variant'] = ['wf1s', 'wf2s', 'wf3s']

    add_lexicon_with_links(dbsession,
                           lexicon_name=name,
                           vocabulary=True,
                           wfs=wfs,
                           from_column='lemma',
                           to_column='variant',
                           from_correct=True,
                           to_correct=True)

    lex = dbsession.query(Lexicon).filter(Lexicon.lexicon_name == name).first()

    assert lex.vocabulary
    assert len(lex.lexicon_wordforms) == 6

    for w1, w2 in zip(wfs['lemma'], wfs['variant']):
        wf1 = dbsession.query(Wordform).filter(Wordform.wordform == w1).first()
        wf2 = dbsession.query(Wordform).filter(Wordform.wordform == w2).first()

        # check wordform links
        links = [w.linked_to for w in wf1.links]
        assert wf2 in links

        links = [w.linked_to for w in wf2.links]
        assert wf1 in links

        # check wordform link sources
        wfl = dbsession.query(WordformLinkSource) \
            .filter(and_(WordformLinkSource.wordform_from == wf1.wordform_id,
                         WordformLinkSource.wordform_to == wf2.wordform_id)) \
            .first()
        assert wfl is not None
        assert wfl.wfls_lexicon == lex

        wfl = dbsession.query(WordformLinkSource) \
            .filter(and_(WordformLinkSource.wordform_from == wf2.wordform_id,
                         WordformLinkSource.wordform_to == wf1.wordform_id)) \
            .first()
        assert wfl is not None
        assert wfl.wfls_lexicon == lex


@pytest.mark.datafiles(os.path.join(data_dir(), 'morph_par.tsv'))
def test_ingest_add_morphological_paradigms(dbsession, datafiles):
    # table morphological paradigms should be empty
    n = dbsession.query(MorphologicalParadigm).count()
    assert n == 0

    add_morphological_paradigms(dbsession, datafiles.listdir()[0])

    # after adding there should be three morpological paradigms
    n = dbsession.query(MorphologicalParadigm).count()
    assert n == 3


@pytest.mark.datafiles(os.path.join(data_dir(), 'morph_par.tsv'))
def test_ingest_add_morp_pars_with_empty_table(dbsession, datafiles):
    # table morphological paradigms should be empty
    n = dbsession.query(MorphologicalParadigm).count()
    assert n == 0

    add_morphological_paradigms(dbsession, datafiles.listdir()[0])
    empty_table(dbsession, MorphologicalParadigm)
    add_morphological_paradigms(dbsession, datafiles.listdir()[0])

    # after adding, emptying, and adding there should be three morpological
    # paradigms
    n = dbsession.query(MorphologicalParadigm).count()
    assert n == 3


# @pytest.mark.datafiles(os.path.join(data_dir(), 'env_no_port'))
# def test_load_envvars_file_no_port(datafiles):
#     load_envvars_file(datafiles.listdir()[0])
#
#     assert os.environ.get('user', None) == 'root'
#     assert os.environ.get('password', None) == '********'
#     assert os.environ.get('host', None) == 'localhost'
#     assert os.environ.get('dbname', None) == 'ticclat'
#     assert os.environ.get('DATABASE_URL',
#                           None) == 'mysql://root:********@localhost/ticclat'


# @pytest.mark.datafiles(os.path.join(data_dir(), 'env_port'))
# def test_load_envvars_file_port(datafiles):
#     load_envvars_file(datafiles.listdir()[0])
#
#     assert os.environ.get('user', None) == 'root'
#     assert os.environ.get('password', None) == '********'
#     assert os.environ.get('host', None) == '127.0.0.1:8008'
#     assert os.environ.get('dbname', None) == 'ticclat'
#     assert os.environ.get(
#         'DATABASE_URL', None) == 'mysql://root:********@127.0.0.1:8008/ticclat'


@pytest.mark.datafiles(os.path.join(data_dir(), 'ticcl_variants.txt'))
def test_add_ticcl_variants(dbsession, datafiles):
    path = str(datafiles)
    variants_file = os.path.join(path, 'ticcl_variants.txt')

    name = 'ticcl variants test corpus'
    df = read_ticcl_variants_file(variants_file)

    add_ticcl_variants(dbsession, name, df)

    lexicon = dbsession.query(Lexicon).first()

    print(lexicon)
    print(lexicon.lexicon_wordforms)
    print(lexicon.lexicon_wordform_links)

    # the lexicon contains 3 wordforms
    assert len(lexicon.lexicon_wordforms) == 3

    # the database contains 3 wordforms
    assert dbsession.query(Wordform).count() == 3

    wf1 = dbsession.query(Wordform).filter(Wordform.wordform == 'wf1').first()
    wflss = dbsession.query(WordformLinkSource).filter(WordformLinkSource.wordform_from == wf1.wordform_id).all()

    assert len(wflss) == 2

    # wf1 is a correct wordform
    # ws1 and wf2 are incorrect
    for link in wflss:
        print(dbsession.query(Wordform).get(link.wordform_from))
        assert link.wordform_from_correct
        print(dbsession.query(Wordform).get(link.wordform_to))
        assert not link.wordform_to_correct

        assert link.ld == 1
