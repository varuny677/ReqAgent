"""
Quick test script to verify Firestore connection.
Run this to test if Firestore is working before starting the app.
"""

import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from services import FirestoreService

def test_firestore():
    """Test Firestore connection."""
    print("Testing Firestore connection...")

    try:
        credentials_path = os.path.join(
            os.path.dirname(__file__), "reqagent-c12e92ab61f5.json"
        )

        print(f"Using credentials: {credentials_path}")
        print(f"Credentials exist: {os.path.exists(credentials_path)}")

        # Initialize service
        print("\nInitializing FirestoreService...")
        service = FirestoreService(credentials_path=credentials_path)
        print("[OK] FirestoreService initialized successfully!")

        # Test listing sessions
        print("\nTesting list_sessions...")
        sessions = service.list_sessions(limit=5)
        print(f"✅ Found {len(sessions)} sessions")

        if sessions:
            print("\nFirst session:")
            for key, value in sessions[0].items():
                print(f"  {key}: {value}")
        else:
            print("No sessions found (this is normal for a fresh database)")

        # Test creating a session
        print("\nTesting create_session...")
        test_session_id = "test-session-123"
        service.create_session(
            session_id=test_session_id,
            title="Test Session",
            preview="This is a test"
        )
        print(f"✅ Created test session: {test_session_id}")

        # Test retrieving the session
        print("\nTesting get_session...")
        session = service.get_session(test_session_id)
        print(f"✅ Retrieved session: {session['title']}")

        # Clean up test session
        print("\nCleaning up test session...")
        service.delete_session(test_session_id)
        print("✅ Deleted test session")

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED! Firestore is working correctly.")
        print("="*50)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_firestore()
