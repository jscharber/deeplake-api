#!/usr/bin/env python3
"""
Disaster Recovery Management Script

This script provides command-line tools for managing backups and disaster recovery
operations for the DeepLake API service.
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.backup_service import BackupService, BackupType, RestoreOptions
from app.services.deeplake_service import DeepLakeService
from app.services.cache_service import CacheService
from app.config.logging import configure_logging, get_logger


class DisasterRecoveryManager:
    """Disaster recovery management tool."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.backup_service = None
        self.deeplake_service = None
        self.cache_service = None
    
    async def initialize(self):
        """Initialize services."""
        try:
            self.logger.info("Initializing disaster recovery manager")
            
            # Initialize services
            self.cache_service = CacheService()
            await self.cache_service.initialize()
            
            self.deeplake_service = DeepLakeService()
            
            self.backup_service = BackupService(
                self.deeplake_service,
                self.cache_service
            )
            await self.backup_service.initialize()
            
            self.logger.info("Disaster recovery manager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize disaster recovery manager: {e}")
            raise
    
    async def create_backup(
        self,
        backup_type: str = "full",
        tenant_id: Optional[str] = None,
        dataset_ids: Optional[List[str]] = None,
        description: Optional[str] = None
    ) -> str:
        """Create a backup."""
        try:
            backup_type_enum = BackupType(backup_type)
            
            metadata = {}
            if description:
                metadata["description"] = description
            
            self.logger.info(f"Creating {backup_type} backup")
            
            backup_id = await self.backup_service.create_backup(
                backup_type=backup_type_enum,
                tenant_id=tenant_id,
                dataset_ids=dataset_ids,
                metadata=metadata
            )
            
            self.logger.info(f"Backup created successfully: {backup_id}")
            return backup_id
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {e}")
            raise
    
    async def list_backups(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List available backups."""
        try:
            backups = await self.backup_service.list_backups(tenant_id, limit)
            
            backup_list = []
            for backup in backups:
                backup_info = {
                    "backup_id": backup.backup_id,
                    "timestamp": backup.timestamp.isoformat(),
                    "type": backup.type.value,
                    "status": backup.status.value,
                    "tenant_id": backup.tenant_id,
                    "dataset_count": len(backup.dataset_ids),
                    "size_mb": backup.size_bytes / (1024 * 1024),
                    "compressed_size_mb": backup.compressed_size_bytes / (1024 * 1024),
                    "duration_seconds": backup.duration_seconds,
                    "storage_path": backup.storage_path,
                    "error_message": backup.error_message
                }
                backup_list.append(backup_info)
            
            return backup_list
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
            raise
    
    async def restore_backup(
        self,
        backup_id: str,
        target_tenant: Optional[str] = None,
        dataset_mapping: Optional[Dict[str, str]] = None,
        overwrite_existing: bool = False
    ) -> bool:
        """Restore from backup."""
        try:
            self.logger.info(f"Starting restore from backup: {backup_id}")
            
            restore_options = RestoreOptions(
                target_tenant=target_tenant,
                dataset_mapping=dataset_mapping or {},
                overwrite_existing=overwrite_existing,
                verify_integrity=True,
                restore_indexes=True,
                restore_metadata=True
            )
            
            success = await self.backup_service.restore_backup(backup_id, restore_options)
            
            if success:
                self.logger.info(f"Restore completed successfully: {backup_id}")
            else:
                self.logger.error(f"Restore failed: {backup_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to restore backup: {e}")
            raise
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        try:
            success = await self.backup_service.delete_backup(backup_id)
            
            if success:
                self.logger.info(f"Backup deleted successfully: {backup_id}")
            else:
                self.logger.error(f"Failed to delete backup: {backup_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to delete backup: {e}")
            raise
    
    async def cleanup_old_backups(self) -> int:
        """Clean up old backups."""
        try:
            self.logger.info("Starting backup cleanup")
            
            # Get all backups
            backups = await self.backup_service.list_backups(limit=1000)
            
            # Find old backups
            retention_days = self.backup_service.config.retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            old_backups = [
                b for b in backups
                if b.timestamp < cutoff_date and b.status.value == "completed"
            ]
            
            self.logger.info(f"Found {len(old_backups)} old backups to clean up")
            
            # Delete old backups
            deleted_count = 0
            for backup in old_backups:
                try:
                    await self.backup_service.delete_backup(backup.backup_id)
                    deleted_count += 1
                    self.logger.info(f"Deleted old backup: {backup.backup_id}")
                except Exception as e:
                    self.logger.error(f"Failed to delete backup {backup.backup_id}: {e}")
            
            self.logger.info(f"Cleanup completed: {deleted_count} backups deleted")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old backups: {e}")
            raise
    
    async def get_backup_status(self, backup_id: str) -> Optional[Dict[str, Any]]:
        """Get backup status."""
        try:
            backup = await self.backup_service.get_backup_status(backup_id)
            
            if not backup:
                return None
            
            return {
                "backup_id": backup.backup_id,
                "timestamp": backup.timestamp.isoformat(),
                "type": backup.type.value,
                "status": backup.status.value,
                "tenant_id": backup.tenant_id,
                "dataset_ids": backup.dataset_ids,
                "size_bytes": backup.size_bytes,
                "compressed_size_bytes": backup.compressed_size_bytes,
                "duration_seconds": backup.duration_seconds,
                "storage_path": backup.storage_path,
                "error_message": backup.error_message,
                "metadata": backup.metadata
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get backup status: {e}")
            raise
    
    async def export_backup_inventory(self, output_file: str):
        """Export backup inventory to JSON file."""
        try:
            backups = await self.list_backups(limit=1000)
            
            inventory = {
                "exported_at": datetime.now().isoformat(),
                "total_backups": len(backups),
                "backups": backups
            }
            
            with open(output_file, 'w') as f:
                json.dump(inventory, f, indent=2)
            
            self.logger.info(f"Backup inventory exported to: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to export backup inventory: {e}")
            raise
    
    async def test_disaster_recovery(self) -> Dict[str, Any]:
        """Test disaster recovery system."""
        try:
            self.logger.info("Starting disaster recovery test")
            
            test_results = {
                "timestamp": datetime.now().isoformat(),
                "tests": {}
            }
            
            # Test 1: Backup service initialization
            try:
                initialized = self.backup_service._initialized
                test_results["tests"]["service_initialization"] = {
                    "status": "pass" if initialized else "fail",
                    "message": "Backup service initialized" if initialized else "Service not initialized"
                }
            except Exception as e:
                test_results["tests"]["service_initialization"] = {
                    "status": "fail",
                    "message": str(e)
                }
            
            # Test 2: Storage backend connectivity
            try:
                storage_backend = self.backup_service.config.storage_backend.value
                test_results["tests"]["storage_backend"] = {
                    "status": "pass",
                    "message": f"Using {storage_backend} storage backend"
                }
                
                # Test S3 connectivity if configured
                if storage_backend == "s3" and self.backup_service._s3_client:
                    self.backup_service._s3_client.head_bucket(
                        Bucket=self.backup_service.config.s3_bucket
                    )
                    test_results["tests"]["s3_connectivity"] = {
                        "status": "pass",
                        "message": "S3 connectivity verified"
                    }
                    
            except Exception as e:
                test_results["tests"]["storage_backend"] = {
                    "status": "fail",
                    "message": str(e)
                }
            
            # Test 3: Create and restore test backup
            try:
                # This would require test data setup
                test_results["tests"]["backup_restore"] = {
                    "status": "skip",
                    "message": "Test backup/restore requires test data setup"
                }
            except Exception as e:
                test_results["tests"]["backup_restore"] = {
                    "status": "fail",
                    "message": str(e)
                }
            
            # Calculate overall status
            passed_tests = sum(1 for t in test_results["tests"].values() if t["status"] == "pass")
            total_tests = len([t for t in test_results["tests"].values() if t["status"] in ["pass", "fail"]])
            
            test_results["summary"] = {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "overall_status": "pass" if passed_tests == total_tests else "fail"
            }
            
            self.logger.info(f"Disaster recovery test completed: {passed_tests}/{total_tests} tests passed")
            
            return test_results
            
        except Exception as e:
            self.logger.error(f"Disaster recovery test failed: {e}")
            raise
    
    async def close(self):
        """Close services."""
        try:
            if self.backup_service:
                await self.backup_service.close()
            if self.cache_service:
                await self.cache_service.close()
        except Exception as e:
            self.logger.error(f"Error closing services: {e}")


async def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="DeepLake API Disaster Recovery Management Tool"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a backup")
    create_parser.add_argument("--type", choices=["full", "incremental", "snapshot"], 
                              default="full", help="Backup type")
    create_parser.add_argument("--tenant-id", help="Specific tenant to backup")
    create_parser.add_argument("--dataset-ids", nargs="+", help="Specific datasets to backup")
    create_parser.add_argument("--description", help="Backup description")
    
    # List backups command
    list_parser = subparsers.add_parser("list", help="List backups")
    list_parser.add_argument("--tenant-id", help="Filter by tenant ID")
    list_parser.add_argument("--limit", type=int, default=50, help="Maximum number of backups to list")
    list_parser.add_argument("--format", choices=["table", "json"], default="table", 
                            help="Output format")
    
    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_id", help="Backup ID to restore")
    restore_parser.add_argument("--target-tenant", help="Target tenant for restore")
    restore_parser.add_argument("--dataset-mapping", help="Dataset mapping (JSON format)")
    restore_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing datasets")
    
    # Delete backup command
    delete_parser = subparsers.add_parser("delete", help="Delete a backup")
    delete_parser.add_argument("backup_id", help="Backup ID to delete")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get backup status")
    status_parser.add_argument("backup_id", help="Backup ID to check")
    
    # Export inventory command
    export_parser = subparsers.add_parser("export", help="Export backup inventory")
    export_parser.add_argument("output_file", help="Output file path")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test disaster recovery system")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Configure logging
    configure_logging("INFO", "structured")
    
    # Initialize disaster recovery manager
    dr_manager = DisasterRecoveryManager()
    
    try:
        await dr_manager.initialize()
        
        if args.command == "create":
            backup_id = await dr_manager.create_backup(
                backup_type=args.type,
                tenant_id=args.tenant_id,
                dataset_ids=args.dataset_ids,
                description=args.description
            )
            print(f"Backup created: {backup_id}")
            
        elif args.command == "list":
            backups = await dr_manager.list_backups(
                tenant_id=args.tenant_id,
                limit=args.limit
            )
            
            if args.format == "json":
                print(json.dumps(backups, indent=2))
            else:
                # Print table format
                if not backups:
                    print("No backups found")
                else:
                    print(f"{'Backup ID':<20} {'Type':<12} {'Status':<10} {'Tenant':<15} {'Size (MB)':<10} {'Date':<20}")
                    print("-" * 100)
                    for backup in backups:
                        print(f"{backup['backup_id']:<20} {backup['type']:<12} {backup['status']:<10} "
                              f"{backup['tenant_id'] or 'N/A':<15} {backup['size_mb']:<10.2f} "
                              f"{backup['timestamp']:<20}")
            
        elif args.command == "restore":
            dataset_mapping = {}
            if args.dataset_mapping:
                dataset_mapping = json.loads(args.dataset_mapping)
            
            success = await dr_manager.restore_backup(
                backup_id=args.backup_id,
                target_tenant=args.target_tenant,
                dataset_mapping=dataset_mapping,
                overwrite_existing=args.overwrite
            )
            
            if success:
                print("Restore completed successfully")
            else:
                print("Restore failed")
                sys.exit(1)
            
        elif args.command == "delete":
            success = await dr_manager.delete_backup(args.backup_id)
            
            if success:
                print("Backup deleted successfully")
            else:
                print("Delete failed")
                sys.exit(1)
            
        elif args.command == "cleanup":
            deleted_count = await dr_manager.cleanup_old_backups()
            print(f"Cleaned up {deleted_count} old backups")
            
        elif args.command == "status":
            status = await dr_manager.get_backup_status(args.backup_id)
            
            if status:
                print(json.dumps(status, indent=2))
            else:
                print("Backup not found")
                sys.exit(1)
            
        elif args.command == "export":
            await dr_manager.export_backup_inventory(args.output_file)
            print(f"Backup inventory exported to: {args.output_file}")
            
        elif args.command == "test":
            test_results = await dr_manager.test_disaster_recovery()
            print(json.dumps(test_results, indent=2))
            
            if test_results["summary"]["overall_status"] == "fail":
                sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    finally:
        await dr_manager.close()


if __name__ == "__main__":
    asyncio.run(main())