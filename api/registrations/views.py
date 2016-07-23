from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import ValidationError, NotFound
from framework.auth.oauth_scopes import CoreScopes

from website.project.model import Q, Node
from api.base import permissions as base_permissions
from api.base.views import JSONAPIBaseView

from api.base.serializers import HideIfWithdrawal
from api.nodes.permissions import ReadOnlyIfRegistration
from api.nodes.permissions import ContributorOrPublicForRelationshipPointers
from api.base.serializers import LinkedNodesRelationshipSerializer
from api.base.parsers import JSONAPIRelationshipParser
from api.base.parsers import JSONAPIRelationshipParserForRegularJSON
from api.base.utils import get_user_auth

from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationDetailSerializer,
    RegistrationContributorsSerializer,
    RegistrationProviderSerializer
)

from api.nodes.views import (
    NodeMixin, ODMFilterMixin, NodeContributorsList, NodeRegistrationsList,
    NodeChildrenList, NodeCommentsList, NodeProvidersList, NodeLinksList,
    NodeContributorDetail, NodeFilesList, NodeLinksDetail, NodeFileDetail,
    NodeAlternativeCitationsList, NodeAlternativeCitationDetail, NodeLogList,
    NodeInstitutionsList, WaterButlerMixin, NodeForksList, NodeWikiList,
    LinkedNodesList
)

from api.registrations.serializers import RegistrationNodeLinksSerializer, RegistrationFileSerializer

from api.nodes.permissions import (
    AdminOrPublic
)
from api.base.utils import get_object_or_error

class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current registration based on the
    current URL. By default, fetches the current registration based on the node_id kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            display_name='node'
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection or not node.is_registration:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class RegistrationList(JSONAPIBaseView, generics.ListAPIView, ODMFilterMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view is a list of all current registrations for which a user
    has access.  A withdrawn registration will display a limited subset of information, namely, title, description,
    date_created, registration, withdrawn, date_registered, withdrawal_justification, and registration supplement. All
    other fields will be displayed as null. Additionally, the only relationships permitted to be accessed for a withdrawn
    registration are the contributors - other relationships will return a 403.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registrations's detail view are not necessary.  Unregistered nodes cannot be accessed through this endpoint.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'registrations'
    view_name = 'registration-list'

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query

    def is_blacklisted(self, query):
        for query_param in query.nodes:
            field_name = getattr(query_param, 'attribute', None)
            if not field_name:
                continue
            field = self.serializer_class._declared_fields.get(field_name)
            if isinstance(field, HideIfWithdrawal):
                return True
        return False

    # overrides ListAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        blacklisted = self.is_blacklisted(query)
        nodes = Node.find(query)
        # If attempting to filter on a blacklisted field, exclude withdrawals.
        if blacklisted:
            non_withdrawn_list = [node._id for node in nodes if not node.is_retracted]
            non_withdrawn_nodes = Node.find(Q('_id', 'in', non_withdrawn_list))
            return non_withdrawn_nodes
        return nodes


class RegistrationDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView, RegistrationMixin, WaterButlerMixin):
    """Node Registrations.

    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registration's detail view are not necessary. A withdrawn registration will display a limited subset of information,
    namely, title, description, date_created, registration, withdrawn, date_registered, withdrawal_justification, and
    registration supplement. All other fields will be displayed as null. Additionally, the only relationships permitted
    to be accessed for a withdrawn registration are the contributors - other relationships will return a 403.

    ##Registration Attributes

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        date_created                    iso8601 timestamp  timestamp that the node was created
        date_modified                   iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": {
                           "type": "registrations",   # required
                           "id":   {registration_id}, # required
                           "attributes": {
                             "public": true           # required
                           }
                         }
                       }
        Success:       200 OK + node representation

    To turn a registration from private to public, issue either a PUT or a PATCH request against the `/links/self` URL.
    Registrations can only be turned from private to public, not vice versa.  The "public" field is the only field that can
    be modified on a registration and you must have admin permission to do so.

    ##Relationships

    ###Registered from

    The registration is branched from this node.

    ###Registered by

    The registration was initiated by this user.

    ###Other Relationships

    See documentation on registered_from detail view.  A registration has many of the same properties as a node.

    ##Links

        self:  the canonical api endpoint of this registration
        html:  this registration's page on the OSF website

    #This Request/Response

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        AdminOrPublic,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationDetailSerializer
    view_category = 'registrations'
    view_name = 'registration-detail'

    # overrides RetrieveAPIView
    def get_object(self):
        registration = self.get_node()
        if not registration.is_registration:
            raise ValidationError('This is not a registration.')
        return registration


class RegistrationContributorsList(NodeContributorsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-contributors'

    def get_serializer_class(self):
        return RegistrationContributorsSerializer


class RegistrationContributorDetail(NodeContributorDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-contributor-detail'
    serializer_class = RegistrationContributorsSerializer


class RegistrationChildrenList(NodeChildrenList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-children'
    serializer_class = RegistrationSerializer

    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_registration', 'eq', True)
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (permission_query | Q('contributors', 'eq', user._id))

        query = base_query & permission_query
        return query

class RegistrationForksList(NodeForksList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-forks'

class RegistrationCommentsList(NodeCommentsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-comments'


class RegistrationLogList(NodeLogList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-logs'


class RegistrationProvidersList(NodeProvidersList, RegistrationMixin):
    serializer_class = RegistrationProviderSerializer

    view_category = 'registrations'
    view_name = 'registration-providers'


class RegistrationNodeLinksList(NodeLinksList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-pointers'
    serializer_class = RegistrationNodeLinksSerializer


class RegistrationNodeLinksDetail(NodeLinksDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-pointer-detail'
    serializer_class = RegistrationNodeLinksSerializer


class RegistrationRegistrationsList(NodeRegistrationsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-registrations'


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-files'
    serializer_class = RegistrationFileSerializer


class RegistrationFileDetail(NodeFileDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-file-detail'
    serializer_class = RegistrationFileSerializer


class RegistrationAlternativeCitationsList(NodeAlternativeCitationsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-alternative-citations'


class RegistrationAlternativeCitationDetail(NodeAlternativeCitationDetail, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-alternative-citation-detail'


class RegistrationInstitutionsList(NodeInstitutionsList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-institutions'


class RegistrationWikiList(NodeWikiList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'registration-wikis'


class RegistrationLinkedNodesList(LinkedNodesList, RegistrationMixin):
    view_category = 'registrations'
    view_name = 'linked-nodes'


class RegistrationLinkedNodesRelationship(JSONAPIBaseView, generics.RetrieveAPIView, RegistrationMixin):
    """ Relationship Endpoint for Nodes -> Linked Node relationships

    Used to retrieve the ids of the linked nodes attached to this collection. For each id, there
    exists a node link that contains that node.

    ##Actions

    """
    view_category = 'registrations'
    view_name = 'node-pointer-relationship'

    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = LinkedNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    def get_object(self):
        node = self.get_node(check_object_permissions=False)
        auth = get_user_auth(self.request)
        obj = {'data': [
            pointer for pointer in
            node.nodes_pointer
            if not pointer.node.is_deleted and not pointer.node.is_collection and
            pointer.node.can_view(auth)
        ], 'self': node}
        self.check_object_permissions(self.request, obj)
        return obj
