#!/usr/bin/env python3
"""
Cleanup script to remove all datasets from the Deep Lake Vector Service.
Run this to clean up test datasets or reset the service state.
"""

import requests
import sys
import os

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY")

if not API_KEY:
    print("ERROR: API_KEY environment variable is required")
    print("Usage: API_KEY=your_api_key python scripts/cleanup_datasets.py")
    sys.exit(1)

def cleanup_all_datasets():
    """Clean up all existing datasets."""
    print("🧹 Deep Lake Vector Service - Dataset Cleanup")
    print("=" * 50)
    
    headers = {
        "Authorization": f"ApiKey {API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        # Test service health first
        print("🔍 Checking service health...")
        health_response = requests.get(f"{BASE_URL}/api/v1/health", timeout=10)
        if health_response.status_code != 200:
            print(f"❌ Service is not healthy: {health_response.status_code}")
            return False
        
        print("✅ Service is healthy")
        
        # Get list of existing datasets
        print("\n📋 Fetching existing datasets...")
        response = requests.get(
            f"{BASE_URL}/api/v1/datasets/",
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to list datasets: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        datasets = response.json()
        total_datasets = len(datasets)
        
        if total_datasets == 0:
            print("✅ No datasets found - already clean!")
            return True
        
        print(f"Found {total_datasets} datasets to delete:")
        for dataset in datasets:
            print(f"  - {dataset.get('name', 'unknown')} (ID: {dataset.get('id', 'unknown')})")
        
        # Ask for confirmation
        confirm = input(f"\n⚠️  Delete ALL {total_datasets} datasets? (y/N): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("❌ Cleanup cancelled by user")
            return False
        
        # Delete each dataset
        print(f"\n🗑️  Deleting {total_datasets} datasets...")
        deleted_count = 0
        failed_count = 0
        
        for i, dataset in enumerate(datasets, 1):
            dataset_id = dataset.get('id')
            dataset_name = dataset.get('name', 'unknown')
            
            if not dataset_id:
                print(f"  [{i}/{total_datasets}] ❌ Skipping dataset with missing ID")
                failed_count += 1
                continue
            
            print(f"  [{i}/{total_datasets}] Deleting: {dataset_name}...")
            
            delete_response = requests.delete(
                f"{BASE_URL}/api/v1/datasets/{dataset_id}",
                headers=headers,
                timeout=30
            )
            
            if delete_response.status_code == 200:
                deleted_count += 1
                print(f"  [{i}/{total_datasets}] ✅ Deleted: {dataset_name}")
            else:
                failed_count += 1
                print(f"  [{i}/{total_datasets}] ❌ Failed to delete {dataset_name}: {delete_response.status_code}")
                print(f"      Error: {delete_response.text}")
        
        # Summary
        print(f"\n📊 Cleanup Summary:")
        print(f"  Total datasets: {total_datasets}")
        print(f"  Successfully deleted: {deleted_count}")
        print(f"  Failed to delete: {failed_count}")
        
        if failed_count == 0:
            print("🎉 All datasets cleaned up successfully!")
            return True
        else:
            print(f"⚠️  {failed_count} datasets could not be deleted")
            return False
        
    except Exception as e:
        print(f"❌ Cleanup failed with error: {e}")
        return False

def main():
    """Main cleanup function."""
    success = cleanup_all_datasets()
    
    if success:
        print("\n✅ Cleanup completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Cleanup completed with errors!")
        sys.exit(1)

if __name__ == "__main__":
    main()