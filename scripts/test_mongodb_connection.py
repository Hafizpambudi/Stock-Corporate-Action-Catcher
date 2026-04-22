#!/usr/bin/env python
"""Test MongoDB connection with various TLS configurations."""

from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from urllib.parse import quote_plus
import sys


def load_env():
    """Load MONGO_URI from .env."""
    from pathlib import Path

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                if line.strip().startswith("MONGO_URI="):
                    return line.split("=", 1)[1].strip().strip('"')
    return None


def test_connection(uri: str, tls_options: dict, description: str) -> bool:
    """Test connection with given TLS options."""
    print(f"\n--- Testing: {description} ---")
    print(f"TLS options: {tls_options}")

    try:
        client = MongoClient(uri, **tls_options, serverSelectionTimeoutMS=10000)
        # Try to ping
        client.admin.command("ping")
        print(f"✓ SUCCESS!")
        client.close()
        return True
    except ServerSelectionTimeoutError as e:
        print(f"✗ ServerSelectionTimeoutError: {str(e)[:100]}...")
        return False
    except ConnectionFailure as e:
        print(f"✗ ConnectionFailure: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        return False


def main():
    original_uri = load_env()

    if not original_uri:
        print("MONGO_URI not found in .env")
        sys.exit(1)

    print(f"Original URI: {original_uri[:50]}...")

    # Test variations
    tests = [
        # Original as-is
        ({}, "No TLS options (baseline)"),
        # TLS v1.2 only
        (
            {"tls": True, "tlsAllowInvalidCertificates": False},
            "tls=True (default TLS 1.2)",
        ),
        # TLS withrelaxed certs (for testing)
        (
            {"tls": True, "tlsAllowInvalidCertificates": True, "tlsInsecure": False},
            "tls with relaxed certs",
        ),
        # TLS 1.2 explicit
        (
            {
                "tls": True,
                "tlsMinVersion": "TLSv1.2",
                "tlsAllowInvalidCertificates": False,
            },
            "TLSv1.2 explicit",
        ),
        # SSL instead of TLS (older compatibility)
        ({"ssl": True, "ssl_cert_reqs": "CERT_NONE"}, "ssl=True (legacy)"),
    ]

    success = False
    for opts, desc in tests:
        if test_connection(original_uri, opts, desc):
            success = True
            break

    if not success:
        print("\n" + "=" * 60)
        print("All connection attempts failed!")
        print("\nPossible causes:")
        print("1. MongoDB Atlas cluster is down or paused")
        print("2. Network/firewall blocking port 27017")
        print("3. IP whitelist not configured in Atlas")
        print("4. Credentials are incorrect")
        print("\nCheck your MongoDB Atlas:")
        print("- Login to https://cloud.mongodb.com")
        print("- Check Network Access whitelist your IP")
        print("- Check Database API access (MongoDB recommends 'API Version 1')")
        print("- Check cluster status (free tier may auto-pause)")


if __name__ == "__main__":
    main()
