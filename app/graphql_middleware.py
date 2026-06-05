"""
graphql_middleware.py — graphene-django 3.x introspection guard.

graphene-django 3.x has no built-in GRAPHQL_INTROSPECTION setting.
The GRAPHQL_INTROSPECTION = DEBUG line in settings.py has zero effect —
introspection queries still return the full schema in production.

This middleware intercepts every field resolution and raises GraphQLError
for any field that begins with '__' (the GraphQL introspection prefix:
__schema, __type, __typename, etc.) when DEBUG is False.

Registered in settings.py under GRAPHENE['MIDDLEWARE'] — only active in
production; the empty list is used in DEBUG mode so development tooling
(GraphiQL, schema introspection) continues to work normally.
"""
from django.conf import settings
from graphql import GraphQLError


# Only __schema and __type are introspection entry points.
# __typename is a standard GraphQL meta-field that Apollo InMemoryCache
# appends to every query for cache normalisation — blocking it would break
# all queries in production. It must remain allowed.
_INTROSPECTION_FIELDS = frozenset({'__schema', '__type'})


class DisableIntrospectionMiddleware:
    def resolve(self, next_middleware, root, info, **kwargs):
        if not settings.DEBUG and info.field_name in _INTROSPECTION_FIELDS:
            raise GraphQLError(
                'GraphQL introspection is disabled in this environment.'
            )
        return next_middleware(root, info, **kwargs)
