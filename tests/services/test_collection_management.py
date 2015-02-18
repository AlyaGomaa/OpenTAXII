import pytest
import tempfile

from taxii_server.server import TAXIIServer
from taxii_server.options import ServerConfig

from taxii_server.data.sql import SQLDB
from taxii_server.data import DataManager
from taxii_server.taxii import entities

from utils import get_service, prepare_headers, as_tm, persist_content
from fixtures import *

ASSIGNED_SERVICES = ['collection-management-A', 'inbox-A', 'inbox-B', 'poll-A']
ASSIGNED_INBOX_INSTANCES = sum(len(v['protocol_bindings']) \
        for k, v in SERVICES.items() if k in ASSIGNED_SERVICES and k.startswith('inbox'))

@pytest.fixture
def manager():
    db_connection = 'sqlite://' # in-memory DB

    config = ServerConfig(services_properties=SERVICES)
    manager = DataManager(config=config, api=SQLDB(db_connection, create_tables=True))
    return manager


@pytest.fixture()
def server(manager):

    server = TAXIIServer(DOMAIN, data_manager=manager)

    for coll in COLLECTIONS_B:
        coll = manager.save_collection(coll)
        manager.assign_collection(coll.id, services_ids=ASSIGNED_SERVICES)

    return server


def prepare_request(version):
    if version == 11:
        return as_tm(version).CollectionInformationRequest(message_id=MESSAGE_ID)
    else:
        return as_tm(version).FeedInformationRequest(message_id=MESSAGE_ID)


@pytest.mark.parametrize("https", [True, False])
@pytest.mark.parametrize("version", [11, 10])
def test_collections(server, version, https):

    service = get_service(server, 'collection-management-A')

    headers = prepare_headers(version, https)
    request = prepare_request(version)
    response = service.process(headers, request)

    names = [c.name for c in COLLECTIONS_B]
    
    if version == 11:
        assert isinstance(response, as_tm(version).CollectionInformationResponse)
        assert len(response.collection_informations) == len(COLLECTIONS_B)

        for c in response.collection_informations:
            assert c.collection_name in names

    else:
        assert isinstance(response, as_tm(version).FeedInformationResponse)
        assert len(response.feed_informations) == len(COLLECTIONS_B)

        for c in response.feed_informations:
            assert c.feed_name in names


@pytest.mark.parametrize("https", [True, False])
def test_collections_inboxes(server, https):

    version = 11
    service = get_service(server, 'collection-management-A')

    headers = prepare_headers(version, https)
    request = prepare_request(version)
    response = service.process(headers, request)
    
    for coll in response.collection_informations:
        inboxes = coll.receiving_inbox_services

        assert len(inboxes) == ASSIGNED_INBOX_INSTANCES


@pytest.mark.parametrize("https", [True, False])
@pytest.mark.parametrize("version", [11, 10])
def test_collections_supported_content(server, version, https):

    service = get_service(server, 'collection-management-A')

    headers = prepare_headers(version, https)
    request = prepare_request(version)
    response = service.process(headers, request)

    if version == 11:

        def get_coll(name):
            return next(c for c in response.collection_informations \
                    if c.collection_name == name)

        assert get_coll(COLLECTION_OPEN).collection_type == entities.CollectionEntity.TYPE_SET

    else:
        def get_coll(name):
            return next(c for c in response.feed_informations \
                    if c.feed_name == name)

    assert len(get_coll(COLLECTION_OPEN).supported_contents) == 0

    assert len(get_coll(COLLECTION_ONLY_STIX).supported_contents) == 1
    assert len(get_coll(COLLECTION_STIX_AND_CUSTOM).supported_contents) == 2

    assert not get_coll(COLLECTION_DISABLED).available


@pytest.mark.parametrize("https", [True, False])
def test_collections_volume(server, manager, https):

    version = 11

    service = get_service(server, 'collection-management-A')

    headers = prepare_headers(version, https)
    request = prepare_request(version)

    # querying empty collection
    response = service.process(headers, request)

    collection = next(c for c in response.collection_informations \
            if c.collection_name == COLLECTION_OPEN)

    assert collection.collection_volume == 0

    blocks_amount = 10

    for i in range(blocks_amount):
        persist_content(manager, COLLECTION_OPEN, service.id)

    # querying filled collection
    response = service.process(headers, request)

    collection = next(c for c in response.collection_informations \
            if c.collection_name == COLLECTION_OPEN)

    assert collection.collection_volume == blocks_amount


@pytest.mark.parametrize("https", [True, False])
@pytest.mark.parametrize("version", [11, 10])
def test_collections_supported_content(server, version, https):

    service = get_service(server, 'collection-management-A')

    headers = prepare_headers(version, https)
    request = prepare_request(version)
    response = service.process(headers, request)

    if version == 10:
        coll = response.feed_informations[0]
    else:
        coll = response.collection_informations[0]

    assert len(coll.polling_service_instances) == 2 # 1 poll with 2 protocol bindings


