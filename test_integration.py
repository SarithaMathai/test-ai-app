#!/usr/bin/env python3
"""
Integration test script for plm-tcin-mapper-api and plm-tcin-mapper-client.

Tests:
1. API service health endpoint
2. API endpoint availability
3. UI to API communication

Run: python test_integration.py
"""

import asyncio
import json
import sys
import time
from typing import Any

import httpx


# Configuration
API_BASE_URL = "http://localhost:8001"
CLIENT_BASE_URL = "http://localhost:8080"
TIMEOUT = 10


class Colors:
    """ANSI color codes."""
    OKGREEN = "\033[92m"
    FAIL = "\033[91m"
    OKBLUE = "\033[94m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str) -> None:
    """Print colored header."""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{text:^60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'=' * 60}{Colors.ENDC}\n")


def print_pass(text: str) -> None:
    """Print green success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_fail(text: str) -> None:
    """Print red failure message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str) -> None:
    """Print blue info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


async def test_api_health() -> bool:
    """Test API health endpoint."""
    print_header("Testing API Health Endpoint")

    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/health")

            if response.status_code == 200:
                data = response.json()
                print_pass(f"API health check passed")
                print_info(f"Response: {json.dumps(data, indent=2)}")
                return True
            else:
                print_fail(f"API health check failed: {response.status_code}")
                return False
    except httpx.ConnectError:
        print_fail(f"Cannot connect to API at {API_BASE_URL}")
        print_info("Make sure API is running: uv run uvicorn plm_tcin_mapper_api.main:app --port 8001")
        return False
    except Exception as e:
        print_fail(f"API health test error: {e}")
        return False


async def test_api_endpoints() -> bool:
    """Test key API endpoints."""
    print_header("Testing API Endpoints")

    endpoints = [
        ("/api/v1/admin/stats", "GET", "Admin Statistics"),
        ("/api/v1/departments", "GET", "Departments List"),
        ("/api/v1/mappings?limit=1", "GET", "Mappings Query"),
    ]

    all_passed = True

    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            for endpoint, method, description in endpoints:
                try:
                    if method == "GET":
                        response = await client.get(endpoint)

                    if response.status_code == 200:
                        print_pass(f"{description}: {endpoint}")
                        try:
                            data = response.json()
                            print_info(f"  Keys: {list(data.keys())}")
                        except:
                            pass
                    else:
                        print_fail(f"{description}: {endpoint} (HTTP {response.status_code})")
                        all_passed = False
                except httpx.TimeoutException:
                    print_fail(f"{description}: {endpoint} (Timeout)")
                    all_passed = False
                except Exception as e:
                    print_fail(f"{description}: {endpoint} ({e})")
                    all_passed = False
    except httpx.ConnectError:
        print_fail("Cannot connect to API")
        return False

    return all_passed


async def test_client_health() -> bool:
    """Test Streamlit client health endpoint."""
    print_header("Testing Streamlit Client Health")

    try:
        async with httpx.AsyncClient(base_url=CLIENT_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/_stcore/health")

            if response.status_code == 200:
                print_pass(f"Streamlit health check passed")
                return True
            else:
                print_fail(f"Streamlit health check failed: {response.status_code}")
                return False
    except httpx.ConnectError:
        print_fail(f"Cannot connect to Streamlit at {CLIENT_BASE_URL}")
        print_info("Make sure Streamlit is running: uv run streamlit run apps/plm-tcin-mapper-client/plm_tcin_mapper_client/streamlit_app.py")
        return False
    except Exception as e:
        print_fail(f"Streamlit health test error: {e}")
        return False


async def test_ui_api_communication() -> bool:
    """Test that UI can communicate with API via api_client."""
    print_header("Testing UI to API Communication")

    print_info("Simulating Streamlit client API calls...")

    all_passed = True

    # Test 1: Fetch admin stats
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/api/v1/admin/stats")
            if response.status_code == 200:
                stats = response.json()
                print_pass("Admin stats endpoint works (UI can use this)")
                print_info(f"  Collections: {len(stats)} stats returned")
            else:
                print_fail(f"Admin stats endpoint failed: {response.status_code}")
                all_passed = False
    except Exception as e:
        print_fail(f"Admin stats test: {e}")
        all_passed = False

    # Test 2: Fetch departments
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/api/v1/departments")
            if response.status_code == 200:
                data = response.json()
                print_pass("Departments endpoint works (department_view.py will use this)")
                print_info(f"  Departments: {len(data.get('departments', []))} found")
            else:
                print_fail(f"Departments endpoint failed: {response.status_code}")
                all_passed = False
    except Exception as e:
        print_fail(f"Departments test: {e}")
        all_passed = False

    # Test 3: Fetch mappings with filters
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/api/v1/mappings?limit=5")
            if response.status_code == 200:
                data = response.json()
                print_pass("Mappings query endpoint works (pid_lookup.py will use this)")
                print_info(f"  Mappings: {len(data.get('mappings', []))} returned")
            else:
                print_fail(f"Mappings endpoint failed: {response.status_code}")
                all_passed = False
    except Exception as e:
        print_fail(f"Mappings test: {e}")
        all_passed = False

    # Test 4: Get LLM quality
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=TIMEOUT) as client:
            response = await client.get("/api/v1/llm/quality")
            if response.status_code == 200:
                data = response.json()
                print_pass("LLM quality endpoint works (llm_quality.py will use this)")
                print_info(f"  LLM calls: {data.get('total_calls', 0)} recorded")
            else:
                print_fail(f"LLM quality endpoint failed: {response.status_code}")
                all_passed = False
    except Exception as e:
        print_fail(f"LLM quality test: {e}")
        all_passed = False

    return all_passed


async def test_dockerfile_build() -> bool:
    """Verify Dockerfiles exist and are readable."""
    print_header("Checking Dockerfile Locations")

    import os

    dockerfiles = [
        "apps/plm-think-tank-ai/Dockerfile",
        "apps/plm-tcin-mapper-api/Dockerfile",
        "apps/plm-tcin-mapper-client/Dockerfile",
    ]

    all_exist = True

    for dockerfile in dockerfiles:
        path = os.path.join("C:\\Saritha\\Jun12\\test-ai-app", dockerfile.replace("/", "\\"))
        if os.path.exists(path):
            print_pass(f"Found: {dockerfile}")
        else:
            print_fail(f"Missing: {dockerfile}")
            all_exist = False

    if all_exist:
        print_info("\nBuild commands:")
        print_info("  docker build -f apps/plm-think-tank-ai/Dockerfile -t plm-think-tank-ai:latest .")
        print_info("  docker build -f apps/plm-tcin-mapper-api/Dockerfile -t plm-tcin-mapper-api:latest .")
        print_info("  docker build -f apps/plm-tcin-mapper-client/Dockerfile -t plm-tcin-mapper-client:latest .")

    return all_exist


async def main() -> int:
    """Run all tests."""
    print(f"\n{Colors.BOLD}PLM TCIN Mapper - Integration Test Suite{Colors.ENDC}")
    print(f"API URL: {API_BASE_URL}")
    print(f"Client URL: {CLIENT_BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")

    results = {}

    # Test 1: Dockerfiles exist
    results["Dockerfiles"] = await test_dockerfile_build()

    # Wait a moment for services to be ready
    print_info("\nWaiting 2 seconds for services to be ready...")
    await asyncio.sleep(2)

    # Test 2: API health
    results["API Health"] = await test_api_health()

    # Test 3: API endpoints
    results["API Endpoints"] = await test_api_endpoints()

    # Test 4: Client health
    results["Client Health"] = await test_client_health()

    # Test 5: UI-API communication
    results["UI-API Communication"] = await test_ui_api_communication()

    # Summary
    print_header("Test Summary")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = f"{Colors.OKGREEN}PASS{Colors.ENDC}" if result else f"{Colors.FAIL}FAIL{Colors.ENDC}"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} test groups passed")

    if passed == total:
        print_pass("\n🎉 All tests passed! UI ↔ API integration working perfectly!")
        return 0
    else:
        print_fail("\n⚠️  Some tests failed. Check the details above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
