from ticclat.utils import set_logger
from ticclat.ingest import elex, gb, opentaal, sonar, inl, sgd, edbo, \
    twente_spelling_correction_list, dbnl, morph_par

import logging


logger = logging.getLogger(__name__)


all_sources = {
    'twente': twente_spelling_correction_list,
    'inl': inl,
    'SoNaR500': sonar,
    'elex': elex,
    'groene boekje': gb,
    'OpenTaal': opentaal,
    'sgd': sgd,
    'edbo': edbo,
    'dbnl': dbnl,
    'morph_par': morph_par
}


def ingest_all(session, base_dir='/data',
               include=[], exclude=[], **kwargs):
    if len(include) > 0 and len(exclude) > 0:
        raise Exception("ingest_all: Don't use include and exclude at the same time!")
    elif len(include) > 0:
        sources = {k: all_sources[k] for k in include}
    elif len(exclude) > 0:
        sources = {k: v for k, v in all_sources.items() if k not in exclude}
    else:
        sources = all_sources

    for name, source in sources.items():
        logger.info('ingesting ' + name + '...')
        source.ingest(session, base_dir=base_dir, **kwargs)


def run(env=".env", reset_db=False,
        alphabet_file="/data/ALPH/nld.aspell.dict.clip20.lc.LD3.charconfus.clip20.lc.chars",
        batch_size=5000, include=[], exclude=[], ingest=True, anahash=True,
        tmpdir="/data/tmp", loglevel="INFO", reset_anahashes=False, **kwargs):
    # Read information to connect to the database and put it in environment variables
    import os
    from ticclat.dbutils import create_ticclat_database, get_session_from_env, update_anahashes, session_scope, load_envvars_file
    from ticclat.ticclat_schema import Anahash

    from tqdm import tqdm
    import tempfile

    set_logger(loglevel)

    tempfile.tempdir = tmpdir

    load_envvars_file(env)

    if reset_db:
        logger.info(f'Reseting database "{os.environ["dbname"]}".')
        create_ticclat_database(delete_existing=True, dbname=os.environ['dbname'],
                                user=os.environ['user'], passwd=os.environ['password'],
                                host=os.environ['host'])

    Session = get_session_from_env()

    if ingest:
        ingest_all(Session, batch_size=batch_size, include=include,
                   exclude=exclude, **kwargs)

    if reset_anahashes:
        logger.info("removing all existing anahashes...")
        with session_scope(Session) as session:
            num_rows_deleted = session.query(Anahash).delete()
        logger.info(f"removed {num_rows_deleted} anahashes")

    if anahash:
        logger.info("adding anahashes...")
        with session_scope(Session) as session:
            update_anahashes(session, alphabet_file, tqdm, batch_size)
