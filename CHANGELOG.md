<!--
SPDX-FileCopyrightText: 2023 Digg - Agency for Digital Government

SPDX-License-Identifier: CC0-1.0
-->

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.1] - 2025-07-16

### Security
- **BREAKING**: Removed hardcoded API keys from examples and scripts
  - Eliminated hardcoded development API key `dev-12345-abcdef-67890-ghijkl`
  - Updated all example scripts to use environment variables
  - Added API key generation scripts for secure key creation
- **BREAKING**: Replaced hardcoded JWT secret with environment variable requirement
  - JWT_SECRET_KEY now required via environment variable
  - Service will not start without proper JWT_SECRET_KEY configuration
  - Added validation to ensure JWT secret is at least 32 characters

### Added
- **API Documentation**: Documentation endpoints now always available
  - `/docs` (Swagger UI) accessible in all environments
  - `/redoc` (ReDoc) accessible in all environments
  - Removed debug-only restriction on documentation endpoints
- **Configuration Management**: Enhanced environment variable handling
  - Added comprehensive `.env` file support for uv run
  - Improved Pydantic settings schema for better validation
  - Added support for nested configuration classes
- **Security Tools**: API key generation and management
  - `generate_api_key_quick.py` - Non-interactive API key generator
  - `bashrc_exports.sh` - Environment variable configuration template
  - Secure key generation using `secrets.token_urlsafe(32)`

### Changed
- **Service Startup**: Fixed uv run compatibility
  - Corrected AuthConfig environment variable mapping
  - Simplified .env file to match settings schema
  - Added `extra = "ignore"` to Settings class for flexibility
- **Documentation**: Updated all examples to use environment variables
  - cURL examples now reference `$API_KEY` environment variable
  - Python client examples use environment-based configuration
  - Docker and deployment examples updated with secure practices

### Fixed
- **Authentication**: Resolved Pydantic validation errors
  - Fixed JWT_SECRET_KEY environment variable loading
  - Corrected nested configuration class initialization
  - Resolved service startup issues with `uv run`
- **Documentation Access**: API documentation now properly accessible
  - Fixed conditional logic that prevented docs access
  - Documentation endpoints work regardless of debug mode
  - Improved root endpoint to display documentation URLs

### Removed
- **Security Risk**: Eliminated all hardcoded credentials
  - Removed hardcoded API key `dev-12345-abcdef-67890-ghijkl`
  - Removed hardcoded JWT secret from configuration
  - Cleaned up test files to use environment variables only
