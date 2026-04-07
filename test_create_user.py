#!/usr/bin/env python3
"""
Test script for createUser GraphQL mutation
Requires: superuser or company admin access token
"""

import requests
import json
import sys

# Configuration
BASE_URL = "http://localhost:8000"  # Change if your server is elsewhere
GRAPHQL_ENDPOINT = f"{BASE_URL}/graphql/"
OAUTH_ENDPOINT = f"{BASE_URL}/o/token/"

# OAuth2 credentials (get these from your Django admin or settings)
CLIENT_ID = "test_client_id"  # Update with your actual client ID
CLIENT_SECRET = "test_client_secret"  # Update with your actual client secret

# Test user credentials (must be superuser or company admin)
TEST_USERNAME = "admin"  # Update with your admin username
TEST_PASSWORD = "admin123"  # Update with your admin password


def get_access_token(username, password):
    """Get OAuth2 access token"""
    print(f"🔐 Getting access token for {username}...")
    
    data = {
        'grant_type': 'password',
        'username': username,
        'password': password,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    }
    
    response = requests.post(OAUTH_ENDPOINT, data=data)
    
    if response.status_code != 200:
        print(f"❌ Failed to get token: {response.status_code}")
        print(response.text)
        return None
    
    token_data = response.json()
    access_token = token_data.get('access_token')
    print(f"✅ Got access token: {access_token[:20]}...")
    return access_token


def create_user_via_graphql(access_token, username, email, password, department=None, is_active=True):
    """Create a user via GraphQL mutation"""
    print(f"\n👤 Creating user: {username}...")
    
    # GraphQL mutation
    mutation = """
    mutation CreateUser(
        $username: String!
        $email: String
        $password: String!
        $department: ID
        $isActive: Boolean
    ) {
        createUser(
            username: $username
            email: $email
            password: $password
            department: $department
            isActive: $isActive
        ) {
            ok
            user {
                id
                username
                email
                company {
                    id
                    name
                }
                department {
                    id
                    name
                }
            }
        }
    }
    """
    
    variables = {
        "username": username,
        "email": email,
        "password": password,
        "isActive": is_active
    }
    
    if department:
        variables["department"] = department
    
    payload = {
        "query": mutation,
        "variables": variables
    }
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Request failed: {response.status_code}")
        print(response.text)
        return None
    
    result = response.json()
    
    if 'errors' in result:
        print(f"❌ GraphQL errors:")
        for error in result['errors']:
            print(f"  - {error.get('message')}")
        return None
    
    data = result.get('data', {}).get('createUser', {})
    
    if data.get('ok'):
        print(f"✅ User created successfully!")
        user = data.get('user', {})
        print(f"   ID: {user.get('id')}")
        print(f"   Username: {user.get('username')}")
        print(f"   Email: {user.get('email')}")
        if user.get('company'):
            print(f"   Company: {user.get('company', {}).get('name')}")
        if user.get('department'):
            print(f"   Department: {user.get('department', {}).get('name')}")
        return user
    else:
        print(f"❌ Failed to create user")
        return None


def list_users(access_token):
    """List users to verify creation"""
    print(f"\n📋 Listing users...")
    
    query = """
    query {
        users {
            id
            username
            email
            company {
                id
                name
            }
            department {
                id
                name
            }
        }
    }
    """
    
    payload = {"query": query}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        users = result.get('data', {}).get('users', [])
        print(f"✅ Found {len(users)} users:")
        for user in users:
            print(f"   - {user.get('username')} ({user.get('email')})")
        return users
    else:
        print(f"❌ Failed to list users: {response.status_code}")
        return []


def main():
    """Main test function"""
    print("=" * 60)
    print("🧪 Testing createUser GraphQL Mutation")
    print("=" * 60)
    
    # Step 1: Get access token
    access_token = get_access_token(TEST_USERNAME, TEST_PASSWORD)
    if not access_token:
        print("\n❌ Cannot proceed without access token")
        sys.exit(1)
    
    # Step 2: List existing users
    existing_users = list_users(access_token)
    
    # Step 3: Create a test user
    test_username = f"testuser_{hash('test') % 10000}"  # Unique username
    test_email = f"{test_username}@example.com"
    test_password = "TestPassword123!"
    
    new_user = create_user_via_graphql(
        access_token=access_token,
        username=test_username,
        email=test_email,
        password=test_password,
        is_active=True
    )
    
    if not new_user:
        print("\n❌ Test failed: Could not create user")
        sys.exit(1)
    
    # Step 4: Verify user appears in list
    print("\n🔍 Verifying user was created...")
    updated_users = list_users(access_token)
    
    user_ids = [u.get('id') for u in updated_users]
    if new_user.get('id') in user_ids:
        print(f"✅ User {test_username} successfully created and verified!")
    else:
        print(f"⚠️  User created but not found in list (may be a permission issue)")
    
    print("\n" + "=" * 60)
    print("✅ Test completed!")
    print("=" * 60)
    print(f"\n📝 Test user credentials:")
    print(f"   Username: {test_username}")
    print(f"   Email: {test_email}")
    print(f"   Password: {test_password}")
    print(f"\n💡 You can now test login with these credentials")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

