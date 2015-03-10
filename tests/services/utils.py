from libtaxii import messages_10 as tm10
from libtaxii import messages_11 as tm11

from opentaxii.taxii.http import *
from opentaxii.taxii.utils import get_utc_now

from fixtures import *

def as_tm(version):
    if version == 10:
        return tm10
    elif version == 11:
        return tm11
    else:
        raise ValueError('Unknown TAXII message version: %s' % version)


def get_service(server, service_id):
    for service in server.services:
        if service.id == service_id:
            return service


def prepare_headers(version, https):
    headers = dict()
    if version == 10:
        if https:
            headers.update(TAXII_10_HTTPS_Headers)
        else:
            headers.update(TAXII_10_HTTP_Headers)
    elif version == 11:
        if https:
            headers.update(TAXII_11_HTTPS_Headers)
        else:
            headers.update(TAXII_11_HTTP_Headers)
    else:
        raise ValueError('Unknown TAXII message version: %s' % version)

    headers[HTTP_ACCEPT] = HTTP_CONTENT_XML
    return headers


def persist_content(manager, collection_name, service_id, timestamp=None,
        binding=CB_STIX_XML_111, subtypes=[]):

    timestamp = timestamp or get_utc_now()

    content_binding = entities.ContentBindingEntity(
        binding = binding,
        subtypes = subtypes
    )

    content = entities.ContentBlockEntity(content=CONTENT, timestamp_label=timestamp,
            message=MESSAGE, content_binding=content_binding)

    collection = manager.get_collection(collection_name, service_id)
    content = manager.create_content(content, collections=[collection])

    return content


def prepare_subscription_request(collection, action, version, subscription_id=None, params=None):

    data = dict(
        action = action,
        message_id = MESSAGE_ID,
        subscription_id = subscription_id,
    )

    mod = as_tm(version)

    if version == 11:
        cls = mod.ManageCollectionSubscriptionRequest
        data.update(dict(
            collection_name = collection,
            subscription_parameters = mod.SubscriptionParameters(**params) if params else None
        ))
    else:
        cls = mod.ManageFeedSubscriptionRequest
        data['feed_name'] = collection

    return cls(**data)
