// ── Apollo Client with automatic token refresh ────────────────────────────────
//
// When the server returns a 401 (expired access token) the error link
// intercepts the response, calls refreshAccessToken(), then retries the
// original operation exactly once with the new token.
//
// If the refresh itself fails (refresh token expired / revoked) the user is
// redirected to /login via logout().
//
// The auth link always attaches the current access token from localStorage
// so the refreshed token is automatically used on the retry.

import {
    ApolloClient,
    InMemoryCache,
    createHttpLink,
    from,
} from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { onError } from '@apollo/client/link/error';
import { getAccessToken, refreshAccessToken, logout } from './api';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

// ── 1. HTTP link ──────────────────────────────────────────────────────────────
const httpLink = createHttpLink({
    uri: `${API_BASE}/graphql/`,
});

// ── 2. Auth link — attach Bearer token to every request ──────────────────────
const authLink = setContext((_, { headers }) => {
    const token = getAccessToken();
    return {
        headers: {
            ...headers,
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
    };
});

// ── 3. Error link — intercept 401 and attempt token refresh ──────────────────
// `forward(operation)` retries the same operation; the auth link above will
// re-read the (now refreshed) token from localStorage on the retry.
//
// The `_refreshing` flag prevents an infinite loop if the refresh itself
// also returns 401 (shouldn't happen, but belt-and-suspenders).

let _refreshing = false;

const errorLink = onError(({ networkError, operation, forward }) => {
    const is401 =
        networkError?.statusCode === 401 ||
        // GraphQL over HTTP sometimes surfaces auth errors as network errors
        // with a response body; check both forms.
        (networkError?.result?.errors || []).some(
            (e) => e?.extensions?.code === 'UNAUTHENTICATED',
        );

    if (is401 && !_refreshing) {
        _refreshing = true;

        // Return an Observable so Apollo can await the async refresh and
        // then replay the operation.
        return new Promise((resolve, reject) => {
            refreshAccessToken()
                .then(() => {
                    _refreshing = false;
                    resolve(forward(operation)); // retry with new token
                })
                .catch((err) => {
                    _refreshing = false;
                    console.error('Token refresh failed — logging out:', err.message);
                    logout();       // clears storage + redirects to /login
                    reject(err);
                });
        });
    }
});

// ── 4. Compose the link chain: error → auth → http ───────────────────────────
export const client = new ApolloClient({
    link: from([errorLink, authLink, httpLink]),
    cache: new InMemoryCache(),
    defaultOptions: {
        watchQuery: {
            // Return cached data immediately, but always re-validate in the background
            fetchPolicy: 'cache-and-network',
            errorPolicy: 'all',
        },
        query: {
            errorPolicy: 'all',
        },
    },
});
